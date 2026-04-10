# shared/plugins/maat_reflection_prethought.py
# -*- coding: utf-8 -*-
from shared.core.rpg_i18n import get_language

class Plugin:
    """
    Maat Reflection Prethought
    ---------------------------
    Leichtgewichtige Vor-Analyse jeder User-Nachricht.
    Schreibt grobe Einschätzung in context["maat_meta"]:
      - prethought_clarity
      - problem_complexity
      - field_prediction (H,B,S,V,R-Heuristik)
    """

    type = "chat"
    commands = {
        "/prethought": {"de": "Zeigt die letzte Vor-Analyse (Klarheit, Komplexitaet, Felder).", "en": "Shows the last pre-analysis (clarity, complexity, fields)."},
    }

    def __init__(self, core=None, **kwargs):
        self.core = core
        self.state = getattr(core, "state", None)
        self.last_meta = None

    def _t(self, de: str, en: str) -> str:
        return en if get_language(("de", "en")) == "en" else de

    def command(self, full_cmd: str, context=None):
        cmd = full_cmd.strip().lower()
        if cmd == "/prethought":
            if not self.last_meta:
                return True, self._t("Noch keine Vor-Analyse in dieser Session.", "No pre-analysis in this session yet.")
            m = self.last_meta
            fields = m.get("field_prediction", {})
            lines = [
                self._t("🧠 Vor-Analyse (Prethought):", "🧠 Pre-analysis (Prethought):"),
                f"- {self._t('Klarheit', 'Clarity'):16}: {m.get('prethought_clarity', 0.0):.2f}",
                f"- {self._t('Komplexitaet', 'Complexity'):16}: {m.get('problem_complexity', 0.0):.2f}",
                f"- {self._t('Felder (Heuristik)', 'Fields (heuristic)')}: {fields}",
            ]
            return True, "\n".join(lines)

        return None

    def before_chat(self, user_input: str, context=None):
        if not isinstance(user_input, str) or not user_input.strip():
            return False, user_input

        if context is None:
            context = {}

        meta = context.setdefault("maat_meta", {})

        text = user_input.lower()
        clarity = 0.5
        complexity = 0.5

        # einfache Heuristik
        if any(w in text for w in ["warum", "wieso", "erkläre", "erklären"]):
            clarity += 0.2
            complexity += 0.2

        if any(w in text for w in ["ethik", "moral", "konflikt", "dilemma"]):
            complexity += 0.3

        # grobe Feld-Vorhersage
        fields = {
            "H": 0.4,
            "B": 0.4,
            "S": 0.4,
            "V": 0.4,
            "R": 0.4,
        }

        if "harmonie" in text or "friedlich" in text:
            fields["H"] = 1.0
        if "balance" in text or "gleichgewicht" in text:
            fields["B"] = 1.0
        if any(w in text for w in ["idee", "vision", "kreativ", "erschaffen"]):
            fields["S"] = 1.0
        if any(w in text for w in ["wir", "gemeinschaft", "team", "zusammen"]):
            fields["V"] = 1.0
        if "respekt" in text or "achtung" in text:
            fields["R"] = 1.0

        clarity = max(0.0, min(1.0, clarity))
        complexity = max(0.0, min(1.0, complexity))

        meta["prethought_clarity"] = round(clarity, 3)
        meta["problem_complexity"] = round(complexity, 3)
        meta["field_prediction"] = fields

        # für /prethought merken
        self.last_meta = {
            "prethought_clarity": clarity,
            "problem_complexity": complexity,
            "field_prediction": fields,
        }

        return False, user_input

    def after_response(self, reply, context=None):
        # dieses Plugin arbeitet nur im before_chat
        return reply
