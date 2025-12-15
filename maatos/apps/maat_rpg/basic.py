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

print("🧪 basic.py: A – std imports done")
import readline
import os
import sys
import sqlite3
import subprocess
from colorama import Fore, Style, init
print("🧪 basic.py: B – colorama done")

# -------------------------------------------------
# ROOT / MODEL_DIR
# -------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
print("🧪 basic.py: C – ROOT done")

MODEL_DIR = os.path.join(ROOT, "models")

from shared.core.self_evolution import SelfEvolutionEngine  # v4.4
print("🧪 basic.py: D – SelfEvolutionEngine imported")

# -------------------------------------------------
# SHARED IMPORTS
# -------------------------------------------------
from shared.profile_loader import ProfileLoader
print("🧪 basic.py: E – ProfileLoader imported")

from shared.core.llm_loader import (
    load_llm,
    choose_performance,
    auto_select_model,
)
print("🧪 basic.py: F – llm_loader imported")

from shared.core.streaming import stream_chat_completion, stream_to_console
print("🧪 basic.py: G – streaming imported")

from shared.core.command_router import CommandRouter
print("🧪 basic.py: H – CommandRouter imported")

# Plugin-System
try:
    from shared.plugins.plugin_loader import PluginManager
    print("➡️ PluginManager erfolgreich importiert.")
except Exception as e:
    print("❌ IMPORTFEHLER PluginManager:", e)
    PluginManager = None
print("🧪 basic.py: Plugin Manager")


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
        data_dir = os.path.join(ROOT, "data")
        db_path = os.path.join(data_dir, "memory_v5.db")
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
        sys_msg = None
        for msg in conversation:
            if msg.get("role") == "system":
                sys_msg = msg.get("content", "")
                break

        if not sys_msg:
            print(Fore.RED + "⚠️ WARNUNG: Kein System-Prompt gefunden!" + Style.RESET_ALL)
            return

        if "maat" not in sys_msg.lower():
            print(Fore.YELLOW + "⚠️ WARNUNG: System-Prompt geladen, aber ohne Maat-Bezug!" + Style.RESET_ALL)

        if len(sys_msg.strip()) < 50:
            print(Fore.YELLOW + "⚠️ WARNUNG: System-Prompt ist extrem kurz – manche Modelle ignorieren ihn." + Style.RESET_ALL)
        else:
            print(Fore.GREEN + "✅ System-Prompt geladen und geprüft." + Style.RESET_ALL)

    except Exception as e:
        print(Fore.RED + f"⚠️ Fehler beim System-Prompt-Check: {e}" + Style.RESET_ALL)


# -------------------------------------------------
# Kontext-Safety (Systemprompt bleibt!)
# -------------------------------------------------
def trim_conversation_keep_system(conversation, max_messages=10):
    """
    Hält den LLM-Kontext klein, behält aber IMMER die erste System-Nachricht.
    """
    if not conversation:
        return

    # Erste Nachricht als System-Anker
    anchor = conversation[0]
    if anchor.get("role") != "system":
        # notfalls: künstlicher Systemanker
        anchor = {"role": "system", "content": "Du bist MAAT-KI im RPG-Modus."}

    if len(conversation) <= max_messages:
        # ensure anchor stays first
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
            # Fall 1: Plugin selbst kann kämpfen
            if hasattr(plugin, "run_fight") and callable(getattr(plugin, "run_fight")):
                return plugin

            # Fall 2: Plugin besitzt ein 'core' Objekt
            core = getattr(plugin, "core", None)
            if core and hasattr(core, "run_fight") and callable(getattr(core, "run_fight")):
                return core
    except Exception:
        pass

    return None


