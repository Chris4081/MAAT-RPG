# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from pathlib import Path

from shared.core.maat_paths import get_default_app_support_dir, get_profiles_dir
from shared.core.reply_style import DEFAULTS as REPLY_STYLE_DEFAULTS
from shared.core.maat_style import STYLE_DEFAULTS


BASE_APP_SUPPORT_DIR = get_default_app_support_dir()
PROFILES_DIR = get_profiles_dir()
PROFILE_SLOT_COUNT = 10
PROFILE_MANAGER_STATE_PATH = BASE_APP_SUPPORT_DIR / "state" / "profile_manager_state.json"

SETTINGS_DEFAULTS = {
    "music_enabled": False,
    "thinking_enabled": False,
    "maat_thinking_enabled": True,
    "show_thinking": False,
    "say_tts_enabled": True,
    "rpg_context_enabled": False,
    "chat_history_messages": 10,
    "hallu_mode": False,
    "emotion_enabled": True,
    "maat_style_enabled": False,
    **STYLE_DEFAULTS,
    "maat_identity_enabled": False,
    "reality_enabled": True,
    "response_formatting_enabled": True,
    "reply_style_enabled": True,
    **REPLY_STYLE_DEFAULTS,
}


def normalize_language(language: str | None, fallback: str = "de") -> str:
    return language if language in ("de", "en") else fallback


