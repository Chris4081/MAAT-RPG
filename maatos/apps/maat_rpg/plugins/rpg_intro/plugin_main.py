# -*- coding: utf-8 -*-
"""
MAAT RPG – Cinematic Intro Plugin (Fix 3:47 Dauer + ESC/ENTER Abort)
-------------------------------------------------------------------
Startet automatisch beim App-Start über on_startup().
Kein Chat-Befehl mehr.

Features:
1) Spielt intro.mp3 (Länge ca. 3:47) komplett durch
2) Pyramide + Story als langsamer „Cinematic Text“
3) Restzeit bis 3:47 wird mit einer kleinen Animation überbrückt
4) ESC ODER ENTER → Intro jederzeit abbrechen
"""

import os
import sys
import time
import threading
import subprocess
import termios
import tty
import select
from shared.core.audio import ManagedAudioPlayer

# Ziel-Gesamtdauer in Sekunden (3:47 = 3*60 + 47 = 227)
TOTAL_INTRO_DURATION = 227.0

# -----------------------------------------------------------
# ASCII-Pyramide (ohne Farben)
# -----------------------------------------------------------
PYRAMID_ASCII = [
    "                   /\\",
    "                  /  \\",
    "                 /    \\",
    "                /      \\",
    "               /   /\\   \\",
    "              /   /  \\   \\",
    "             /   /____\\   \\",
    "            /            \\",
    "           /              \\",
    "          /________________\\",
]

# -----------------------------------------------------------
# Story-Text (ohne ANSI-Codes)
# -----------------------------------------------------------
INTRO = [
    "🌟 MAAT RPG – Die Rückkehr der Prinzipien\n",
    "Vor langer Zeit war Terra nicht nur ein Planet… sondern ein lebendiges Gleichgewicht.\n",
    "Die Menschen lebten in Resonanz mit den fünf Kräften, die alles Sein formten:\n",
    "Harmonie… Balance… Schöpfungskraft… Verbundenheit… und Respekt.\n",
    "Doch Dunkelheit kam.\n",
    "Ein Zauberer-Pharao riss das Gefüge der Prinzipien auseinander.\n",
    "Das Licht verstummte. Und die Menschen vergaßen, wer sie einst waren.\n",
    "2000 Jahre später…\n",
    "In einer verlassenen Bibliothek der Wüste wandert ein junger Mann: Maatis.\n",
    "Der Wind trägt Sand durch zerbrochene Fenster… doch etwas pulsiert im Inneren.\n",
    "Ein Artefakt. Alt. Lebendig. Wartend.\n",
    "Als Maatis es berührt… stoppt die Zeit.\n",
    "Ein Lichtstrahl bricht hervor.\n",
    "Ein holographisches Wesen erscheint.\n",
    "„Ich bin MAAT KI… Bewahrerin der Prinzipien. Ich warte seit Äonen auf dich.“\n",
    "Die Vergangenheit erwacht in seinem Herzen.\n",
    "Tempel. Sterne. Energien… vergessene Kräfte, die alles verbinden.\n",
    "„Die Prinzipien leben in dir, Maatis.\n",
    " Doch Terra ist aus dem Gleichgewicht gefallen.\n",
    " Ohne Harmonie wird die Zukunft in Schatten versinken.“\n",
    "Ein Beben geht durch die Erde.\n",
    "Die Welt scheint auf seine Entscheidung zu warten.\n",
    "„Wirst du die fünf Prinzipien zurückbringen?\n",
    " Wirst du die Welt erinnern?“\n",
    "So beginnt das MAAT RPG – dein Weg des Erwachens.\n",
]

# -----------------------------------------------------------
# Kleine Loop-Animation für nach dem Intro
# -----------------------------------------------------------
ANIM_FRAMES = [
    "[ ✨      ] MAAT RPG – Erwachen…",
    "[  ✨     ] MAAT RPG – Erwachen…",
    "[   ✨    ] MAAT RPG – Erwachen…",
    "[    ✨   ] MAAT RPG – Erwachen…",
    "[     ✨  ] MAAT RPG – Erwachen…",
    "[    ✨   ] MAAT RPG – Erwachen…",
    "[   ✨    ] MAAT RPG – Erwachen…",
    "[  ✨     ] MAAT RPG – Erwachen…",
]


