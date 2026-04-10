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
from shared.core.rpg_i18n import get_language


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

    def _prepare_tts_text(self, text: str) -> str:
        cleaned = (text or "").strip()
        if self._lang() == "de":
            cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
            cleaned = re.sub(r"</?think>", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
        return cleaned

    # ----------------------------------------------------
    # Startup
    # ----------------------------------------------------
    def on_startup(self):
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

        if self._lang() == "de":
            self._think_buffer += token

            while self._think_buffer:
                if self._inside_think:
                    end_idx = self._think_buffer.lower().find("</think>")
                    if end_idx == -1:
                        return
                    self._think_buffer = self._think_buffer[end_idx + len("</think>"):]
                    self._inside_think = False
                    continue

                start_idx = self._think_buffer.lower().find("<think>")
                visible = self._think_buffer if start_idx == -1 else self._think_buffer[:start_idx]

                if visible:
                    self.buffer += visible
                    if any(self.buffer.endswith(end) for end in [".", "!", "?", "…"]):
                        self._speak(self.buffer)
                        self.buffer = ""

                if start_idx == -1:
                    self._think_buffer = ""
                    return

                self._think_buffer = self._think_buffer[start_idx + len("<think>"):]
                self._inside_think = True
            return

        self.buffer += token

        # Satzende erkannt → sprechen
        if any(self.buffer.endswith(end) for end in [".", "!", "?", "…"]):
            self._speak(self.buffer)
            self.buffer = ""

    def after_stream(self, full_text):
        """ Reste sprechen """
        if self._lang() == "de" and self._think_buffer and not self._inside_think:
            self.buffer += self._think_buffer
            self._think_buffer = ""
        if self.enabled and self.buffer.strip():
            self._speak(self.buffer)
        self.buffer = ""
        self._think_buffer = ""
        self._inside_think = False

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
