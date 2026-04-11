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
import re
import json
from colorama import Fore, Style

from .backend_router import stream_chat as backend_stream_chat
from .rpg_i18n import get_language
from .maat_paths import state_file


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


def _stream_lang() -> str:
    return get_language(("de", "en"))


def _show_thinking_enabled() -> bool:
    try:
        settings_path = state_file("settings_state.json")
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return bool(data.get("show_thinking", False))
    except Exception:
        return False

def rainbow_progress(stop_event: threading.Event):
    """Animierter Ladebalken."""
    idx = 0
    bar_len = 22

    while not stop_event.is_set():
        bar = ""
        for i in range(bar_len):
            bar += RAINBOW[(idx + i) % len(RAINBOW)] + "█" + RESET

        prefix = "⏳ Loading model… " if _stream_lang() == "en" else "⏳ Lade Modell… "
        sys.stdout.write(f"\r{prefix}{bar}")
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
    pending = ""
    inside_think = False
    show_thinking = _show_thinking_enabled()
    announced_thinking = False
    print(Fore.GREEN, end="")

    def flush_visible(text: str):
        nonlocal full
        if not text:
            return
        sys.stdout.write(text)
        sys.stdout.flush()
        full += text

    def announce_thinking():
        nonlocal announced_thinking
        if announced_thinking:
            return
        message = "\nMAAT-KI is thinking:\n" if _stream_lang() == "en" else "\nMAAT-KI denkt nach:\n"
        flush_visible(message)
        announced_thinking = True

    try:
        tty.setcbreak(fd)

        for tok in generator:
            if tok is None:
                continue

            r, _, _ = select.select([sys.stdin], [], [], 0)
            if r:
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    print(Style.RESET_ALL + "\n⏹️ Stream mit ESC abgebrochen.\n")
                    return full

            pending += tok

            while pending:
                lower = pending.lower()

                if inside_think:
                    end_idx = lower.find("</think>")
                    if end_idx == -1:
                        if show_thinking:
                            safe = pending[:-7] if len(pending) > 7 else ""
                            if safe:
                                flush_visible(safe)
                                pending = pending[len(safe):]
                            break
                        pending = pending[-7:] if len(pending) > 7 else pending
                        break

                    think_text = pending[:end_idx]
                    if show_thinking and think_text:
                        flush_visible(think_text)
                    pending = pending[end_idx + len("</think>"):]
                    inside_think = False
                    continue

                start_idx = lower.find("<think>")
                if start_idx == -1:
                    safe = pending[:-6] if len(pending) > 6 else ""
                    if safe:
                        flush_visible(safe)
                        pending = pending[len(safe):]
                    break

                visible = pending[:start_idx]
                flush_visible(visible)
                pending = pending[start_idx + len("<think>"):]
                if not show_thinking:
                    announce_thinking()
                inside_think = True

    except Exception as e:
        print(Style.RESET_ALL + Fore.RED + f"[STREAM PRINT ERROR] {e}" + Style.RESET_ALL)

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    if pending and not inside_think:
        pending = re.sub(r"</?think>", "", pending, flags=re.IGNORECASE)
        flush_visible(pending)

    print(Style.RESET_ALL + "\n")
    return full
