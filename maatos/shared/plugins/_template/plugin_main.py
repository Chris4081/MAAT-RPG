# -*- coding: utf-8 -*-
"""
MAAT-KI UNIVERSAL PLUGIN TEMPLATE — v3.0
Garantiert kompatibel mit PluginManager v2.3
"""

class Plugin:
    # type = "chat" → reagiert auf Befehle
    # type = "stream" → reagiert auf Token beim Streaming
    type = "chat"

    def __init__(self):
        """Grundinitialisierung — wird immer aufgerufen"""
        pass

    # -------------------------------------------------------
    # COMMAND-HOOK (für /befehle)
    # -------------------------------------------------------
    def command(self, cmd: str, context: dict = None):
        """
        Wird ausgeführt, wenn der User einen /befehl eingibt.
        Rückgabe:
            None → nicht gehandelt
            str → Text sofort ausgeben und abbrechen
            (True, reply) → handled=true, Text ausgeben
        """
        return None

    # -------------------------------------------------------
    # BEFORE_CHAT-HOOK
    # -------------------------------------------------------
    def before_chat(self, user_input: str, context: dict = None):
        """
        Wird *vor* der Anfrage an das Modell ausgeführt.
        Rückgabe:
            (False, None) → nicht gehandelt → weiter an Modell
            (True, new_input) → handled → Model erhält new_input
        """
        return (False, None)

    # -------------------------------------------------------
    # AFTER_RESPONSE-HOOK
    # -------------------------------------------------------
    def after_response(self, reply: str, context: dict = None):
        """
        Kann die Modellantwort verändern.
        Rückgabe:
            None → unverändert lassen
            str → ersetzen
        """
        return None

    # -------------------------------------------------------
    # STARTUP HOOK
    # -------------------------------------------------------
    def on_startup(self):
        """
        Wird einmal nach dem Laden aller Plugins ausgeführt.
        Ideal für:
            • TTS aktivieren
            • RPG-Modus anmelden
            • Einstellungsdialoge
        """
        pass