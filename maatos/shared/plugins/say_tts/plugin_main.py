# -*- coding: utf-8 -*-
"""
Say-TTS Streaming Plugin (Sequential MAAT Edition)
-------------------------------------------------
✓ spricht Sätze NACHEINANDER
✓ kein Überlappen mehr
✓ kompatibel mit PluginManager / CommandRouter
✓ /say Befehle integriert
"""

import subprocess
import queue
import threading
import platform
import re
import time
import json
from shared.core.rpg_i18n import get_language
from shared.core.maat_paths import state_file


_GERMAN_TTS_META_LINE = re.compile(
    r"^\s*(?:"
    r"The user is asking\b|"
    r"They'?ve asked\b|"
    r"As MAAT-KI\b|"
    r"I should respond\b|"
    r"I'll follow\b|"
    r"Let me craft\b|"
    r"-\s+(?:Honest|Acknowledging|Brief|Including)\b"
    r")",
    re.IGNORECASE,
)


class Plugin:
    type = "stream"
    DEFAULT_VOICES = {
        "de": "Anna",
        "en": "Samantha",
    }

    # ----------------------------------------------------
    # Plugin-Befehle (für CommandRouter / /help)
    # ----------------------------------------------------
    commands = {
        "/say": {"de": "Zeigt die Say-TTS-Hilfe an.", "en": "Shows Say-TTS help."},
        "/say on": {"de": "Aktiviert Say-TTS.", "en": "Enables Say-TTS."},
        "/say off": {"de": "Deaktiviert Say-TTS.", "en": "Disables Say-TTS."},
        "/say voice": {"de": "Aendert die TTS-Stimme (/say voice <Name>).", "en": "Changes the TTS voice (/say voice <Name>)."}
    }

    def __init__(self):
        self.enabled = False
        self.voice = self.DEFAULT_VOICES["de"]
        self.voice_is_manual = False
        self.rate = 180

        # Stream-Buffer für Token
        self.buffer = ""
        self._think_buffer = ""
        self._inside_think = False

        # Sequenzieller TTS-Queue
        self.tts_queue = queue.Queue()

        # Stop-Signal
        self.stop_event = threading.Event()

        # TTS Worker (spricht IMMER EINEN Satz nach dem anderen)
        threading.Thread(target=self._tts_worker, daemon=True).start()

    def _lang(self):
        return get_language(("de", "en"))

    def _t(self, de: str, en: str) -> str:
        return en if self._lang() == "en" else de

    def _default_voice(self) -> str:
        return self.DEFAULT_VOICES.get(self._lang(), "Anna")

    def _sync_voice_with_language(self):
        if not self.voice_is_manual:
            self.voice = self._default_voice()

    def _show_thinking_enabled(self) -> bool:
        try:
            with open(state_file("settings_state.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
            return bool(data.get("show_thinking", False))
        except Exception:
            return False

    def _thinking_tts_enabled(self) -> bool:
        return self._lang() == "en" and self._show_thinking_enabled()

    def _strip_meta_reasoning_for_german_tts(self, text: str) -> str:
        if self._lang() != "de":
            return text

        lines = (text or "").splitlines()
        kept: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                kept.append(line)
                continue
            if _GERMAN_TTS_META_LINE.match(stripped):
                continue
            kept.append(line)

        cleaned = "\n".join(kept)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def _prepare_tts_text(self, text: str) -> str:
        cleaned = (text or "").strip()
        if self._lang() == "de" or not self._thinking_tts_enabled():
            cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"</?think>", "", cleaned, flags=re.IGNORECASE)
        cleaned = self._strip_meta_reasoning_for_german_tts(cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r" *\n *", "\n", cleaned)
        cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
        return cleaned

    def _append_visible(self, text: str):
        if not text:
            return
        self.buffer += text
        if any(self.buffer.endswith(end) for end in [".", "!", "?", "…"]):
            self._speak(self.buffer)
            self.buffer = ""

    # ----------------------------------------------------
    # Startup
    # ----------------------------------------------------
    def on_startup(self, context=None):
        self._sync_voice_with_language()
        choice = input(
            self._t(
                "🔊 Say-TTS aktivieren? (J/N): ",
                "🔊 Enable Say-TTS? (Y/N): ",
            )
        ).strip().lower()
        self.enabled = choice.startswith("j") or choice.startswith("y")
        print(
            self._t("✔ Aktiviert\n", "✔ Enabled\n")
            if self.enabled
            else self._t("✖ Deaktiviert\n", "✖ Disabled\n")
        )

    # ----------------------------------------------------
    # Worker spricht ALLES nacheinander
    # ----------------------------------------------------
    def _tts_worker(self):
        """ Spricht die Queue sequential ab """
        if platform.system().lower() != "darwin":
            return

        while not self.stop_event.is_set():
            try:
                text = self.tts_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if not text.strip():
                continue

            # BLOCKIEREND sprechen = Nacheinander
            subprocess.call(
                ["say", "-v", self.voice, "-r", str(self.rate), text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Kurze Pause, um “Atmen” zu simulieren
            time.sleep(0.05)

    def _speak(self, text: str):
        """ Text in Queue einreihen (wird SEQUENZIELL gesprochen). """
        prepared = self._prepare_tts_text(text)
        if self.enabled and prepared:
            self._sync_voice_with_language()
            self.tts_queue.put(prepared)

    # ----------------------------------------------------
    # STREAMING LOGIK
    # ----------------------------------------------------
    def before_stream(self, text):
        self.buffer = ""
        self._think_buffer = ""
        self._inside_think = False

    def on_token(self, token):
        if not self.enabled:
            return

        allow_thinking_tts = self._thinking_tts_enabled()
        self._think_buffer += token

        while self._think_buffer:
            lower = self._think_buffer.lower()

            if self._inside_think:
                end_idx = lower.find("</think>")
                if end_idx == -1:
                    if allow_thinking_tts:
                        self._append_visible(self._think_buffer)
                        self._think_buffer = ""
                    return

                think_text = self._think_buffer[:end_idx]
                if allow_thinking_tts and think_text:
                    self._append_visible(think_text)
                self._think_buffer = self._think_buffer[end_idx + len("</think>"):]
                self._inside_think = False
                continue

            start_idx = lower.find("<think>")
            visible = self._think_buffer if start_idx == -1 else self._think_buffer[:start_idx]
            if visible:
                self._append_visible(visible)

            if start_idx == -1:
                self._think_buffer = ""
                return

            self._think_buffer = self._think_buffer[start_idx + len("<think>"):]
            self._inside_think = True

    def after_stream(self, full_text):
        """ Reste sprechen """
        if self._think_buffer and not self._inside_think:
            self.buffer += self._prepare_tts_text(self._think_buffer)
            self._think_buffer = ""
        if self.enabled and self.buffer.strip():
            self._speak(self.buffer)
        self.buffer = ""
        self._think_buffer = ""
        self._inside_think = False

    def after_final_response(self, reply, context=None):
        if self.enabled and isinstance(reply, str) and reply.strip():
            self._speak(reply)
        return reply

    # ----------------------------------------------------
    # CHAT BEFEHLE
    # ----------------------------------------------------
    def command(self, cmd, context=None):
        c = cmd.strip()
        self._sync_voice_with_language()

        # /say → Hilfe anzeigen
        if c == "/say":
            text = (
                self._t(
                    "🎤 Say-TTS Plugin\n\n"
                    "Verfuegbare Befehle:\n"
                    "• /say on - TTS aktivieren\n"
                    "• /say off - TTS deaktivieren\n"
                    "• /say voice <Name> - Stimme aendern (z.B. Anna, Markus)\n"
                    f"Aktuelle Stimme: {self.voice}\n"
                    f"Aktiver Status: {'AN' if self.enabled else 'AUS'}",
                    "🎤 Say-TTS Plugin\n\n"
                    "Available commands:\n"
                    "• /say on - Enable TTS\n"
                    "• /say off - Disable TTS\n"
                    "• /say voice <Name> - Change the voice (e.g. Anna, Markus)\n"
                    f"Current voice: {self.voice}\n"
                    f"Current status: {'ON' if self.enabled else 'OFF'}",
                )
            )
            return True, text

        if c == "/say on":
            self.enabled = True
            return True, self._t("🔊 Say-TTS aktiviert.", "🔊 Say-TTS enabled.")

        if c == "/say off":
            self.enabled = False
            return True, self._t("🔇 Say-TTS deaktiviert.", "🔇 Say-TTS disabled.")

        if c.lower().startswith("/say voice "):
            self.voice = c[11:].strip()  # alles nach "/say voice " nehmen
            if not self.voice:
                return True, self._t(
                    "Bitte gib eine Stimme an, z.B.: /say voice Anna",
                    "Please provide a voice, e.g.: /say voice Anna",
                )
            self.voice_is_manual = True
            return True, self._t(
                f"🎤 Stimme gesetzt: {self.voice}",
                f"🎤 Voice set: {self.voice}",
            )

        # nichts gehandelt → weiter zum nächsten Plugin / Modell
        return False, None
