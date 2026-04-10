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
from colorama import Fore, Style
import shutil
from shared.core.maat_paths import state_file, get_data_dir
from shared.core.audio import ManagedAudioPlayer


SETTINGS_FILE = state_file("settings_state.json")


TEXT = {
    "de": {
        "lang_title": "Sprache waehlen",
        "lang_prompt": "Language / Sprache:",
        "lang_german": "[1] Deutsch",
        "lang_english": "[2] English",
        "lang_invalid": "Ungueltige Auswahl. Bitte 1 oder 2 waehlen.",
        "brand": "MAAT-OS / MAAT-RPG",
        "version": "Version 0.2 - Rueckkehr der Prinzipien",
        "title_continue": "Druecke Enter zum Fortfahren",
        "fallback_title": "Suchender im Aeon der Maat",
        "fallback_rank": "Erwachend",
        "fallback_motif": "Die Welt tastet nach der Form, die Maatis annimmt.",
        "profile": "Pfadprofil",
        "rank": "Rang",
        "motif": "Motiv",
        "progress": "Fortschritt",
        "potions": "Traenke",
        "boss_wins": "Boss-Siege",
        "final_wins": "Finalsiege",
        "principles": "Prinzipien",
        "journal_entries": "Journal-Eintraege",
        "combat_achievements": "Kampf-Erfolge",
        "menu_intro": "Waehl den naechsten Schritt fuer Maatis.",
        "menu_start": "[1] Erwachen und Spiel starten",
        "menu_options": "[2] Optionen und Reset",
        "menu_new": "[3] Neues Aeon beginnen",
        "menu_info": "[4] Info MAAT-OS",
        "menu_exit": "[5] Beenden",
        "menu_shortcuts": "Direkt im Spiel wichtig: /journal  /erfolge  /xp  /maatbond",
        "choice": "Auswahl: ",
        "start_msg": "🌿 MAAT-RPG startet... Viel Erfolg, Wanderer.",
        "bye": "Auf Wiedersehen im Aeon der MAAT.",
        "invalid": "Ungueltige Auswahl. Bitte nochmal.",
        "active_game": "Du bist bereits im aktiven Spiel.",
        "restart_hint": "Starte MAAT-RPG neu, um das Hauptmenue vollstaendig zu nutzen.",
        "active_shortcuts": "Im aktuellen Lauf helfen dir besonders: /journal, /erfolge, /xp, /maatbond",
        "options_title": "⚙ Optionen",
        "opt_reset": "[1] Zaehler zuruecksetzen (Story + Battle)",
        "opt_full_reset": "[2] Alles zuruecksetzen (Story + Battle + Self-Evo)",
        "opt_memory": "[3] Alle Erinnerungen loeschen (Application Support/MAAT-RPG/data)",
        "opt_language": "[4] Sprache wechseln",
        "opt_back": "[5] Zurueck",
        "info_title": "ℹ MAAT-OS – Info",
        "info_overview": "[1] Was ist MAAT-OS?",
        "info_plugins": "[2] Wie funktioniert das Plugin-System?",
        "info_build": "[3] Wie baue ich eigene Plugins?",
        "info_back": "[4] Zurueck",
        "enter_back": "\n[Enter] zurueck",
        "overview_title": "ℹ MAAT-OS – Das Maat-RPG Betriebssystem",
        "plugin_title": "🧩 Das MAAT-OS Plugin-System",
        "build_title": "🔧 Eigene MAAT-OS Plugins erstellen",
        "build_section_2": "2) Minimale Plugin-Struktur",
        "build_section_3": "3) Commands hinzufuegen",
        "build_section_4": "4) before_chat und after_response",
        "build_section_5": "5) Kontext (context)",
        "reset_warning_full": "⚠ WARNUNG: Vollstaendiger Reset",
        "reset_warning_small": "⚠ Warnung: Zaehler-Reset",
        "reset_confirm": "Bist du sicher? (ja/nein): ",
        "memory_warning": "⚠ WARNUNG: Alle Erinnerungen loeschen",
        "memory_confirm": "Wirklich alle Erinnerungen loeschen? (ja/nein): ",
        "new_game_title": "✨ Neues Spiel – Neues Aeon",
        "new_game_confirm": "Fortfahren und alles loeschen? (ja/nein): ",
    },
    "en": {
        "lang_title": "Choose language",
        "lang_prompt": "Language / Sprache:",
        "lang_german": "[1] German",
        "lang_english": "[2] English",
        "lang_invalid": "Invalid choice. Please choose 1 or 2.",
        "brand": "MAAT-OS / MAAT-RPG",
        "version": "Version 0.2 - Return of the Principles",
        "title_continue": "Press enter to continue",
        "fallback_title": "Seeker in the Aeon of Maat",
        "fallback_rank": "Awakening",
        "fallback_motif": "The world is feeling for the shape Maatis is becoming.",
        "profile": "Path Profile",
        "rank": "Rank",
        "motif": "Motive",
        "progress": "Progress",
        "potions": "Potions",
        "boss_wins": "Boss Victories",
        "final_wins": "Final Victories",
        "principles": "Principles",
        "journal_entries": "Journal Entries",
        "combat_achievements": "Combat Achievements",
        "menu_intro": "Choose Maatis' next step.",
        "menu_start": "[1] Awaken and start the game",
        "menu_options": "[2] Options and reset",
        "menu_new": "[3] Begin a new aeon",
        "menu_info": "[4] MAAT-OS info",
        "menu_exit": "[5] Quit",
        "menu_shortcuts": "Useful in game: /journal  /erfolge  /xp  /maatbond",
        "choice": "Choice: ",
        "start_msg": "🌿 MAAT-RPG is starting... Walk well, wanderer.",
        "bye": "Farewell in the Aeon of MAAT.",
        "invalid": "Invalid choice. Please try again.",
        "active_game": "You are already inside the active game.",
        "restart_hint": "Restart MAAT-RPG to use the full main menu.",
        "active_shortcuts": "Helpful right now: /journal, /erfolge, /xp, /maatbond",
        "options_title": "⚙ Options",
        "opt_reset": "[1] Reset counters (Story + Battle)",
        "opt_full_reset": "[2] Reset everything (Story + Battle + Self-Evo)",
        "opt_memory": "[3] Delete all memories (Application Support/MAAT-RPG/data)",
        "opt_language": "[4] Change language",
        "opt_back": "[5] Back",
        "info_title": "ℹ MAAT-OS – Info",
        "info_overview": "[1] What is MAAT-OS?",
        "info_plugins": "[2] How does the plugin system work?",
        "info_build": "[3] How do I build my own plugins?",
        "info_back": "[4] Back",
        "enter_back": "\n[Enter] back",
        "overview_title": "ℹ MAAT-OS – The MAAT-RPG Operating World",
        "plugin_title": "🧩 The MAAT-OS Plugin System",
        "build_title": "🔧 Build Your Own MAAT-OS Plugins",
        "build_section_2": "2) Minimal plugin structure",
        "build_section_3": "3) Add commands",
        "build_section_4": "4) before_chat and after_response",
        "build_section_5": "5) Context (context)",
        "reset_warning_full": "⚠ WARNING: Full reset",
        "reset_warning_small": "⚠ Warning: Counter reset",
        "reset_confirm": "Are you sure? (yes/no): ",
        "memory_warning": "⚠ WARNING: Delete all memories",
        "memory_confirm": "Really delete all memories? (yes/no): ",
        "new_game_title": "✨ New Game – New Aeon",
        "new_game_confirm": "Continue and delete everything? (yes/no): ",
    },
}


