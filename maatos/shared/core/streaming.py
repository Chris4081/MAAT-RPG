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
import select
import re
from colorama import Fore, Style

try:
    import tty  # type: ignore
    import termios  # type: ignore
except Exception:
    tty = None  # type: ignore
    termios = None  # type: ignore

try:
    import msvcrt  # type: ignore
except Exception:
    msvcrt = None  # type: ignore

from .backend_router import stream_chat as backend_stream_chat
from .rpg_i18n import get_language
from .repetition_guard import guard_chunks, RepetitionStopped
from .thinking_mode import (
    chat_completion_thinking_kwargs,
    prepare_generation_messages,
    show_thinking_enabled,
)


# =====================================================================
# 0) GLOBAL — Regenbogen nur beim ersten Stream überhaupt
# =====================================================================
FIRST_RUN_DONE = False


# =====================================================================
# 1) Non-blocking Keyboard Check (für ESC)
# =====================================================================

def key_pressed():
    if msvcrt is not None:
        try:
            return bool(msvcrt.kbhit())
        except Exception:
            return False
    dr, _, _ = select.select([sys.stdin], [], [], 0)
    return bool(dr)

def read_key():
    if msvcrt is not None:
        try:
            return msvcrt.getwch()
        except Exception:
            return ""
    return sys.stdin.read(1)


def _can_use_posix_cbreak() -> bool:
    return (
        termios is not None
        and tty is not None
        and bool(getattr(sys.stdin, "isatty", lambda: False)())
    )


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
    return show_thinking_enabled()

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
    def __init__(self, plugins=None, on_first_token=None):
        self.plugins = plugins or []
        self.on_first_token = on_first_token

    def call_before(self, text):
        for p in self.plugins:
            fn = getattr(p, "before_stream", None)
            if callable(fn):
                try:
                    fn(text)
                except Exception as e:
                    print(Fore.RED + f"[PLUGIN before_stream ERROR] {e}" + Style.RESET_ALL)

    def call_token(self, token):
        if token and self.on_first_token is not None:
            callback, self.on_first_token = self.on_first_token, None
            callback()
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
def _router_stream(llm, messages, perf, plugin_api, query=''):
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
    if not FIRST_RUN_DONE and not perf.get("gui_mode"):
        threading.Thread(
            target=rainbow_progress, args=(stop_event,), daemon=True
        ).start()

    fd = None
    old = None
    if _can_use_posix_cbreak():
        try:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        except Exception:
            fd = None
            old = None

    stream = None
    try:
        # Router → liefert Generator mit String-Chunks
        stream = guard_chunks(backend_stream_chat(llm, messages, perf=perf),
                              query=query, turn=perf.get('_chat_turn'))

        got_first_token = False

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

            # Delta tokens may repeat legitimately (100, **, indentation).
            full += chunk
            plugin_api.call_token(chunk)
            yield chunk

    except Exception as e:
        stop_event.set()
        if perf.get("raise_errors"):
            raise
        err = f"[STREAM ERROR backend] {e}"
        full += err
        plugin_api.call_token(err)
        yield err

    finally:
        if stream is not None:
            stream.close()
        stop_event.set()
        if fd is not None and old is not None and termios is not None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            except Exception:
                pass

    plugin_api.call_after(full)


def _local_stream(llm, messages, perf, plugin_api, query=''):
    global FIRST_RUN_DONE

    full = ""
    plugin_api.call_before("")

    stop_event = threading.Event()
    if not FIRST_RUN_DONE and not perf.get("gui_mode"):
        threading.Thread(
            target=rainbow_progress, args=(stop_event,), daemon=True
        ).start()

    fd = None
    old = None
    if _can_use_posix_cbreak():
        try:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        except Exception:
            fd = None
            old = None

    stream = None
    raw_stream = None
    try:
        kwargs = {
            "messages": messages,
            "temperature": float(perf.get("temperature", 0.7)),
            "top_p": float(perf.get("top_p", 0.9)),
            "stream": True,
        }
        kwargs.update(chat_completion_thinking_kwargs(getattr(llm, "create_chat_completion", None)))
        if 'max_tokens' in perf:
            kwargs['max_tokens'] = perf['max_tokens']
        raw_stream = llm.create_chat_completion(**kwargs)
        def chunks():
            for token in raw_stream:
                choices = token.get('choices') or []
                if choices:
                    yield choices[0].get('delta', {}).get('content', '')
        stream = guard_chunks(chunks(), query=query, turn=perf.get('_chat_turn'))

        got_first_token = False

        for chunk in stream:
            if key_pressed():
                if read_key() == "\x1b":
                    stop_event.set()
                    print("\n⛔ Streaming abgebrochen (ESC)\n")
                    break

            if not chunk:
                continue

            if not got_first_token:
                got_first_token = True
                stop_event.set()
                FIRST_RUN_DONE = True
                time.sleep(0.02)
                print("")

            full += chunk
            plugin_api.call_token(chunk)
            yield chunk

    except Exception as e:
        stop_event.set()
        if perf.get("raise_errors"):
            raise
        err = f"[STREAM ERROR local] {e}"
        full += err
        plugin_api.call_token(err)
        yield err

    finally:
        if stream is not None:
            stream.close()
        close = getattr(raw_stream, 'close', None)
        if close:
            close()
        turn = perf.get('_chat_turn')
        if turn and turn.cancelled.is_set():
            reset = getattr(llm, 'reset', None)
            if callable(reset):
                reset()
        stop_event.set()
        if fd is not None and old is not None and termios is not None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            except Exception:
                pass

    plugin_api.call_after(full)


