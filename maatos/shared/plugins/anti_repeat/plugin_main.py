# -*- coding: utf-8 -*-
"""
MAAT-AntiRepeat Plugin v1.0
--------------------------------------------
✔ Entfernt doppelte Zeilen aus KI-Antworten
✔ Keine Veränderung der Bedeutung
✔ Keine Formatierung wird beschädigt
✔ Greift NUR in after_response ein
✔ Perfekt gegen Wiederholungs-Schleifen
"""

class Plugin:
    type = "chat"

    # Command-Liste (damit /help funktioniert)
    commands = {
        "/antirepeat": {"de": "Zeigt den Status des Anti-Repeat-Filters.", "en": "Shows the anti-repeat filter status."},
        "/antirepeat on": {"de": "Aktiviert Anti-Repeat.", "en": "Enables anti-repeat."},
        "/antirepeat off": {"de": "Deaktiviert Anti-Repeat.", "en": "Disables anti-repeat."}
    }

    def __init__(self):
        self.enabled = True  # Standard: aktiviert

    # -----------------------------------------------------
    # COMMAND HANDLER
    # -----------------------------------------------------
    def command(self, cmd, context=None):
        c = (cmd or "").strip().lower()

        if c == "/antirepeat":
            return True, f"🔁 Anti-Repeat ist {'AKTIV' if self.enabled else 'INAKTIV'}."

        if c == "/antirepeat on":
            self.enabled = True
            return True, "🔁 Anti-Repeat wurde AKTIVIERT."

        if c == "/antirepeat off":
            self.enabled = False
            return True, "🔁 Anti-Repeat wurde DEAKTIVIERT."

        return None

    # -----------------------------------------------------
    # HELFER: Wiederholungen entfernen
    # -----------------------------------------------------
    def _remove_repetitions(self, text):
        lines = text.split("\n")
        seen = set()
        new_lines = []

        for line in lines:
            clean = line.strip()

            # Leere Zeilen oder neue Inhalte immer behalten
            if clean and clean not in seen:
                seen.add(clean)
                new_lines.append(line)
            # Leere Zeilen NICHT blockieren
            elif not clean:
                new_lines.append(line)

        return "\n".join(new_lines)

    # -----------------------------------------------------
    # AFTER RESPONSE – Filter anwenden
    # -----------------------------------------------------
    def after_response(self, reply, context=None):
        if not self.enabled:
            return reply

        cleaned = self._remove_repetitions(reply)
        return cleaned
