# -*- coding: utf-8 -*-
"""
MAAT RPG – Inner Boss System v1
--------------------------------
• Unsichtbare Trigger
• Keine KI-Meta-Wahrnehmung
• Zustand bleibt persistent
• Beeinflusst Kampfsystem
"""

import os
import json
import random
from colorama import Fore, Style

# -------------------------------------------------
# Setup
# -------------------------------------------------
class Plugin:
    type = "chat"

    def __init__(self):
        self.plugin_dir = os.path.dirname(__file__)
        self.bosses_path = os.path.join(self.plugin_dir, "bosses.json")
        self.state_path = os.path.join(self.plugin_dir, "boss_state.json")

        self.bosses = self._load_json(self.bosses_path, {})
        self.state = self._load_json(self.state_path, {
            "active_boss": None,
            "trigger_counter": {},
            "resolved": {}
        })

    # -------------------------------------------------
    # Utils
    # -------------------------------------------------
    def _load_json(self, path, fallback):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return fallback

    def _save_state(self):
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    # -------------------------------------------------
    # BEFORE CHAT – Trigger sammeln
    # -------------------------------------------------
    def before_chat(self, user_input, context=None):
        text = user_input.lower()
        context = context or {}

        # Kein Trigger, wenn bereits ein Inner Boss aktiv ist
        if self.state["active_boss"]:
            return False, user_input

        for boss_id, boss in self.bosses.items():
            if self.state["resolved"].get(boss_id):
                continue

            trig = boss["trigger"]
            hits = self.state["trigger_counter"].get(boss_id, 0)

            for kw in trig["keywords"]:
                if kw in text:
                    hits += 1
                    break

            self.state["trigger_counter"][boss_id] = hits

            if hits >= trig["min_hits"]:
                self._spawn_boss(boss_id)
                self._save_state()
                break

        self._save_state()
        return False, user_input

    # -------------------------------------------------
    # Spawn Boss
    # -------------------------------------------------
    def _spawn_boss(self, boss_id):
        boss = self.bosses[boss_id]
        self.state["active_boss"] = {
            "id": boss_id,
            "hp": boss["hp"]
        }

        print(
            Fore.MAGENTA + Style.BRIGHT +
            "\n👁️ Die Luft wird schwer.\n"
            "Etwas beobachtet dich.\n\n"
            f"🧠 INNERER BOSS ERWACHT: {boss['name']}\n"
            + Style.RESET_ALL
        )

    # -------------------------------------------------
    # Hook für Battle-System
    # -------------------------------------------------
    def apply_battle_modifier(self, dmg, attack_type):
        """
        Wird vom Battle-Plugin abgefragt (falls aktiv)
        """
        active = self.state.get("active_boss")
        if not active:
            return dmg

        boss = self.bosses.get(active["id"])
        if not boss:
            return dmg

        # Standardangriffe geschwächt
        dmg = int(dmg * boss["effects"]["player_damage_mult"])

        # MAAT-Boni
        maat_bonus = boss["effects"].get("maat_bonus", {})
        if attack_type in maat_bonus:
            dmg = int(dmg * maat_bonus[attack_type])

        return dmg

    # -------------------------------------------------
    # Nach Boss-Schaden prüfen
    # -------------------------------------------------
    def on_boss_damage(self, damage):
        active = self.state.get("active_boss")
        if not active:
            return

        active["hp"] -= damage

        if active["hp"] <= 0:
            self._resolve_boss(active["id"])

        self._save_state()

    # -------------------------------------------------
    # Boss besiegt
    # -------------------------------------------------
    def _resolve_boss(self, boss_id):
        boss = self.bosses[boss_id]

        print(
            Fore.CYAN + Style.BRIGHT +
            f"\n{boss['name']} tritt einen Schritt zurück.\n"
            "Er verschwindet nicht.\n"
            "Aber er herrscht nicht mehr.\n"
            + Style.RESET_ALL
        )

        self.state["resolved"][boss_id] = True
        self.state["active_boss"] = None
        self.state["trigger_counter"][boss_id] = 0