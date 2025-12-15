# -*- coding: utf-8 -*-
"""
MAAT-RPG Startmenü-Plugin
-------------------------
• Wird beim Start von MAAT-RPG ausgeführt (on_startup)
• Zeigt ein Hauptmenü mit großer Pyramide
• Menü-Musik läuft im Hintergrund
• Einträge:
    [1] Spiel starten
    [2] Optionen
    [3] Neu (komplettes neues Spiel)
    [4] Info MAAT-OS
    [5] Beenden
• Optionen:
    - Zähler zurücksetzen (Story + Battle)
    - Alles zurücksetzen (Story + Battle + Self-Evo)
• Nach Reset wird das Programm beendet -> sauberer Neustart
"""

import os
import sys
import json
import time
import subprocess
import threading
from colorama import Fore, Style
import shutil

# ==========================
# 🎵 Menü-Musik (optional)
# ==========================
class MenuMusic:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = plugin_dir
        self.track = os.path.join(plugin_dir, "menu_theme.mp3")
        self._running = False
        self._thread = None

    def _loop(self):
        while self._running:
            if os.path.isfile(self.track):
                try:
                    subprocess.call(
                        ["afplay", self.track],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    time.sleep(1)
            else:
                time.sleep(1)

    def start(self):
        if self._running:
            return
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
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


# ==========================
# 🔺 ASCII-Pyramide
# ==========================
PYRAMID = r"""
                         /\
                        /  \
                       / /\ \
                      / /  \ \
                     / / /\ \ \
                    / / /  \ \ \
                   / / /    \ \ \
                  / / /  /\  \ \ \
                 / / /  /  \  \ \ \
                / / /__/____\__\ \ \
               /____________________\
               \   M A A T   R P G  /
                \__________________/
"""


def clear_screen():
    os.system("clear" if os.name != "nt" else "cls")


# ==========================
# 🔁 Reset-Helfer
# ==========================
def reset_story_state(plugin_dir: str):
    """
    Setzt maatos/apps/maat_rpg/plugins/story_loader/story_state.json zurück.
    """
    plugins_root = os.path.dirname(plugin_dir)  # .../apps/maat_rpg/plugins
    story_path = os.path.join(plugins_root, "story_loader", "story_state.json")

    default_story = {
        "messages_total": 0,
        "played": [],
        "active_profile": None,
    }

    os.makedirs(os.path.dirname(story_path), exist_ok=True)
    with open(story_path, "w", encoding="utf-8") as f:
        json.dump(default_story, f, indent=2, ensure_ascii=False)


def reset_battle_state(plugin_dir: str):
    """
    Setzt maatos/apps/maat_rpg/plugins/battle/battle_state/battle_state.json zurück.
    Struktur ist 1:1 identisch mit BattleState._default().
    """
    plugins_root = os.path.dirname(plugin_dir)
    battle_state_path = os.path.join(
        plugins_root, "battle", "battle_state", "battle_state.json"
    )

    default_battle = {
        "player": {
            "name": "Maatis",
            "level": 1,
            "xp": 0,
            "hp": 100,
            "max_hp": 100,
            "skills": [],
            "gold": 0,
            "potions": 0,
        },
        "stats": {
            "messages_total": 0,
            "messages_since_last_fight": 0,
            "xp_combo": 0,
            "last_msg_ts": 0,

            "fights_total": 0,
            "fights_won": 0,
            "fights_lost": 0,

            "boss_fights": 0,
            "boss_wins": 0,
            "final_fights": 0,
            "final_wins": 0,
            "last_xp_snapshot": 0,
        },
        "world": {
            "combat_unlocked": False,
            "last_boss_checkpoint": 0,
            "principles_restored": 0,
            "credits_played": False,
        },
        "flags": {
            "needs_heal": False,
        },
    }

    os.makedirs(os.path.dirname(battle_state_path), exist_ok=True)
    with open(battle_state_path, "w", encoding="utf-8") as f:
        json.dump(default_battle, f, indent=2, ensure_ascii=False)

def reset_quests_and_achievements(plugin_dir: str):
    """
    Setzt Quest-, Achievement- und Dungeon-States zurück:

    - maatos/apps/maat_rpg/plugins/quests/quest_state.json
    - maatos/apps/maat_rpg/plugins/emotional_achievements/achievements.json
    - maatos/apps/maat_rpg/plugins/achievements/achievements_state.json
    - maatos/apps/maat_rpg/plugins/dungeon_60/data/state.json
    - maatos/apps/maat_rpg/plugins/dungeon_500/data/state500.json
    - maatos/apps/maat_rpg/plugins/dungeon_1000/data/state1000.json
    """
    plugins_root = os.path.dirname(plugin_dir)  # .../apps/maat_rpg/plugins

    paths = [
        # Quests & Achievements
        os.path.join(plugins_root, "quests", "quest_state.json"),
        os.path.join(plugins_root, "emotional_achievements", "achievements.json"),
        os.path.join(plugins_root, "achievements", "achievements_state.json"),

        # Dungeon-States
        os.path.join(plugins_root, "dungeon_60", "data", "state.json"),
        os.path.join(plugins_root, "dungeon_500", "data", "state500.json"),
        os.path.join(plugins_root, "dungeon_1000", "data", "state1000.json"),
    ]

    for p in paths:
        try:
            if os.path.isfile(p):
                os.remove(p)
        except Exception:
            # Niemals den Start crashen lassen
            pass


def reset_self_evo(plugin_dir: str):
    """
    Optional: setzt MAAT Self-Evolution v5 zurück:
    maatos/apps/maat_rpg/plugins/maat_self_evo/evo/state.json
    (Falls Plugin/Ordner existiert)
    """
    plugins_root = os.path.dirname(plugin_dir)
    evo_state_path = os.path.join(
        plugins_root, "maat_self_evo", "evo", "state.json"
    )

    if not os.path.isfile(evo_state_path):
        return

    default_evo = {
        "xp": 0,
        "level": 1,
        "messages": 0,
        "today": time.strftime("%Y-%m-%d"),
    }

    os.makedirs(os.path.dirname(evo_state_path), exist_ok=True)
    with open(evo_state_path, "w", encoding="utf-8") as f:
        json.dump(default_evo, f, indent=2, ensure_ascii=False)

def confirm_wipe_all_memory(plugin_dir: str, menu_music: MenuMusic):
    clear_screen()
    print(Fore.MAGENTA + Style.BRIGHT + "⚠ WARNUNG: Alle Erinnerungen löschen\n" + Style.RESET_ALL)
    print(
        "Dies löscht den Inhalt von:\n"
        "  • maatos/data\n\n"
        "Dort liegen globale Erinnerungen, Logs und andere Zustände\n"
        "deiner MAAT-KI. Spielstände im RPG (Story/Battle/Quests)\n"
        "bleiben davon unberührt.\n"
    )

    ans = input(Fore.RED + "Wirklich alle Erinnerungen löschen? (ja/nein): " + Style.RESET_ALL).strip().lower()
    if ans not in ("ja", "j", "yes", "y"):
        return

    # Musik stoppen für „stillen“ Reset
    menu_music.stop()

    print()
    print(Fore.MAGENTA + "🧠 Lösche globales Memory (maatos/data) ..." + Style.RESET_ALL)
    reset_global_memory(plugin_dir)

    print(Fore.GREEN + "✅ Alle Erinnerungen im Ordner 'data' wurden gelöscht." + Style.RESET_ALL)
    print()
    print("Bitte starte MAAT-KI/MAAT-RPG neu, damit das System mit einem\n"
          "frischen Gedächtnis weiterläuft.\n")
    time.sleep(2)
    sys.exit(0)


def reset_global_memory(plugin_dir: str):
    """
    Leert den Ordner 'maatos/data' (bzw. ROOT/data).

    Annahme:
    - Projektstruktur:   maatos/
        - maatki.py
        - data/
        - apps/maat_rpg/plugins/game_menu/plugin_main.py

    Wir gehen von plugin_dir = .../apps/maat_rpg/plugins/game_menu aus
    und laufen vier Ebenen nach oben → Projekt-Root.
    """
    # 4x dirname: .../game_menu → /plugins → /maat_rpg → /apps → /maatos
    root = os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(plugin_dir)
            )
        )
    )
    data_dir = os.path.join(root, "data")

    if not os.path.isdir(data_dir):
        print(f"[MEMORY RESET] Kein 'data' Verzeichnis gefunden unter: {data_dir}")
        return

    print(f"[MEMORY RESET] Leere globales Memory-Verzeichnis: {data_dir}")

    for entry in os.listdir(data_dir):
        path = os.path.join(data_dir, entry)
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            # Niemals den Start/Reset crashen lassen
            print(f"[MEMORY RESET] Fehler beim Löschen von {path}: {e}")