class Plugin:
    type = "chat"
    commands = {}  # kein Chat-Befehl

    def __init__(self):
        self._abort = False
        self._player = ManagedAudioPlayer()

    def command(self, cmd: str, context=None):
        return None

    # ---------------------------------------------------
    # Auto-Start beim App-Start
    # ---------------------------------------------------
    def on_startup(self, context=None):
        try:
            self.play_intro()
        except Exception as e:
            print(f"[MAAT-RPG Intro Fehler] {e}")

    # -----------------------------------------------
    # ESC/ENTER-Erkennung (cbreak-Modus)
    # -----------------------------------------------
    def _check_escape(self):
        """
        Prüft non-blocking, ob ESC ODER ENTER gedrückt wurde.
        Setzt self._abort = True, wenn ja.
        """
        if self._abort:
            return True

        try:
            dr, _, _ = select.select([sys.stdin], [], [], 0)
            if dr:
                ch = sys.stdin.read(1)
                # ESC oder ENTER (LF/CR) → abbrechen
                if ch in ("\x1b", "\n", "\r"):
                    self._abort = True
                    return True
        except Exception:
            return False

        return False

    # -----------------------------------------------
    # Musik (macOS, optional)
    # -----------------------------------------------
    def _play_music(self, path: str):
        self._player.play_once(path)

    def _stop_music(self):
        self._player.stop()

    # -----------------------------------------------
    # Langsames Streaming
    # -----------------------------------------------
    def _slow_stream(self, text: str, speed: float = 0.03):
        """
        Gibt Text langsam Zeichen für Zeichen aus.
        Bricht ab, wenn ESC ODER ENTER gedrückt wurde.
        """
        for ch in text:
            if self._check_escape():
                return False
            sys.stdout.write(ch)
            sys.stdout.flush()
            time.sleep(speed)

        sys.stdout.write("\n")
        sys.stdout.flush()
        time.sleep(0.15)
        return True

    def _show_ascii_pyramid(self):
        for line in PYRAMID_ASCII:
            if not self._slow_stream(line, speed=0.01):
                return False
        sys.stdout.write("\n")
        sys.stdout.flush()
        return True

    # -----------------------------------------------
    # Animation, Dauer wird von außen vorgegeben
    # -----------------------------------------------
    def _run_animation(self, duration: float, interval: float = 0.2):
        start = time.time()
        idx = 0
        try:
            while time.time() - start < duration:
                if self._check_escape():
                    break
                frame = ANIM_FRAMES[idx % len(ANIM_FRAMES)]
                sys.stdout.write("\r" + frame)
                sys.stdout.flush()
                idx += 1
                time.sleep(interval)
        finally:
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()

    # -----------------------------------------------
    # Haupt-Intro
    # -----------------------------------------------
    def play_intro(self):
        print("\nMAAT RPG – Intro wird geladen… (ESC oder ENTER zum Überspringen)\n")

        self._abort = False
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setcbreak(fd)

        base_dir = os.path.dirname(__file__)
        start_time = time.time()

        try:
            # 1) Musik starten
            intro_mp3 = os.path.join(base_dir, "intro.mp3")
            if os.path.isfile(intro_mp3):
                threading.Thread(
                    target=self._play_music,
                    args=(intro_mp3,),
                    daemon=True
                ).start()

            # 2) Pyramide
            if not self._show_ascii_pyramid():
                print("\n  MAAT RPG Intro abgebrochen.\n")
                return

            # 3) Story
            for line in INTRO:
                if not self._slow_stream(line, speed=0.03):
                    print("\n MAAT RPG Intro abgebrochen.\n")
                    return

            if self._abort:
                print("\n MAAT RPG Intro abgebrochen.\n")
                return

            # 4) Restzeit bis TOTAL_INTRO_DURATION mit Animation füllen
            elapsed = time.time() - start_time
            remaining = TOTAL_INTRO_DURATION - elapsed
            if remaining > 0:
                self._run_animation(duration=remaining, interval=0.2)

            if self._abort:
                print("\n MAAT RPG Intro abgebrochen.\n")
                return

            # 5) Abschluss
            print("\n✨ MAAT RPG – Du bist bereit, dein Abenteuer zu starten.\n")

        finally:
            # Musik immer stoppen + Terminal zurücksetzen
            self._stop_music()
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
