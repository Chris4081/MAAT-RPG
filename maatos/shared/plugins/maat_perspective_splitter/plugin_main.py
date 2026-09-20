# shared/plugins/maat_perspective_splitter.py
# -*- coding: utf-8 -*-

class Plugin:
    """
    Maat Perspective Splitter
    -------------------------
    Kann Antworten optional in zwei Perspektiven strukturieren:
      - Logische Sicht
      - Ethische Sicht (Bezug auf H,B,S,V,R)
    Standard: AUS, Aktivierung per /perspective on.
    """

    type = "chat"
    commands = {
        "/perspective on": {"de": "Aktiviert die Perspektiv-Trennung fuer Antworten.", "en": "Enables perspective splitting for responses."},
        "/perspective off": {"de": "Deaktiviert die Perspektiv-Trennung.", "en": "Disables perspective splitting."},
    }

    def __init__(self, core=None, **kwargs):
        self.core = core
        self.state = getattr(core, "state", None)
        self.enabled = False

    def command(self, full_cmd: str, context=None):
        cmd = full_cmd.strip().lower()
        if cmd == "/perspective on":
            self.enabled = True
            return True, "Perspektiv-Trennung AKTIV."
        if cmd == "/perspective off":
            self.enabled = False
            return True, "Perspektiv-Trennung DEAKTIVIERT."
        return None

    def before_chat(self, user_input, context=None):
        return False, user_input

    def after_response(self, reply: str, context=None):
        if not self.enabled:
            return reply
        if not isinstance(reply, str) or not reply.strip():
            return reply

        # Einfaches Doppel-Layout
        out = (
            "🔹 **Logische Sicht:**\n"
            + reply.strip()
            + "\n\n"
            + "🔹 **Ethische Sicht:**\n"
            + "Betrachte die Auswirkungen dieser Antwort auf Harmonie, Balance, Kreativität, Verbundenheit und Respekt."
        )
        return out