# =====================================================================
# 5) Öffentlicher Stream-Entry
# =====================================================================
def stream_chat_completion(llm, messages, perf, plugins=None, runtime_context=None):
    turn = (runtime_context or {}).get('gui_chat_turn')
    options = dict(perf or {})
    if turn:
        turn.check()
        options['_chat_turn'] = turn
    source = _stream_chat_completion_impl(llm, messages, options, plugins, runtime_context)
    try:
        for token in source:
            if turn: turn.check()
            yield token
        if turn: turn.check()
    except RepetitionStopped:
        # Drop queued/current speech as well as the unfinished reply. No
        # after-stream, memory-save or successful-turn hooks run on this path.
        for plugin in plugins or []:
            stop = getattr(plugin, 'begin_response_speech', None)
            if callable(stop):
                try:
                    stop()
                except Exception:
                    pass
        raise
    finally:
        source.close()


def _stream_chat_completion_impl(llm, messages, perf, plugins=None, runtime_context=None):
    from .super_memory import SaveStreamFilter
    memory = (runtime_context or {}).get('super_memory')
    if not memory:
        yield from _stream_chat_completion_raw(llm,messages,perf,plugins,runtime_context)
        return
    # TTS and other output plugins must receive exactly the same filtered prose
    # as the chat. Keep cancellation tied to the first raw model token.
    plugin_api = StreamingPluginInterface(plugins)
    plugin_api.call_before('')
    raw_context = dict(runtime_context or {})
    first_callback = raw_context.get('on_first_response_token')
    def first_raw_token():
        if first_callback:
            first_callback()
        else:
            for plugin in plugins or []:
                stop = getattr(plugin,'begin_response_speech',None)
                if callable(stop):stop()
    raw_context['on_first_response_token'] = first_raw_token
    source = _stream_chat_completion_raw(llm,messages,perf,[],raw_context)
    filtered = SaveStreamFilter(memory)
    shown = []
    failed = False
    for token in source:
        if not token:continue
        failed = failed or '[STREAM ERROR' in token or '[STREAM WARNING' in token
        visible = filtered.feed(token)
        if visible:
            plugin_api.call_token(visible); shown.append(visible)
            yield visible
    # A failed/cancelled generation must never become a durable model save.
    if isinstance(runtime_context,dict) and raw_context.get('super_memory_error'):
        runtime_context['super_memory_error'] = raw_context['super_memory_error']
    if not failed:
        try:
            def save_memory():
                # Deferred callbacks execute when the GUI commits the turn,
                # outside this generator's try block. A memory error must not
                # interrupt chat archiving or the remaining completion hooks.
                try:
                    from .maat_assessment import correct_average
                    memory.finish_turn((runtime_context or {}).get('super_memory_query',''),correct_average(filtered.raw,messages),
                                       (runtime_context or {}).get('super_memory_turn',''),runtime_context=runtime_context)
                except Exception:
                    if isinstance(runtime_context,dict):
                        runtime_context['super_memory_error']='Neue Erinnerung konnte nicht gespeichert werden.'
            turn = (runtime_context or {}).get('gui_chat_turn')
            if turn:
                turn.defer(save_memory)
            else:
                save_memory()
        except Exception:
            if isinstance(runtime_context,dict):
                runtime_context['super_memory_error']='Neue Erinnerung konnte nicht gespeichert werden.'
    tail = filtered.finish()
    if tail:
        plugin_api.call_token(tail); shown.append(tail)
        yield tail
    plugin_api.call_after(''.join(shown))


