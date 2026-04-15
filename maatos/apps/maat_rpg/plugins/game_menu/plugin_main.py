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
import subprocess
import select
import termios
import tty
import time
import threading
from colorama import Fore, Style
import shutil
from pathlib import Path
from shared.core.maat_paths import state_file, get_data_dir, get_default_app_support_dir, get_profiles_dir
from shared.core.audio import ManagedAudioPlayer, stop_all_audio_backends


SETTINGS_FILE = state_file("settings_state.json")
PROFILE_MANAGER_STATE_PATH = get_default_app_support_dir() / "state" / "profile_manager_state.json"
PROFILES_ROOT = get_profiles_dir()


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
        "title_idle_hint": "Oder warte 20 Sekunden fuer eine Demo-Vorschau.",
        "fallback_title": "Suchender im Aeon der Maat",
        "fallback_rank": "Erwachend",
        "fallback_motif": "Die Welt tastet nach der Form, die Maatis annimmt.",
        "profile_slot": "Profil",
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
        "menu_shortcuts": "Direkt im Spiel wichtig: /fight  /journal  /erfolge  /xp  /maatbond",
        "menu_hint_restart": "Wenn MAAT-KI ein Problem beim Antworten hat, starte das System einfach mit /restart neu.",
        "menu_hint_language": "Tipp: Sage MAAT-KI, in welcher Sprache er mit dir sprechen soll.",
        "choice": "Auswahl: ",
        "start_msg": "🌿 MAAT-RPG startet... Viel Erfolg, Wanderer.",
        "bye": "Auf Wiedersehen im Aeon der MAAT.",
        "invalid": "Ungueltige Auswahl. Bitte nochmal.",
        "active_game": "Du bist bereits im aktiven Spiel.",
        "restart_hint": "Starte MAAT-RPG neu, um das Hauptmenue vollstaendig zu nutzen.",
        "active_shortcuts": "Im aktuellen Lauf helfen dir besonders: /fight, /journal, /erfolge, /xp, /maatbond",
        "options_title": "⚙ Optionen",
        "opt_text_speed": "[1] Story-Texttempo: {value}",
        "opt_music": "[2] Musik: {value}",
        "opt_voice": "[3] Voice / TTS: {value}",
        "opt_thinking": "[4] Thinking anzeigen: {value}",
        "opt_hallu": "[5] Hallu-Modus: {value}",
        "opt_reset": "[6] Zaehler zuruecksetzen (Story + Battle)",
        "opt_full_reset": "[7] Alles zuruecksetzen (Story + Battle + Self-Evo)",
        "opt_memory": "[8] Alle Erinnerungen loeschen (Application Support/MAAT-RPG/data)",
        "opt_language": "[9] Sprache wechseln",
        "opt_profile_switch": "[10] Profil wechseln: {value}",
        "opt_profile_delete": "[11] Profil loeschen",
        "opt_back": "[12] Zurueck",
        "speed_slow": "Langsam",
        "speed_fast": "Schnell",
        "music_on": "An",
        "music_off": "Aus",
        "profile_standard": "Standardprofil",
        "profile_slot": "Profil",
        "profile_change_prompt": "Welches Profil soll aktiv werden? [1-4]: ",
        "profile_change_done": "✅ Aktives Profil gesetzt: {label}",
        "profile_change_restart": "Bitte starte MAAT-RPG neu, damit das neue Profil geladen wird.\n",
        "profile_delete_prompt": "Welches Profil soll geloescht werden? [2-4]: ",
        "profile_delete_active": "Das aktuell aktive Profil kann hier nicht geloescht werden. Bitte zuerst wechseln.",
        "profile_delete_empty": "Dieser Profil-Slot ist bereits leer.",
        "profile_delete_confirm": "Profil {label} wirklich inklusive Spielstand und Erinnerung loeschen? (ja/nein): ",
        "profile_delete_done": "🗑 Profil {label} wurde geloescht.",
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
        "memory_details": (
            "Dies loescht den Inhalt von:\n"
            "{path}\n\n"
            "Dort liegen globale Erinnerungen, Logs und andere Zustaende\n"
            "deiner MAAT-KI. Spielstaende im RPG (Story/Battle/Quests)\n"
            "bleiben davon unberuehrt.\n"
        ),
        "memory_progress": "🧠 Loesche globales Memory ({path}) ...",
        "memory_done": "✅ Alle Erinnerungen im Ordner 'data' wurden geloescht.",
        "memory_restart": (
            "Bitte starte MAAT-KI/MAAT-RPG neu, damit das System mit einem\n"
            "frischen Gedaechtnis weiterlaeuft.\n"
        ),
        "new_game_title": "✨ Neues Spiel – Neues Aeon",
        "new_game_confirm": "Fortfahren und alles loeschen? (ja/nein): ",
        "reset_full_details": (
            "Dies setzt zurueck:\n"
            "  • Story-Fortschritt\n"
            "  • Battle-Status (Kaempfe, Bosse, Prinzipien)\n"
            "  • Self-Evolution (Level & XP)\n\n"
            "Alle Fortschritte gehen verloren. Du beginnst ein neues Aeon."
        ),
        "reset_small_details": (
            "Dies setzt zurueck:\n"
            "  • Story-Zaehler (Nachrichten, gespielte Kapitel)\n"
            "  • Battle-Zustand (Kaempfe, Freischaltung Kampfmodus)\n\n"
            "Self-Evolution (Level & XP) bleibt erhalten."
        ),
        "reset_progress_full": "🔁 Setze Story, Battle und Self-Evolution zurueck ...",
        "reset_progress_small": "🔁 Setze Story- und Battle-Zaehler zurueck ...",
        "reset_story_done": "📖 Story- und Battle-Zustand zurueckgesetzt.",
        "reset_quests_done": "🏹 Quests & Achievements wurden zurueckgesetzt.",
        "reset_self_evo_done": "🧬 Self-Evolution wurde ebenfalls zurueckgesetzt.",
        "reset_done": "✅ Reset abgeschlossen.",
        "reset_restart": (
            "MAAT-KI wird jetzt beendet. Bitte starte MAAT-RPG neu,\n"
            "um mit einem frischen Spielstand zu beginnen.\n"
        ),
        "new_game_details": (
            "Du beginnst eine neue Reise im Aeon der MAAT.\n"
            "Dein bisheriger Fortschritt wird vollstaendig geloescht:\n"
            "  • Story\n"
            "  • Battle\n"
            "  • Self-Evolution\n"
        ),
        "new_game_done": "📖 Story, ⚔ Battle, 🏹 Quests/Achievements und 🧬 Self-Evo wurden zurueckgesetzt.",
        "new_game_ready": "✅ Neues Spiel vorbereitet.",
        "new_game_restart": "Bitte starte MAAT-RPG neu, um das neue Aeon zu beginnen.\n",
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
        "title_idle_hint": "Or wait 20 seconds for a demo preview.",
        "fallback_title": "Seeker in the Aeon of Maat",
        "fallback_rank": "Awakening",
        "fallback_motif": "The world is feeling for the shape Maatis is becoming.",
        "profile_slot": "Profile",
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
        "menu_shortcuts": "Useful in game: /fight  /journal  /erfolge  /xp  /maatbond",
        "menu_hint_restart": "If MAAT-KI has trouble answering, simply restart the system with /restart.",
        "menu_hint_language": "Tip: Tell MAAT-KI which language it should speak with you.",
        "choice": "Choice: ",
        "start_msg": "🌿 MAAT-RPG is starting... Walk well, wanderer.",
        "bye": "Farewell in the Aeon of MAAT.",
        "invalid": "Invalid choice. Please try again.",
        "active_game": "You are already inside the active game.",
        "restart_hint": "Restart MAAT-RPG to use the full main menu.",
        "active_shortcuts": "Helpful right now: /fight, /journal, /erfolge, /xp, /maatbond",
        "options_title": "⚙ Options",
        "opt_text_speed": "[1] Story text speed: {value}",
        "opt_music": "[2] Music: {value}",
        "opt_voice": "[3] Voice / TTS: {value}",
        "opt_thinking": "[4] Show thinking: {value}",
        "opt_hallu": "[5] Hallu mode: {value}",
        "opt_reset": "[6] Reset counters (Story + Battle)",
        "opt_full_reset": "[7] Reset everything (Story + Battle + Self-Evo)",
        "opt_memory": "[8] Delete all memories (Application Support/MAAT-RPG/data)",
        "opt_language": "[9] Change language",
        "opt_profile_switch": "[10] Change profile: {value}",
        "opt_profile_delete": "[11] Delete profile",
        "opt_back": "[12] Back",
        "speed_slow": "Slow",
        "speed_fast": "Fast",
        "music_on": "On",
        "music_off": "Off",
        "profile_standard": "Standard profile",
        "profile_slot": "Profile",
        "profile_change_prompt": "Which profile should become active? [1-4]: ",
        "profile_change_done": "✅ Active profile set: {label}",
        "profile_change_restart": "Please restart MAAT-RPG so the new profile can be loaded.\n",
        "profile_delete_prompt": "Which profile should be deleted? [2-4]: ",
        "profile_delete_active": "The currently active profile cannot be deleted here. Please switch first.",
        "profile_delete_empty": "That profile slot is already empty.",
        "profile_delete_confirm": "Really delete {label} including save data and memory? (yes/no): ",
        "profile_delete_done": "🗑 Profile {label} was deleted.",
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
        "memory_details": (
            "This deletes the contents of:\n"
            "{path}\n\n"
            "This folder contains global memories, logs, and other MAAT-KI state.\n"
            "RPG save data (Story/Battle/Quests)\n"
            "will not be affected.\n"
        ),
        "memory_progress": "🧠 Deleting global memory ({path}) ...",
        "memory_done": "✅ All memories in the 'data' folder were deleted.",
        "memory_restart": (
            "Please restart MAAT-KI/MAAT-RPG so the system continues with\n"
            "a fresh memory state.\n"
        ),
        "new_game_title": "✨ New Game – New Aeon",
        "new_game_confirm": "Continue and delete everything? (yes/no): ",
        "reset_full_details": (
            "This resets:\n"
            "  • story progress\n"
            "  • battle status (fights, bosses, principles)\n"
            "  • self-evolution (level & XP)\n\n"
            "All progress will be lost. You begin a new aeon."
        ),
        "reset_small_details": (
            "This resets:\n"
            "  • story counters (messages, played chapters)\n"
            "  • battle state (fights, combat unlock)\n\n"
            "Self-evolution (level & XP) is kept."
        ),
        "reset_progress_full": "🔁 Resetting Story, Battle, and Self-Evolution ...",
        "reset_progress_small": "🔁 Resetting Story and Battle counters ...",
        "reset_story_done": "📖 Story and battle state reset.",
        "reset_quests_done": "🏹 Quests and achievements reset.",
        "reset_self_evo_done": "🧬 Self-evolution was reset as well.",
        "reset_done": "✅ Reset complete.",
        "reset_restart": (
            "MAAT-KI will now close. Please restart MAAT-RPG\n"
            "to begin with a fresh save state.\n"
        ),
        "new_game_details": (
            "You are beginning a new journey in the Aeon of MAAT.\n"
            "Your previous progress will be fully deleted:\n"
            "  • Story\n"
            "  • Battle\n"
            "  • Self-Evolution\n"
        ),
        "new_game_done": "📖 Story, ⚔ Battle, 🏹 Quests/Achievements, and 🧬 Self-Evo were reset.",
        "new_game_ready": "✅ New game prepared.",
        "new_game_restart": "Please restart MAAT-RPG to begin the new aeon.\n",
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


