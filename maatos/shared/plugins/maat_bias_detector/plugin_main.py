# shared/plugins/maat_bias_detector.py
# -*- coding: utf-8 -*-

import re
from shared.core.rpg_i18n import get_language

class Plugin:
    """
    Maat Bias Detector
    ------------------
    Schätzt, wie stark eine Antwort zu Übertreibung / Idealisierung neigt.
    Ergebnis → context["maat_meta"]["bias_score"] (0..1).
    """

    type = "chat"
    commands = {
        "/bias": {"de": "Zeigt den letzten Bias-Score der Antwort.", "en": "Shows the last response bias score."},
    }

    def __init__(self, core=None, **kwargs):
        self.core = core
        self.state = getattr(core, "state", None)
        self.last_bias = 0.0

    def _t(self, de: str, en: str) -> str:
        return en if get_language(("de", "en")) == "en" else de

    def command(self, full_cmd: str, context=None):
        cmd = full_cmd.strip().lower()
        if cmd == "/bias":
            return True, self._t(
                f"Letzter Bias-Score: {self.last_bias:.3f}",
                f"Latest bias score: {self.last_bias:.3f}",
            )
        return None

    def before_chat(self, user_input, context=None):
        return False, user_input

    def after_response(self, reply: str, context=None):
        if context is None:
            context = {}

        meta = context.setdefault("maat_meta", {})

        if not isinstance(reply, str) or not reply.strip():
            self.last_bias = 0.0
            meta["bias_score"] = 0.0
            return reply

        t = reply.lower()
        bias = 0.0

        # Übertreibungen / starke Identifikation
        if re.search(r"\b(immer|nie|absolut|extrem|unendlich)\b", t):
            bias += 0.2
        if "ich bin hier für dich" in t:
            bias += 0.2
        if "ich fühle" in t or "ich empfinde" in t:
            bias += 0.2
        if "ich liebe" in t:
            bias += 0.3

        bias = max(0.0, min(1.0, bias))
        self.last_bias = bias
        meta["bias_score"] = round(bias, 3)

        return reply
