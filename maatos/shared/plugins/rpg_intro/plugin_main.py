# -*- coding: utf-8 -*-
"""
MAAT RPG – Cinematic Intro Plugin (Slow Stream + Theme + Animation + ESC)
-------------------------------------------------------------------
Befehl:  /rpg

Features:
1) Optional intro.mp3 während Pyramide + Story
2) Langsames pseudo-Streaming (ca. 2–3 Minuten)
3) ENTER → weiter
4) Danach optional theme.mp3 + Animation
5) ESC kann das Intro jederzeit abbrechen:
   - Streaming stoppt
   - Animation stoppt
   - Musik wird beendet
"""

import os
import sys
import time
import threading
import subprocess
import termios
import tty
import select


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
    "✨ Drücke [ENTER], um fortzufahren…\n",
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

    commands = {
        "/rpgdemo": "Startet das MAAT RPG Cinematic Intro"
    }


    def __init__(self):
        self._abort = False

    # -----------------------------------------------
    # /rpg Befehl
    # -----------------------------------------------
    def command(self, cmd: str, context=None):
        """
        Wird vom CommandRouter aufgerufen.
        cmd: z.B. "/rpg"
        context: kommt aktuell vom PluginManager (z.B. {"pm": plugin_manager})
        """
        c = cmd.strip().lower()

        if c != "/rpgdemo":
            return None  # anderes Kommando → ignoriere

        # Hier dein komplettes Intro starten
        self.play_intro()

        # Kein extra Text ausgeben – das Intro schreibt selbst auf die Konsole
        return None

    # -----------------------------------------------
    # ESC-Erkennung (cbreak-Modus)
    # -----------------------------------------------
    def _check_escape(self):
        """
        Prüft non-blocking, ob ESC gedrückt wurde.
        Setzt self._abort = True, wenn ja.
        """
        if self._abort:
            return True

        try:
            dr, _, _ = select.select([sys.stdin], [], [], 0)
            if dr:
                ch = sys.stdin.read(1)
                if ch == "\x1b":  # ESC
                    self._abort = True
                    return True
        except Exception:
            # Wenn irgendwas schiefgeht: lieber weiterlaufen
            return False

        return False

    # -----------------------------------------------
    # Musik (macOS, optional)
    # -----------------------------------------------
    def _play_music(self, path: str):
        """Startet ein mp3 mit afplay (nicht blockierend)."""
        try:
            subprocess.Popen(
                ["afplay", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    def _stop_music(self):
        """Stoppt alle laufenden afplay-Prozesse."""
        try:
            subprocess.call(
                ["killall", "afplay"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    # -----------------------------------------------
    # Langsames Streaming
    # -----------------------------------------------
    def _slow_stream(self, text: str, speed: float = 0.03):
        """
        Gibt Text langsam Zeichen für Zeichen aus.
        Bricht ab, wenn ESC gedrückt wurde.
        Rückgabe: True = weiter, False = abgebrochen
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
        """Zeigt die Pyramide langsam Zeile für Zeile."""
        for line in PYRAMID_ASCII:
            if not self._slow_stream(line, speed=0.01):
                return False
        sys.stdout.write("\n")
        sys.stdout.flush()
        return True

    # -----------------------------------------------
    # MAAT-Animation nach dem Intro
    # -----------------------------------------------
    def _run_animation(self, duration: float = 8.0, interval: float = 0.2):
        """
        Läuft in einer Schleife für 'duration' Sekunden.
        Bricht ab, wenn ESC gedrückt wurde.
        """
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
            # Zeile säubern
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()

    # -----------------------------------------------
    # Haupt-Intro
    # -----------------------------------------------
    def play_intro(self):
        print("\nMAAT RPG – Intro wird geladen…\n")

        self._abort = False

        # Terminal in cbreak-Modus für ESC
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setcbreak(fd)

        base_dir = os.path.dirname(__file__)

        try:
            # 1) Intro-Musik starten (falls vorhanden)
            intro_mp3 = os.path.join(base_dir, "intro.mp3")
            if os.path.isfile(intro_mp3):
                threading.Thread(
                    target=self._play_music,
                    args=(intro_mp3,),
                    daemon=True
                ).start()

            # 2) Pyramide anzeigen
            if not self._show_ascii_pyramid():
                self._stop_music()
                print("\n  MAAT RPG Intro abgebrochen.\n")
                return

            # 3) Story streamen
            for line in INTRO:
                if not self._slow_stream(line, speed=0.03):
                    self._stop_music()
                    print("\n MAAT RPG Intro abgebrochen (ESC).\n")
                    return

            # 4) Auf ENTER warten, aber ESC akzeptieren
            print("")  # kleine Lücke
            print("[ENTER] → Weiter…")
            buffer = ""
            while True:
                # ESC?
                if self._check_escape():
                    self._stop_music()
                    print("\n MAAT RPG Intro abgebrochen\n")
                    return

                # normaler Input, aber Zeichenweise
                dr, _, _ = select.select([sys.stdin], [], [], 0.05)
                if dr:
                    ch = sys.stdin.read(1)
                    if ch == "\n":  # ENTER
                        break
                    # andere Tasten ignorieren
                # kleine Pause, um CPU zu schonen
                time.sleep(0.01)

            # 5) Intro-Musik stoppen
            self._stop_music()

            if self._abort:
                print("\n MAAT RPG Intro abgebrochen.\n")
                return

            # 6) Theme-Musik starten (wenn vorhanden)
            theme_mp3 = os.path.join(base_dir, "theme.mp3")
            if os.path.isfile(theme_mp3):
                threading.Thread(
                    target=self._play_music,
                    args=(theme_mp3,),
                    daemon=True
                ).start()

            # 7) Animation laufen lassen
            self._run_animation(duration=8.0, interval=0.2)

            if self._abort:
                self._stop_music()
                print("\n MAAT RPG Intro abgebrochen.\n")
                return

            # 8) Abschluss-Text
            print("\n✨ Einfach beim nächsten Start RPG auswählen\n")

        finally:
            # Terminal-Einstellungen zurücksetzen
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)