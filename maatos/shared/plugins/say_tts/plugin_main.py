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
import time


class Plugin:
    type = "stream"

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
        self.voice = "Anna"
        self.rate = 180

        # Stream-Buffer für Token
        self.buffer = ""

        # Sequenzieller TTS-Queue
        self.tts_queue = queue.Queue()

        # Stop-Signal
        self.stop_event = threading.Event()

        # TTS Worker (spricht IMMER EINEN Satz nach dem anderen)
        threading.Thread(target=self._tts_worker, daemon=True).start()

    # ----------------------------------------------------
    # Startup
    # ----------------------------------------------------
    def on_startup(self):
        choice = input("🔊 Say-TTS aktivieren? (J/N): ").strip().lower()
        self.enabled = choice.startswith("j")
        print("✔ Aktiviert\n" if self.enabled else "✖ Deaktiviert\n")

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
        if self.enabled:
            self.tts_queue.put(text.strip())

    # ----------------------------------------------------
    # STREAMING LOGIK
    # ----------------------------------------------------
    def before_stream(self, text):
        self.buffer = ""

    def on_token(self, token):
        if not self.enabled:
            return

        self.buffer += token

        # Satzende erkannt → sprechen
        if any(self.buffer.endswith(end) for end in [".", "!", "?", "…"]):
            self._speak(self.buffer)
            self.buffer = ""

    def after_stream(self, full_text):
        """ Reste sprechen """
        if self.enabled and self.buffer.strip():
            self._speak(self.buffer)
        self.buffer = ""

    # ----------------------------------------------------
    # CHAT BEFEHLE
    # ----------------------------------------------------
    def command(self, cmd, context=None):
        c = cmd.strip()

        # /say → Hilfe anzeigen
        if c == "/say":
            text = (
                "🎤 Say-TTS Plugin\n\n"
                "Verfügbare Befehle:\n"
                "• /say on – TTS aktivieren\n"
                "• /say off – TTS deaktivieren\n"
                "• /say voice <Name> – Stimme ändern (z.B. Anna, Markus)\n"
                f"Aktuelle Stimme: {self.voice}\n"
                f"Aktiver Status: {'AN' if self.enabled else 'AUS'}"
            )
            return True, text

        if c == "/say on":
            self.enabled = True
            return True, "🔊 Say-TTS aktiviert."

        if c == "/say off":
            self.enabled = False
            return True, "🔇 Say-TTS deaktiviert."

        if c.lower().startswith("/say voice "):
            self.voice = c[11:].strip()  # alles nach "/say voice " nehmen
            if not self.voice:
                return True, "Bitte gib eine Stimme an, z.B.: /say voice Anna"
            return True, f"🎤 Stimme gesetzt: {self.voice}"

        # nichts gehandelt → weiter zum nächsten Plugin / Modell
        return False, None
