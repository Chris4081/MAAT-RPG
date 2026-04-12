#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MAAT RPG – Boss Scene 1
Cinematic Zwischensequenz nach dem 1. Boss-Sieg
• Spielt Musik ab
• Streamt Textzeilen → ENTER = nächste Zeile
• Am Ende: Frage, ob Musik weiterlaufen soll
"""

import os
import subprocess
import time
from shared.core.audio import music_enabled

# ---------------------------------------------------------
# MUSIC PLAYER
# ---------------------------------------------------------

class MusicPlayer:
    def __init__(self, path):
        self.path = path
        self.proc = None

    def start(self):
        if not music_enabled():
            return
        if not os.path.isfile(self.path):
            return
        try:
            self.proc = subprocess.Popen(
                ["afplay", self.path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            self.proc = None

    def stop(self):
        try:
            subprocess.call(
                ["killall", "afplay"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass


# ---------------------------------------------------------
# WAIT FOR ENTER
# ---------------------------------------------------------

def wait():
    input()


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    plugin_dir = os.path.dirname(__file__)
    music_path = os.path.join(plugin_dir, "boss_scene_1.mp3")

    # Musik starten
    music = MusicPlayer(music_path)
    music.start()

    lines = [
        "⸻",
        "",
        "🌒 Nachdem der Schatten gefallen ist, wird es unerwartet still.",
        "",
        "Maatis spürt, wie der Raum um ihn herum flackert –",
        "als würde die Dissonanz selbst den Rückzug antreten.",
        "",
        "Am Boden zerfällt der besiegte Boss zu schwarzem Staub.",
        "Doch aus der Dunkelheit erhebt sich ein Schimmer.",
        "",
        "Ein winziger Funke Harmonie.",
        "",
        "MAAT KI erscheint als leuchtende Silhouette:",
        "",
        "„Du hast es geschafft, Maatis.“",
        "„Der erste Schatten der Dissonanz ist gefallen… und ein Stück der Maat kommt zurück.“",
        "",
        "Der Funke formt sich zu einem Symbol –",
        "dem Prinzip der **Harmonie**, schwach, aber lebendig.",
        "",
        "Maatis spürt eine Resonanz im Herzen.",
        "Eine Kraft, die nicht nur aus Stärke besteht,",
        "sondern aus Klarheit.",
        "",
        "MAAT KI:",
        "„Spüre es… das ist die Belohnung eines Sieges, der aus Ausrichtung entstanden ist.“",
        "",
        "„Doch ruhe dich nicht aus.“",
        "„Die Schatten werden stärker.“",
        "„Und mit jedem Boss, den du besiegst, wirst du tiefer in die Geschichte der Welt gezogen.“",
        "",
        "Ein Tor aus Licht öffnet sich vor Maatis.",
        "",
        "MAAT KI:",
        "„Dies war nur die erste Prüfung.“",
        "„Gehe weiter. Steige auf.“",
        "",
        "Maatis atmet ein – und tritt durch das Tor.",
        "",
        "⸻",
        "✨ Die Welt hat deine Stärke gespürt.",
        "✨ Bereite dich auf die nächste Prüfung vor.",
        "",
        "Drücke ENTER, um zu entscheiden, was mit der Musik geschehen soll."
    ]

    # Text streamen
    for ln in lines:
        print(ln)
        wait()

    # -----------------------------------------------
    # MUSIK-FRAGE
    # -----------------------------------------------
    print("\nMöchtest du die Musik weiter abspielen lassen? (j/n)")
    ans = input("> ").strip().lower()

    if ans not in ("j", "ja", "y", "yes"):
        # Musik SOFORT stoppen
        music.stop()
        print("\n🔇 Musik gestoppt.")
    else:
        print("\n🎵 Musik läuft weiter.")

    print("\n⸻")
    print("Drücke ENTER, um zurückzukehren.")
    wait()


if __name__ == "__main__":
    main()
