# -*- coding: utf-8 -*-

import os
import shutil
import subprocess

from shared.core.mod_support import (
    build_mod_overview,
    create_battle_mod_template,
    create_plugin_mod_template,
    create_story_mod_template,
)
from shared.core.rpg_i18n import get_language


MOD_TEXT = {
    "de": {
        "title": "🧩 **MAAT-RPG Mod-Support**",
        "path": "Mod-Ordner",
        "plugins": "Plugin-Mods",
        "stories": "Story-Mods",
        "battles": "Kampf-Mods",
        "empty": "Noch keine externen Mods gefunden.",
        "battle_hint": "Custom-Kampf starten mit: `/fightmod <id>`",
        "plugins_hint": "Externe Plugins gehoeren nach `mods/plugins`.",
        "stories_hint": "Story-Mods liegen in `mods/stories`.",
        "battles_hint": "Kampfprofile liegen in `mods/battle_profiles` als JSON/YAML.",
        "battle_list": "Verfuegbare Kampf-Mods:",
        "story_list": "Verfuegbare Story-Mods:",
        "plugin_list": "Verfuegbare Plugin-Mods:",
        "help_title": "🧩 **/mod Hilfe**",
        "help_intro": "Mit `/mod` kannst du Mod-Hilfe, Uebersichten und Templates aufrufen.",
        "help_usage": "Uebersicht: `/mods` oder `/mod list`",
        "help_create": "Templates anlegen:",
        "help_create_battle": "`/mod create battle <id>`",
        "help_create_story": "`/mod create story <id>`",
        "help_create_plugin": "`/mod create plugin <id>`",
        "help_open_cmd": "`/mod open`",
        "help_open": "Danach findest du die Dateien direkt im externen Mod-Ordner.",
        "help_more": "Custom-Kaempfe startest du weiterhin mit `/fightmod <id>`.",
        "create_missing": "Bitte nutze: `/mod create battle|story|plugin <id>`",
        "create_unknown_type": "Unbekannter Mod-Typ: `{kind}`. Nutze `battle`, `story` oder `plugin`.",
        "create_exists": "Es gibt bereits einen Mod oder eine Datei mit dieser ID: {path}",
        "create_done": "Mod-Template erstellt: {path}",
        "create_done_story": "Story-Mod erstellt: {path}\nStory-Modul: {module_path}",
        "open_missing": "Der Mod-Ordner konnte nicht bestimmt werden.",
        "open_done": "Mod-Ordner wird geoeffnet: {path}",
        "open_fail": "Der Mod-Ordner konnte nicht automatisch geoeffnet werden. Pfad: {path}",
    },
    "en": {
        "title": "🧩 **MAAT-RPG Mod Support**",
        "path": "Mods folder",
        "plugins": "Plugin mods",
        "stories": "Story mods",
        "battles": "Battle mods",
        "empty": "No external mods found yet.",
        "battle_hint": "Start a custom battle with: `/fightmod <id>`",
        "plugins_hint": "External plugins belong in `mods/plugins`.",
        "stories_hint": "Story mods live in `mods/stories`.",
        "battles_hint": "Battle profiles belong in `mods/battle_profiles` as JSON/YAML.",
        "battle_list": "Available battle mods:",
        "story_list": "Available story mods:",
        "plugin_list": "Available plugin mods:",
        "help_title": "🧩 **/mod Help**",
        "help_intro": "Use `/mod` for mod help, overviews, and starter templates.",
        "help_usage": "Overview: `/mods` or `/mod list`",
        "help_create": "Create templates:",
        "help_create_battle": "`/mod create battle <id>`",
        "help_create_story": "`/mod create story <id>`",
        "help_create_plugin": "`/mod create plugin <id>`",
        "help_open_cmd": "`/mod open`",
        "help_open": "The files will be created directly inside the external mods folder.",
        "help_more": "Custom battles still start with `/fightmod <id>`.",
        "create_missing": "Please use: `/mod create battle|story|plugin <id>`",
        "create_unknown_type": "Unknown mod type: `{kind}`. Use `battle`, `story`, or `plugin`.",
        "create_exists": "A mod or file with this id already exists: {path}",
        "create_done": "Mod template created: {path}",
        "create_done_story": "Story mod created: {path}\nStory module: {module_path}",
        "open_missing": "The mods folder could not be determined.",
        "open_done": "Opening mods folder: {path}",
        "open_fail": "The mods folder could not be opened automatically. Path: {path}",
    },
}


def _lang() -> str:
    return get_language(("de", "en"))