def _stop_all_afplay():
    stop_all_audio_backends()


def _restore_terminal_input_mode():
    try:
        if not getattr(sys.stdin, "isatty", lambda: False)():
            return
        fd = sys.stdin.fileno()
        attrs = termios.tcgetattr(fd)
        attrs[3] |= termios.ECHO | termios.ICANON
        attrs[6][termios.VMIN] = 1
        attrs[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSADRAIN, attrs)
    except Exception:
        pass


def _setting_text_speed(settings: dict) -> str:
    value = str(settings.get("story_text_speed", "fast")).lower()
    return value if value in {"slow", "fast"} else "fast"


def _setting_music_enabled(settings: dict) -> bool:
    return bool(settings.get("music_enabled", True))


def _setting_show_thinking(settings: dict) -> bool:
    return bool(settings.get("show_thinking", False))


def _setting_say_tts_enabled(settings: dict) -> bool:
    return bool(settings.get("say_tts_enabled", True))


def _setting_hallu_mode(settings: dict) -> bool:
    return bool(settings.get("hallu_mode", False))


def _settings_labels(language: str, settings: dict) -> tuple[str, str, str, str, str]:
    t = TEXT.get(language, TEXT["de"])
    speed = t["speed_slow"] if _setting_text_speed(settings) == "slow" else t["speed_fast"]
    music = t["music_on"] if _setting_music_enabled(settings) else t["music_off"]
    voice = t["music_on"] if _setting_say_tts_enabled(settings) else t["music_off"]
    thinking = t["music_on"] if _setting_show_thinking(settings) else t["music_off"]
    hallu = t["music_on"] if _setting_hallu_mode(settings) else t["music_off"]
    return speed, music, voice, thinking, hallu
