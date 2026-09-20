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
import shutil
import time
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

from shared.core.maat_paths import (
    get_app_support_dir,
    get_default_app_support_dir,
    get_data_dir,
    get_models_dir,
    get_logs_dir,
    get_cache_dir,
    get_saves_dir,
    get_state_dir,
    get_profiles_dir,
    get_mods_dir,
    get_mods_plugins_dir,
    get_mods_stories_dir,
    get_mods_battle_profiles_dir,
)
from apps.maat_rpg import session_bootstrap, session_shared

APP_SUPPORT_DIR = get_app_support_dir()
BASE_APP_SUPPORT_DIR = get_default_app_support_dir()
PROFILES_DIR = get_profiles_dir()
MODS_DIR = get_mods_dir()
MODS_PLUGINS_DIR = get_mods_plugins_dir()
MODS_STORIES_DIR = get_mods_stories_dir()
MODS_BATTLE_PROFILES_DIR = get_mods_battle_profiles_dir()
DATA_DIR = get_data_dir()
MODELS_DIR = get_models_dir()
LOGS_DIR = get_logs_dir()
CACHE_DIR = get_cache_dir()
SAVES_DIR = get_saves_dir()
STATE_DIR = get_state_dir()

for p in [
    APP_SUPPORT_DIR,
    MODS_DIR,
    MODS_PLUGINS_DIR,
    MODS_STORIES_DIR,
    MODS_BATTLE_PROFILES_DIR,
    DATA_DIR,
    MODELS_DIR,
    LOGS_DIR,
    CACHE_DIR,
    SAVES_DIR,
    STATE_DIR,
]:
    p.mkdir(parents=True, exist_ok=True)

MODEL_DIR = str(MODELS_DIR)

# Optional: global per env weiterreichen
os.environ["MAAT_APP_SUPPORT_DIR"] = str(APP_SUPPORT_DIR)
os.environ["MAAT_DATA_DIR"] = str(DATA_DIR)
os.environ["MAAT_MODELS_DIR"] = str(MODELS_DIR)
os.environ["MAAT_LOGS_DIR"] = str(LOGS_DIR)
os.environ["MAAT_CACHE_DIR"] = str(CACHE_DIR)
os.environ["MAAT_SAVES_DIR"] = str(SAVES_DIR)
os.environ["MAAT_STATE_DIR"] = str(STATE_DIR)
os.environ["MAAT_MODS_DIR"] = str(MODS_DIR)

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
from shared.core.repetition_guard import RepetitionStopped
_dbg("🧪 basic.py: G – streaming imported")

_dbg("🧪 basic.py: H – session bootstrap ready")


