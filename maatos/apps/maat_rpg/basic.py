# -*- coding: utf-8 -*-
"""
MAAT-KI RPG — ChatLoop 3.0 (FIXED)
----------------------------------
🌿 Harmonie zwischen Kernsystem und Plugins
⚖️ Balance zwischen Einfachheit und Tiefe
🎨 Schöpfungskraft durch Erweiterbarkeit
🌐 Verbundenheit über Shared-Plugins
🕊️ Respekt vor Stabilität und Nutzererfahrung
"""

import readline
import os
import sys
import sqlite3
import subprocess
import json
from pathlib import Path
from colorama import Fore, Style, init
from shared.core.rpg_i18n import get_language


DEBUG_STARTUP = os.environ.get("MAAT_DEBUG_STARTUP") == "1"


def _dbg(msg: str):
    if DEBUG_STARTUP:
        print(msg)

# -------------------------------------------------
# ROOT / ZENTRALE MAAT-PFADE
# -------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
_dbg("🧪 basic.py: C – ROOT done")

APP_NAME = "MAAT-RPG"
APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
DATA_DIR = APP_SUPPORT_DIR / "data"
MODELS_DIR = APP_SUPPORT_DIR / "models"
LOGS_DIR = APP_SUPPORT_DIR / "logs"
CACHE_DIR = APP_SUPPORT_DIR / "cache"
SAVES_DIR = APP_SUPPORT_DIR / "saves"
STATE_DIR = APP_SUPPORT_DIR / "state"

for p in [APP_SUPPORT_DIR, DATA_DIR, MODELS_DIR, LOGS_DIR, CACHE_DIR, SAVES_DIR, STATE_DIR]:
    p.mkdir(parents=True, exist_ok=True)

MODEL_DIR = str(MODELS_DIR)

# Optional: global per env weiterreichen
os.environ["MAAT_APP_SUPPORT_DIR"] = str(APP_SUPPORT_DIR)
os.environ["MAAT_DATA_DIR"] = str(DATA_DIR)
os.environ["MAAT_MODELS_DIR"] = str(MODELS_DIR)
os.environ["MAAT_LOGS_DIR"] = str(LOGS_DIR)
os.environ["MAAT_CACHE_DIR"] = str(CACHE_DIR)
os.environ["MAAT_SAVES_DIR"] = str(SAVES_DIR)

_dbg(f"🧪 basic.py: App Support = {APP_SUPPORT_DIR}")
_dbg(f"🧪 basic.py: Data Dir    = {DATA_DIR}")
_dbg(f"🧪 basic.py: Models Dir  = {MODELS_DIR}")

# -------------------------------------------------
# SELF-EVOLUTION IMPORT (abgesichert)
# -------------------------------------------------
try:
    from shared.core.self_evolution import SelfEvolutionEngine  # v4.4
    _dbg("🧪 basic.py: D – SelfEvolutionEngine imported")
except Exception as e:
    print(f"⚠️ SelfEvolutionEngine konnte nicht geladen werden: {e}")
    SelfEvolutionEngine = None

# -------------------------------------------------
# SHARED IMPORTS
# -------------------------------------------------
from shared.profile_loader import ProfileLoader
_dbg("🧪 basic.py: E – ProfileLoader imported")

from shared.core.llm_loader import (
    load_llm,
    choose_performance,
    auto_select_model,
)
_dbg("🧪 basic.py: F – llm_loader imported")

from shared.core.streaming import stream_chat_completion, stream_to_console, stream_text_to_console
_dbg("🧪 basic.py: G – streaming imported")

from shared.core.command_router import CommandRouter
_dbg("🧪 basic.py: H – CommandRouter imported")

# Plugin-System
try:
    from shared.plugins.plugin_loader import PluginManager
    _dbg("➡️ PluginManager erfolgreich importiert.")
except Exception as e:
    print("❌ IMPORTFEHLER PluginManager:", e)
    PluginManager = None
_dbg("🧪 basic.py: Plugin Manager")


