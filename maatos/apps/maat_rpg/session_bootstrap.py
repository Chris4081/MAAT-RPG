# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dataclasses import dataclass, field
from textwrap import dedent
from typing import Any

from shared.core.command_router import CommandRouter


@dataclass(slots=True)
class BootstrapNotice:
    level: str
    message: str


@dataclass(slots=True)
class SessionBootstrap:
    language: str
    profile: dict
    profile_path: str | None
    system_prompt: str
    plugin_manager: Any | None
    command_router: CommandRouter
    conversation: list[dict]
    context: dict
    battle_core: Any | None
    notices: list[BootstrapNotice] = field(default_factory=list)


def load_yaml_profile(root: str, language: str) -> tuple[dict, str | None, list[BootstrapNotice]]:
    import yaml

    notices: list[BootstrapNotice] = []
    profile_name = "maat_rpg_en.yaml" if language == "en" else "maat_rpg.yaml"
    profile_path = os.path.join(root, "profiles", profile_name)

    def _read(path: str) -> dict | None:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            notices.append(
                BootstrapNotice(
                    "warning",
                    (
                        f"⚠️ YAML could not be loaded: {exc}"
                        if language == "en"
                        else f"⚠️ YAML konnte nicht geladen werden: {exc}"
                    ),
                )
            )
            return None

    profile = _read(profile_path) or {}
    if not profile and profile_name != "maat_rpg.yaml":
        fallback_path = os.path.join(root, "profiles", "maat_rpg.yaml")
        profile = _read(fallback_path) or {}
        profile_path = fallback_path

    if profile:
        notices.append(
            BootstrapNotice(
                "success",
                (
                    f"✅ YAML profile loaded: {profile_path}"
                    if language == "en"
                    else f"✅ YAML-Profil geladen: {profile_path}"
                ),
            )
        )
        return profile, profile_path, notices

    notices.append(
        BootstrapNotice(
            "warning",
            (
                "⚠️ No YAML profile found – using standard prompt."
                if language == "en"
                else "⚠️ Kein YAML-Profil gefunden – nutze Standardprompt."
            ),
        )
    )
    return {}, None, notices


def build_systemprompt(profile: dict) -> str:
    sp = profile.get("systemprompt")
    if isinstance(sp, str) and sp.strip():
        return sp.strip()

    name = profile.get("name", "MAAT-KI")
    title = profile.get("title", "Äonische Resonanz-Intelligenz")

    return dedent(
        f"""
        Du bist {name} – {title}.

        Regeln:
        - Folge dem gewählten Antwortstil; ohne Vorgabe kurz und klar (1–3 Sätze)
        - Optional 1 passendes Emoji
        - Keine Wiederholungen
        - Keine lange Selbstbeschreibung
        - Wenn passend: kurze Reflexionsfrage am Ende

        Prinzipien:
        Harmonie, Balance, Schöpfungskraft, Verbundenheit, Respekt

        Nutze den Maat-Wert:
        - Maat-Wert = (H + B + S + V + R) / 5
        """
    ).strip()


def resolve_battle_core(pm: Any | None) -> Any | None:
    if not pm:
        return None

    try:
        for plugin in pm.iter_all_plugins():
            if hasattr(plugin, "run_fight") and callable(getattr(plugin, "run_fight")):
                return plugin

            core = getattr(plugin, "core", None)
            if core and hasattr(core, "run_fight") and callable(getattr(core, "run_fight")):
                return core
    except Exception:
        pass

    return None


def build_command_router(language: str, clear_handler=None, exit_handler=None) -> CommandRouter:
    command_router = CommandRouter()

    command_router.register(
        "/help",
        lambda args: command_router.help_text(),
        aliases=["/h", "/hilfe"],
        description={
            "de": "Zeigt alle Kommandos.",
            "en": "Shows all commands.",
        },
    )

    def cmd_clear(args):
        if callable(clear_handler):
            return clear_handler(args)
        os.system("cls" if os.name == "nt" else "clear")
        return None

    command_router.register(
        "/clear",
        cmd_clear,
        aliases=["/cls"],
        description={
            "de": "Leert den Bildschirm.",
            "en": "Clears the screen.",
        },
    )

    command_router.register(
        "/exit",
        exit_handler
        if callable(exit_handler)
        else lambda args: (
            "Use /quit or CTRL+C."
            if language == "en"
            else "Nutze /quit oder STRG+C."
        ),
        aliases=["/quit"],
        description={
            "de": "Beendet das Programm.",
            "en": "Exits the program.",
        },
    )
    return command_router