def _stream_chat_completion_raw(llm, messages, perf, plugins=None, runtime_context=None):
    """Optional whole-answer guards run before token hooks and durable saves."""
    from .ai_plugin_settings import SNAPSHOT, current_settings
    context = runtime_context if isinstance(runtime_context, dict) else {}
    context['_ai_generation_state'] = {}
    if SNAPSHOT not in context:
        context[SNAPSHOT] = current_settings()
    context.setdefault('_ai_plugin_query', next((str(m.get('content', '')) for m in reversed(messages)
                                               if m.get('role') == 'user'), ''))
    manager = context.get('pm')
    select = getattr(manager, 'generation_output_guards', None)
    guards = select(context) if callable(select) else []
    if not isinstance(guards, (list, tuple)) or not guards:
        yield from _model_stream_chat_completion_raw(llm, messages, perf, plugins, context)
        return
    api = StreamingPluginInterface(plugins)
    api.call_before('')
    source = _model_stream_chat_completion_raw(llm, messages, perf, [], context)
    turn = (perf or {}).get('_chat_turn')
    try:
        # Native max_tokens/context limits still bound the generated reply.
        parts = []
        for chunk in source:
            if turn: turn.check()
            parts.append(chunk)
        reply = ''.join(parts)
        if not any(marker in reply for marker in ('[STREAM ERROR', '[STREAM WARNING')):
            for guard in guards:
                if turn: turn.check()
                reply = guard(reply, context)
        if turn: turn.check()
        for offset in range(0, len(reply), 32):
            if turn: turn.check()
            chunk = reply[offset:offset + 32]
            api.call_token(chunk)
            yield chunk
        api.call_after(reply)
    finally:
        source.close()


def _model_stream_chat_completion_raw(llm, messages, perf, plugins=None, runtime_context=None):
    plugin_api = StreamingPluginInterface(plugins, (runtime_context or {}).get('on_first_response_token'))
    prepared_messages = prepare_generation_messages(
        messages,
        language=_stream_lang(),
        runtime_context=runtime_context,
        llm=llm,
        generation_state=(runtime_context or {}).get('_ai_generation_state'),
    )
    from .ai_plugin_settings import settings_for
    from .reply_style import generation_length_options
    perf = generation_length_options(perf, settings_for(runtime_context))
    query = (runtime_context or {}).get('_ai_plugin_query', next(
        (str(m.get('content', '')) for m in reversed(messages) if m.get('role') == 'user'), ''))

    # Dict-Backends (MLX / neues llama_backend) → Router
    if isinstance(llm, dict) and llm.get("backend") in ("mlx", "llama", "llama_intel"):
        yield from _router_stream(llm, prepared_messages, perf, plugin_api, query)
        return

    # Classic: reine llama_cpp-Instanz (Fallback aus llm_loader)
    if hasattr(llm, "create_chat_completion"):
        yield from _local_stream(llm, prepared_messages, perf, plugin_api, query)
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

def stream_to_console(generator, echo: bool = True, raise_errors: bool = False, on_first_visible=None):
    """
    Liest Text-Chunks aus dem Generator, gibt sie auf der Konsole aus
    und bricht bei ESC sauber ab.
    Gibt immer den bisher gesammelten Text zurück.
    """

    fd = None
    old_settings = None

    full = ""
    pending = ""
    inside_think = False
    show_thinking = _show_thinking_enabled()
    announced_thinking = False
    if echo:
        print(Fore.GREEN, end="")

    def flush_visible(text: str, *, response=True):
        nonlocal full, on_first_visible
        if not text:
            return
        if response and text.strip() and on_first_visible is not None:
            callback, on_first_visible = on_first_visible, None
            callback()
        if echo:
            sys.stdout.write(text)
            sys.stdout.flush()
        full += text

    def announce_thinking():
        nonlocal announced_thinking
        if announced_thinking:
            return
        message = "\nMAAT-KI is thinking:\n" if _stream_lang() == "en" else "\nMAAT-KI denkt nach:\n"
        if echo:
            flush_visible(message, response=False)
        announced_thinking = True

    try:
        if _can_use_posix_cbreak():
            try:
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                tty.setcbreak(fd)
            except Exception:
                fd = None
                old_settings = None

        for tok in generator:
            if tok is None:
                continue

            if key_pressed():
                ch = read_key()
                if ch == "\x1b":
                    if echo:
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
        if raise_errors:
            raise
        if echo:
            print(Style.RESET_ALL + Fore.RED + f"[STREAM PRINT ERROR] {e}" + Style.RESET_ALL)

    finally:
        if fd is not None and old_settings is not None and termios is not None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass

    if pending and not inside_think:
        pending = re.sub(r"</?think>", "", pending, flags=re.IGNORECASE)
        flush_visible(pending)

    if echo:
        print(Style.RESET_ALL + "\n")
    return full


def stream_text_to_console(text: str, chunk_size: int = 8, delay: float = 0.003):
    """
    Zeigt bereits vorliegenden Text im selben visuellen Stil wie den normalen Stream an.
    """
    if not isinstance(text, str) or not text:
        return ""

    size = max(1, int(chunk_size))

    def _generator():
        for i in range(0, len(text), size):
            yield text[i:i + size]
            if delay > 0:
                time.sleep(delay)

    try:
        return stream_to_console(_generator(), echo=True)
    except Exception:
        print(Fore.GREEN + text + Style.RESET_ALL + "\n")
        return text
