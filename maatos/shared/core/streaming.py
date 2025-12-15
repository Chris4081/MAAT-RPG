# -*- coding: utf-8 -*-
"""
MAAT-KI Streaming Engine — v4.0 Router Edition
----------------------------------------------
• Regenbogen nur beim allerersten Prompt (Modell-Load)
• SayTTS / Plugin-System voll unterstützt
• ESC-Notaus funktioniert
• Backend-Router Streaming (llama.cpp & MLX)
"""

import sys
import time
import threading
import tty
import termios
import select
from colorama import Fore, Style

from .backend_router import stream_chat as backend_stream_chat


# =====================================================================
# 0) GLOBAL — Regenbogen nur beim ersten Stream überhaupt
# =====================================================================
FIRST_RUN_DONE = False


# =====================================================================
# 1) Non-blocking Keyboard Check (für ESC)
# =====================================================================

def key_pressed():
    dr, _, _ = select.select([sys.stdin], [], [], 0)
    return bool(dr)

def read_key():
    return sys.stdin.read(1)


# =====================================================================
# 2) Regenbogen-Anzeige
# =====================================================================

RAINBOW = [
    "\033[38;5;196m",
    "\033[38;5;202m",
    "\033[38;5;226m",
    "\033[38;5;46m",
    "\033[38;5;51m",
    "\033[38;5;21m",
    "\033[38;5;93m",
]
RESET = "\033[0m"

def rainbow_progress(stop_event: threading.Event):
    """Animierter Ladebalken."""
    idx = 0
    bar_len = 22

    while not stop_event.is_set():
        bar = ""
        for i in range(bar_len):
            bar += RAINBOW[(idx + i) % len(RAINBOW)] + "█" + RESET

        sys.stdout.write(f"\r⏳ Lade Modell… {bar}")
        sys.stdout.flush()
        idx = (idx + 1) % len(RAINBOW)
        time.sleep(0.10)

    # Zeile löschen
    sys.stdout.write("\r" + " " * 200 + "\r")
    sys.stdout.flush()


# =====================================================================
# 3) Plugin Wrapper
# =====================================================================

class StreamingPluginInterface:
    def __init__(self, plugins=None):
        self.plugins = plugins or []

    def call_before(self, text):
        for p in self.plugins:
            fn = getattr(p, "before_stream", None)
            if callable(fn):
                try:
                    fn(text)
                except Exception as e:
                    print(Fore.RED + f"[PLUGIN before_stream ERROR] {e}" + Style.RESET_ALL)

    def call_token(self, token):
        for p in self.plugins:
            fn = getattr(p, "on_token", None)
            if callable(fn):
                try:
                    fn(token)
                except Exception as e:
                    print(Fore.RED + f"[PLUGIN on_token ERROR] {e}" + Style.RESET_ALL)

    def call_after(self, text):
        for p in self.plugins:
            fn = getattr(p, "after_stream", None)
            if callable(fn):
                try:
                    fn(text)
                except Exception as e:
                    print(Fore.RED + f"[PLUGIN after_stream ERROR] {e}" + Style.RESET_ALL)


# =====================================================================
# 4) Backend-Router Streaming (llama.cpp & MLX)
# =====================================================================
def _router_stream(llm, messages, perf, plugin_api):
    """
    Einheitliches Streaming über backend_router.stream_chat.
    Funktioniert für:
      • llama.cpp-Backend (llama_backend)
      • MLX-Backend (mlx_backend)
    """
    global FIRST_RUN_DONE

    full = ""
    plugin_api.call_before("")

    stop_event = threading.Event()
    if not FIRST_RUN_DONE:
        threading.Thread(
            target=rainbow_progress, args=(stop_event,), daemon=True
        ).start()

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setcbreak(fd)

    try:
        # Router → liefert Generator mit String-Chunks
        stream = backend_stream_chat(llm, messages, perf=perf)

        got_first_token = False
        last_chunk = ""

        for chunk in stream:
            # ESC NOT-AUS
            if key_pressed():
                if read_key() == "\x1b":
                    stop_event.set()
                    print("\n⛔ Streaming abgebrochen (ESC)\n")
                    break

            if not chunk:
                continue

            # falls ein Backend mal kein String liefert:
            if not isinstance(chunk, str):
                chunk = str(chunk)

            # Erster Token → Regenbogen weg
            if not got_first_token:
                got_first_token = True
                stop_event.set()
                FIRST_RUN_DONE = True
                time.sleep(0.02)
                print("")

            # Doppelte Chunks vermeiden
            if chunk.strip() == last_chunk.strip():
                continue
            last_chunk = chunk

            full += chunk
            plugin_api.call_token(chunk)
            yield chunk

    except Exception as e:
        stop_event.set()
        err = f"[STREAM ERROR backend] {e}"
        full += err
        plugin_api.call_token(err)
        yield err

    finally:
        stop_event.set()
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

    plugin_api.call_after(full)


# =====================================================================
# 5) Öffentlicher Stream-Entry
# =====================================================================
def stream_chat_completion(llm, messages, perf, plugins=None):
    plugin_api = StreamingPluginInterface(plugins)

    # Dict-Backends (MLX / neues llama_backend) → Router
    if isinstance(llm, dict) and llm.get("backend") in ("mlx", "llama"):
        yield from _router_stream(llm, messages, perf, plugin_api)
        return

    # Classic: reine llama_cpp-Instanz (Fallback aus llm_loader)
    if hasattr(llm, "create_chat_completion"):
        yield from _local_stream(llm, messages, perf, plugin_api)
        return

    # sonst: kein Streaming möglich
    msg = "[STREAM WARNING] Modelltyp unbekannt – kein Streaming möglich."
    plugin_api.call_before(msg)
    plugin_api.call_token(msg)
    plugin_api.call_after(msg)
    yield msg



# =====================================================================
# 6) Ausgabe in die Konsole
# =====================================================================

def stream_to_console(generator):
    """
    Liest Text-Chunks aus dem Generator, gibt sie auf der Konsole aus
    und bricht bei ESC sauber ab.
    Gibt immer den bisher gesammelten Text zurück.
    """

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    full = ""
    print(Fore.GREEN, end="")

    try:
        # Terminal in cbreak-Modus → Tasten sofort lesbar
        tty.setcbreak(fd)

        for tok in generator:
            if tok is None:
                continue

            # 🔴 ESC-Check (non-blocking)
            r, _, _ = select.select([sys.stdin], [], [], 0)
            if r:
                ch = sys.stdin.read(1)
                if ch == "\x1b":  # ESC
                    print(Style.RESET_ALL + "\n⏹️ Stream mit ESC abgebrochen.\n")
                    return full

            # Normale Ausgabe
            sys.stdout.write(tok)
            sys.stdout.flush()
            full += tok

    except Exception as e:
        print(Style.RESET_ALL + Fore.RED + f"[STREAM PRINT ERROR] {e}" + Style.RESET_ALL)

    finally:
        # Terminal-Einstellungen zurücksetzen
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    print(Style.RESET_ALL + "\n")
    return full