# shared/plugins/maat_usercontext_memory.py
# -*- coding: utf-8 -*-

class Plugin:
    """
    Maat Usercontext Memory
    -----------------------
    Leichtes, nicht-identifizierendes Profiling:
    - merkt sich, ob der Nutzer viele Fragen stellt
    - ob emotionale Sensibilität sichtbar ist
    Schreibt Snapshot in context["maat_meta"]["user_profile_snapshot"].
    """

    type = "chat"
    commands = {
        "/userstyle": "Zeigt den aktuellen User-Stil-Snapshot (anonym).",
    }

    def __init__(self, core=None, **kwargs):
        self.core = core
        self.state = getattr(core, "state", None)
        self.profile = {}

    def command(self, full_cmd: str, context=None):
        cmd = full_cmd.strip().lower()
        if cmd == "/userstyle":
            if not self.profile:
                return True, "Noch kein User-Stil erkannt."
            return True, f"Aktueller User-Stil: {self.profile}"
        return None

    def before_chat(self, user_input: str, context=None):
        if context is None:
            context = {}

        meta = context.setdefault("maat_meta", {})

        # Fragen-Stil
        if user_input.strip().endswith("?"):
            self.profile["prefers_questions"] = True

        # emotionale Begriffe
        lowered = user_input.lower()
        if any(w in lowered for w in ["angst", "überfordert", "traurig", "unsicher"]):
            self.profile["emotional_sensitivity"] = True

        meta["user_profile_snapshot"] = dict(self.profile)

        return False, user_input

    def after_response(self, reply, context=None):
        return reply