def _load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_settings(data: dict):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
# ==========================
# 🎵 Menü-Musik (optional)
# ==========================
class MenuMusic:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = plugin_dir
        self.track = os.path.join(plugin_dir, "menu_theme.mp3")
        self._player = ManagedAudioPlayer(self.track)

    def start(self):
        self._player.start_loop(self.track)

    def stop(self):
        self._player.stop()


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
                \        0.2       /
                 \________________/
"""

def clear_screen():
    os.system("clear" if os.name != "nt" else "cls")


def _load_state(name: str) -> dict:
    path = state_file(name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _localize_path_profile(profile: dict, language: str) -> dict:
    localized = dict(profile or {})
    if language != "en":
        return localized

    title_map = {
        "Grenzhüter der Wahrheit": "Boundary Keeper of Truth",
        "Grenzhüter der Erinnerung": "Boundary Keeper of Memory",
        "Klangsucher der Harmonie": "Tone Seeker of Harmony",
        "Formträger der Schöpfung": "Form Bearer of Creation",
        "Wegsucher": "Path Seeker",
    }
    rank_map = {
        "Erwachend": "Awakening",
        "Vertieft": "Deepening",
        "Verankert": "Anchored",
    }
    motif_map = {
        "Wahrheit darf Grenzen nicht verletzen.": "Truth must not violate boundaries.",
        "Erinnerung darf nicht zu Besitz werden.": "Memory must not become possession.",
        "Harmonie ohne Wahrheit bleibt fragil.": "Harmony without truth remains fragile.",
    }

    title = localized.get("title")
    rank = localized.get("rank")
    motif = localized.get("motif")
    if title:
        localized["title"] = title_map.get(title, title)
    if rank:
        localized["rank"] = rank_map.get(rank, rank)
    if motif:
        localized["motif"] = motif_map.get(motif, motif)
    return localized


def _menu_context() -> dict:
    story = _load_state("story_state.json")
    battle = _load_state("battle_state.json")
    settings = _load_settings()
    language = settings.get("language", "de")

    player = battle.get("player", {})
    stats = battle.get("stats", {})
    world = battle.get("world", {})
    achievements = battle.get("achievements", {})
    profile = story.get("path_profile") if isinstance(story.get("path_profile"), dict) else {}
    profile = _localize_path_profile(profile, language)

    return {
        "profile_title": profile.get("title"),
        "profile_rank": profile.get("rank"),
        "profile_motif": profile.get("motif"),
        "level": int(player.get("level", 1) or 1),
        "xp": int(player.get("xp", 0) or 0),
        "gold": int(player.get("gold", 0) or 0),
        "potions": int(player.get("potions", 0) or 0),
        "boss_wins": int(stats.get("boss_wins", 0) or 0),
        "final_wins": int(stats.get("final_wins", 0) or 0),
        "principles_restored": int(world.get("principles_restored", 0) or 0),
        "journal_entries": len(story.get("journal", []) or []),
        "combat_achievements": len(achievements.get("combat", []) or []),
    }


def _render_progress_panel(language: str) -> str:
    t = TEXT.get(language, TEXT["de"])
    ctx = _menu_context()
    profile_title = ctx["profile_title"] or t["fallback_title"]
    profile_rank = ctx["profile_rank"] or t["fallback_rank"]
    profile_motif = ctx["profile_motif"] or t["fallback_motif"]
    lines = [
        Fore.YELLOW + Style.BRIGHT + t["brand"] + Style.RESET_ALL,
        Fore.CYAN + Style.BRIGHT + t["version"] + Style.RESET_ALL,
        "",
        Fore.MAGENTA + Style.BRIGHT + f"{t['profile']}: {profile_title}" + Style.RESET_ALL,
        f"{t['rank']}: {profile_rank}",
        f"{t['motif']}: {profile_motif}",
        "",
        Fore.CYAN + t["progress"] + Style.RESET_ALL,
        f"Level {ctx['level']}  |  XP {ctx['xp']}  |  {t['potions']} {ctx['potions']}  |  Gold {ctx['gold']}",
        f"{t['boss_wins']} {ctx['boss_wins']}  |  {t['final_wins']} {ctx['final_wins']}  |  {t['principles']} {ctx['principles_restored']}/5",
        f"{t['journal_entries']} {ctx['journal_entries']}  |  {t['combat_achievements']} {ctx['combat_achievements']}",
    ]
    return "\n".join(lines)


def _render_title_screen(language: str) -> str:
    t = TEXT.get(language, TEXT["de"])
    lines = [
        Fore.CYAN + Style.BRIGHT + PYRAMID + Style.RESET_ALL,
        "",
        Fore.YELLOW + Style.BRIGHT + t["brand"] + Style.RESET_ALL,
        Fore.CYAN + Style.BRIGHT + t["version"] + Style.RESET_ALL,
        "",
        Fore.GREEN + Style.BRIGHT + t["title_continue"] + Style.RESET_ALL,
    ]
    return "\n".join(lines)


def _yes(answer: str) -> bool:
    return answer.strip().lower() in ("ja", "j", "yes", "y")


def choose_language() -> str:
    while True:
        clear_screen()
        print(Fore.CYAN + PYRAMID + Style.RESET_ALL)
        print()
        print(Fore.YELLOW + Style.BRIGHT + TEXT["de"]["lang_title"] + " / " + TEXT["en"]["lang_title"] + Style.RESET_ALL)
        print()
        print(TEXT["de"]["lang_prompt"])
        print("  " + TEXT["de"]["lang_german"])
        print("  " + TEXT["de"]["lang_english"])
        print()
        choice = input(Fore.GREEN + "> " + Style.RESET_ALL).strip()
        if choice == "1":
            return "de"
        if choice == "2":
            return "en"
        print(Fore.RED + TEXT["de"]["lang_invalid"] + Style.RESET_ALL)
        time.sleep(1)


# ==========================
# 🔁 Reset-Helfer
# ==========================
def reset_story_state(plugin_dir: str):
    story_path = state_file("story_state.json")

    default_story = {
        "messages_total": 0,
        "played": [],
        "active_profile": None,
        "choices": {},
        "choice_labels": {},
        "consequences": {},
        "path_profile": None,
        "reflection_seen": [],
        "journal": [],
    }

    os.makedirs(os.path.dirname(story_path), exist_ok=True)
    with open(story_path, "w", encoding="utf-8") as f:
        json.dump(default_story, f, indent=2, ensure_ascii=False)


def reset_battle_state(plugin_dir: str):
    battle_state_path = state_file("battle_state.json")

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
        "achievements": {
            "combat": [],
        },
    }

    os.makedirs(os.path.dirname(battle_state_path), exist_ok=True)
    with open(battle_state_path, "w", encoding="utf-8") as f:
        json.dump(default_battle, f, indent=2, ensure_ascii=False)

def reset_quests_and_achievements(plugin_dir: str):
    paths = [
        state_file("quest_state.json"),
        state_file("achievements.json"),
        state_file("achievements_state.json"),
        state_file("state.json"),
        state_file("state500.json"),
        state_file("state1000.json"),
    ]

    for p in paths:
        try:
            if os.path.isfile(p):
                os.remove(p)
        except Exception:
            pass


def reset_self_evo(plugin_dir: str):
    evo_state_path = state_file("self_evo_state.json")

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
    settings = _load_settings()
    language = settings.get("language", "de")
    t = TEXT.get(language, TEXT["de"])
    clear_screen()
    print(Fore.MAGENTA + Style.BRIGHT + t["memory_warning"] + "\n" + Style.RESET_ALL)
    print(
        "Dies löscht den Inhalt von:\n"
        "~/Library/Application Support/MAAT-RPG/data\n\n"
        "Dort liegen globale Erinnerungen, Logs und andere Zustände\n"
        "deiner MAAT-KI. Spielstände im RPG (Story/Battle/Quests)\n"
        "bleiben davon unberührt.\n"
    )

    ans = input(Fore.RED + t["memory_confirm"] + Style.RESET_ALL).strip().lower()
    if not _yes(ans):
        return

    # Musik stoppen für „stillen“ Reset
    menu_music.stop()

    print()
    print(Fore.MAGENTA + "🧠 Lösche globales Memory (~/Library/Application Support/MAAT-RPG/data) ..." + Style.RESET_ALL)
    reset_global_memory(plugin_dir)

    print(Fore.GREEN + "✅ Alle Erinnerungen im Ordner 'data' wurden gelöscht." + Style.RESET_ALL)
    print()
    print("Bitte starte MAAT-KI/MAAT-RPG neu, damit das System mit einem\n"
          "frischen Gedächtnis weiterläuft.\n")
    time.sleep(2)
    sys.exit(0)

def reset_global_memory(plugin_dir: str):
    data_dir = str(get_data_dir())

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
            print(f"[MEMORY RESET] Fehler beim Löschen von {path}: {e}")



# ==========================
# ℹ Info-Helfer
# ==========================
def show_info_overview():
    settings = _load_settings()
    language = settings.get("language", "de")
    t = TEXT.get(language, TEXT["de"])
    clear_screen()
    print(Fore.YELLOW + Style.BRIGHT + t["overview_title"] + "\n" + Style.RESET_ALL)

    text = """
