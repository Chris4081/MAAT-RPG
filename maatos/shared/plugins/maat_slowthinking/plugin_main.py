# shared/plugins/maat_slowthinking.py
# -*- coding: utf-8 -*-

class Plugin:
    """
    Maat Slow Thinking
    ------------------
    Legt eine kleine interne Struktur in context["maat_meta"]["_internal_prethought"] an,
    damit andere Module/Evo sehen: es wurde bewusst über Problem/Felder nachgedacht.
    """

    type = "chat"
    commands = {}

    def __init__(self, core=None, **kwargs):
        self.core = core
        self.state = getattr(core, "state", None)

    def command(self, full_cmd: str, context=None):
        # hat keine User-Kommandos
        return None

    def before_chat(self, user_input: str, context=None):
        if context is None:
            context = {}

        meta = context.setdefault("maat_meta", {})
        field_pred = meta.get("field_prediction", {})

        meta["_internal_prethought"] = {
            "user_need": "Frage verstehen + ethische Abwägung vorbereiten",
            "core_fields": field_pred,
            "focus": "Klarheit und Balance der Antwort",
        }

        return False, user_input

    def after_response(self, reply, context=None):
        return reply