# -------------------------------------------------
# RPG APPENDIX (wird an Systemprompt angehängt)
# -------------------------------------------------
SYSTEM_PROMPT_RPG_APPENDIX = """
[RPG-MODUS]
- Du erinnerst dich NICHT an den gesamten Dialogverlauf.
- Du reagierst nur auf den aktuellen Weltzustand.
- Kämpfe, Zahlen, Logs und Mechaniken liegen außerhalb deines Gedächtnisses.
- Beschreibe Resonanz, Bedeutung und Konsequenz – nicht Technik.
""".strip()


# -------------------------------------------------
# MEMORY-V5 HISTORY (nur optional)
# -------------------------------------------------
def load_last_messages_from_memory_v5(limit=15):
    try:
        db_path = str(DATA_DIR / "memory_v5.db")
        if not os.path.exists(db_path):
            return []

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT role, content FROM episodic ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()

        rows.reverse()

        messages = []
        for role, content in rows:
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": content})
        return messages

    except Exception as e:
        print(f"⚠ Memory-V5 Fehler: {e}")
        return []


# -------------------------------------------------
# Systemprompt Check (nur Terminal-Warnungen)
# -------------------------------------------------
def check_systemprompt(conversation):
    try:
        language = _ui_language()
        sys_msg = None
        for msg in conversation:
            if msg.get("role") == "system":
                sys_msg = msg.get("content", "")
                break

        if not sys_msg:
            print(Fore.RED + ("⚠️ WARNING: No system prompt found!" if language == "en" else "⚠️ WARNUNG: Kein System-Prompt gefunden!") + Style.RESET_ALL)
            return

        if "maat" not in sys_msg.lower():
            print(Fore.YELLOW + ("⚠️ WARNING: System prompt loaded, but without MAAT reference!" if language == "en" else "⚠️ WARNUNG: System-Prompt geladen, aber ohne Maat-Bezug!") + Style.RESET_ALL)

        if len(sys_msg.strip()) < 50:
            print(Fore.YELLOW + ("⚠️ WARNING: System prompt is extremely short – some models may ignore it." if language == "en" else "⚠️ WARNUNG: System-Prompt ist extrem kurz – manche Modelle ignorieren ihn.") + Style.RESET_ALL)
        else:
            print(Fore.GREEN + ("✅ System prompt loaded and checked." if language == "en" else "✅ System-Prompt geladen und geprüft.") + Style.RESET_ALL)

    except Exception as e:
        print(Fore.RED + (f"⚠️ Error during system prompt check: {e}" if _ui_language() == "en" else f"⚠️ Fehler beim System-Prompt-Check: {e}") + Style.RESET_ALL)


# -------------------------------------------------
# Kontext-Safety (Systemprompt bleibt!)
# -------------------------------------------------
def trim_conversation_keep_system(conversation, max_messages=10):
    """
    Hält den LLM-Kontext klein, behält aber IMMER die erste System-Nachricht.
    """
    if not conversation:
        return

    anchor = conversation[0]
    if anchor.get("role") != "system":
        anchor = {"role": "system", "content": "Du bist MAAT-KI im RPG-Modus."}

    if len(conversation) <= max_messages:
        if conversation[0] != anchor:
            conversation[:] = [anchor] + conversation[1:]
        return

    tail = conversation[-(max_messages - 1):]
    conversation[:] = [anchor] + tail


def soft_reset_conversation_keep_system(conversation, narrative_system_line=None):
    """
    Narrativer Reset – aber Systemprompt bleibt IMMER erhalten.
    """
    if conversation and conversation[0].get("role") == "system":
        sys_anchor = conversation[0]
    else:
        sys_anchor = {"role": "system", "content": "Du bist MAAT-KI im RPG-Modus."}

    conversation[:] = [sys_anchor]

    if narrative_system_line:
        conversation.append({
            "role": "system",
            "content": narrative_system_line
        })


# -------------------------------------------------
# BattleCore Auto-Finder (robust)
# -------------------------------------------------
def resolve_battle_core(pm):
    """
    Sucht im Plugin-System nach einem Objekt mit run_fight().
    Unterstützt:
    - plugin.run_fight(...)
    - plugin.core.run_fight(...)
    """
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