MAAT-OS ist dein terminalbasiertes Rollenspiel-Universum.
Es verbindet eine lokale KI mit:

  • Story-Plugins (Kapitel & Quests)
  • Battle-Plugins (Kampfsystem & Bosse)
  • Self-Evolution (XP & Level fuer die KI)
  • Musik, Intro, Profile & Memory

Alles laeuft in einem einzigen Chat-Fenster – aber unter der Haube
arbeiten viele unabhaengige Module zusammen, gesteuert ueber Hooks
und ein sauberes Plugin-System.

Wie es grob funktioniert:

  1) Du startest MAAT-KI (z.B. MAAT Classic / MAAT RPG).
  2) Die App laedt alle Plugins aus 'shared/plugins' und
     'apps/maat_rpg/plugins'.
  3) Jedes Plugin kann auf drei Arten eingreifen:
       • on_startup      – beim Start (Intro, Menue, Setup)
       • before_chat     – bevor die KI antwortet (Storytrigger, Kaempfe)
       • after_response  – nach der KI-Antwort (HUD, Heilung, Hinweise)
  4) Der CommandRouter verbindet Slash-Befehle wie /fight oder /evo
     automatisch mit den passenden Plugins.

So entsteht ein lebendes System, das reagiert, speichert, kaempft,
lernt und gleichzeitig philosophisch im Aeon der MAAT verankert bleibt.
""" if language == "de" else """
MAAT-OS is your terminal-based roleplaying universe.
It connects a local KI with:

  • story plugins (chapters & quests)
  • battle plugins (combat system & bosses)
  • self-evolution (XP & level for the KI)
  • music, intro, profiles & memory