def load_json_file(path: str | Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_json_file(path: str | Path, payload: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def yes_choice(choice: str) -> bool:
    return choice.strip().lower() in {"j", "ja", "y", "yes"}


def application_settings_path() -> Path:
    return BASE_APP_SUPPORT_DIR / 'state' / 'application_settings.json'


def application_language() -> str | None:
    value = load_json_file(application_settings_path()).get('language')
    return value if value in ('de', 'en') else None


def write_application_language(language: str) -> None:
    if language not in ('de', 'en'):
        raise ValueError('Unsupported language')
    import tempfile
    path = application_settings_path()
    data = load_json_file(path)
    data['language'] = language
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.app-language-', delete=False) as handle:
            temporary = handle.name
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def profile_text(language: str) -> dict:
    language = normalize_language(language)
    if language == "en":
        return {
            "title": "MAAT-RPG Profile Manager",
            "subtitle": "Choose a profile before the game starts.",
            "slot_default": "Standard profile",
            "slot_extra": "Profile {slot}",
            "active": "active",
            "empty": "empty",
            "empty_hint": "Fresh save slot with its own memory and states.",
            "path_profile": "Path Profile",
            "level": "Level",
            "boss_wins": "Boss Wins",
            "principles": "Principles",
            "memory": "Memory",
            "delete_hint": "Press D or L to delete a profile slot.",
            "prompt": "Choose [1-10, ENTER = active profile {active}, D/L = delete]: ",
            "delete_slot_prompt": "Which slot should be deleted? [2-10]: ",
            "delete_default": "The standard profile cannot be deleted.",
            "delete_empty": "That profile slot is already empty.",
            "delete_confirm": "Really delete profile {slot} including save data and memory? (yes/no): ",
            "delete_done": "Profile {slot} was deleted.",
            "invalid": "Invalid choice. Please try again.",
            "current_path": "Storage",
        }
    return {
        "title": "MAAT-RPG Profilmanager",
        "subtitle": "Waehle ein Profil, bevor das Spiel startet.",
        "slot_default": "Standardprofil",
        "slot_extra": "Profil {slot}",
        "active": "aktiv",
        "empty": "leer",
        "empty_hint": "Frischer Spielstand-Slot mit eigener Erinnerung und eigenen Zustaenden.",
        "path_profile": "Pfadprofil",
        "level": "Level",
        "boss_wins": "Boss-Siege",
        "principles": "Prinzipien",
        "memory": "Erinnerung",
        "delete_hint": "Druecke D oder L, um einen Profil-Slot zu loeschen.",
        "prompt": "Waehle [1-10, ENTER = aktives Profil {active}, D/L = loeschen]: ",
        "delete_slot_prompt": "Welcher Slot soll geloescht werden? [2-10]: ",
        "delete_default": "Das Standardprofil kann nicht geloescht werden.",
        "delete_empty": "Dieser Profil-Slot ist bereits leer.",
        "delete_confirm": "Profil {slot} wirklich inklusive Spielstand und Erinnerung loeschen? (ja/nein): ",
        "delete_done": "Profil {slot} wurde geloescht.",
        "invalid": "Ungueltige Auswahl. Bitte nochmal.",
        "current_path": "Speicherort",
    }


def profile_slot_root(slot: int) -> Path:
    if slot <= 1:
        return BASE_APP_SUPPORT_DIR
    return PROFILES_DIR / f"profile_{slot}"


def profile_slot_label(slot: int, language: str) -> str:
    name = load_json_file(profile_slot_root(slot) / 'state' / 'profile_metadata.json').get('name')
    if isinstance(name, str) and name.strip():
        return name.strip()
    text = profile_text(language)
    return text["slot_default"] if slot == 1 else text["slot_extra"].format(slot=slot)


def profile_labels(language: str) -> list[str]:
    return [profile_slot_label(slot, language) for slot in range(1, PROFILE_SLOT_COUNT + 1)]


def profile_settings_path(slot: int) -> Path:
    return profile_slot_root(slot) / "state" / "settings_state.json"


def load_profile_settings(slot: int) -> dict:
    data = load_json_file(profile_settings_path(slot))
    merged = dict(SETTINGS_DEFAULTS)
    if data.get("language") in ("de", "en"):
        merged["language"] = data["language"]
    merged.update({key: value for key, value in data.items() if key != "language"})
    language = application_language()
    if language:
        merged['language'] = language
    return merged


def write_profile_settings(slot: int, updates: dict) -> dict:
    current = load_json_file(profile_settings_path(slot))
    current.update(updates or {})
    save_json_file(profile_settings_path(slot), current)
    return load_profile_settings(slot)


def profile_language(slot: int, fallback: str = "de") -> str:
    language = application_language()
    if language:
        return language
    settings = load_json_file(profile_settings_path(slot))
    return normalize_language(settings.get("language"), fallback=fallback)


def profile_has_explicit_language(slot: int) -> bool:
    return load_json_file(profile_settings_path(slot)).get("language") in ("de", "en")


def read_profile_manager_state() -> dict:
    data = load_json_file(PROFILE_MANAGER_STATE_PATH)
    slot = int(data.get("active_profile", 1) or 1)
    if slot < 1 or slot > PROFILE_SLOT_COUNT:
        slot = 1
    return {"active_profile": slot}


def write_profile_manager_state(state: dict) -> dict:
    payload = {"active_profile": int(state.get("active_profile", 1) or 1)}
    if payload["active_profile"] < 1 or payload["active_profile"] > PROFILE_SLOT_COUNT:
        payload["active_profile"] = 1
    save_json_file(PROFILE_MANAGER_STATE_PATH, payload)
    return payload


def active_profile_slot() -> int:
    return int(read_profile_manager_state().get("active_profile", 1) or 1)


def profile_slot_used(slot: int) -> bool:
    if slot == 1:
        return True
    root = profile_slot_root(slot)
    if not root.exists():
        return False
    try:
        return any(root.iterdir())
    except Exception:
        return False


def profile_slot_exists(slot: int) -> bool:
    """Recognize legacy saves, without treating shared models as profile 1."""
    if type(slot) is not int or not 1 <= slot <= PROFILE_SLOT_COUNT:
        return False
    root = profile_slot_root(slot)
    for folder in ('state', 'data', 'saves'):
        path = root / folder
        try:
            if any(p.name not in (PROFILE_MANAGER_STATE_PATH.name, application_settings_path().name)
                   for p in path.iterdir()):
                return True
        except OSError:
            pass
    return False


def existing_profile_slots() -> list[int]:
    return [slot for slot in range(1, PROFILE_SLOT_COUNT + 1) if profile_slot_exists(slot)]


def set_profile_name(slot: int, name: str) -> None:
    """Names are metadata only; profile paths, saves and model choices stay put."""
    if type(slot) is not int or not 1 <= slot <= PROFILE_SLOT_COUNT:
        raise ValueError('Ungültiger Profilplatz.')
    name = name.strip() if isinstance(name, str) else ''
    if not 1 <= len(name) <= 48 or any(ord(char) < 32 or ord(char) == 127 for char in name):
        raise ValueError('Bitte einen Namen mit 1 bis 48 Zeichen ohne Zeilenumbrüche eingeben.')
    import tempfile
    path = profile_slot_root(slot) / 'state' / 'profile_metadata.json'
    data = load_json_file(path)
    data['name'] = name
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.profile-name-', delete=False) as handle:
            temporary = handle.name
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def create_profile(name: str) -> int:
    slot = next((slot for slot in range(1, PROFILE_SLOT_COUNT + 1)
                 if not profile_slot_exists(slot)), None)
    if slot is None:
        raise ValueError('Alle zehn Profilplätze sind belegt.')
    set_profile_name(slot, name)
    return slot


def profile_model_name(slot: int) -> str:
    try:
        name = (profile_slot_root(slot) / 'data' / 'model_override.txt').read_text(encoding='utf-8').strip()
    except (OSError, UnicodeError):
        return ''
    return name.replace('\\', '/').rsplit('/', 1)[-1]


def xp_needed_for_level(level: int) -> int:
    level = max(1, int(level or 1))
    return int(60 * (level ** 1.7))


def title_text(language: str) -> dict:
    language = normalize_language(language)
    if language == "en":
        return {
            "fallback_title": "Seeker in the Aeon of Maat",
            "fallback_rank": "Awakening",
            "fallback_motif": "The world is testing what shape is taking form in Maatis.",
            "subtitle_default": "Version 0.2 - Return of the Principles",
            "subtitle_restored": "The world remembers through your victory",
            "subtitle_boss": "The trials are becoming deeper and more personal",
            "subtitle_path": "A path woven from {title}",
            "profile": "Path Profile",
            "level": "Level",
            "boss_wins": "Boss Victories",
            "principles": "Principles",
            "profile_slot": "Profile",
            "enter": "ENTER - Awaken",
            "journal": "/journal - Decisions",
            "achievements": "/erfolge - Achievements",
            "help": "/help - Commands",
            "active": "MAAT-KI RPG ChatLoop 3.0 active.",
            "tip": "Tip: Use /help",
        }
    return {
        "fallback_title": "Suchender im Aeon der Maat",
        "fallback_rank": "Erwachend",
        "fallback_motif": "Die Welt prueft, was in Maatis Form annimmt.",
        "subtitle_default": "Version 0.2 - Rueckkehr der Prinzipien",
        "subtitle_restored": "Die Welt erinnert sich durch deinen Sieg",
        "subtitle_boss": "Die Pruefungen werden tiefer und persoenlicher",
        "subtitle_path": "Ein Weg aus {title}",
        "profile": "Pfadprofil",
        "level": "Level",
        "boss_wins": "Boss-Siege",
        "principles": "Prinzipien",
        "profile_slot": "Profil",
        "enter": "ENTER - Erwachen",
        "journal": "/journal - Entscheidungen",
        "achievements": "/erfolge - Erfolge",
        "help": "/help - Kommandos",
        "active": "MAAT-KI RPG ChatLoop 3.0 aktiv.",
        "tip": "Tipp: Nutze /help",
    }


def localize_path_profile(profile: dict, language: str) -> dict:
    localized = dict(profile or {})
    if normalize_language(language) != "en":
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


def profile_summary(slot: int, language: str | None = None) -> dict:
    language = normalize_language(language or profile_language(slot))
    root = profile_slot_root(slot)
    story_filename = "companion_story_state.json" if load_profile_settings(slot).get("gui_perspective") == "companion" else "story_state.json"
    story_state = load_json_file(root / "state" / story_filename)
    battle_state = load_json_file(root / "state" / "battle_state.json")

    player = battle_state.get("player", {}) if isinstance(battle_state.get("player"), dict) else {}
    stats = battle_state.get("stats", {}) if isinstance(battle_state.get("stats"), dict) else {}
    world = battle_state.get("world", {}) if isinstance(battle_state.get("world"), dict) else {}
    achievements = battle_state.get("achievements", {}) if isinstance(battle_state.get("achievements"), dict) else {}
    path_profile = story_state.get("path_profile") if isinstance(story_state.get("path_profile"), dict) else {}
    path_profile = localize_path_profile(path_profile, language)

    level = int(player.get("level", 1) or 1)
    from shared.core.hero_classes import selected_class
    records = battle_state.get("dungeon_runs", {})
    records = [r for r in records.values() if isinstance(r, dict)] if isinstance(records, dict) else []
    plus = battle_state.get("dungeon_plus", {})
    plus = plus if isinstance(plus, dict) else {}
    return {
        "slot": slot,
        "name": profile_slot_label(slot, language),
        "model_name": profile_model_name(slot),
        "hero_class": selected_class(battle_state),
        "fights_total": int(stats.get("fights_total", 0) or 0),
        "fights_won": int(stats.get("fights_won", 0) or 0),
        "dungeon_attempts": sum(int(r.get("attempts", 0) or 0) for r in records),
        "dungeon_completed": sum(int(r.get("completed", 0) or 0) for r in records),
        "dungeon_plus_best": int(plus.get("best_wave", 0) or 0),
        "used": profile_slot_used(slot),
        "language": language,
        "root": root,
        "title": path_profile.get("title"),
        "rank": path_profile.get("rank"),
        "motif": path_profile.get("motif"),
        "level": level,
        "hp": int(player.get("hp", player.get("max_hp", 120)) or 120),
        "max_hp": int(player.get("max_hp", 120) or 120),
        "xp": int(player.get("xp", 0) or 0),
        "next_xp": xp_needed_for_level(level + 1),
        "gold": int(player.get("gold", 0) or 0),
        "potions": int(player.get("potions", 0) or 0),
        "boss_wins": int(stats.get("boss_wins", 0) or 0),
        "final_wins": int(stats.get("final_wins", 0) or 0),
        "principles": int(world.get("principles_restored", 0) or 0),
        "messages_total": int(stats.get("messages_total", 0) or 0),
        "journal_entries": len(story_state.get("journal", []) or []),
        "combat_achievements": len(achievements.get("combat", []) or []),
    }


def title_context(language: str | None = None, slot: int | None = None) -> dict:
    slot = int(slot or active_profile_slot() or 1)
    language = normalize_language(language or profile_language(slot))
    text = title_text(language)
    summary = profile_summary(slot, language=language)

    title = summary["title"] or text["fallback_title"]
    rank = summary["rank"] or text["fallback_rank"]
    motif = summary["motif"] or text["fallback_motif"]
    restored = int(summary["principles"])
    boss_wins = int(summary["boss_wins"])

    if restored > 0:
        subtitle = text["subtitle_restored"]
    elif boss_wins >= 3:
        subtitle = text["subtitle_boss"]
    elif summary["title"]:
        subtitle = text["subtitle_path"].format(title=title.lower())
    else:
        subtitle = text["subtitle_default"]

    return {
        "language": language,
        "subtitle": subtitle,
        "title": title,
        "rank": rank,
        "motif": motif,
        "level": int(summary["level"]),
        "boss_wins": boss_wins,
        "final_wins": int(summary["final_wins"]),
        "restored": restored,
        "gold": int(summary["gold"]),
        "potions": int(summary["potions"]),
        "xp": int(summary["xp"]),
        "journal_entries": int(summary["journal_entries"]),
        "combat_achievements": int(summary["combat_achievements"]),
        "active_profile_label": profile_slot_label(slot, language),
        "root": summary["root"],
    }


def prepare_profile_runtime(slot: int, language_hint: str | None = None) -> dict:
    profile_root = profile_slot_root(slot)
    models_dir = BASE_APP_SUPPORT_DIR / "models"
    data_dir = profile_root / "data"
    logs_dir = profile_root / "logs"
    cache_dir = profile_root / "cache"
    saves_dir = profile_root / "saves"
    state_dir = profile_root / "state"

    for path in [profile_root, models_dir, data_dir, logs_dir, cache_dir, saves_dir, state_dir]:
        path.mkdir(parents=True, exist_ok=True)

    os.environ["MAAT_APP_SUPPORT_DIR"] = str(profile_root)
    os.environ["MAAT_DATA_DIR"] = str(data_dir)
    os.environ["MAAT_MODELS_DIR"] = str(models_dir)
    os.environ["MAAT_LOGS_DIR"] = str(logs_dir)
    os.environ["MAAT_CACHE_DIR"] = str(cache_dir)
    os.environ["MAAT_SAVES_DIR"] = str(saves_dir)
    os.environ["MAAT_STATE_DIR"] = str(state_dir)

    # Older terminal plugins read this field directly. It mirrors the global
    # choice when a profile starts; it is no longer a separate GUI preference.
    effective_language = application_language() or language_hint
    saved_language = load_json_file(profile_settings_path(slot)).get('language')
    if (application_language() and saved_language != effective_language) or (
            effective_language in ('de', 'en') and not profile_has_explicit_language(slot)):
        write_profile_settings(slot, {"language": effective_language})

    return {
        "app_support_dir": profile_root,
        "data_dir": data_dir,
        "models_dir": models_dir,
        "logs_dir": logs_dir,
        "cache_dir": cache_dir,
        "saves_dir": saves_dir,
        "state_dir": state_dir,
    }


def delete_profile_slot(slot: int) -> bool:
    """Delete exactly one extra save slot; the standard root holds shared assets."""
    import shutil
    if type(slot) is not int or not 2 <= slot <= PROFILE_SLOT_COUNT:
        raise ValueError('Nur die zusätzlichen Profile 2 bis 4 können gelöscht werden.')
    root = profile_slot_root(slot)
    if root.is_symlink() or root.resolve().parent != PROFILES_DIR.resolve():
        raise ValueError('Der Profilpfad verweist nicht auf einen regulären Profilordner.')
    if not root.exists():
        return False
    shutil.rmtree(root)
    if active_profile_slot() == slot:
        write_profile_manager_state({'active_profile': 1})
    return True