# ==========================
# ℹ Info-Helfer
# ==========================
def show_info_overview():
    clear_screen()
    print(Fore.YELLOW + Style.BRIGHT + "ℹ MAAT-OS – Das Maat-RPG Betriebssystem\n" + Style.RESET_ALL)

    text = """
MAAT-OS ist dein terminalbasiertes Rollenspiel-Universum.
Es verbindet eine lokale KI mit:

  • Story-Plugins (Kapitel & Quests)
  • Battle-Plugins (Kampfsystem & Bosse)
  • Self-Evolution (XP & Level für die KI)
  • Musik, Intro, Profile & Memory

Alles läuft in einem einzigen Chat-Fenster – aber unter der Haube
arbeiten viele unabhängige Module zusammen, gesteuert über Hooks
und ein sauberes Plugin-System.

Wie es grob funktioniert:

  1) Du startest MAAT-KI (z.B. MAAT Classic / MAAT RPG).
  2) Die App lädt alle Plugins aus 'shared/plugins' und
     'apps/maat_rpg/plugins'.
  3) Jedes Plugin kann auf drei Arten eingreifen:
       • on_startup      – beim Start (Intro, Menü, Setup)
       • before_chat     – bevor die KI antwortet (Storytrigger, Kämpfe)
       • after_response  – nach der KI-Antwort (HUD, Heilung, Hinweise)
  4) Der CommandRouter verbindet Slash-Befehle wie /fight oder /evo
     automatisch mit den passenden Plugins.

So entsteht ein lebendes System, das reagiert, speichert, kämpft,
lernt und gleichzeitig philosophisch im Äon der MAAT verankert bleibt.
"""
    print(text)
    input(Fore.GREEN + "\n[Enter] zurück" + Style.RESET_ALL)