Everything runs inside a single chat window – but beneath the surface
many independent modules work together, driven by hooks
and a clean plugin system.

How it works in broad strokes:

  1) You start MAAT-KI (for example MAAT Classic / MAAT RPG).
  2) The app loads all plugins from 'shared/plugins' and
     'apps/maat_rpg/plugins'.
  3) Each plugin can intervene in three ways:
       • on_startup      – at startup (intro, menu, setup)
       • before_chat     – before the KI answers (story triggers, battles)
       • after_response  – after the KI answer (HUD, healing, hints)
  4) The CommandRouter automatically connects slash commands such as
     /fight or /evo to the correct plugins.

This creates a living system that reacts, remembers, fights,
learns, and still remains philosophically rooted in the Aeon of MAAT.
"""
    print(text)
    input(Fore.GREEN + t["enter_back"] + Style.RESET_ALL)


def show_plugin_system_info():
    settings = _load_settings()
    language = settings.get("language", "de")
    t = TEXT.get(language, TEXT["de"])
    clear_screen()
    print(Fore.YELLOW + Style.BRIGHT + t["plugin_title"] + "\n" + Style.RESET_ALL)

    text = """
MAAT-OS behandelt fast jede Erweiterung als Plugin.

Beispiele:

  • story_loader   → steuert Story-Kapitel
  • battle         → Kampfsystem & Bosse
  • maat_self_evo  → XP & Level
  • game_menu      → dieses Hauptmenue

