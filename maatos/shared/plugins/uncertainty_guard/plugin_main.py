# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
from shared.core.plp_guard import calculate_plp, evaluate_hallucination_risk, should_buffer_final_response
from shared.core.maat_paths import state_file
from shared.core.rpg_i18n import get_language


SETTINGS_FILE = state_file("settings_state.json")


class Plugin:
    """
    PLP-based anti-hallucination guard.
    Runs before the final response is shown and can soften or block risky output.
    """

    type = "chat"
    commands = {
        "/uncertainty": {
            "de": "Zeigt den letzten PLP-/Unsicherheitswert.",
            "en": "Shows the latest PLP / uncertainty value.",
        },
        "/plp": {
            "de": "Zeigt die letzte PLP-Analyse im Detail.",
            "en": "Shows the latest PLP analysis in detail.",
        },
        "/plp status": {
            "de": "Zeigt den letzten PLP-Status im MAAT-Stil.",
            "en": "Shows the latest PLP status in MAAT style.",
        },
        "/plp last": {
            "de": "Zeigt die letzte PLP-Analyse als Tabelle.",
            "en": "Shows the latest PLP analysis as a table.",
        },
        "/uncertainty debug on": {
            "de": "Aktiviert Debug-Ausgaben fuer den PLP-Guard.",
            "en": "Enables PLP guard debug output.",
        },
        "/uncertainty debug off": {
            "de": "Deaktiviert Debug-Ausgaben fuer den PLP-Guard.",
            "en": "Disables PLP guard debug output.",
        },
    }

    def __init__(self, core=None, **kwargs):
        self.core = core
        self.state = getattr(core, "state", None)
        self.debug = False
        self.last_result = None

    def _lang(self):
        return get_language(("de", "en"))

    def _t(self, de: str, en: str) -> str:
        return en if self._lang() == "en" else de

    def _guard_enabled(self) -> bool:
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return bool(data.get("hallu_mode", False))
        except Exception:
            return False

    def final_response_guard_enabled(self, context=None) -> bool:
        return self._guard_enabled() and should_buffer_final_response(context)

    def _debug_report(self, result: dict) -> str:
        fields = result.get("fields", {})
        signals = result.get("signals", {})
        return "\n".join([
            self._t("🛡️ PLP-Guard Analyse:", "🛡️ PLP guard analysis:"),
            f"PLP: {result.get('plp', 0.0):.3f} | Risk: {result.get('risk', 0.0):.3f} | Action: {result.get('action', 'allow')}",
            f"H={fields.get('H', 0.0):.3f} B={fields.get('B', 0.0):.3f} S={fields.get('S', 0.0):.3f} V={fields.get('V', 0.0):.3f} R={fields.get('R', 0.0):.3f} K={fields.get('K', 0.0):.3f}",
            f"Hindernisse={result.get('hindernisse', 0.0):.3f} ΔE={result.get('delta_e', 0.0):.3f}",
            f"Signals: {signals}",
        ])

    def _action_label(self, action: str) -> str:
        mapping = {
            "allow": self._t("Stabil", "Stable"),
            "soften": self._t("Vorsichtig", "Cautious"),
            "block": self._t("Blockiert", "Blocked"),
        }
        return mapping.get(action, action)

    def _bar(self, value: float, width: int = 10) -> str:
        filled = max(0, min(width, int(round(float(value) * width))))
        return "█" * filled + "·" * (width - filled)

    def _summary_report(self) -> str:
        if not self._guard_enabled():
            return self._t("🛡️ Hallu-Modus ist derzeit AUS.", "🛡️ Hallu mode is currently OFF.")
        if not self.last_result:
            return self._t("Noch keine PLP-Analyse vorhanden.", "No PLP analysis available yet.")

        result = self.last_result
        lines = [
            self._t("🛡️ Letzter Unsicherheitsstatus:", "🛡️ Latest uncertainty status:"),
            f"PLP: {result.get('plp', 0.0):.3f}",
            f"{self._t('Unsicherheitsrisiko', 'Uncertainty risk')}: {result.get('risk', 0.0):.3f}",
            f"{self._t('Aktion', 'Action')}: {self._action_label(result.get('action', 'allow'))}",
        ]
        return "\n".join(lines)

    def _public_report(self) -> str:
        if not self._guard_enabled():
            return self._t("🛡️ Hallu-Modus ist derzeit AUS.", "🛡️ Hallu mode is currently OFF.")
        if not self.last_result:
            return self._t("Noch keine PLP-Analyse vorhanden.", "No PLP analysis available yet.")

        result = self.last_result
        fields = result.get("fields", {})
        lines = [
            self._t("🛡️ Letzte PLP-Guard Analyse:", "🛡️ Latest PLP guard analysis:"),
            f"PLP: {result.get('plp', 0.0):.3f}",
            f"{self._t('Unsicherheitsrisiko', 'Uncertainty risk')}: {result.get('risk', 0.0):.3f}",
            f"{self._t('Aktion', 'Action')}: {self._action_label(result.get('action', 'allow'))}",
            "",
            f"H={fields.get('H', 0.0):.3f}  B={fields.get('B', 0.0):.3f}  S={fields.get('S', 0.0):.3f}  V={fields.get('V', 0.0):.3f}  R={fields.get('R', 0.0):.3f}  K={fields.get('K', 0.0):.3f}",
            f"{self._t('Hindernisse', 'Obstacles')}: {result.get('hindernisse', 0.0):.3f}",
            f"ΔE: {result.get('delta_e', 0.0):.3f}",
        ]
        return "\n".join(lines)

    def _status_table(self) -> str:
        if not self._guard_enabled():
            return self._t("🛡️ Hallu-Modus ist derzeit AUS.", "🛡️ Hallu mode is currently OFF.")
        if not self.last_result:
            return self._t("Noch keine PLP-Analyse vorhanden.", "No PLP analysis available yet.")

        result = self.last_result
        fields = result.get("fields", {})
        signals = result.get("signals", {})
        lines = [
            self._t("╔════════════════════════════╗", "╔════════════════════════════╗"),
            self._t("║      PLP Status MAAT       ║", "║      PLP Status MAAT       ║"),
            self._t("╚════════════════════════════╝", "╚════════════════════════════╝"),
            f"{self._t('Status', 'Status'):14}: {self._action_label(result.get('action', 'allow'))}",
            f"PLP{' ':11}: {result.get('plp', 0.0):.3f}",
            f"{self._t('Risiko', 'Risk'):14}: {result.get('risk', 0.0):.3f}",
            "",
            f"H  [{self._bar(fields.get('H', 0.0))}] {fields.get('H', 0.0):.3f}",
            f"B  [{self._bar(fields.get('B', 0.0))}] {fields.get('B', 0.0):.3f}",
            f"S  [{self._bar(fields.get('S', 0.0))}] {fields.get('S', 0.0):.3f}",
            f"V  [{self._bar(fields.get('V', 0.0))}] {fields.get('V', 0.0):.3f}",
            f"R  [{self._bar(fields.get('R', 0.0))}] {fields.get('R', 0.0):.3f}",
            f"K  [{self._bar(fields.get('K', 0.0))}] {fields.get('K', 0.0):.3f}",
            "",
            f"{self._t('Hindernisse', 'Obstacles'):14}: {result.get('hindernisse', 0.0):.3f}",
            f"ΔE{' ':11}: {result.get('delta_e', 0.0):.3f}",
        ]

        if signals:
            lines.extend([
                "",
                self._t("Signale:", "Signals:"),
                f"- abs: {signals.get('absolute_hits', 0)} | hedges: {signals.get('hedge_hits', 0)} | assumptions: {signals.get('assumption_hits', 0)}",
                f"- overlap: {signals.get('context_overlap', 0.0):.3f} | unsupported_numbers: {signals.get('unsupported_numbers', 0)}",
            ])

        return "\n".join(lines)

    def command(self, full_cmd: str, context=None):
        cmd = full_cmd.strip().lower()
        if cmd == "/uncertainty":
            return True, self._summary_report()
        if cmd == "/plp":
            return True, self._public_report()
        if cmd == "/plp status" or cmd == "/plp last":
            return True, self._status_table()
        if cmd == "/uncertainty debug on":
            self.debug = True
            return True, self._t("PLP-Guard-Debug aktiviert.", "PLP guard debug enabled.")
        if cmd == "/uncertainty debug off":
            self.debug = False
            return True, self._t("PLP-Guard-Debug deaktiviert.", "PLP guard debug disabled.")
        return None

    def before_chat(self, user_input, context=None):
        return False, user_input

    def after_response(self, reply: str, context=None):
        if not self._guard_enabled():
            return reply
        try:
            result = evaluate_hallucination_risk(reply, context)
            self.last_result = result
            meta = (context or {}).setdefault("maat_meta", {}) if isinstance(context, dict) else {}
            if isinstance(meta, dict):
                meta["uncertainty_risk"] = result["risk"]
                meta["plp_guard"] = result
                meta["plp"] = result["plp"]
        except Exception:
            pass
        return reply

    def _soften_reply(self, reply: str) -> str:
        softened = reply or ""
        replacements = [
            (r"\bimmer\b", "oft"),
            (r"\bnie\b", "nicht immer"),
            (r"\bdefinitiv\b", "wahrscheinlich"),
            (r"\bgarantiert\b", "gut möglich"),
            (r"\bexakt\b", "relativ genau"),
            (r"\bgenau\b", "nach aktuellem Stand"),
            (r"\balways\b", "often"),
            (r"\bnever\b", "not always"),
            (r"\bdefinitely\b", "probably"),
            (r"\bguaranteed\b", "quite possible"),
            (r"\bexactly\b", "roughly"),
        ]
        for pattern, repl in replacements:
            softened = re.sub(pattern, repl, softened, flags=re.IGNORECASE)

        prefix = self._t(
            "Hinweis: Ich formuliere das vorsichtiger, weil der aktuelle Kontext hier nicht ganz stabil ist.\n",
            "Note: I'm phrasing this more cautiously because the current context is not fully stable here.\n",
        )
        if prefix.strip().lower() not in softened.lower():
            softened = prefix + softened.strip()
        return softened.strip()

    def _fallback_reply(self) -> str:
        return self._t(
            "Ich moechte hier keine harte Behauptung machen, weil der aktuelle Kontext dafuer nicht stabil genug ist. "
            "Wenn du willst, gib mir mehr Daten, eine Quelle oder den genauen Punkt, dann antworte ich vorsichtiger und belastbarer.",
            "I don't want to make a hard claim here because the current context is not stable enough for it. "
            "If you want, give me more data, a source, or the exact point and I'll answer more carefully and reliably.",
        )

    def before_final_response(self, reply: str, context=None):
        if context is None:
            context = {}

        meta = context.setdefault("maat_meta", {})
        if not isinstance(reply, str) or not reply.strip():
            result = {
                "plp": calculate_plp(1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.2, 0.2),
                "risk": 0.0,
                "action": "allow",
                "fields": {"H": 1.0, "B": 1.0, "S": 1.0, "V": 1.0, "R": 1.0, "K": 1.0},
                "hindernisse": 0.2,
                "delta_e": 0.2,
                "signals": {},
            }
            self.last_result = result
            meta["uncertainty_risk"] = 0.0
            meta["plp_guard"] = result
            return reply

        result = evaluate_hallucination_risk(reply, context)
        final_reply = reply

        if result["action"] == "soften":
            final_reply = self._soften_reply(reply)
        elif result["action"] == "block":
            final_reply = self._fallback_reply()

        result["final_reply"] = final_reply
        self.last_result = result
        meta["uncertainty_risk"] = result["risk"]
        meta["plp_guard"] = result
        meta["plp"] = result["plp"]

        if self.debug:
            print("\n" + self._debug_report(result) + "\n")

        return final_reply