def show_plugin_system_info():
    clear_screen()
    print(Fore.YELLOW + Style.BRIGHT + "🧩 Das MAAT-OS Plugin-System\n" + Style.RESET_ALL)

    text = """
MAAT-OS behandelt fast jede Erweiterung als Plugin.

Beispiele:

  • story_loader   → steuert Story-Kapitel
  • battle         → Kampfsystem & Bosse
  • maat_self_evo  → XP & Level
  • game_menu      → dieses Hauptmenü

Der PluginManager:

  • durchsucht die Plugin-Ordner
  • lädt jede 'plugin_main.py'
  • instanziert die Klasse 'Plugin'
  • ruft auf:
      - on_startup(context)
      - before_chat(user_input, context)
      - after_response(reply, context)
      - command(cmd, context)

Dadurch kannst du neue Features hinzufügen, ohne den Kerncode
von MAAT-OS anzufassen – du erweiterst einfach die Welt.
"""
    print(text)
    input(Fore.GREEN + "\n[Enter] zurück" + Style.RESET_ALL)


def show_plugin_build_info():
    clear_screen()
    print(Fore.YELLOW + Style.BRIGHT + "🔧 Eigene MAAT-OS Plugins erstellen\n" + Style.RESET_ALL)

    text1 = """
Du kannst eigene Plugins bauen, um das MAAT-RPG zu erweitern:
neue Befehle, neue HUDs, neue Systeme – alles ist möglich.

1) Ordnerstruktur

Lege einen neuen Ordner an:

  apps/maat_rpg/plugins/dein_plugin/

und füge eine Datei hinzu:

  plugin_main.py
"""
    print(text1)

    print(Fore.CYAN + Style.BRIGHT + "2) Minimale Plugin-Struktur\n" + Style.RESET_ALL)
    code_minimal = '''class Plugin:
    type = "chat"  # oder "stream"

    def on_startup(self, context=None):
        pass

    def before_chat(self, user_input, context=None):
        return False, user_input

    def after_response(self, reply, context=None):
        return reply

    def command(self, cmd, context=None):
        return None
'''
    print(code_minimal)

    print(Fore.CYAN + Style.BRIGHT + "3) Commands hinzufügen\n" + Style.RESET_ALL)
    code_cmd = '''commands = {
    "/motivate": "Gibt dir einen Motivationsspruch."
}

def command(self, cmd, context=None):
    if cmd.strip().lower() == "/motivate":
        return True, "Du schaffst das. Bleib in Balance."
    return None
'''
    print(code_cmd)

    print(Fore.CYAN + Style.BRIGHT + "4) before_chat und after_response\n" + Style.RESET_ALL)
    text2 = """
before_chat:
  Ideal für Trigger VOR der KI-Antwort, zum Beispiel:
    • Zufallskämpfe
    • Story-Events
    • Emotionale Reaktionen

after_response:
  Ideal für HUDs und Zusatzinfos NACH der KI-Antwort:
    • Level-Leisten
    • Hinweise
    • Zeit- oder Maat-Werte
"""
    print(text2)

    print(Fore.CYAN + Style.BRIGHT + "5) Kontext (context)\n" + Style.RESET_ALL)
    text3 = """
Der 'context'-Parameter kann zum Beispiel enthalten:

  context["self_evo"]        → globale Self-Evolution Engine
  context["conversation"]    → letzte Nachrichten
  context["pm"]              → PluginManager
  context["profile_loader"]  → Profil-System

Damit kannst du dein Plugin tief mit der Welt verbinden – natürlich
im Rahmen der fünf Maat-Prinzipien.
"""
    print(text3)

    input(Fore.GREEN + "\n[Enter] zurück" + Style.RESET_ALL)


