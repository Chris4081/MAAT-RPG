# -*- coding: utf-8 -*-
"""
MAAT-KI Auto-Think Plugin v1.3
Aktiviert einen globalen Denkmodus:
    /think        → Hilfe & Status
    /think on     → ThinkLoop wird bei jeder Anfrage ausgeführt
    /think off    → normaler Modus
    /think status → Status anzeigen

Debug-Modus:
    /think debug on   → zeigt Analyse + finalen Prompt im Terminal
    /think debug once → nur für die nächste Anfrage
    /think debug off  → Debug aus
"""

import time
import sys


class Plugin:
    type = "chat"

    commands = {
        "/think": "Auto-Think Hilfe & Status",
        "/think on": "Auto-Think einschalten (jede Eingabe wird tiefer analysiert)",
        "/think off": "Auto-Think ausschalten",
        "/think status": "Status von Auto-Think anzeigen",
        "/think debug on": "Debug-Modus: zeige Analyse & finalen Prompt bei jeder Eingabe",
        "/think debug off": "Debug-Modus deaktivieren",
        "/think debug once": "Debug-Modus einmalig für die nächste Eingabe",
    }

    def __init__(self):
        # Standard: Auto-Think ist AUS
        self.auto = False
        # Trigger-Liste bleibt nur informativ, wird aber NICHT mehr benutzt,
        # damit nichts "von alleine" anspringt.
        self.triggers = [
            "denke", "denk", "überlege", "prüfe", "analyse",
            "reflektiere", "programmier", "programmiere",
            "code", "skript", "script", "fix", "debug",
            "warum", "wieso", "erkläre"
        ]
        self.thinking_symbol = "🌀 MAAT denkt…"
        self.debug = False
        self.debug_once = False

    # ------------------------------------------------------------
    # COMMAND: /think ...
    # ------------------------------------------------------------
    def command(self, cmd: str, context=None):
        c = cmd.strip().lower()

        if c == "/think":
            status = "ON" if self.auto else "OFF"
            dbg = "ON" if self.debug else "OFF"
            return (
                "🧠 MAAT Auto-Think\n"
                f"Status: {status}\n"
                f"Debug:  {dbg}\n"
                "Befehle:\n"
                "  • /think on          – Auto-Think aktivieren\n"
                "  • /think off         – Auto-Think deaktivieren\n"
                "  • /think status      – Status anzeigen\n"
                "  • /think debug on    – Debug-Modus aktivieren\n"
                "  • /think debug off   – Debug-Modus deaktivieren\n"
                "  • /think debug once  – Debug nur für die nächste Eingabe\n"
            )

        if c == "/think on":
            self.auto = True
            return "🧠 Auto-Think ist jetzt AKTIV. Jede Eingabe wird tiefer analysiert."

        if c == "/think off":
            self.auto = False
            return "😌 Auto-Think wurde deaktiviert. Normale Antworten aktiv."

        if c == "/think status":
            return (
                f"📊 Auto-Think Status: {'ON' if self.auto else 'OFF'} | "
                f"Debug: {'ON' if self.debug else 'OFF'}"
            )

        if c == "/think debug on":
            self.debug = True
            self.debug_once = False
            return "🧪 THINK-DEBUG ist jetzt AKTIV. Analyse & finaler Prompt werden im Terminal angezeigt."

        if c == "/think debug off":
            self.debug = False
            self.debug_once = False
            return "🧪 THINK-DEBUG wurde deaktiviert."

        if c == "/think debug once":
            self.debug_once = True
            return "🧪 THINK-DEBUG wird EINMALIG für die nächste Eingabe aktiviert."

        return None

    # ------------------------------------------------------------
    # BEFORE-HOOK – entscheidet, ob ThinkLoop laufen muss
    # ------------------------------------------------------------
    def before_chat(self, user_input: str, context=None):
        """
        Neue Logik:
        - Wenn Auto-Think OFF → nichts tun, immer direkt durchreichen.
        - Wenn Auto-Think ON → jede Eingabe bekommt ThinkLoop.
        """
        ctx = context or {}
        llm = ctx.get("llm")
        conversation = ctx.get("conversation")

        # Wenn kein LLM oder keine Conversation → nichts tun
        if llm is None or conversation is None:
            return (False, user_input)

        # 🚫 Auto-Think ist aus → keinerlei Eingriff
        if not self.auto:
            return (False, user_input)

        # ----------------------------------------
        # THINKLOOP AUSFÜHREN (Auto-Think aktiv)
        # ----------------------------------------
        self._thinking_indicator()

        thoughts = self._run_thinkloop(
            llm,
            conversation + [{"role": "user", "content": user_input}]
        )

        new_input = (
            "Hier ist eine technische Hilfs-Zusammenfassung, "
            "die du als Orientierung nutzen kannst (nicht wörtlich wiederholen):\n"
            f"{thoughts}\n\n"
            "Formuliere jetzt eine eigenständige, klare und hilfreiche Antwort "
            "auf die folgende Eingabe. Verwende deine eigenen Worte und "
            "wiederhole die obige Zusammenfassung nicht 1:1:\n\n"
            f"EINGABE:\n{user_input}"
        )

        if self.debug or self.debug_once:
            print("\n🧪 [THINK-DEBUG] Interne Analyse:\n")
            print(thoughts)
            print("\n🧪 [THINK-DEBUG] Finaler Prompt an das Modell:\n")
            print(new_input)
            print("\n🧪 [THINK-DEBUG ENDE]\n")
            self.debug_once = False

        return (False, new_input)

    # ------------------------------------------------------------
    # VISUELLE ANZEIGE
    # ------------------------------------------------------------
    def _thinking_indicator(self):
        sys.stdout.write(self.thinking_symbol + " (Auto-Think aktiv)\n")
        sys.stdout.flush()
        time.sleep(0.05)

    # ------------------------------------------------------------
    # LLM-NEUTRALE THINKLOOP ENGINE (mini)
    # ------------------------------------------------------------
    def _run_thinkloop(self, llm, conversation):
        msgs = conversation + [{
            "role": "system",
            "content": (
                "Du bist im erweiterten Denkmodus. "
                "Analysiere die Unterhaltung und die letzte Nutzereingabe "
                "schrittweise, logisch und strukturiert. "
                "Identifiziere wichtige Annahmen, mögliche Fehlerquellen "
                "und sinnvolle nächste Schritte. "
                "Fasse am Ende deine wichtigsten Einsichten komprimiert zusammen."
            )
        }]

        if hasattr(llm, "create_chat_completion"):
            resp = llm.create_chat_completion(
                messages=msgs,
                max_tokens=256,
                temperature=0.4
            )
            return resp["choices"][0]["message"]["content"].strip()

        if hasattr(llm, "chat") and hasattr(llm.chat, "completions"):
            resp = llm.chat.completions.create(
                model=llm.model,
                messages=msgs,
                max_tokens=256,
                temperature=0.4
            )
            return resp.choices[0].message.content.strip()

        if hasattr(llm, "generate"):
            return llm.generate(
                prompt=str(msgs),
                max_tokens=256,
                temperature=0.4
            ).strip()

        return "Analyse nicht möglich (unbekannte LLM-API)."