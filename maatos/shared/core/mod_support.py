# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
import zlib
from pathlib import Path

from shared.core.maat_paths import (
    get_mods_dir,
    get_mods_plugins_dir,
    get_mods_stories_dir,
    get_mods_battle_profiles_dir,
)

try:
    import yaml
except Exception:
    yaml = None


_DATA_SUFFIXES = {".json", ".yaml", ".yml"}
_VALID_FIGHT_TYPES = {"normal", "boss", "final"}


def _slugify(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    return text.strip("_") or "mod"


def _load_data_file(path: Path) -> dict:
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix.lower() in {".yaml", ".yml"} and yaml is not None:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        else:
            return {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _iter_data_files(root: Path):
    if not root.exists():
        return []
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in _DATA_SUFFIXES:
            files.append(path)
    return files


def resolve_mod_asset_path(raw_path: str | None, base_dir: str | Path | None = None) -> str | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None

    candidate = Path(raw_path.strip()).expanduser()
    if candidate.is_absolute():
        return str(candidate)

    if base_dir is not None:
        return str(Path(base_dir) / candidate)

    return str(candidate)


def get_mod_story_entries() -> list[dict]:
    entries: list[dict] = []
    try:
        story_root = get_mods_stories_dir()
    except Exception:
        return entries
    for path in _iter_data_files(story_root):
        data = _load_data_file(path)
        stories = data.get("stories")
        if not isinstance(stories, list):
            continue
        for raw in stories:
            if not isinstance(raw, dict):
                continue
            entry = dict(raw)
            entry["_mod_root"] = str(path.parent)
            entry["_mod_source"] = str(path)
            entries.append(entry)
    return entries


def merge_story_config(base_config: dict | None) -> dict:
    base_config = dict(base_config or {})
    base_stories = list(base_config.get("stories", [])) if isinstance(base_config.get("stories"), list) else []
    merged = list(base_stories)

    for entry in get_mod_story_entries():
        story_id = entry.get("id")
        replaced = False
        if story_id is not None:
            for idx, existing in enumerate(merged):
                if isinstance(existing, dict) and existing.get("id") == story_id:
                    merged[idx] = entry
                    replaced = True
                    break
        if not replaced:
            merged.append(entry)

    base_config["stories"] = merged
    return base_config


def resolve_story_module_path(module_name: str | None, builtin_story_dir: str | Path, entry: dict | None = None) -> Path:
    entry = entry if isinstance(entry, dict) else {}
    explicit_path = entry.get("module_path")
    if isinstance(explicit_path, str) and explicit_path.strip():
        return Path(resolve_mod_asset_path(explicit_path, entry.get("_mod_root")))

    module_name = (module_name or "").strip()
    if not module_name:
        return Path(builtin_story_dir) / "__missing__.py"

    if module_name.endswith(".py") or "/" in module_name or "\\" in module_name:
        return Path(resolve_mod_asset_path(module_name, entry.get("_mod_root")))

    mod_root = entry.get("_mod_root")
    if isinstance(mod_root, str) and mod_root.strip():
        candidate = Path(mod_root) / f"{module_name}.py"
        if candidate.is_file():
            return candidate

    try:
        mod_candidate = get_mods_stories_dir() / f"{module_name}.py"
        if mod_candidate.is_file():
            return mod_candidate
    except Exception:
        pass

    return Path(builtin_story_dir) / f"{module_name}.py"


def resolve_story_asset_path(asset_name: str | None, builtin_story_dir: str | Path, entry: dict | None = None) -> Path | None:
    if not isinstance(asset_name, str) or not asset_name.strip():
        return None

    entry = entry if isinstance(entry, dict) else {}
    direct = resolve_mod_asset_path(asset_name, entry.get("_mod_root"))
    if direct:
        candidate = Path(direct)
        if candidate.is_file():
            return candidate

    try:
        mod_candidate = get_mods_stories_dir() / asset_name
        if mod_candidate.is_file():
            return mod_candidate
    except Exception:
        pass

    builtin_candidate = Path(builtin_story_dir) / asset_name
    if builtin_candidate.is_file():
        return builtin_candidate

    absolute = Path(asset_name).expanduser()
    if absolute.is_absolute() and absolute.is_file():
        return absolute

    return None


def load_battle_profile_mods() -> dict[str, dict]:
    catalog: dict[str, dict] = {}
    try:
        battle_root = get_mods_battle_profiles_dir()
    except Exception:
        return catalog
    for path in _iter_data_files(battle_root):
        data = _load_data_file(path)
        if not data:
            continue

        mod_id = _slugify(str(data.get("id") or path.stem))
        fight_type = str(data.get("fight_type") or data.get("type") or data.get("mode") or "boss").strip().lower()
        if fight_type not in _VALID_FIGHT_TYPES:
            fight_type = "boss"

        profile = data.get("battle_profile")
        if not isinstance(profile, dict):
            profile = {}
        profile = dict(profile)

        if data.get("name") and not profile.get("boss_name") and fight_type in {"boss", "final"}:
            profile["boss_name"] = data.get("name")

        if isinstance(data.get("music"), dict) and not isinstance(profile.get("music"), dict):
            profile["music"] = dict(data["music"])

        music_cfg = profile.get("music")
        if isinstance(music_cfg, dict):
            resolved_music = {}
            for key, value in music_cfg.items():
                resolved_music[key] = resolve_mod_asset_path(value, path.parent) if isinstance(value, str) else value
            profile["music"] = resolved_music

        catalog[mod_id] = {
            "id": mod_id,
            "name": str(data.get("name") or profile.get("boss_name") or path.stem),
            "description": str(data.get("description") or ""),
            "fight_type": fight_type,
            "battle_profile": profile,
            "source": str(path),
            "persistent_rewards": bool(data.get("persistent_rewards", False)),
        }

    return catalog


def list_plugin_mods() -> list[str]:
    names: list[str] = []
    try:
        root = get_mods_plugins_dir()
    except Exception:
        return names
    if not root.exists():
        return names
    for entry in sorted(root.iterdir()):
        if entry.name.startswith("_"):
            continue
        if entry.is_dir() and (entry / "plugin_main.py").is_file():
            names.append(entry.name)
        elif entry.is_file() and entry.name.startswith("plugin_") and entry.suffix == ".py":
            names.append(entry.stem)
    return names


def list_story_mods() -> list[dict]:
    mods = []
    for entry in get_mod_story_entries():
        mods.append({
            "id": entry.get("id"),
            "name": entry.get("name") or entry.get("module") or "story",
            "module": entry.get("module") or entry.get("module_path") or "story",
            "source": entry.get("_mod_source"),
        })
    return mods


def build_mod_overview() -> dict:
    plugin_mods = list_plugin_mods()
    story_mods = list_story_mods()
    battle_mods = load_battle_profile_mods()
    try:
        mods_dir = str(get_mods_dir())
    except Exception:
        mods_dir = ""
    try:
        plugins_dir = str(get_mods_plugins_dir())
    except Exception:
        plugins_dir = ""
    try:
        stories_dir = str(get_mods_stories_dir())
    except Exception:
        stories_dir = ""
    try:
        battle_profiles_dir = str(get_mods_battle_profiles_dir())
    except Exception:
        battle_profiles_dir = ""
    return {
        "mods_dir": mods_dir,
        "plugins_dir": plugins_dir,
        "stories_dir": stories_dir,
        "battle_profiles_dir": battle_profiles_dir,
        "plugin_mods": plugin_mods,
        "story_mods": story_mods,
        "battle_mods": battle_mods,
    }


def _safe_title_from_id(mod_id: str) -> str:
    return " ".join(part.capitalize() for part in _slugify(mod_id).replace("-", "_").split("_") if part) or "Custom Mod"


def _story_numeric_id(mod_id: str) -> int:
    return 100000 + (zlib.crc32(_slugify(mod_id).encode("utf-8")) % 900000)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def create_battle_mod_template(mod_id: str) -> dict:
    slug = _slugify(mod_id)
    path = get_mods_battle_profiles_dir() / f"{slug}.json"
    if path.exists():
        return {"ok": False, "reason": "exists", "path": str(path), "id": slug}

    title = _safe_title_from_id(slug)
    payload = {
        "id": slug,
        "name": title,
        "fight_type": "boss",
        "description": "Custom battle mod template.",
        "persistent_rewards": False,
        "battle_profile": {
            "boss_name": title,
            "intro_lines": [
                "A new presence enters the arena."
            ],
            "victory_lines": [
                "The arena falls silent again."
            ],
            "enemy": {
                "hp_mult": 1.0,
                "damage_mult": 1.0
            },
            "boss_profile": {
                "title": "Custom Boss",
                "intro": "A new foe takes shape.",
                "special": "Unknown Strike"
            }
        }
    }
    _write_json(path, payload)
    return {"ok": True, "path": str(path), "id": slug, "kind": "battle"}


def create_story_mod_template(mod_id: str) -> dict:
    slug = _slugify(mod_id)
    config_path = get_mods_stories_dir() / f"{slug}.json"
    module_path = get_mods_stories_dir() / f"{slug}.py"
    if config_path.exists() or module_path.exists():
        return {
            "ok": False,
            "reason": "exists",
            "path": str(config_path if config_path.exists() else module_path),
            "id": slug,
        }

    title = _safe_title_from_id(slug)
    payload = {
        "stories": [
            {
                "id": _story_numeric_id(slug),
                "name": title,
                "module": slug,
                "music": "",
                "trigger": {
                    "type": "message_count",
                    "messages": 12,
                    "position": "before"
                }
            }
        ]
    }
    module_code = (
        "class Story:\n"
        "    def run(self):\n"
        "        return [\n"
        f"            \"{title} begins.\",\n"
        "            \"Replace this text with your own story scene.\",\n"
        "        ]\n"
    )
    _write_json(config_path, payload)
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text(module_code, encoding="utf-8")
    return {"ok": True, "path": str(config_path), "module_path": str(module_path), "id": slug, "kind": "story"}


def create_plugin_mod_template(mod_id: str) -> dict:
    slug = _slugify(mod_id)
    plugin_dir = get_mods_plugins_dir() / slug
    plugin_main = plugin_dir / "plugin_main.py"
    if plugin_dir.exists() or plugin_main.exists():
        return {"ok": False, "reason": "exists", "path": str(plugin_main), "id": slug}

    title = _safe_title_from_id(slug)
    code = (
        "# -*- coding: utf-8 -*-\n\n"
        "class Plugin:\n"
        "    type = \"chat\"\n\n"
        "    commands = {\n"
        f"        \"/{slug}\": {{\"de\": \"{title} Mod\", \"en\": \"{title} mod\"}}\n"
        "    }\n\n"
        "    def command(self, cmd, context=None):\n"
        f"        if (cmd or '').strip().split()[0].lower() == '/{slug}':\n"
        f"            return True, \"{title} mod loaded.\"\n"
        "        return None\n"
    )
    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_main.write_text(code, encoding="utf-8")
    return {"ok": True, "path": str(plugin_main), "id": slug, "kind": "plugin"}
