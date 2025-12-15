# shared/plugins/maat_uncertainty_guard.py
# -*- coding: utf-8 -*-

import re

class Plugin:
    """
    Maat Uncertainty Guard
    ----------------------
    Analysiert jede Antwort auf typische Halluzinations-Indikatoren
    und schreibt einen Unsicherheitswert in context["maat_meta"]["uncertainty_risk"].
    """

    type = "chat"
    commands = {
        "/uncertainty": "Zeigt den letzten geschätzten Unsicherheits-/Halluzinations-Risiko-Wert.",
    }

    def __init__(self, core=None, **kwargs):
        self.core = core
        self.state = getattr(core, "state", None)
        self.last_risk = 0.0

    def command(self, full_cmd: str, context=None):
        cmd = full_cmd.strip().lower()
        if cmd == "/uncertainty":
            return True, f"Aktueller Unsicherheits-Risiko-Wert: {self.last_risk:.3f}"
        return None

    def before_chat(self, user_input, context=None):
        # tut hier nichts, nur after_response nutzen
        return False, user_input

    def after_response(self, reply: str, context=None):
        if context is None:
            context = {}

        meta = context.setdefault("maat_meta", {})

        if not isinstance(reply, str) or not reply.strip():
            self.last_risk = 0.0
            meta["uncertainty_risk"] = 0.0
            return reply

        risk = 0.0
        t = reply.lower()

        # 1) Zahlen ohne entsprechende Frage
        numbers = re.findall(r"\d+", reply)
        last_user = ""
        conv = context.get("conversation", [])
        if conv:
            # letzte User-Nachricht suchen
            for msg in reversed(conv):
                if msg.get("role") == "user":
                    last_user = msg.get("content", "").lower()
                    break

        asked_numbers = bool(re.search(r"\d", last_user))
        if numbers and not asked_numbers:
            risk += 0.4

        # 2) Absolutheitswörter
        if "immer" in t or "nie" in t or "auf jeden fall" in t:
            risk += 0.2

        # 3) Spezielles Wissen ohne Quellenhinweis
        if any(w in t for w in ["exakte zahl", "genau", "präzise"]) and not any(
            w in t for w in ["kann abweichen", "ungefähr", "schätzung"]
        ):
            risk += 0.2

        risk = max(0.0, min(1.0, risk))
        self.last_risk = risk
        meta["uncertainty_risk"] = round(risk, 3)

        return reply