# ==========================
# 🎵 Menü-Musik (optional)
# ==========================
class MenuMusic:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = plugin_dir
        self.track = ""
        self._player = ManagedAudioPlayer(self.track)

    def _resolve_track(self) -> str:
        settings = _load_settings()
        language = settings.get("language", "de")
        if language == "en":
            english_track = os.path.join(self.plugin_dir, "menu_theme_en.mp3")
            if os.path.isfile(english_track):
                return english_track
        return os.path.join(self.plugin_dir, "menu_theme.mp3")

    def start(self):
        settings = _load_settings()
        if not _setting_music_enabled(settings):
            return
        self.track = self._resolve_track()
        self._player.set_track(self.track)
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


def _active_profile_slot() -> int:
    try:
        data = json.loads(Path(PROFILE_MANAGER_STATE_PATH).read_text(encoding="utf-8"))
        slot = int(data.get("active_profile", 1) or 1)
        return slot if 1 <= slot <= 4 else 1
    except Exception:
        return 1


def _active_profile_label(language: str) -> str:
    slot = _active_profile_slot()
    return _profile_slot_label(slot, language)


def _profile_slot_label(slot: int, language: str) -> str:
    t = TEXT.get(language, TEXT["de"])
    if slot == 1:
        return t["profile_standard"]
    return f"Profile {slot}" if language == "en" else f"Profil {slot}"