# -------------------------------------------------
# START
# -------------------------------------------------
def start_classic():
    init(autoreset=True)
    print(Fore.GREEN + "🌟 MAAT-KI RPG wird gestartet …\n" + Style.RESET_ALL)

    # -------------------------------------------------
    # LOAD YAML PROFILE
    # -------------------------------------------------
    def load_yaml_profile(path):
        import yaml
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(Fore.YELLOW + f"⚠️ YAML konnte nicht geladen werden: {e}\n" + Style.RESET_ALL)
            return None

    profile_path = os.path.join(ROOT, "profiles", "maat_rpg.yaml")
    profile = load_yaml_profile(profile_path) or {}
    if profile:
        print(Fore.GREEN + f"✅ YAML-Profil geladen: {profile_path}\n" + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + "⚠️ Kein YAML-Profil gefunden – nutze Standardprompt.\n" + Style.RESET_ALL)

    # -------------------------------------------------
    # BUILD SYSTEM PROMPT
    # -------------------------------------------------
    from textwrap import dedent

    def build_systemprompt(profile: dict) -> str:
        # 1) Direkter systemprompt aus YAML
        sp = profile.get("systemprompt")
        if isinstance(sp, str) and sp.strip():
            return sp.strip()

        # 2) Fallback-Prompt
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
            pm = PluginManager([app_plugin_root, shared_plugin_root])
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
        description="Zeigt alle Kommandos."
    )

    def cmd_clear(args):
        os.system("cls" if os.name == "nt" else "clear")
        return None

    command_router.register(
        "/clear",
        cmd_clear,
        aliases=["/cls"],
        description="Cleart den Bildschirm."
    )

    command_router.register(
        "/exit",
        lambda args: "Nutze /quit oder STRG+C.",
        aliases=["/quit"],
        description="Beendet das Programm."
    )

    if pm:
        pm.register_plugin_commands(command_router)
        print("🔌 Plugin-Kommandos geladen.\n")

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

    # Systemprompt im RPG wirklich aktivieren (Appendix)
    if context["rpg"]["mode"]:
        conversation[0]["content"] = conversation[0]["content"].rstrip() + "\n\n" + SYSTEM_PROMPT_RPG_APPENDIX

    check_systemprompt(conversation)

    # -------------------------------------------------
    # SELF-EVOLUTION ENGINE v4.4
    # -------------------------------------------------
    evo_engine = SelfEvolutionEngine(
        memory=None,
        alignment_kernel=None,
        identity_kernel=None,
        base_dir=os.path.join(ROOT, "data"),
    )
    context["evo_engine"] = evo_engine

    # -------------------------------------------------
    # STARTUP HOOKS
    # -------------------------------------------------
    if pm:
        for plugin in pm.iter_all_plugins():
            on_start = getattr(plugin, "on_startup", None)
            if callable(on_start):
                try:
                    on_start()
                except Exception as e:
                    print(Fore.RED + f"[PLUGIN STARTUP ERROR] {e}" + Style.RESET_ALL)

    # -------------------------------------------------
    # BATTLE CORE AUTO-BIND (nach Plugin-Load!)
    # -------------------------------------------------
    battle_core = resolve_battle_core(pm)
    if battle_core:
        context["rpg"]["battle_core"] = battle_core
        print(Fore.GREEN + "⚔️ BattleCore automatisch gefunden und gebunden." + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + "⚠️ Kein BattleCore gefunden (Plugin 'battle' prüfen)." + Style.RESET_ALL)

    # -------------------------------------------------
    # LOAD MODEL
    # -------------------------------------------------
    model_path = auto_select_model(MODEL_DIR)
    perf = choose_performance()

    print(Fore.CYAN + f"🤖 Lade Modell: {os.path.basename(model_path)} ({perf}) …" + Style.RESET_ALL)
    llm = load_llm(model_path, perf)
    context["llm"] = llm
    print(Fore.GREEN + "✅ Modell geladen.\n" + Style.RESET_ALL)

    # Bildschirm leeren
    try:
        subprocess.call("clear", shell=True)
    except Exception:
        pass

    print(Fore.CYAN + "🌿 MAAT-KI RPG ChatLoop 3.0 aktiv." + Style.RESET_ALL)
    print("\n📘 Tipp: Nutze /help\n")

    # OPTIONAL: Memory-V5 nur im NON-RPG
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

            # Self-Evolution Status
            if user_input.strip() == "/evo":
                print(evo_engine.get_status_text() if evo_engine else "⚠️ Self-Evolution Engine ist nicht aktiv.")
                continue

            # -------------------------------------------------
            # RPG COMMANDS
            # -------------------------------------------------
            if context.get("rpg", {}).get("mode"):
                if user_input.strip() == "/fight":
                    bc = context["rpg"].get("battle_core")
                    if bc:
                        result = bc.run_fight("normal", context)
                        print(result)

                        # narrativer Anker (kurz)
                        conversation.append({
                            "role": "assistant",
                            "content": "Ein Kampf ist vorüber. Etwas hat sich verschoben."
                        })

                        # Reset: Kontext „atmet“ (Systemprompt bleibt!)
                        context["rpg"]["messages_since_reset"] = 0
                        soft_reset_conversation_keep_system(
                            conversation,
                            narrative_system_line="Die Welt atmet. Erinnerungen verblassen, Bedeutung bleibt."
                        )
                    else:
                        print("⚠️ Kein BattleCore aktiv.")
                    continue

            # Commands (/help etc.)
            if command_router.match(user_input):
                out = command_router.execute(user_input, context)
                if out:
                    print(out)
                continue

            # BEFORE HOOKS
            if pm:
                handled, out = pm.handle_before_chat(user_input, context)
                if handled:
                    if out:
                        print(out)
                    continue
                # out kann ein modifizierter user_input sein
                if isinstance(out, str) and out.strip():
                    user_input = out

            # MODEL CALL (stream)
            conversation.append({"role": "user", "content": user_input})

            stream_plugins = pm.get_streaming_plugins() if pm else []
            generator = stream_chat_completion(llm, conversation, perf, stream_plugins)

            reply = stream_to_console(generator)
            original_reply = reply or ""

            # AFTER HOOKS
            if pm:
                new_reply = pm.handle_after_response(reply, context)
                if new_reply is not None:
                    reply = new_reply

            # Extra Ausgabe (falls Plugin ergänzt)
            if reply != original_reply:
                extra = reply[len(original_reply):]
                if extra.strip():
                    print(extra)

            # SAVE
            conversation.append({"role": "assistant", "content": reply})

            # CONTEXT-SAFETY (immer)
            trim_conversation_keep_system(conversation, max_messages=10)

            # SELF-EVOLUTION (optional)
            evo = context.get("evo_engine")
            if evo is not None:
                try:
                    patch = evo.evaluate_from_context(reply, context)
                except Exception:
                    patch = None

                if patch and patch.get("status") == "applied":
                    xp = patch.get("xp_gained", 50)
                    print(Fore.GREEN + f"\n✨ KI hat sich selbst verbessert (+{xp} XP)\n" + Style.RESET_ALL)

            # RPG TICK + SOFT RESET
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

        except Exception as e:
            print(Fore.RED + f"\n⚠ FEHLER IM CHATLOOP:\n{e}\n" + Style.RESET_ALL)


if __name__ == "__main__":
    start_classic()