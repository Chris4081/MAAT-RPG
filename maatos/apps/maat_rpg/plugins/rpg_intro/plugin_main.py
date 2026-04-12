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
import subprocess
import termios
import tty
import select
from shared.core.rpg_i18n import get_language
from shared.core.audio import music_enabled

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

INTRO_TEXT = {
    "de": [
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
    ],
    "en": [
        "🌟 MAAT RPG – Return of the Principles\n",
        "Long ago, Terra was not only a planet… but a living balance.\n",
        "Humanity lived in resonance with the five forces that shaped all being:\n",
        "Harmony… Balance… Creative Power… Connectedness… and Respect.\n",
        "But darkness came.\n",
        "A sorcerer-pharaoh tore the fabric of the principles apart.\n",
        "The light fell silent. And humanity forgot who they once were.\n",
        "2000 years later…\n",
        "In an abandoned library of the desert, a young man walks alone: Maatis.\n",
        "The wind carries sand through broken windows… yet something pulses within.\n",
        "An artifact. Ancient. Alive. Waiting.\n",
        "When Maatis touches it… time stops.\n",
        "A beam of light breaks forth.\n",
        "A holographic being appears.\n",
        "“I am MAAT KI… keeper of the principles. I have waited aeons for you.”\n",
        "The past awakens in his heart.\n",
        "Temples. Stars. Energies… forgotten forces that bind everything together.\n",
        "“The principles live within you, Maatis.\n",
        " But Terra has fallen out of balance.\n",
        " Without harmony, the future will sink into shadow.”\n",
        "A tremor moves through the earth.\n",
        "The world itself seems to wait for his decision.\n",
        "“Will you restore the five principles?\n",
        " Will you help the world remember?”\n",
        "Thus begins MAAT RPG – your path of awakening.\n",
    ],
}

ANIM_FRAMES = {
    "de": [
        "[ ✨      ] MAAT RPG – Erwachen…",
        "[  ✨     ] MAAT RPG – Erwachen…",
        "[   ✨    ] MAAT RPG – Erwachen…",
        "[    ✨   ] MAAT RPG – Erwachen…",
        "[     ✨  ] MAAT RPG – Erwachen…",
        "[    ✨   ] MAAT RPG – Erwachen…",
        "[   ✨    ] MAAT RPG – Erwachen…",
        "[  ✨     ] MAAT RPG – Erwachen…",
    ],
    "en": [
        "[ ✨      ] MAAT RPG – Awakening…",
        "[  ✨     ] MAAT RPG – Awakening…",
        "[   ✨    ] MAAT RPG – Awakening…",
        "[    ✨   ] MAAT RPG – Awakening…",
        "[     ✨  ] MAAT RPG – Awakening…",
        "[    ✨   ] MAAT RPG – Awakening…",
        "[   ✨    ] MAAT RPG – Awakening…",
        "[  ✨     ] MAAT RPG – Awakening…",
    ],
}


class Plugin:
    type = "chat"
    commands = {}  # kein Chat-Befehl

    def __init__(self):
        self._abort = False
        self._music_proc: subprocess.Popen | None = None

    def _lang(self) -> str:
        return get_language(("de", "en"))

    def _intro_lines(self):
        return INTRO_TEXT.get(self._lang(), INTRO_TEXT["de"])

    def _anim_frames(self):
        return ANIM_FRAMES.get(self._lang(), ANIM_FRAMES["de"])

    def _t(self, de: str, en: str) -> str:
        return en if self._lang() == "en" else de

    def _interactive_terminal(self) -> bool:
        return bool(
            getattr(sys.stdin, "isatty", lambda: False)()
            and getattr(sys.stdout, "isatty", lambda: False)()
        )

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
    def _play_music(self, path: str) -> bool:
        if not music_enabled():
            return False
        if not path or not os.path.isfile(path):
            return False

        self._stop_music()

        try:
            self._music_proc = subprocess.Popen(
                ["afplay", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            self._music_proc = None
            return False

    def _stop_music(self):
        proc = self._music_proc
        self._music_proc = None
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=1)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

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
                frames = self._anim_frames()
                frame = frames[idx % len(frames)]
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
        print(
            self._t(
                "\nMAAT RPG – Intro wird geladen… (ESC oder ENTER zum Überspringen)\n",
                "\nMAAT RPG – Intro is loading… (ESC or ENTER to skip)\n",
            )
        )

        if not self._interactive_terminal():
            print(
                self._t(
                    "[MAAT-RPG Intro] Kein interaktives Terminal erkannt - Intro wird übersprungen.\n",
                    "[MAAT-RPG Intro] No interactive terminal detected - skipping intro.\n",
                )
            )
            self._stop_music()
            return

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
                started = self._play_music(intro_mp3)
                if not started:
                    print(self._t("[MAAT-RPG Intro] Intro-Musik konnte nicht gestartet werden.", "[MAAT-RPG Intro] Failed to start intro music."))

            # 2) Pyramide
            if not self._show_ascii_pyramid():
                print("\n  MAAT RPG Intro abgebrochen.\n")
                return

            # 3) Story
            for line in self._intro_lines():
                if not self._slow_stream(line, speed=0.03):
                    print(self._t("\n MAAT RPG Intro abgebrochen.\n", "\n MAAT RPG intro aborted.\n"))
                    return

            if self._abort:
                print(self._t("\n MAAT RPG Intro abgebrochen.\n", "\n MAAT RPG intro aborted.\n"))
                return

            # 4) Restzeit bis TOTAL_INTRO_DURATION mit Animation füllen
            elapsed = time.time() - start_time
            remaining = TOTAL_INTRO_DURATION - elapsed
            if remaining > 0:
                self._run_animation(duration=remaining, interval=0.2)

            if self._abort:
                print(self._t("\n MAAT RPG Intro abgebrochen.\n", "\n MAAT RPG intro aborted.\n"))
                return

            # 5) Abschluss
            print(
                self._t(
                    "\n✨ MAAT RPG – Du bist bereit, dein Abenteuer zu starten.\n",
                    "\n✨ MAAT RPG – You are ready to begin your adventure.\n",
                )
            )

        finally:
            # Musik immer stoppen + Terminal zurücksetzen
            self._stop_music()
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