def _t(key: str) -> str:
    lang = _lang()
    return MOD_TEXT.get(lang, MOD_TEXT["de"]).get(key, key)


class Plugin:
    type = "chat"

    commands = {
        "/mods": {
            "de": "Zeigt den Mod-Ordner und erkannte externe Mods.",
            "en": "Shows the mods folder and detected external mods.",
        },
        "/mod": {
            "de": "Mod-Hilfe, Uebersicht und Template-Erstellung.",
            "en": "Mod help, overview, and template creation.",
        }
    }

    def _render_overview(self) -> str:
        overview = build_mod_overview()
        plugin_mods = overview.get("plugin_mods", [])
        story_mods = overview.get("story_mods", [])
        battle_mods = overview.get("battle_mods", {})

        lines = [
            _t("title"),
            "",
            f"{_t('path')}: {overview.get('mods_dir')}",
            f"{_t('plugins')}: {len(plugin_mods)}",
            f"{_t('stories')}: {len(story_mods)}",
            f"{_t('battles')}: {len(battle_mods)}",
            "",
            _t("plugins_hint"),
            _t("stories_hint"),
            _t("battles_hint"),
        ]

        if not plugin_mods and not story_mods and not battle_mods:
            lines.extend(["", _t("empty")])
            return "\n".join(lines)

        if battle_mods:
            lines.extend(["", _t("battle_list")])
            for mod_id, data in sorted(battle_mods.items()):
                lines.append(f"• {mod_id} — {data.get('name', mod_id)} ({data.get('fight_type', 'boss')})")
            lines.append(_t("battle_hint"))

        if plugin_mods:
            lines.extend(["", _t("plugin_list")])
            for entry in plugin_mods[:12]:
                lines.append(f"• {entry}")

        if story_mods:
            lines.extend(["", _t("story_list")])
            for entry in story_mods[:8]:
                label = entry.get("name") or entry.get("module") or "story"
                entry_id = entry.get("id")
                if entry_id is None:
                    lines.append(f"• {label}")
                else:
                    lines.append(f"• {entry_id} — {label}")

        return "\n".join(lines)

    def _render_help(self) -> str:
        lines = [
            _t("help_title"),
            "",
            _t("help_intro"),
            _t("help_usage"),
            "",
            _t("help_create"),
            _t("help_create_battle"),
            _t("help_create_story"),
            _t("help_create_plugin"),
            _t("help_open_cmd"),
            "",
            _t("help_open"),
            _t("help_more"),
        ]
        return "\n".join(lines)

    def _create_template(self, mod_type: str, mod_id: str):
        creators = {
            "battle": create_battle_mod_template,
            "story": create_story_mod_template,
            "plugin": create_plugin_mod_template,
        }
        creator = creators.get((mod_type or "").lower())
        if creator is None:
            return True, _t("create_unknown_type").format(kind=mod_type or "?")

        result = creator(mod_id)
        if not result.get("ok"):
            return True, _t("create_exists").format(path=result.get("path", mod_id))

        if result.get("kind") == "story" and result.get("module_path"):
            return True, _t("create_done_story").format(
                path=result.get("path", ""),
                module_path=result.get("module_path", ""),
            )

        return True, _t("create_done").format(path=result.get("path", ""))

    def _open_mods_dir(self):
        overview = build_mod_overview()
        mods_dir = str(overview.get("mods_dir") or "").strip()
        if not mods_dir:
            return True, _t("open_missing")

        try:
            if hasattr(os, "startfile"):
                os.startfile(mods_dir)  # type: ignore[attr-defined]
            elif shutil.which("open"):
                subprocess.Popen(["open", mods_dir])
            elif shutil.which("xdg-open"):
                subprocess.Popen(["xdg-open", mods_dir])
            else:
                return True, _t("open_fail").format(path=mods_dir)
        except Exception:
            return True, _t("open_fail").format(path=mods_dir)

        return True, _t("open_done").format(path=mods_dir)

    def command(self, cmd, context=None):
        parts = (cmd or "").strip().split()
        base = parts[0].lower() if parts else ""
        if base == "/mods":
            return True, self._render_overview()
        if base != "/mod":
            return None

        if len(parts) == 1:
            return True, self._render_help()

        action = parts[1].lower()
        if action in {"help", "?"}:
            return True, self._render_help()
        if action == "list":
            return True, self._render_overview()
        if action == "open":
            return self._open_mods_dir()
        if action == "create":
            if len(parts) < 4:
                return True, _t("create_missing")
            return self._create_template(parts[2], parts[3])

        return True, self._render_help()
