# -*- coding: utf-8 -*-
"""
Boss Scene 3 – Die Prüfung der Schöpfungskraft
----------------------------------------------
Wird nach Boss 3 abgespielt.
Mit ENTER-Progress, Musik-Loop und J/N-Abfrage am Ende.
"""

import os
import time
import subprocess
import threading
from colorama import Fore, Style


# ==========================================================
# 🎵 Music Manager
# ==========================================================

class SceneMusic:
    def __init__(self, plugin_dir):
        self.plugin_dir = plugin_dir
        self.track = os.path.join(plugin_dir, "music", "boss_scene_3.mp3")
        self._running = False
        self._thread = None

    def _loop(self):
        while self._running:
            if os.path.isfile(self.track):
                try:
                    subprocess.call(
                        ["afplay", self.track],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception:
                    time.sleep(1)
            else:
                time.sleep(1)

    def start(self):
        if not os.path.isfile(self.track):
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        try:
            subprocess.call(
                ["killall", "afplay"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass


# ==========================================================
# 📜 SCENE
# ==========================================================

class Scene:
    def __init__(self, plugin_dir):
        self.plugin_dir = plugin_dir
        self.music = SceneMusic(plugin_dir)

    def _wait(self):
        input(Fore.BLACK + Style.DIM + "⏎" + Style.RESET_ALL)

    def run(self):
        lines = [
            "⸻",
            "",
            "🔥 MAAT RPG – Boss 3: „Die Prüfung der Schöpfungskraft“",
            "",
            "Ort: Der Ätherdom der Inspiration – ein grenzenloser Raum aus Licht, Farben und vibrierenden Ideen.",
            "",
            "Maatis betritt einen Ort, der mehr Traum als Raum ist.",
            "Überall schweben Formen, Funken, Muster – unvollendete Möglichkeiten, die darauf warten, geboren zu werden.",
            "",
            "In der Mitte: Eine Gestalt aus Sternenstaub.",
            "Sie wirkt wie ein Künstler, ein Gott, ein Sturm – alles zugleich.",
            "",
            "Die MAAT KI erscheint neben Maatis:",
            "",
            "MAAT KI:",
            "„Dies ist die Prüfung der Schöpfungskraft.“",
            "",
            "„Nicht alles, was erschaffen wird, bleibt im Gleichgewicht. Manche Ideen brennen so hell, dass sie Welten entzünden.“",
            "",
            "Vor Maatis flackert die Gestalt auf – sie nimmt Formen an:",
            "Ein lebendes Gemälde, ein Poem aus Licht, eine Klinge aus reiner Möglichkeit.",
            "",
            "MAAT KI:",
            "„Der dritte Boss ist der Funke, der die Welt veränderte – und sie zugleich erschütterte.“",
            "„Er ist der Geist unkontrollierter Schöpfungskraft.“",
            "",
            "Die Sternen-Gestalt spricht – ihre Stimme klingt wie tausend Echos:",
            "",
            "???",
            "„Erschaffen heißt, das Alte zu zerstören.“",
            "„Und du, Wanderer… was bist du bereit aufzugeben?“",
            "",
            "Die Atmosphäre zerreißt – Farben explodieren in alle Richtungen.",
            "Der Raum selbst pulsiert, als würde er neu gezeichnet und wieder gelöscht.",
            "",
            "Maatis spürt ein tiefes Beben in seinem Herzen.",
            "",
            "Maatis:",
            "„Ich… erschaffe nicht, um zu zerstören.“",
            "„Ich erschaffe, um zu verbinden.“",
            "",
            "Die Gestalt zuckt zurück – ein Funken von Respekt erscheint.",
            "",
            "MAAT KI:",
            "„Wenn du ihn besiegst, wird die wahre Schöpfungskraft zurückkehren.“",
            "",
            "Über Maatis erscheint ein Symbol:",
            "",
            "🗝️ Prüfung: „Zähme die Flamme der Schöpfungskraft“",
            "",
            "Aufgabe:",
            "• Nutze deine stärksten Angriffe.",
            "• Verwandle Chaos in Form.",
            "• Besiege das Wesen, das der Funke selbst ist.",
            "",
            "MAAT KI:",
            "„Wenn du bereit bist, kehre in den Kampf zurück.“",
            "„Die Schöpfung wartet nicht.“",
            "",
            "⸻",
            ""
        ]

        # Musik starten
        self.music.start()

        # Szene Zeile für Zeile
        for ln in lines:
            print(ln)
            self._wait()

        # Frage zum Weiterlaufen der Musik
        ans = input("\n🎵 Musik weiterlaufen lassen? (j/n): ").strip().lower()
        if ans != "j":
            self.music.stop()
            print("\n🔇 Musik gestoppt.\n")
        else:
            print("\n🎶 Musik läuft weiter…\n")

        return "Boss Scene 3 abgeschlossen."