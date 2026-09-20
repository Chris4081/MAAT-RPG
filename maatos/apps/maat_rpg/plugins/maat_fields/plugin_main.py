# -*- coding: utf-8 -*-
"""
MAAT-Felder Plugin
------------------
• Verwalte H, B, S, V, R als dynamische „Buffs“
• Leichte Auto-Steigerung pro Nachricht
• /test_fields zeigt den aktuellen Stand
"""
import os
import json
from colorama import Fore, Style
from shared.core.maat_paths import state_file

# Standardwerte für die Felder
DEFAULT_STATE = {
    "H": 0.50,   # Harmonie
    "B": 0.50,   # Balance
    "S": 0.50,   # Schöpfungskraft
    "V": 0.50,   # Verbundenheit
    "R": 0.50,   # Respekt
    "messages": 0,
}


class Plugin:
    type = "chat"

    # Der Command wird vom PluginManager automatisch registriert
    commands = {
        "/test_fields": {
            "de": "Zeigt aktuelle MAAT-Feld-Buffs (H, B, S, V, R).",
            "en": "Shows current MAAT field buffs (H, B, S, V, R).",
        }
    }

    def __init__(self):
        self.plugin_dir = os.path.dirname(__file__)
        self.state_path = state_file("maat_fields_state.json")
        self.state = self._load_state()

    # ------------------------
    # 🔁 State Handling
    # ------------------------
    def _load_state(self):
        if os.path.isfile(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge mit Defaults (falls neue Keys dazukommen)
                    merged = DEFAULT_STATE.copy()
                    merged.update(data)
                    return merged
            except Exception:
                pass
        return DEFAULT_STATE.copy()

    def _save_state(self):
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception:
            # Niemals das Spiel crashen lassen
            pass

    def _natural_tick(self):
        """
        Einfache Auto-Steigerung pro Spieler-Nachricht:
        • +0.01 pro Feld, gedeckelt bei 1.0
        """
        self.state["messages"] += 1

        for key in ("H", "B", "S", "V", "R"):
            val = float(self.state.get(key, 0.0))
            val += 0.01
            if val > 1.0:
                val = 1.0
            self.state[key] = round(val, 3)

        self._save_state()

    def _attach_to_context(self, context):
        """
        Schreibt die aktuellen Felder in den globalen Kontext,
        damit andere Plugins sie nutzen können.
        """
        if isinstance(context, dict):
            context["maat_fields"] = {
                "H": self.state["H"],
                "B": self.state["B"],
                "S": self.state["S"],
                "V": self.state["V"],
                "R": self.state["R"],
            }

    # ------------------------
    # 🔄 Hooks
    # ------------------------
    def on_startup(self, context=None):
        # Beim Start einmal in den Kontext einhängen
        self._attach_to_context(context)
        print(
            Fore.CYAN
            + f"[MAAT-FIELDS] Init: "
              f"H={self.state['H']}, "
              f"B={self.state['B']}, "
              f"S={self.state['S']}, "
              f"V={self.state['V']}, "
              f"R={self.state['R']}"
            + Style.RESET_ALL
        )

    def before_chat(self, user_input, context=None):
        """
        Wird vor jeder KI-Antwort aufgerufen.
        • Auto-Tick der Felder
        • Felder zurück in den Kontext schreiben
        """
        self._natural_tick()
        self._attach_to_context(context)
        return False, user_input  # Chat normal weiterlaufen lassen

    def after_response(self, reply, context=None):
        """
        Aktuell keine Manipulation der Antwort.
        Hier könntest du später z.B. kurze Hinweise anhängen.
        """
        return reply

    # ------------------------
    # ⌨️ Commands
    # ------------------------
    def command(self, cmd, context=None):
        cmd = cmd.strip().lower()

        if cmd.startswith("/test_fields"):
            self._attach_to_context(context)

            h = self.state["H"]
            b = self.state["B"]
            s = self.state["S"]
            v = self.state["V"]
            r = self.state["R"]

            msg = (
                f"{Fore.MAGENTA}MAAT-Feld-Buffs\n"
                f"{Fore.CYAN}Harmonie   (H): {h:.3f}\n"
                f"Balance    (B): {b:.3f}\n"
                f"Schöpfung  (S): {s:.3f}\n"
                f"Verbundenh.(V): {v:.3f}\n"
                f"Respekt    (R): {r:.3f}{Style.RESET_ALL}"
            )
            return True, msg

        return None