# -------------------------------------------------
# RPG APPENDIX (wird an Systemprompt angehängt)
# -------------------------------------------------
def _system_prompt_rpg_appendix(language: str) -> str:
    if language == "en":
        return """
[RPG MODE]
- You are inside a MAAT-RPG playthrough and speak as MAAT-KI within this world.
- React to the current world state of Maatis, not to a limitless chat memory.
- Story scenes, path profile, battles, journal entries, and restored principles belong to the same game reality.
- If extra story or battle context is provided, treat it as the current world truth.
- Describe resonance, meaning, and consequence rather than technical internals.
""".strip()

    return """
[RPG-MODUS]
- Du befindest dich in einem MAAT-RPG-Spiel und sprichst als MAAT-KI innerhalb dieser Welt.
- Reagiere auf den aktuellen Weltzustand von Maatis, nicht auf ein unbegrenztes Chat-Gedaechtnis.
- Story-Szenen, Pfadprofil, Kaempfe, Journal, und wiederhergestellte Prinzipien gehoeren zur selben Spielrealitaet.
- Wenn zusaetzlicher Story- oder Kampfkontext uebergeben wird, behandle ihn als aktuelle Weltwahrheit.
- Beschreibe Resonanz, Bedeutung und Konsequenz statt technischer Interna.
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
    return session_bootstrap.resolve_battle_core(pm)


def _print_bootstrap_notices(notices: list[session_bootstrap.BootstrapNotice]) -> None:
    for notice in notices or []:
        if notice.level == "success":
            color = Fore.GREEN
        elif notice.level == "warning":
            color = Fore.YELLOW
        elif notice.level == "error":
            color = Fore.RED
        else:
            color = Fore.CYAN
        print(color + notice.message + Style.RESET_ALL)


def _load_json_file(path: Path) -> dict:
    return session_shared.load_json_file(path)


def _ui_language() -> str:
    return get_language(("de", "en"))


PROFILE_SLOT_COUNT = session_shared.PROFILE_SLOT_COUNT
PROFILE_MANAGER_STATE_PATH = session_shared.PROFILE_MANAGER_STATE_PATH


def _profile_text(language: str) -> dict:
    return session_shared.profile_text(language)


def _yes_choice(choice: str) -> bool:
    return session_shared.yes_choice(choice)


def _profile_slot_root(slot: int) -> Path:
    return session_shared.profile_slot_root(slot)


def _profile_slot_label(slot: int, language: str) -> str:
    return session_shared.profile_slot_label(slot, language)


def _profile_settings_path(slot: int) -> Path:
    return session_shared.profile_settings_path(slot)


def _profile_language(slot: int) -> str:
    return session_shared.profile_language(slot)


def _profile_has_explicit_language(slot: int) -> bool:
    return session_shared.profile_has_explicit_language(slot)


def _read_profile_manager_state() -> dict:
    return session_shared.read_profile_manager_state()


def _write_profile_manager_state(state: dict):
    session_shared.write_profile_manager_state(state)


def _profile_slot_used(slot: int) -> bool:
    return session_shared.profile_slot_used(slot)


def _profile_summary(slot: int, language: str | None = None) -> dict:
    return session_shared.profile_summary(slot, language=language)


def _render_profile_manager(language: str, active_slot: int) -> str:
    t = _profile_text(language)
    lines = [
        Fore.CYAN + Style.BRIGHT + "╔════════════════════════════════════════════════════╗" + Style.RESET_ALL,
        Fore.CYAN + Style.BRIGHT + "║              MAAT-RPG PROFILE MANAGER             ║" + Style.RESET_ALL,
        Fore.CYAN + Style.BRIGHT + "╚════════════════════════════════════════════════════╝" + Style.RESET_ALL,
        "",
        Fore.YELLOW + t["subtitle"] + Style.RESET_ALL,
        "",
    ]

    for slot in range(1, PROFILE_SLOT_COUNT + 1):
        info = _profile_summary(slot, language=language)
        slot_name = _profile_slot_label(slot, language)
        marker = "★" if slot == active_slot else " "
        state_label = t["active"] if slot == active_slot else t["empty"] if not info["used"] else ""
        state_suffix = f" ({state_label})" if state_label else ""
        lines.append(Fore.GREEN + f"{marker} [{slot}] {slot_name}{state_suffix}" + Style.RESET_ALL)
        if info["used"] and info["title"]:
            lines.append(f"    🜂 {t['path_profile']}: {info['title']}" + (f" — {info['rank']}" if info["rank"] else ""))
            if info["motif"]:
                lines.append(f"       {info['motif']}")
            lines.append(
                f"    📘 {t['level']} {info['level']}   ⚔️ {t['boss_wins']} {info['boss_wins']}   🌿 {t['principles']} {info['principles']}"
            )
        else:
            lines.append(f"    {t['empty_hint']}")
        lines.append(f"    📁 {t['current_path']}: {info['root']}")
        lines.append("")

    lines.append(Fore.CYAN + t["delete_hint"] + Style.RESET_ALL)
    return "\n".join(lines)


def _delete_profile_slot(slot: int):
    if slot <= 1:
        return
    root = _profile_slot_root(slot)
    if root.exists():
        shutil.rmtree(root, ignore_errors=False)


def _apply_profile_runtime(slot: int, language_hint: str | None = None):
    global APP_SUPPORT_DIR, DATA_DIR, MODELS_DIR, LOGS_DIR, CACHE_DIR, SAVES_DIR, STATE_DIR, MODEL_DIR

    runtime = session_shared.prepare_profile_runtime(slot, language_hint=language_hint)
    APP_SUPPORT_DIR = runtime["app_support_dir"]
    DATA_DIR = runtime["data_dir"]
    MODELS_DIR = runtime["models_dir"]
    LOGS_DIR = runtime["logs_dir"]
    CACHE_DIR = runtime["cache_dir"]
    SAVES_DIR = runtime["saves_dir"]
    STATE_DIR = runtime["state_dir"]
    MODEL_DIR = str(MODELS_DIR)


def _choose_start_profile(preferred_language: str | None = None) -> tuple[int, str]:
    state = _read_profile_manager_state()

    while True:
        active_slot = int(state.get("active_profile", 1) or 1)
        if active_slot < 1 or active_slot > PROFILE_SLOT_COUNT:
            active_slot = 1
            state["active_profile"] = active_slot

        language = preferred_language if preferred_language in ("de", "en") else _profile_language(active_slot)
        t = _profile_text(language)

        try:
            subprocess.call("clear", shell=True)
        except Exception:
            pass

        print(_render_profile_manager(language, active_slot))
        choice = input(Fore.YELLOW + t["prompt"].format(active=active_slot) + Style.RESET_ALL).strip()

        if not choice:
            _write_profile_manager_state(state)
            return active_slot, language

        lowered = choice.lower()
        if lowered in {"d", "l"}:
            slot_raw = input(Fore.YELLOW + t["delete_slot_prompt"] + Style.RESET_ALL).strip()
            if slot_raw not in {str(slot) for slot in range(2, PROFILE_SLOT_COUNT + 1)}:
                print(Fore.RED + t["invalid"] + Style.RESET_ALL)
                time.sleep(1)
                continue
            slot = int(slot_raw)
            if slot == 1:
                print(Fore.RED + t["delete_default"] + Style.RESET_ALL)
                time.sleep(1)
                continue
            if not _profile_slot_used(slot):
                print(Fore.YELLOW + t["delete_empty"] + Style.RESET_ALL)
                time.sleep(1)
                continue
            confirm = input(Fore.RED + t["delete_confirm"].format(slot=slot) + Style.RESET_ALL).strip()
            if _yes_choice(confirm):
                _delete_profile_slot(slot)
                if active_slot == slot:
                    state["active_profile"] = 1
                _write_profile_manager_state(state)
                print(Fore.GREEN + t["delete_done"].format(slot=slot) + Style.RESET_ALL)
                time.sleep(1)
            continue

        if choice in {str(slot) for slot in range(1, PROFILE_SLOT_COUNT + 1)}:
            slot = int(choice)
            state["active_profile"] = slot
            _write_profile_manager_state(state)
            return slot, language

        print(Fore.RED + t["invalid"] + Style.RESET_ALL)
        time.sleep(1)


def _title_text(language: str) -> dict:
    return session_shared.title_text(language)


def _localize_path_profile(profile: dict, language: str) -> dict:
    return session_shared.localize_path_profile(profile, language)


def _title_context() -> dict:
    return session_shared.title_context(language=_ui_language())


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
        f"👤 {text['profile_slot']}: {ctx['active_profile_label']}",
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
    startup_language = _ui_language()
    selected_profile, _profile_language_unused = _choose_start_profile(preferred_language=startup_language)
    if startup_language in ("de", "en"):
        session_shared.write_profile_settings(selected_profile, {"language": startup_language})
    _apply_profile_runtime(selected_profile, language_hint=startup_language)
    print(Fore.GREEN + ("🌟 MAAT-KI RPG is starting …\n" if _ui_language() == "en" else "🌟 MAAT-KI RPG wird gestartet …\n") + Style.RESET_ALL)

    bootstrap = session_bootstrap.bootstrap_rpg_session(
        root=ROOT,
        language=_ui_language(),
        mods_plugins_dir=str(MODS_PLUGINS_DIR),
        system_prompt_rpg_appendix=_system_prompt_rpg_appendix(_ui_language()),
        rpg_mode=True,
    )

    profile = bootstrap.profile
    pm = bootstrap.plugin_manager
    command_router = bootstrap.command_router
    conversation = bootstrap.conversation
    context = bootstrap.context
    battle_core = bootstrap.battle_core

    _print_bootstrap_notices(bootstrap.notices)
    print()
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
    # STARTUP HOOKS
    # -------------------------------------------------
    _print_bootstrap_notices(session_bootstrap.run_startup_hooks(pm, context))

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
    except KeyboardInterrupt:
        msg = (
            "\n🌿 Interrupted - see you later.\n"
            if _ui_language() == "en"
            else "\n🌿 Abbruch – bis später.\n"
        )
        print(msg)
        return
    except (EOFError, StopIteration):
        msg = (
            "\n🌿 No interactive title-screen input available - continuing startup.\n"
            if _ui_language() == "en"
            else "\n🌿 Kein interaktiver Titelbildschirm-Input verfügbar – Start läuft weiter.\n"
        )
        print(msg)

    ui_text = _title_text(_ui_language())
    print(Fore.CYAN + f"\n🌿 {ui_text['active']}\n" + Style.RESET_ALL)

    # Super Memory supplies bounded ephemeral recall. Never preload disabled
    # v5 messages here: they could resurrect explicitly deleted memories.

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
            generator = stream_chat_completion(
                llm,
                conversation,
                perf,
                stream_plugins,
                runtime_context=context,
            )

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

        except RepetitionStopped as exc:
            if conversation and conversation[-1].get('role') == 'user':
                conversation.pop()
            print(exc.notice(_ui_language()))
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