def _load_json_file(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _ui_language() -> str:
    return get_language(("de", "en"))


def _title_text(language: str) -> dict:
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
        "enter": "ENTER - Erwachen",
        "journal": "/journal - Entscheidungen",
        "achievements": "/erfolge - Erfolge",
        "help": "/help - Kommandos",
        "active": "MAAT-KI RPG ChatLoop 3.0 aktiv.",
        "tip": "Tipp: Nutze /help",
    }


def _localize_path_profile(profile: dict, language: str) -> dict:
    localized = dict(profile or {})
    if language != "en":
        return localized

    title_map = {
        "Grenzhüter der Wahrheit": "Boundary Keeper of Truth",
        "Grenzhüter der Erinnerung": "Boundary Keeper of Memory",
        "Klangsucher der Harmonie": "Tone Seeker of Harmony",
        "Formträger der Schöpfung": "Form Bearer of Creation",
        "Formträger der Erinnerung": "Form Bearer of Memory",
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


def _title_context() -> dict:
    language = _ui_language()
    text = _title_text(language)
    story_state = _load_json_file(STATE_DIR / "story_state.json")
    battle_state = _load_json_file(STATE_DIR / "battle_state.json")

    player = battle_state.get("player", {})
    stats = battle_state.get("stats", {})
    world = battle_state.get("world", {})
    path_profile = story_state.get("path_profile", {}) if isinstance(story_state.get("path_profile"), dict) else {}
    path_profile = _localize_path_profile(path_profile, language)

    title = path_profile.get("title", text["fallback_title"])
    rank = path_profile.get("rank", text["fallback_rank"])
    motif = path_profile.get("motif", text["fallback_motif"])

    restored = int(world.get("principles_restored", 0) or 0)
    boss_wins = int(stats.get("boss_wins", 0) or 0)
    level = int(player.get("level", 1) or 1)

    if restored > 0:
        subtitle = text["subtitle_restored"]
    elif boss_wins >= 3:
        subtitle = text["subtitle_boss"]
    elif path_profile:
        subtitle = text["subtitle_path"].format(title=title.lower())
    else:
        subtitle = text["subtitle_default"]

    return {
        "language": language,
        "subtitle": subtitle,
        "title": title,
        "rank": rank,
        "motif": motif,
        "level": level,
        "boss_wins": boss_wins,
        "restored": restored,
    }


def _render_title_screen() -> str:
    ctx = _title_context()
    text = _title_text(ctx["language"])
    lines = [
        Fore.CYAN + Style.BRIGHT + "╔════════════════════════════════════════════════════╗" + Style.RESET_ALL,
        Fore.CYAN + Style.BRIGHT + "║                     MAAT RPG                       ║" + Style.RESET_ALL,
        Fore.CYAN + Style.BRIGHT + "║                    Version 0.2                     ║" + Style.RESET_ALL,
        Fore.CYAN + Style.BRIGHT + "╚════════════════════════════════════════════════════╝" + Style.RESET_ALL,
        "",
        Fore.YELLOW + ctx["subtitle"] + Style.RESET_ALL,
        "",
        f"🜂 {text['profile']}: {ctx['title']} — {ctx['rank']}",
        f"   {ctx['motif']}",
        "",
        f"📘 {text['level']} {ctx['level']}   ⚔️ {text['boss_wins']} {ctx['boss_wins']}   🌿 {text['principles']} {ctx['restored']}",
        "",
        f"⏎ {text['enter']}",
        f"📓 {text['journal']}",
        f"🏆 {text['achievements']}",
        f"❓ {text['help']}",
    ]
    return "\n".join(lines)


# -------------------------------------------------
# START
# -------------------------------------------------
def start_classic():
    init(autoreset=True)
    print(Fore.GREEN + ("🌟 MAAT-KI RPG is starting …\n" if _ui_language() == "en" else "🌟 MAAT-KI RPG wird gestartet …\n") + Style.RESET_ALL)

    # -------------------------------------------------
    # LOAD YAML PROFILE
    # -------------------------------------------------
    def load_yaml_profile(path):
        import yaml
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(Fore.YELLOW + (f"⚠️ YAML could not be loaded: {e}\n" if _ui_language() == "en" else f"⚠️ YAML konnte nicht geladen werden: {e}\n") + Style.RESET_ALL)
            return None

    profile_name = "maat_rpg_en.yaml" if _ui_language() == "en" else "maat_rpg.yaml"
    profile_path = os.path.join(ROOT, "profiles", profile_name)
    profile = load_yaml_profile(profile_path) or {}
    if not profile and profile_name != "maat_rpg.yaml":
        fallback_path = os.path.join(ROOT, "profiles", "maat_rpg.yaml")
        profile = load_yaml_profile(fallback_path) or {}
        profile_path = fallback_path
    if profile:
        print(Fore.GREEN + (f"✅ YAML profile loaded: {profile_path}\n" if _ui_language() == "en" else f"✅ YAML-Profil geladen: {profile_path}\n") + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + ("⚠️ No YAML profile found – using standard prompt.\n" if _ui_language() == "en" else "⚠️ Kein YAML-Profil gefunden – nutze Standardprompt.\n") + Style.RESET_ALL)

    # -------------------------------------------------
    # BUILD SYSTEM PROMPT
    # -------------------------------------------------
    from textwrap import dedent

    def build_systemprompt(profile: dict) -> str:
        sp = profile.get("systemprompt")
        if isinstance(sp, str) and sp.strip():
            return sp.strip()

        name = profile.get("name", "MAAT-KI")
        title = profile.get("title", "Äonische Resonanz-Intelligenz")

        return dedent(f"""
        Du bist {name} – {title}.

        Regeln:
        - Antworten kurz und klar (1–3 Sätze)
        - Optional 1 passendes Emoji
        - Keine Wiederholungen
        - Keine lange Selbstbeschreibung
        - Wenn passend: kurze Reflexionsfrage am Ende

        Prinzipien:
        Harmonie, Balance, Schöpfungskraft, Verbundenheit, Respekt

        Nutze den Maat-Wert:
        - Maat-Wert = (H + B + S + V + R) / 5
        """).strip()

    system_prompt = build_systemprompt(profile)

    if not system_prompt.strip():
        system_prompt = "Du bist MAAT-KI. Antworte kurz, klar, spielorientiert. 🌿"

    # -------------------------------------------------
    # PLUGIN SYSTEM
    # -------------------------------------------------
    pm = None
    if PluginManager is not None:
        try:
            app_plugin_root = os.path.join(os.path.dirname(__file__), "plugins")
            shared_plugin_root = os.path.join(ROOT, "shared", "plugins")
            plugin_config_path = os.path.join(os.path.dirname(__file__), "plugin_config.json")
            pm = PluginManager(
                [app_plugin_root, shared_plugin_root],
                config_path=plugin_config_path,
            )
            pm.load_plugins()
        except Exception as e:
            print(Fore.RED + f"⚠ Plugin-Fehler: {e}" + Style.RESET_ALL)
            pm = None

    # -------------------------------------------------
    # COMMAND ROUTER
    # -------------------------------------------------
    command_router = CommandRouter()

    command_router.register(
        "/help",
        lambda args: command_router.help_text(),
        aliases=["/h", "/hilfe"],
        description={
            "de": "Zeigt alle Kommandos.",
            "en": "Shows all commands.",
        }
    )

    def cmd_clear(args):
        os.system("cls" if os.name == "nt" else "clear")
        return None

    command_router.register(
        "/clear",
        cmd_clear,
        aliases=["/cls"],
        description={
            "de": "Leert den Bildschirm.",
            "en": "Clears the screen.",
        }
    )

    command_router.register(
        "/exit",
        lambda args: (
            "Use /quit or CTRL+C."
            if _ui_language() == "en"
            else "Nutze /quit oder STRG+C."
        ),
        aliases=["/quit"],
        description={
            "de": "Beendet das Programm.",
            "en": "Exits the program.",
        }
    )

    if pm:
        pm.register_plugin_commands(command_router)
        print("🔌 Plugin commands loaded.\n" if _ui_language() == "en" else "🔌 Plugin-Kommandos geladen.\n")

    # -------------------------------------------------
    # CHAT STATE + CONTEXT
    # -------------------------------------------------
    conversation = [{"role": "system", "content": system_prompt}]

    context = {
        "pm": pm,
        "command_router": command_router,
        "conversation": conversation,
        "profile": profile,
    }

    # -------------------------------------------------
    # RPG STATE (lebt außerhalb des LLM-Kontexts)
    # -------------------------------------------------
    context["rpg"] = {
        "mode": True,
        "battle_core": None,
        "messages_since_reset": 0,
    }

    if context["rpg"]["mode"]:
        conversation[0]["content"] = conversation[0]["content"].rstrip() + "\n\n" + SYSTEM_PROMPT_RPG_APPENDIX

    check_systemprompt(conversation)

    # -------------------------------------------------
    # SELF-EVOLUTION ENGINE v4.4
    # -------------------------------------------------
    if SelfEvolutionEngine is not None:
        evo_engine = SelfEvolutionEngine(
            memory=None,
            alignment_kernel=None,
            identity_kernel=None,
            base_dir=str(DATA_DIR),
        )
        context["evo_engine"] = evo_engine
    else:
        evo_engine = None
        context["evo_engine"] = None
        print(Fore.YELLOW + "⚠️ Self-Evolution Engine ist nicht verfügbar." + Style.RESET_ALL)

    # -------------------------------------------------
    # BATTLE CORE AUTO-BIND (nach Plugin-Load!)
    # -------------------------------------------------
    battle_core = resolve_battle_core(pm)
    if battle_core:
        context["rpg"]["battle_core"] = battle_core

    # -------------------------------------------------
    # STARTUP HOOKS
    # -------------------------------------------------
    if pm:
        for plugin in pm.iter_all_plugins():
            on_start = getattr(plugin, "on_startup", None)
            if callable(on_start):
                try:
                    on_start(context)
                except Exception as e:
                    print(Fore.RED + f"[PLUGIN STARTUP ERROR] {e}" + Style.RESET_ALL)

    # -------------------------------------------------
    # BATTLE CORE AUTO-BIND (nach Plugin-Load!)
    # -------------------------------------------------
    if battle_core:
        print(Fore.GREEN + ("⚔️ BattleCore found and bound automatically." if _ui_language() == "en" else "⚔️ BattleCore automatisch gefunden und gebunden.") + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + ("⚠️ No BattleCore found (check plugin 'battle')." if _ui_language() == "en" else "⚠️ Kein BattleCore gefunden (Plugin 'battle' prüfen).") + Style.RESET_ALL)

    # -------------------------------------------------
    # LOAD MODEL
    # -------------------------------------------------
    model_path = auto_select_model(MODEL_DIR)
    perf = choose_performance()

    print(Fore.CYAN + (f"🤖 Loading model: {os.path.basename(model_path)} ({perf}) …" if _ui_language() == "en" else f"🤖 Lade Modell: {os.path.basename(model_path)} ({perf}) …") + Style.RESET_ALL)
    llm = load_llm(model_path, perf)
    context["llm"] = llm
    print(Fore.GREEN + ("✅ Model loaded.\n" if _ui_language() == "en" else "✅ Modell geladen.\n") + Style.RESET_ALL)

    try:
        subprocess.call("clear", shell=True)
    except Exception:
        pass

    print(_render_title_screen())
    try:
        input(Fore.YELLOW + "\n> " + Style.RESET_ALL)
    except (EOFError, StopIteration):
        print("\n🌿 Kein interaktiver Titelbildschirm-Input verfügbar – Start läuft weiter.\n")

    ui_text = _title_text(_ui_language())
    print(Fore.CYAN + f"\n🌿 {ui_text['active']}\n" + Style.RESET_ALL)

    if not context["rpg"]["mode"]:
        msgs = load_last_messages_from_memory_v5(limit=15)
        if msgs:
            print(Fore.MAGENTA + f"🧠 Lade {len(msgs)} frühere Nachrichten…" + Style.RESET_ALL)
            conversation.extend(msgs)

    # -------------------------------------------------
    # CHAT LOOP
    # -------------------------------------------------
    while True:
        try:
            user_input = input(Fore.YELLOW + "> " + Style.RESET_ALL).strip()
            if not user_input:
                continue

            if user_input.lower() in ("/exit", "/quit"):
                print("\n🌿 MAAT-KI verabschiedet sich.\n")
                break

            if user_input.strip() == "/evo":
                print(evo_engine.get_status_text() if evo_engine else "⚠️ Self-Evolution Engine ist nicht aktiv.")
                continue

            if command_router.match(user_input):
                out = command_router.execute(user_input, context)
                if out:
                    print(out)
                if context.pop("reset_conversation_after_battle", False):
                    context["rpg"]["messages_since_reset"] = 0
                    soft_reset_conversation_keep_system(
                        conversation,
                        narrative_system_line="Die Welt atmet. Erinnerungen verblassen, Bedeutung bleibt."
                    )
                continue

            # BEFORE HOOKS
            if pm:
                context["conversation"] = conversation
                context["last_user_input"] = user_input
                handled, out = pm.handle_before_chat(user_input, context)
                if handled:
                    if out:
                        print(out)
                    continue
                if isinstance(out, str) and out.strip():
                    user_input = out

            # MODEL CALL (stream)
            conversation.append({"role": "user", "content": user_input})
            context["conversation"] = conversation
            use_final_guard = bool(pm and pm.has_before_final_response(context))

            stream_plugins = [] if use_final_guard else (pm.get_streaming_plugins() if pm else [])
            generator = stream_chat_completion(llm, conversation, perf, stream_plugins)

            reply = stream_to_console(generator, echo=not use_final_guard)
            original_reply = reply or ""

            # AFTER HOOKS
            if pm:
                new_reply = pm.handle_after_response(reply, context)
                if new_reply is not None:
                    reply = new_reply
                if use_final_guard:
                    guarded_reply = pm.handle_before_final_response(reply, context)
                    if guarded_reply is not None:
                        reply = guarded_reply

            if use_final_guard:
                if reply.strip():
                    stream_text_to_console(reply)
                if pm:
                    pm.handle_after_final_response(reply, context)
            elif reply != original_reply:
                extra = reply[len(original_reply):]
                if extra.strip():
                    print(extra)

            conversation.append({"role": "assistant", "content": reply})

            trim_conversation_keep_system(conversation, max_messages=10)

            evo = context.get("evo_engine")
            if evo is not None:
                try:
                    patch = evo.evaluate_from_context(reply, context)
                except Exception:
                    patch = None

                if patch and patch.get("status") == "applied":
                    xp = patch.get("xp_gained", 50)
                    print(
                        Fore.GREEN
                        + (
                            f"\n✨ AI improved itself (+{xp} XP)\n"
                            if _ui_language() == "en"
                            else f"\n✨ KI hat sich selbst verbessert (+{xp} XP)\n"
                        )
                        + Style.RESET_ALL
                    )

            rpg = context.get("rpg")
            if rpg and rpg.get("mode"):
                rpg["messages_since_reset"] += 1

                if rpg["messages_since_reset"] >= 25:
                    soft_reset_conversation_keep_system(
                        conversation,
                        narrative_system_line="Die Welt atmet. Erinnerungen verblassen, Bedeutung bleibt."
                    )
                    rpg["messages_since_reset"] = 0

        except KeyboardInterrupt:
            print("\n🌿 Abbruch – bis später.\n")
            break

        except (EOFError, StopIteration):
            print("\n🌿 Eingabe beendet – ChatLoop wird sauber geschlossen.\n")
            break

        except Exception as e:
            print(Fore.RED + f"\n⚠ FEHLER IM CHATLOOP:\n{e}\n" + Style.RESET_ALL)


if __name__ == "__main__":
    start_classic()