def load_plugin_manager(root: str, mods_plugins_dir: str, language: str) -> tuple[Any | None, list[BootstrapNotice]]:
    notices: list[BootstrapNotice] = []

    try:
        from shared.plugins.plugin_loader import PluginManager
    except Exception as exc:
        notices.append(BootstrapNotice("error", f"❌ IMPORTFEHLER PluginManager: {exc}"))
        return None, notices

    try:
        app_plugin_root = os.path.join(os.path.dirname(__file__), "plugins")
        shared_plugin_root = os.path.join(root, "shared", "plugins")
        plugin_config_path = os.path.join(os.path.dirname(__file__), "plugin_config.json")
        pm = PluginManager(
            [app_plugin_root, shared_plugin_root, str(mods_plugins_dir)],
            config_path=plugin_config_path,
        )
        pm.load_plugins()
        notices.append(
            BootstrapNotice(
                "success",
                "🔌 Plugin commands loaded."
                if language == "en"
                else "🔌 Plugin-Kommandos geladen.",
            )
        )
        return pm, notices
    except Exception as exc:
        notices.append(BootstrapNotice("error", f"⚠ Plugin-Fehler: {exc}"))
        return None, notices


def run_startup_hooks(pm: Any | None, context: dict) -> list[BootstrapNotice]:
    notices: list[BootstrapNotice] = []
    if not pm:
        return notices

    for plugin in pm.iter_all_plugins():
        on_start = getattr(plugin, "on_startup", None)
        if callable(on_start):
            try:
                on_start(context)
            except Exception as exc:
                notices.append(BootstrapNotice("error", f"[PLUGIN STARTUP ERROR] {exc}"))
    return notices


def bootstrap_rpg_session(
    *,
    root: str,
    language: str,
    mods_plugins_dir: str,
    system_prompt_rpg_appendix: str,
    rpg_mode: bool = True,
) -> SessionBootstrap:
    notices: list[BootstrapNotice] = []
    profile, profile_path, yaml_notices = load_yaml_profile(root, language)
    notices.extend(yaml_notices)
    other_language = 'de' if language == 'en' else 'en'
    other_profile, _, _ = load_yaml_profile(root, other_language)

    system_prompt = build_systemprompt(profile)
    if not system_prompt.strip():
        system_prompt = "Du bist MAAT-KI. Antworte kurz, klar, spielorientiert. 🌿"

    pm, plugin_notices = load_plugin_manager(root, mods_plugins_dir, language)
    notices.extend(plugin_notices)

    command_router = build_command_router(language)
    if pm:
        pm.register_plugin_commands(command_router)

    conversation = [{"role": "system", "content": system_prompt}]
    context = {
        "pm": pm,
        "command_router": command_router,
        "conversation": conversation,
        "profile": profile,
        "profile_variants": {language: profile, other_language: other_profile},
        "rpg": {
            "mode": bool(rpg_mode),
            "battle_core": None,
            "messages_since_reset": 0,
        },
    }

    if rpg_mode:
        conversation[0]["content"] = conversation[0]["content"].rstrip() + "\n\n" + system_prompt_rpg_appendix

    battle_core = resolve_battle_core(pm)
    if battle_core:
        context["rpg"]["battle_core"] = battle_core
        # The loader constructs plugins without arguments. Bind quests before
        # startup so levels, rewards and saves use the same authoritative state.
        for plugin in pm.iter_all_plugins():
            if getattr(plugin, 'plugin_id', '') == 'quests':
                plugin.core = battle_core
                plugin.state = battle_core.state
                plugin._ensure_state()
                plugin._ensure_default_quests()
                plugin._save_runtime_state()
        notices.append(
            BootstrapNotice(
                "success",
                "⚔️ BattleCore found and bound automatically."
                if language == "en"
                else "⚔️ BattleCore automatisch gefunden und gebunden.",
            )
        )
    else:
        notices.append(
            BootstrapNotice(
                "warning",
                "⚠️ No BattleCore found (check plugin 'battle')."
                if language == "en"
                else "⚠️ Kein BattleCore gefunden (Plugin 'battle' prüfen).",
            )
        )

    return SessionBootstrap(
        language=language,
        profile=profile,
        profile_path=profile_path,
        system_prompt=conversation[0]["content"],
        plugin_manager=pm,
        command_router=command_router,
        conversation=conversation,
        context=context,
        battle_core=battle_core,
        notices=notices,
    )
