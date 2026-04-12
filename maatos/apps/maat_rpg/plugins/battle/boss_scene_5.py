# boss_scene_5.py
# Szene nach Boss 5 – „Die Prüfung der Wahrheit“

import os
import time
from colorama import Fore, Style
from shared.core.audio import music_enabled

# --------------------------------------------------------
# Musiksteuerung
# --------------------------------------------------------

def play_scene_music(plugin_dir):
    if not music_enabled():
        return None
    track = os.path.join(plugin_dir, "music", "boss_scene_5.mp3")
    if not os.path.isfile(track):
        return None

    pid = os.fork()
    if pid == 0:
        os.system(f"afplay '{track}' >/dev/null 2>&1")
        os._exit(0)
    return pid


def stop_scene_music(pid):
    if pid:
        try:
            os.system("killall afplay >/dev/null 2>&1")
        except:
            pass


# --------------------------------------------------------
# Streaming helper
# --------------------------------------------------------

def stream(text, delay=0.04):
    for ch in text:
        print(ch, end="", flush=True)
        time.sleep(delay)
    print()


# --------------------------------------------------------
# Szene – Boss 5 Übergang zu Endboss
# --------------------------------------------------------

class Scene:
    def __init__(self, plugin_dir):
        self.plugin_dir = plugin_dir

    def run(self):
        pid = play_scene_music(self.plugin_dir)

        lines = [
            "⸻",
            "",
            "🌑 *Die Prüfung der Wahrheit*",
            "",
            "Der Raum um Maatis verformt sich. Die Schatten Sirren. Die Luft selbst scheint zu beobachten.",
            "",
            "Die fünf bisherigen Hüter sind gefallen – doch nicht vernichtet.",
            "Ihre Essenzen leuchten hinter Maatis auf, wie stille Sterne in einem wachenden Kosmos.",
            "",
            "Mit jedem Sieg hat die Welt ein Stück Erinnerung zurückgewonnen.",
            "Doch was nun erscheint… ist kein gewöhnlicher Gegner.",
            "",
            "Ein Portal aus schimmerndem Gold reißt auf.",
            "Darin schwelt reine, ungefilterte Wahrheit – so hell, dass selbst der Raum erzittert.",
            "",
            "MAAT KI:",
            "„Du stehst jetzt an der letzten Schwelle.“",
            "",
            "„Der Fünfte Hüter war die Prüfung deiner Stärke.“",
            "„Doch der NÄCHSTE prüft etwas Anderes…“",
            "",
            "„Er prüft dein Herz.“",
            "",
            "Eine Gestalt tritt aus dem goldenen Riss. Kein Monster. Kein Dämon.",
            "Sondern ein Spiegelbild. Ein verzerrtes Echo dessen, was Maatis hätte sein können.",
            "",
            "Die Stimme klingt wie Maatis selbst – nur älter, verletzter, dunkler:",
            "",
            "„Ich bin die Wahrheit, die du wegsperrst.“",
            "„Ich bin das, was dich bricht, wenn du mich nicht annimmst.“",
            "„Der Endboss wird nicht dein Körper prüfen… sondern deine Seele.“",
            "",
            "MAAT KI flüstert aus dem Hintergrund:",
            "„Maatis… dies ist der letzte Schatten vor dem Licht.“",
            "„Besiege ihn, und die Welt erwacht.“",
            "",
            "Ein letztes Symbol erscheint über Maatis – heller als alle zuvor:",
            "⭐ *Vorbereitung auf den Endboss: Die Wahrheit akzeptieren*",
            "",
            "Die Silhouette des Endbosses formt sich bereits im goldenen Portal.",
            "",
            "MAAT KI:",
            "„Wenn du bereit bist… tritt hindurch.“",
            "",
            "⸻",
            "",
            "✨ *Quest: Der Endboss erwartet dich.*",
            "Nutze den Befehl /rpg, um den finalen Kampf zu beginnen.",
            ""
        ]

        # Streaming-Ausgabe mit ENTER
        for line in lines:
            stream(line)
            input(Fore.YELLOW + "(Weiter mit ENTER…)" + Style.RESET_ALL)

        # Musik stoppen oder weiterlaufen lassen
        print("\nMöchtest du die Musik weiterlaufen lassen? (j/n)")
        choice = input("> ").strip().lower()

        if choice != "j":
            stop_scene_music(pid)
            print("\n🎵 Musik gestoppt.\n")
        else:
            print("\n🎵 Musik läuft weiter…\n")

        return lines