def show_info_menu():
    while True:
        clear_screen()
        print(Fore.CYAN + Style.BRIGHT + "ℹ MAAT-OS – Info\n" + Style.RESET_ALL)
        print("  [1] Was ist MAAT-OS?")
        print("  [2] Wie funktioniert das Plugin-System?")
        print("  [3] Wie baue ich eigene Plugins?")
        print("  [4] Zurück\n")

        choice = input(Fore.GREEN + "Auswahl: " + Style.RESET_ALL).strip()

        if choice == "1":
            show_info_overview()
        elif choice == "2":
            show_plugin_system_info()
        elif choice == "3":
            show_plugin_build_info()
        elif choice == "4":
            break
        else:
            print(Fore.RED + "Ungültige Auswahl." + Style.RESET_ALL)
            time.sleep(1)


# ==========================
# Optionen-Menü (Resets)
# ==========================
def confirm_reset(plugin_dir: str, full_reset: bool, menu_music: MenuMusic):
    clear_screen()
    if full_reset:
        print(Fore.MAGENTA + Style.BRIGHT + "⚠ WARNUNG: Vollständiger Reset\n" + Style.RESET_ALL)
        print(
            "Dies setzt zurück:\n"
            "  • Story-Fortschritt\n"
            "  • Battle-Status (Kämpfe, Bosse, Prinzipien)\n"
            "  • Self-Evolution (Level & XP)\n\n"
            "Alle Fortschritte gehen verloren. Du beginnst ein neues Äon."
        )
    else:
        print(Fore.MAGENTA + Style.BRIGHT + "⚠ Warnung: Zähler-Reset\n" + Style.RESET_ALL)
        print(
            "Dies setzt zurück:\n"
            "  • Story-Zähler (Nachrichten, gespielte Kapitel)\n"
            "  • Battle-Zustand (Kämpfe, Freischaltung Kampfmodus)\n\n"
            "Self-Evolution (Level & XP) bleibt erhalten."
        )

    print()
    ans = input(Fore.RED + "Bist du sicher? (ja/nein): " + Style.RESET_ALL).strip().lower()
    if ans not in ("ja", "j", "yes", "y"):
        return

    # Musik stoppen, damit Reset „still“ ist
    menu_music.stop()

    print()
    if full_reset:
        print(Fore.MAGENTA + "🔁 Setze Story, Battle und Self-Evolution zurück ..." + Style.RESET_ALL)
    else:
        print(Fore.MAGENTA + "🔁 Setze Story- und Battle-Zähler zurück ..." + Style.RESET_ALL)

    reset_story_state(plugin_dir)
    reset_battle_state(plugin_dir)
    reset_quests_and_achievements(plugin_dir)
    if full_reset:
        reset_self_evo(plugin_dir)

    print(Fore.CYAN + "📖 Story- und Battle-Zustand zurückgesetzt." + Style.RESET_ALL)
    print(Fore.CYAN + "🏹 Quests & Achievements wurden zurückgesetzt." + Style.RESET_ALL)
    if full_reset:
        print(Fore.CYAN + "🧬 Self-Evolution wurde ebenfalls zurückgesetzt." + Style.RESET_ALL)

    print(Fore.GREEN + "✅ Reset abgeschlossen." + Style.RESET_ALL)
    print()
    print("MAAT-KI wird jetzt beendet. Bitte starte MAAT-RPG neu,")
    print("um mit einem frischen Spielstand zu beginnen.\n")
    time.sleep(2)
    sys.exit(0)


