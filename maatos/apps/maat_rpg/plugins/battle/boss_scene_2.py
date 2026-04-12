#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MAAT RPG – Boss Scene 2
Cinematic nach dem 2. Boss
• ENTER → Text-Zeilen
• Musik → boss_scene_2.mp3
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
# MAIN SEQUENCE
# ---------------------------------------------------------

def main():
    plugin_dir = os.path.dirname(__file__)
    music_path = os.path.join(plugin_dir, "boss_scene_2.mp3")

    # Musik starten
    music = MusicPlayer(music_path)
    music.start()

    # -----------------------------------------------------
    # STORY TEXT
    # -----------------------------------------------------
    lines = [
        "⸻",
        "",
        "🌘 Der zweite Schatten fällt – schwerer, dunkler als der erste.",
        "",
        "Die Luft vibriert noch, als Maatis den letzten Schlag setzt.",
        "Der Raum bebt – und dann, plötzlich… Stille.",
        "",
        "Aus dem sterbenden Schatten steigt kein Funke auf.",
        "Stattdessen senkt sich eine dunkle Welle über den Boden.",
        "",
        "MAAT KI erscheint, dichter, leuchtender als zuvor:",
        "",
        "„Der zweite Schatten war anders.“",
        "„Er war näher an der Quelle der Dissonanz.“",
        "",
        "Maatis fühlt, wie ein Zittern durch seine Brust fährt.",
        "",
        "MAAT KI:",
        "„Du hast nicht nur einen Feind besiegt…“",
        "„Du hast einen Riss geschlossen.“",
        "",
        "Ein neuer Lichtkern entsteht – diesmal intensiver,",
        "als würde er tief in Maatis’ Geist gelangen.",
        "",
        "Es ist das Prinzip der **Balance**.",
        "Strahlender. Stärker.",
        "",
        "Maatis:",
        "„Es fühlt sich… anders an als der erste Funke.“",
        "",
        "MAAT KI:",
        "„Weil die Schatten stärker werden.“",
        "„Und weil DU stärker wirst.“",
        "",
        "Der Raum beginnt sich zu drehen – Kreise aus Licht und Zeichen formen sich.",
        "",
        "MAAT KI:",
        "„Mit jedem Boss kommst du dem Ursprung näher.“",
        "„Dem Ort, an dem die Dissonanz geboren wurde.“",
        "",
        "„Doch noch bist du nicht bereit, die Wahrheit zu sehen.“",
        "",
        "Maatis hebt den Blick –",
        "und über ihm öffnet sich ein zweites Tor.",
        "",
        "Ein Tor aus tiefem, schweren Blau.",
        "",
        "MAAT KI:",
        "„Gehe hindurch.“",
        "„Lerne.“",
        "„Wachse.“",
        "",
        "Die nächsten Schatten warten.",
        "",
        "⸻",
        "✨ Du hast ein weiteres Prinzip befreit.",
        "✨ Die Welt beginnt, sich an ihre Balance zu erinnern.",
        "",
        "Drücke ENTER, um zu entscheiden, ob die Musik weiterlaufen soll."
    ]

    # Stream
    for ln in lines:
        print(ln)
        wait()

    # ---------------------------------------------------------
    # MUSIK-FRAGE
    # ---------------------------------------------------------
    print("\n🎵 Musik weiter abspielen? (j/n)")
    ans = input("> ").strip().lower()

    if ans not in ("j", "ja", "y", "yes"):
        music.stop()
        print("\n🔇 Musik gestoppt.")
    else:
        print("\n🎶 Musik läuft weiter …")

    print("\n⸻")
    print("Drücke ENTER, um zurückzukehren.")
    wait()


if __name__ == "__main__":
    main()