Der PluginManager:

  • durchsucht die Plugin-Ordner
  • laedt jede 'plugin_main.py'
  • instanziert die Klasse 'Plugin'
  • ruft auf:
      - on_startup(context)
      - before_chat(user_input, context)
      - after_response(reply, context)
      - command(cmd, context)

Dadurch kannst du neue Features hinzufuegen, ohne den Kerncode
von MAAT-OS anzufassen – du erweiterst einfach die Welt.
""" if language == "de" else """
MAAT-OS treats almost every extension as a plugin.

Examples:

  • story_loader   → controls story chapters
  • battle         → combat system & bosses
  • maat_self_evo  → XP & level
  • game_menu      → this main menu

The PluginManager:

  • scans the plugin folders
  • loads every 'plugin_main.py'
  • instantiates the class 'Plugin'
  • calls:
      - on_startup(context)
      - before_chat(user_input, context)
      - after_response(reply, context)
      - command(cmd, context)

Because of that, you can add new features without touching
the MAAT-OS core code – you simply extend the world.
"""
    print(text)
    input(Fore.GREEN + t["enter_back"] + Style.RESET_ALL)


def show_plugin_build_info():
    settings = _load_settings()
    language = settings.get("language", "de")
    t = TEXT.get(language, TEXT["de"])
    clear_screen()
    print(Fore.YELLOW + Style.BRIGHT + t["build_title"] + "\n" + Style.RESET_ALL)

    text1 = """