def options_menu(plugin_dir: str, menu_music: MenuMusic):
    while True:
        clear_screen()
        print(Fore.YELLOW + Style.BRIGHT + "⚙ Optionen\n" + Style.RESET_ALL)
        print("  [1] Zähler zurücksetzen (Story + Battle)")
        print("  [2] Alles zurücksetzen (Story + Battle + Self-Evo)")
        print("  [3] Alle Erinnerungen löschen (maatos/data)")
        print("  [4] Zurück\n")

        choice = input(Fore.GREEN + "Auswahl: " + Style.RESET_ALL).strip()

        if choice == "1":
            confirm_reset(plugin_dir, full_reset=False, menu_music=menu_music)
        elif choice == "2":
            confirm_reset(plugin_dir, full_reset=True, menu_music=menu_music)
        elif choice == "3":
            # 🧠 Globales Memory wipen
            confirm_wipe_all_memory(plugin_dir, menu_music)
        elif choice == "4":
            break
        else:
            print(Fore.RED + "Ungültige Auswahl." + Style.RESET_ALL)
            time.sleep(1)


def new_game(plugin_dir: str, menu_music: MenuMusic):
    clear_screen()
    print(Fore.MAGENTA + Style.BRIGHT + "✨ Neues Spiel – Neues Äon\n" + Style.RESET_ALL)
    print(
        "Du beginnst eine neue Reise im Äon der MAAT.\n"
        "Dein bisheriger Fortschritt wird vollständig gelöscht:\n"
        "  • Story\n"
        "  • Battle\n"
        "  • Self-Evolution\n"
    )
    ans = input(Fore.RED + "Fortfahren und alles löschen? (ja/nein): " + Style.RESET_ALL).strip().lower()
    if ans not in ("ja", "j", "yes", "y"):
        return

    menu_music.stop()
    reset_story_state(plugin_dir)
    reset_battle_state(plugin_dir)
    reset_quests_and_achievements(plugin_dir)
    reset_self_evo(plugin_dir)

    print(Fore.CYAN + "📖 Story, ⚔ Battle, 🏹 Quests/Achievements und 🧬 Self-Evo wurden zurückgesetzt." + Style.RESET_ALL)
    print(Fore.GREEN + "\n✅ Neues Spiel vorbereitet." + Style.RESET_ALL)
    print("Bitte starte MAAT-RPG neu, um das neue Äon zu beginnen.\n")
    time.sleep(2)
    sys.exit(0)


