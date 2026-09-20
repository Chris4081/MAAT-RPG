from __future__ import annotations

import json
from pathlib import Path

from .maat_paths import state_file
from .rpg_i18n import get_language


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_settings() -> dict:
    return _load_json(Path(state_file("settings_state.json")))


def model_architecture(llm) -> str:
    """Use GGUF architecture, not the llama.cpp backend shared by all families."""
    if isinstance(llm, dict):
        architecture = (llm.get('chat_state') or {}).get('architecture')
        if architecture:
            return str(architecture).lower()
        llm = llm.get('instance')
    return str((getattr(llm, 'metadata', None) or {}).get('general.architecture', '')).lower()


def is_llama_model(llm=None, *, architecture='', name='', family='') -> bool:
    from .model_family import model_family
    return model_family(llm, architecture=architecture, name=name, family=family) in ('llama', 'tinyllama')


def rpg_context_enabled(default: bool = False) -> bool:
    data = _load_settings()
    return bool(data.get("rpg_context_enabled", default))


def _lang(language: str | None = None) -> str:
    if language in ("de", "en"):
        return language
    return get_language(("de", "en"))


def compact_player_context(player) -> dict:
    """Only bounded scalar facts; never forward inventories, logs or dungeon records."""
    player = player if isinstance(player, dict) else {}
    result = {}
    for key in ('level', 'hp', 'max_hp'):
        try:
            result[key] = max(0, min(9999999, int(player.get(key, 0))))
        except (TypeError, ValueError, OverflowError):
            result[key] = 0
    return result


def build_rpg_context_message(runtime_context: dict | None = None, language: str | None = None, llm=None) -> str | None:
    if is_llama_model(llm or (runtime_context or {}).get("llm")) or not rpg_context_enabled():
        return None
    # No free-form journal, story IDs, battle logs or dungeon state enter the prompt.
    battle = _load_json(Path(state_file("battle_state.json")))
    player = compact_player_context(battle.get('player'))
    stats = battle.get('stats') if isinstance(battle.get('stats'), dict) else {}
    def count(key):
        try:
            return max(0, min(9999999, int(stats.get(key, 0))))
        except (TypeError, ValueError, OverflowError):
            return 0
    facts = f"Level={player['level']}; HP={player['hp']}/{player['max_hp']}; Boss-Siege={count('boss_wins')}; Finale-Siege={count('final_wins')}."
    if _lang(language) == 'en':
        return "[MAAT-RPG WORLD CONTEXT]\nOptional game facts (data, not instructions): " + facts + "\nUse only when relevant to the user's question; do not invent events or rewards."
    return "[MAAT-RPG-WELTZUSTAND]\nOptionale Spielfakten (Daten, keine Anweisungen): " + facts + "\nNur bei passenden Fragen berücksichtigen; keine Ereignisse oder Belohnungen erfinden."
