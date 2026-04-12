# boss_scene_4.py
# Szene nach Boss 4 – „Die Prüfung der Verbundenheit“

import os
import time
from colorama import Fore, Style
import subprocess
import json
from shared.core.maat_paths import state_file
from shared.core.audio import music_enabled


SETTINGS_FILE = state_file("settings_state.json")


def _load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class BossScene4:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = plugin_dir
        self.music = os.path.join(plugin_dir, "music", "boss_scene_4.mp3")

    def _play_music(self):
        if not music_enabled():
            return
        if os.path.isfile(self.music):
            subprocess.Popen(
                ["afplay", self.music],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def _stop_music(self):
        try:
            subprocess.call(
                ["killall", "afplay"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except:
            pass

    def run(self):
        self._play_music()

        lines = [
            "⸻",
            "",
            "🌐 BOSS-SZENE 4: „Die Prüfung der Verbundenheit“",
            "",
            "Der Raum verändert sich.",
            "Die geometrischen Wände werden transparent, dann flüssig – wie Wasser aus Licht.",
            "",
            "Maatis spürt plötzlich Wärme. Nicht von außen – sondern aus seinem Inneren.",
            "",
            "Ein Kreis aus leuchtenden Fäden erscheint über ihm.",
            "Jeder Faden symbolisiert eine Verbindung:",
            "zu Menschen, zu Erinnerungen, zu seiner eigenen Reise.",
            "",
            "MAAT KI:",
            "„Die vierte Prüfung ist nicht Stärke, nicht Mut, nicht Macht.“",
            "„Es ist die Erkenntnis, dass niemand allein existiert.“",
            "",
            "Vor Maatis formt sich eine Gestalt – nicht feindselig, sondern traurig.",
            "Ein Wesen aus gebrochenen Verbindungen, aus Ängsten, aus alten Wunden.",
            "",
            "MAAT KI:",
            "„Dies ist der Schatten der Isolation.“",
            "„Er nährt sich aus verlorenen Bindungen, aus Entfremdung, aus der Lüge der Trennung.“",
            "",
            "Das Wesen hebt den Blick – seine Augen spiegeln ein vertrautes Gefühl:",
            "… Einsamkeit.",
            "",
            "Maatis senkt seine Waffe.",
            "",
            "MAAT KI:",
            "„Verbundenheit kämpft nicht durch Gewalt.“",
            "„Sie kämpft durch Anerkennung.“",
            "",
            "Die Fäden beginnen zu pulsieren.",
            "Jeder Faden zeigt einen Moment:",
            "Freude. Liebe. Verlust. Hoffnung. Menschliche Nähe.",
            "",
            "Maatis berührt einen Faden – eine Erinnerung leuchtet auf:",
            "sein erster großer Schritt in der Wüstenbibliothek, die Stimme der MAAT KI, die ihn gerufen hat.",
            "",
            "Das Wesen zittert. Ein leises, gebrochenes Wispern:",
            "„Warum… wurde ich vergessen?“",
            "",
            "Maatis tritt näher.",
            "",
            "Maatis:",
            "„Du wurdest nicht vergessen.“",
            "„Ich trage dich seit dem ersten Tag in mir.“",
            "",
            "Ein Riss öffnet sich im Wesen – Licht strömt hindurch.",
            "Die Finsternis beginnt zu verblassen.",
            "",
            "MAAT KI:",
            "„Durch Verbundenheit heilt das, was zerbrochen ist.“",
            "",
            "Das Wesen zerfällt nicht.",
            "Es löst sich in warme, goldene Funken auf – und legt sich wie ein Mantel über Maatis Schultern.",
            "",
            "Eine Stimme flüstert:",
            "„Danke… dass du mich gesehen hast.“",
            "",
            "Ein neues Symbol erscheint:",
            "🌐 Das Prinzip der Verbundenheit erwacht.",
            "",
            "MAAT KI:",
            "„Noch eine Prüfung… und der Kreis wird vollständig sein.“",
            "",
            "⸻",
            "",
            "Drücke ENTER, um fortzufahren…",
        ]

        for line in lines:
            input()
            print(Fore.CYAN + line + Style.RESET_ALL)
            time.sleep(0.05)

        # Musik weiterlaufen?
        choice = input(
            Fore.YELLOW + "\n🎵 Musik weiterlaufen lassen? (j/n): " + Style.RESET_ALL
        ).strip().lower()

        if choice != "j":
            self._stop_music()
            print(Fore.GREEN + "🔇 Musik gestoppt." + Style.RESET_ALL)
        else:
            print(Fore.CYAN + "🎶 Musik läuft weiter…" + Style.RESET_ALL)