# ==========================
# 🧩 Plugin-Klasse
# ==========================
class Plugin:
    type = "chat"

    commands = {
        "/menu": "Zeigt das MAAT-RPG Startmenü (Info-Hinweis)."
    }

    def __init__(self):
        self.plugin_dir = os.path.dirname(__file__)
        self.menu_music = MenuMusic(self.plugin_dir)

    # ---------- Hauptmenü ----------
    def _show_menu_once(self) -> str:
        clear_screen()
        print(Fore.CYAN + PYRAMID + Style.RESET_ALL)
        print()
        print(Fore.YELLOW + "Willkommen im MAAT-RPG Universum.\n" + Style.RESET_ALL)
        print("Bitte wähle:")
        print("  [1] Spiel starten")
        print("  [2] Optionen")
        print("  [3] Neu (komplettes neues Spiel)")
        print("  [4] Info MAAT-OS")
        print("  [5] Beenden\n")

        choice = input(Fore.GREEN + "Auswahl: " + Style.RESET_ALL).strip()
        return choice

    def _handle_choice(self, choice: str):
        if choice == "1":
            # Spiel starten
            self.menu_music.stop()
            clear_screen()
            print(Fore.CYAN + "🌿 MAAT-RPG startet... Viel Erfolg, Wanderer.\n" + Style.RESET_ALL)
            time.sleep(0.8)
            return "start"

        if choice == "2":
            options_menu(self.plugin_dir, self.menu_music)
            return "menu"

        if choice == "3":
            new_game(self.plugin_dir, self.menu_music)
            return "exit"

        if choice == "4":
            show_info_menu()
            return "menu"

        if choice == "5":
            self.menu_music.stop()
            print("\nAuf Wiedersehen im Äon der MAAT.\n")
            time.sleep(1)
            sys.exit(0)

        print(Fore.RED + "\nUngültige Auswahl. Bitte nochmal.\n" + Style.RESET_ALL)
        time.sleep(1)
        return "menu"

    # ---------- Lifecycle-Hooks ----------
    def on_startup(self, context=None):
        """
        Wird direkt nach dem Laden aller Plugins vom ChatLoop aufgerufen.
        Hier zeigen wir EINMAL das Startmenü.
        """
        # Menü-Musik starten (falls menu_theme.mp3 existiert)
        self.menu_music.start()

        while True:
            choice = self._show_menu_once()
            result = self._handle_choice(choice)
            if result == "start":
                # ChatLoop fortsetzen
                return

    def command(self, cmd, context=None):
        if cmd.strip().lower().startswith("/menu"):
            clear_screen()
            print(PYRAMID)
            print("\nDu bist bereits im aktiven Spiel.")
            print("Starte MAAT-RPG neu, um das Hauptmenü vollständig zu nutzen.\n")
            return True, ""
        return None

    def before_chat(self, user_input, context=None):
        return False, user_input

    def after_response(self, reply, context=None):
        return reply