Du kannst eigene Plugins bauen, um das MAAT-RPG zu erweitern:
neue Befehle, neue HUDs, neue Systeme – alles ist moeglich.

1) Ordnerstruktur

Lege einen neuen Ordner an:

  apps/maat_rpg/plugins/dein_plugin/

und fuege eine Datei hinzu:

  plugin_main.py
""" if language == "de" else """
You can build your own plugins to expand MAAT-RPG:
new commands, new HUDs, new systems – everything is possible.

1) Folder structure

Create a new folder:

  apps/maat_rpg/plugins/your_plugin/

and add a file:

  plugin_main.py
"""
    print(text1)

    print(Fore.CYAN + Style.BRIGHT + t["build_section_2"] + "\n" + Style.RESET_ALL)
    code_minimal = '''class Plugin:
    type = "chat"  # or "stream"

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

    print(Fore.CYAN + Style.BRIGHT + t["build_section_3"] + "\n" + Style.RESET_ALL)
    code_cmd = '''commands = {
    "/motivate": "Gives you a motivational line."
}

def command(self, cmd, context=None):
    if cmd.strip().lower() == "/motivate":
        return True, "You can do this. Stay in balance."
    return None
'''
    print(code_cmd)

    print(Fore.CYAN + Style.BRIGHT + t["build_section_4"] + "\n" + Style.RESET_ALL)
    text2 = """
before_chat:
  Ideal fuer Trigger VOR der KI-Antwort, zum Beispiel:
    • Zufallskämpfe
    • Story-Events
    • Emotionale Reaktionen

after_response:
  Ideal für HUDs und Zusatzinfos NACH der KI-Antwort:
    • Level-Leisten
    • Hinweise
    • Zeit- oder Maat-Werte
""" if language == "de" else """
before_chat:
  Ideal for triggers BEFORE the KI response, for example:
    • random battles
    • story events
    • emotional reactions