def _profile_slot_root(slot: int) -> Path:
    if slot <= 1:
        return get_default_app_support_dir()
    return PROFILES_ROOT / f"profile_{slot}"


def _profile_slot_used(slot: int) -> bool:
    if slot == 1:
        return True
    root = _profile_slot_root(slot)
    if not root.exists():
        return False
    try:
        return any(root.iterdir())
    except Exception:
        return False


def _save_active_profile_slot(slot: int):
    PROFILE_MANAGER_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_MANAGER_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"active_profile": slot}, f, indent=2, ensure_ascii=False)


def _localize_path_profile(profile: dict, language: str) -> dict:
    localized = dict(profile or {})
    if language != "en":
        return localized

    title_map = {
        "Grenzhüter der Wahrheit": "Boundary Keeper of Truth",
        "Grenzhüter der Erinnerung": "Boundary Keeper of Memory",
        "Grenzhüter der Maat": "Boundary Keeper of Maat",
        "Klangsucher der Harmonie": "Tone Seeker of Harmony",
        "Klangsucher der Wahrheit": "Tone Seeker of Truth",
        "Klangsucher der Erinnerung": "Tone Seeker of Memory",
        "Klangsucher der Maat": "Tone Seeker of Maat",
        "Formträger der Schöpfung": "Form Bearer of Creation",
        "Formträger der Wahrheit": "Form Bearer of Truth",
        "Formträger der Erinnerung": "Form Bearer of Memory",
        "Formträger der Maat": "Form Bearer of Maat",
        "Wegsucher": "Path Seeker",
        "Wegsucher der Maat": "Path Seeker of Maat",
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
        "Maatis' Weg formt sich aus Entscheidung und Bewährung.": "Maatis' path is shaped by choice and trial.",
        "Erinnerung klingt als Ordnung weiter.": "Memory continues to resonate as order.",
        "Moeglichkeit wird zum Echo der Welt.": "Possibility becomes the echo of the world.",
        "Möglichkeit wird zum Echo der Welt.": "Possibility becomes the echo of the world.",
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
        "active_profile_label": _active_profile_label(language),
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
        Fore.GREEN + f"{t['profile_slot']}: {ctx['active_profile_label']}" + Style.RESET_ALL,
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
    active_profile_label = _active_profile_label(language)
    lines = [
        Fore.CYAN + Style.BRIGHT + PYRAMID + Style.RESET_ALL,
        "",
        Fore.YELLOW + Style.BRIGHT + t["brand"] + Style.RESET_ALL,
        Fore.CYAN + Style.BRIGHT + t["version"] + Style.RESET_ALL,
        "",
        Fore.GREEN + f"{t['profile_slot']}: {active_profile_label}" + Style.RESET_ALL,
        "",
        Fore.GREEN + Style.BRIGHT + t["title_continue"] + Style.RESET_ALL,
        Fore.CYAN + t["title_idle_hint"] + Style.RESET_ALL,
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

    battle_state_path = state_file("battle_state.json")
    try:
        if os.path.isfile(battle_state_path):
            with open(battle_state_path, "r", encoding="utf-8") as f:
                battle_state = json.load(f)
            if isinstance(battle_state, dict):
                battle_state.pop("quests", None)
                achievements = battle_state.get("achievements")
                if isinstance(achievements, dict):
                    achievements["combat"] = []
                with open(battle_state_path, "w", encoding="utf-8") as f:
                    json.dump(battle_state, f, indent=2, ensure_ascii=False)
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
    data_dir = str(get_data_dir())
    clear_screen()
    print(Fore.MAGENTA + Style.BRIGHT + t["memory_warning"] + "\n" + Style.RESET_ALL)
    print(t["memory_details"].format(path=data_dir))

    ans = input(Fore.RED + t["memory_confirm"] + Style.RESET_ALL).strip().lower()
    if not _yes(ans):
        return

    # Musik stoppen für „stillen“ Reset
    menu_music.stop()

    print()
    print(Fore.MAGENTA + t["memory_progress"].format(path=data_dir) + Style.RESET_ALL)
    reset_global_memory(plugin_dir)

    print(Fore.GREEN + t["memory_done"] + Style.RESET_ALL)
    print()
    print(t["memory_restart"])
    time.sleep(2)
    sys.exit(0)

def reset_global_memory(plugin_dir: str):
    data_dir = str(get_data_dir())

    if not os.path.isdir(data_dir):
        print(f"[MEMORY RESET] No 'data' directory found under: {data_dir}")
        return

    print(f"[MEMORY RESET] Clearing global memory directory: {data_dir}")

    for entry in os.listdir(data_dir):
        path = os.path.join(data_dir, entry)
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            print(f"[MEMORY RESET] Error deleting {path}: {e}")



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
            print(Fore.RED + t["invalid"] + Style.RESET_ALL)
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
        print(t["reset_full_details"])
    else:
        print(Fore.MAGENTA + Style.BRIGHT + t["reset_warning_small"] + "\n" + Style.RESET_ALL)
        print(t["reset_small_details"])

    print()
    ans = input(Fore.RED + t["reset_confirm"] + Style.RESET_ALL).strip().lower()
    if not _yes(ans):
        return

    # Musik stoppen, damit Reset „still“ ist
    menu_music.stop()

    print()
    if full_reset:
        print(Fore.MAGENTA + t["reset_progress_full"] + Style.RESET_ALL)
    else:
        print(Fore.MAGENTA + t["reset_progress_small"] + Style.RESET_ALL)

    reset_story_state(plugin_dir)
    reset_battle_state(plugin_dir)
    reset_quests_and_achievements(plugin_dir)
    if full_reset:
        reset_self_evo(plugin_dir)

    print(Fore.CYAN + t["reset_story_done"] + Style.RESET_ALL)
    print(Fore.CYAN + t["reset_quests_done"] + Style.RESET_ALL)
    if full_reset:
        print(Fore.CYAN + t["reset_self_evo_done"] + Style.RESET_ALL)

    print(Fore.GREEN + t["reset_done"] + Style.RESET_ALL)
    print()
    print(t["reset_restart"])
    time.sleep(2)
    sys.exit(0)


def _change_profile_from_settings(menu_music: MenuMusic, language: str):
    t = TEXT.get(language, TEXT["de"])
    choice = input(Fore.GREEN + t["profile_change_prompt"] + Style.RESET_ALL).strip()
    if choice not in {"1", "2", "3", "4"}:
        print(Fore.RED + t["invalid"] + Style.RESET_ALL)
        time.sleep(1)
        return

    slot = int(choice)
    label = _profile_slot_label(slot, language)
    current = _active_profile_slot()
    if slot == current:
        print(Fore.CYAN + t["profile_change_done"].format(label=label) + Style.RESET_ALL)
        time.sleep(1)
        return

    _save_active_profile_slot(slot)
    menu_music.stop()
    print(Fore.GREEN + t["profile_change_done"].format(label=label) + Style.RESET_ALL)
    print()
    print(t["profile_change_restart"])
    time.sleep(2)
    sys.exit(0)


def _delete_profile_from_settings(language: str):
    t = TEXT.get(language, TEXT["de"])
    choice = input(Fore.GREEN + t["profile_delete_prompt"] + Style.RESET_ALL).strip()
    if choice not in {"2", "3", "4"}:
        print(Fore.RED + t["invalid"] + Style.RESET_ALL)
        time.sleep(1)
        return

    slot = int(choice)
    if slot == _active_profile_slot():
        print(Fore.YELLOW + t["profile_delete_active"] + Style.RESET_ALL)
        time.sleep(1.4)
        return

    if not _profile_slot_used(slot):
        print(Fore.YELLOW + t["profile_delete_empty"] + Style.RESET_ALL)
        time.sleep(1)
        return

    label = _profile_slot_label(slot, language)
    confirm = input(Fore.RED + t["profile_delete_confirm"].format(label=label) + Style.RESET_ALL).strip()
    if not _yes(confirm):
        return

    shutil.rmtree(_profile_slot_root(slot), ignore_errors=False)
    print(Fore.GREEN + t["profile_delete_done"].format(label=label) + Style.RESET_ALL)
    time.sleep(1.2)


def options_menu(plugin_dir: str, menu_music: MenuMusic):
    while True:
        settings = _load_settings()
        language = settings.get("language", "de")
        t = TEXT.get(language, TEXT["de"])
        speed_label, music_label, voice_label, thinking_label, hallu_label = _settings_labels(language, settings)
        active_profile_label = _active_profile_label(language)
        clear_screen()
        print(Fore.YELLOW + Style.BRIGHT + t["options_title"] + "\n" + Style.RESET_ALL)
        print("  " + t["opt_text_speed"].format(value=speed_label))
        print("  " + t["opt_music"].format(value=music_label))
        print("  " + t["opt_voice"].format(value=voice_label))
        print("  " + t["opt_thinking"].format(value=thinking_label))
        print("  " + t["opt_hallu"].format(value=hallu_label))
        print(f"  {t['opt_reset']}")
        print(f"  {t['opt_full_reset']}")
        print(f"  {t['opt_memory']}")
        print(f"  {t['opt_language']}")
        print("  " + t["opt_profile_switch"].format(value=active_profile_label))
        print(f"  {t['opt_profile_delete']}")
        print(f"  {t['opt_back']}\n")

        choice = input(Fore.GREEN + t["choice"] + Style.RESET_ALL).strip()

        if choice == "1":
            current = _setting_text_speed(settings)
            settings["story_text_speed"] = "slow" if current == "fast" else "fast"
            _save_settings(settings)
        elif choice == "2":
            enabled = _setting_music_enabled(settings)
            settings["music_enabled"] = not enabled
            _save_settings(settings)
            if settings["music_enabled"]:
                menu_music.start()
            else:
                menu_music.stop()
                _stop_all_afplay()
        elif choice == "3":
            enabled = _setting_say_tts_enabled(settings)
            settings["say_tts_enabled"] = not enabled
            _save_settings(settings)
        elif choice == "4":
            enabled = _setting_show_thinking(settings)
            settings["show_thinking"] = not enabled
            _save_settings(settings)
        elif choice == "5":
            enabled = _setting_hallu_mode(settings)
            settings["hallu_mode"] = not enabled
            _save_settings(settings)
        elif choice == "6":
            confirm_reset(plugin_dir, full_reset=False, menu_music=menu_music)
        elif choice == "7":
            confirm_reset(plugin_dir, full_reset=True, menu_music=menu_music)
        elif choice == "8":
            confirm_wipe_all_memory(plugin_dir, menu_music)
        elif choice == "9":
            settings = _load_settings()
            settings["language"] = choose_language()
            _save_settings(settings)
            if _setting_music_enabled(settings):
                menu_music.stop()
                menu_music.start()
        elif choice == "10":
            _change_profile_from_settings(menu_music, language)
        elif choice == "11":
            _delete_profile_from_settings(language)
        elif choice == "12":
            break
        else:
            print(Fore.RED + t["invalid"] + Style.RESET_ALL)
            time.sleep(1)


def new_game(plugin_dir: str, menu_music: MenuMusic):
    settings = _load_settings()
    language = settings.get("language", "de")
    t = TEXT.get(language, TEXT["de"])
    clear_screen()
    print(Fore.MAGENTA + Style.BRIGHT + t["new_game_title"] + "\n" + Style.RESET_ALL)
    print(t["new_game_details"])
    ans = input(Fore.RED + t["new_game_confirm"] + Style.RESET_ALL).strip().lower()
    if not _yes(ans):
        return

    menu_music.stop()
    reset_story_state(plugin_dir)
    reset_battle_state(plugin_dir)
    reset_quests_and_achievements(plugin_dir)
    reset_self_evo(plugin_dir)

    print(Fore.CYAN + t["new_game_done"] + Style.RESET_ALL)
    print(Fore.GREEN + f"\n{t['new_game_ready']}" + Style.RESET_ALL)
    print(t["new_game_restart"])
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
        self._title_demo_stage = 0

    def _t(self, key: str) -> str:
        language = self.language if self.language in TEXT else "de"
        return TEXT[language].get(key, key)

    def _choose_language(self) -> str:
        language = choose_language()
        self.language = language
        self.settings["language"] = language
        _save_settings(self.settings)
        return language

    def _title_wait_or_timeout(self, timeout: float = 20.0) -> bool:
        """True wenn irgendeine Taste gedrückt wurde, False bei Timeout."""
        fd = None
        old_settings = None
        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setcbreak(fd)
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
            if ready:
                try:
                    sys.stdin.read(1)
                except Exception:
                    pass
                return True
            return False
        except Exception:
            try:
                ready, _, _ = select.select([sys.stdin], [], [], timeout)
                if ready:
                    sys.stdin.readline()
                    return True
            except Exception:
                pass
            return False
        finally:
            if fd is not None and old_settings is not None:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                except Exception:
                    pass

    def _title_key_pressed(self) -> bool:
        return self._title_wait_or_timeout(0.05)

    def _graceful_exit(self):
        _restore_terminal_input_mode()
        self.menu_music.stop()
        _stop_all_afplay()
        print(f"\n{self._t('bye')}\n")
        time.sleep(0.3)
        raise SystemExit(0)

    def _run_title_music_phase(self) -> bool:
        if not self._title_wait_or_timeout(180.0):
            self._title_demo_stage += 1
        return True

    def _run_title_demo(self, context=None) -> bool:
        battle_core = None
        if isinstance(context, dict):
            battle_core = ((context.get("rpg") or {}).get("battle_core"))
        if battle_core is None or not hasattr(battle_core, "run_fight"):
            return False

        cycle = self._title_demo_stage % 4
        if cycle == 0:
            mode = "normal"
            actions = [
                "1", "3", "1", "1", "5", "1", "4", "1", "5",
                "1", "2", "1", "3", "1", "5", "1", "1", "4",
                "1", "3", "5",
            ]
        elif cycle == 1:
            mode = "boss"
            actions = [
                "1", "3", "1", "5", "1", "2", "1", "1", "5",
                "1", "4", "1", "3", "1", "5", "3", "1", "2",
                "5", "1", "1", "1", "4", "1", "3", "5", "1",
                "2", "1", "5",
            ]
        elif cycle == 2:
            mode = "final"
            actions = [
                "1", "5", "1", "3", "1", "2", "1", "4", "5",
                "1", "1", "1", "5", "3", "1", "2", "1", "3",
                "5", "1", "4", "1", "1", "1", "2", "5", "1",
                "3", "1", "5",
            ]
        else:
            return self._run_title_music_phase()

        clear_screen()
        self.menu_music.stop()
        demo_context = {
            "guide_mode": True,
            # Titel-Demo darf sichtbaren Schaden zeigen, ohne den echten Spielstand zu veraendern.
            "no_hp_loss": False,
            "title_demo_mode": True,
            "title_demo_abort": False,
            "scripted_actions": list(actions),
            "battle_profile": {
                "enemy": {
                    "hp_mult": 0.9 if mode == "normal" else (0.78 if mode == "boss" else 0.72),
                }
            },
        }
        result = {"error": None}

        def _run():
            try:
                battle_core.run_fight(mode, demo_context)
            except Exception as e:
                result["error"] = e

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        aborted = False
        while thread.is_alive():
            if self._title_key_pressed():
                demo_context["title_demo_abort"] = True
                demo_music = demo_context.get("_battle_music_manager")
                if demo_music is not None and hasattr(demo_music, "stop"):
                    try:
                        demo_music.stop()
                    except Exception:
                        pass
                self.menu_music.stop()
                _stop_all_afplay()
                aborted = True
                break

        if aborted:
            deadline = time.time() + 4.0
            while thread.is_alive() and time.time() < deadline:
                demo_context["title_demo_abort"] = True
                demo_music = demo_context.get("_battle_music_manager")
                if demo_music is not None and hasattr(demo_music, "stop"):
                    try:
                        demo_music.stop()
                    except Exception:
                        pass
                thread.join(timeout=0.1)
            if thread.is_alive():
                _stop_all_afplay()
        else:
            thread.join()

        if result["error"] is not None and not aborted:
            print(Fore.RED + f"[TITLE DEMO ERROR] {result['error']}" + Style.RESET_ALL)
            time.sleep(1.2)
            clear_screen()
            self.menu_music.stop()
            _stop_all_afplay()
            self.menu_music.start()
            return False

        clear_screen()
        _restore_terminal_input_mode()
        self.menu_music.stop()
        _stop_all_afplay()
        time.sleep(0.35)
        _stop_all_afplay()
        if not thread.is_alive():
            self.menu_music.start()
        if not aborted:
            self._title_demo_stage += 1
        return True

    def _show_title_screen(self, context=None):
        while True:
            clear_screen()
            print(_render_title_screen(self.language or "de"))
            if self._title_wait_or_timeout(20.0):
                self._title_seen = True
                return
            if not self._run_title_demo(context):
                continue

    # ---------- Hauptmenü ----------
    def _show_menu_once(self) -> str:
        _restore_terminal_input_mode()
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
        print(Fore.CYAN + self._t("menu_hint_restart") + Style.RESET_ALL)
        print(Fore.CYAN + self._t("menu_hint_language") + Style.RESET_ALL)
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
            self.settings = _load_settings()
            self.language = self.settings.get("language")
            return "menu"

        if choice == "3":
            new_game(self.plugin_dir, self.menu_music)
            return "exit"

        if choice == "4":
            show_info_menu()
            return "menu"

        if choice == "5":
            self._graceful_exit()

        print(Fore.RED + f"\n{self._t('invalid')}\n" + Style.RESET_ALL)
        time.sleep(1)
        return "menu"

    # ---------- Lifecycle-Hooks ----------
    def on_startup(self, context=None):
        """
        Wird direkt nach dem Laden aller Plugins vom ChatLoop aufgerufen.
        Hier zeigen wir EINMAL das Startmenü.
        """
        try:
            if self.language not in TEXT:
                self._choose_language()

            self.menu_music.start()

            if not self._title_seen:
                self._show_title_screen(context)

            while True:
                choice = self._show_menu_once()
                result = self._handle_choice(choice)
                if result == "start":
                    # ChatLoop fortsetzen
                    return
        except KeyboardInterrupt:
            self._graceful_exit()

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