after_response:
  Ideal for HUDs and extra information AFTER the KI response:
    • level bars
    • hints
    • time or maat values
"""
    print(text2)

    print(Fore.CYAN + Style.BRIGHT + t["build_section_5"] + "\n" + Style.RESET_ALL)
    text3 = """
Der 'context'-Parameter kann zum Beispiel enthalten:

  context["self_evo"]        → globale Self-Evolution Engine
  context["conversation"]    → letzte Nachrichten
  context["pm"]              → PluginManager
  context["profile_loader"]  → Profil-System

Damit kannst du dein Plugin tief mit der Welt verbinden – natürlich
im Rahmen der fünf Maat-Prinzipien.
""" if language == "de" else """
The 'context' parameter may contain, for example:

  context["self_evo"]        → global self-evolution engine
  context["conversation"]    → recent messages
  context["pm"]              → PluginManager
  context["profile_loader"]  → profile system

This lets you connect your plugin deeply with the world – naturally
within the frame of the five principles of Maat.
"""
    print(text3)

    input(Fore.GREEN + t["enter_back"] + Style.RESET_ALL)


def show_info_menu():
    settings = _load_settings()
    language = settings.get("language", "de")
    t = TEXT.get(language, TEXT["de"])
    while True:
        clear_screen()
        print(Fore.CYAN + Style.BRIGHT + t["info_title"] + "\n" + Style.RESET_ALL)
        print(f"  {t['info_overview']}")
        print(f"  {t['info_plugins']}")
        print(f"  {t['info_build']}")
        print(f"  {t['info_back']}\n")

        choice = input(Fore.GREEN + t["choice"] + Style.RESET_ALL).strip()

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
    settings = _load_settings()
    language = settings.get("language", "de")
    t = TEXT.get(language, TEXT["de"])
    clear_screen()
    if full_reset:
        print(Fore.MAGENTA + Style.BRIGHT + t["reset_warning_full"] + "\n" + Style.RESET_ALL)
        print(
            "Dies setzt zurück:\n"
            "  • Story-Fortschritt\n"
            "  • Battle-Status (Kämpfe, Bosse, Prinzipien)\n"
            "  • Self-Evolution (Level & XP)\n\n"
            "Alle Fortschritte gehen verloren. Du beginnst ein neues Äon."
        )
    else:
        print(Fore.MAGENTA + Style.BRIGHT + t["reset_warning_small"] + "\n" + Style.RESET_ALL)
        print(
            "Dies setzt zurück:\n"
            "  • Story-Zähler (Nachrichten, gespielte Kapitel)\n"
            "  • Battle-Zustand (Kämpfe, Freischaltung Kampfmodus)\n\n"
            "Self-Evolution (Level & XP) bleibt erhalten."
        )

    print()
    ans = input(Fore.RED + t["reset_confirm"] + Style.RESET_ALL).strip().lower()
    if not _yes(ans):
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
        settings = _load_settings()
        language = settings.get("language", "de")
        t = TEXT.get(language, TEXT["de"])
        clear_screen()
        print(Fore.YELLOW + Style.BRIGHT + t["options_title"] + "\n" + Style.RESET_ALL)
        print(f"  {t['opt_reset']}")
        print(f"  {t['opt_full_reset']}")
        print(f"  {t['opt_memory']}")
        print(f"  {t['opt_language']}")
        print(f"  {t['opt_back']}\n")

        choice = input(Fore.GREEN + t["choice"] + Style.RESET_ALL).strip()

        if choice == "1":
            confirm_reset(plugin_dir, full_reset=False, menu_music=menu_music)
        elif choice == "2":
            confirm_reset(plugin_dir, full_reset=True, menu_music=menu_music)
        elif choice == "3":
            confirm_wipe_all_memory(plugin_dir, menu_music)
        elif choice == "4":
            settings["language"] = choose_language()
            _save_settings(settings)
        elif choice == "5":
            break
        else:
            print(Fore.RED + "Ungültige Auswahl." + Style.RESET_ALL)
            time.sleep(1)


def new_game(plugin_dir: str, menu_music: MenuMusic):
    settings = _load_settings()
    language = settings.get("language", "de")
    t = TEXT.get(language, TEXT["de"])
    clear_screen()
    print(Fore.MAGENTA + Style.BRIGHT + t["new_game_title"] + "\n" + Style.RESET_ALL)
    print(
        "Du beginnst eine neue Reise im Äon der MAAT.\n"
        "Dein bisheriger Fortschritt wird vollständig gelöscht:\n"
        "  • Story\n"
        "  • Battle\n"
        "  • Self-Evolution\n"
    )
    ans = input(Fore.RED + t["new_game_confirm"] + Style.RESET_ALL).strip().lower()
    if not _yes(ans):
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
        "/menu": {
            "de": "Zeigt das MAAT-RPG-Startmenue.",
            "en": "Shows the MAAT-RPG start menu.",
        }
    }

    def __init__(self):
        self.plugin_dir = os.path.dirname(__file__)
        self.menu_music = MenuMusic(self.plugin_dir)
        self.settings = _load_settings()
        self.language = self.settings.get("language")
        self._title_seen = False

    def _t(self, key: str) -> str:
        language = self.language if self.language in TEXT else "de"
        return TEXT[language].get(key, key)

    def _choose_language(self) -> str:
        language = choose_language()
        self.language = language
        self.settings["language"] = language
        _save_settings(self.settings)
        return language

    def _show_title_screen(self):
        clear_screen()
        print(_render_title_screen(self.language or "de"))
        input()
        self._title_seen = True

    # ---------- Hauptmenü ----------
    def _show_menu_once(self) -> str:
        clear_screen()
        print(_render_progress_panel(self.language or "de"))
        print()
        print(Fore.YELLOW + self._t("menu_intro") + "\n" + Style.RESET_ALL)
        print(f"  {self._t('menu_start')}")
        print(f"  {self._t('menu_options')}")
        print(f"  {self._t('menu_new')}")
        print(f"  {self._t('menu_info')}")
        print(f"  {self._t('menu_exit')}")
        print()
        print(Fore.GREEN + self._t("menu_shortcuts") + Style.RESET_ALL)
        print()

        choice = input(Fore.GREEN + self._t("choice") + Style.RESET_ALL).strip()
        return choice

    def _handle_choice(self, choice: str):
        if choice == "1":
            self.menu_music.stop()
            clear_screen()
            print(Fore.CYAN + self._t("start_msg") + "\n" + Style.RESET_ALL)
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
            print(f"\n{self._t('bye')}\n")
            time.sleep(1)
            sys.exit(0)

        print(Fore.RED + f"\n{self._t('invalid')}\n" + Style.RESET_ALL)
        time.sleep(1)
        return "menu"

    # ---------- Lifecycle-Hooks ----------
    def on_startup(self, context=None):
        """
        Wird direkt nach dem Laden aller Plugins vom ChatLoop aufgerufen.
        Hier zeigen wir EINMAL das Startmenü.
        """
        if self.language not in TEXT:
            self._choose_language()

        self.menu_music.start()

        if not self._title_seen:
            self._show_title_screen()

        while True:
            choice = self._show_menu_once()
            result = self._handle_choice(choice)
            if result == "start":
                # ChatLoop fortsetzen
                return

    def command(self, cmd, context=None):
        if cmd.strip().lower().startswith("/menu"):
            clear_screen()
            print(Fore.CYAN + PYRAMID + Style.RESET_ALL)
            print()
            print(_render_progress_panel(self.language or "de"))
            print()
            print(self._t("active_game"))
            print(self._t("restart_hint"))
            print(self._t("active_shortcuts") + "\n")
            return True, ""
        return None

    def before_chat(self, user_input, context=None):
        return False, user_input

    def after_response(self, reply, context=None):
        return reply
