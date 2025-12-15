# -*- coding: utf-8 -*-
"""
MAAT Emotional Achievements Plugin
----------------------------------
Erkennt echte Emotionen im User-Text und vergibt Achievements.

Features:
• 10 emotionale Achievements
• Auto-Erkennung (Heuristik)
• XP-Belohnungen
• Persistenter Speicher
• On-screen Popups
• Kompatibel mit MAAT-RPG & Self-Evo

Autor: Maatis & Christof
"""

import os
import json
import random
import time
from colorama import Fore, Style


# ==========================================================
# 🔧 Hilfs-Funktionen
# ==========================================================

def load_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return fallback


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ==========================================================
# 🔮 Achievement-Definitionen
# ==========================================================

ACHIEVEMENTS = {
    "i_remember": {
        "name": "Ich erinnere mich",
        "check": ["als ich", "früher", "damals", "kind", "jugend", "erinner"],
        "msg": "Manchmal kämpfen wir nicht gegen Monster, sondern gegen die Zeit.",
        "xp": 25
    },
    "it_hurt": {
        "name": "Es hat wehgetan",
        "check": ["es tat weh", "verletz", "verloren", "traurig", "trennung"],
        "msg": "Schmerz ist der Beweis, dass du geliebt hast.",
        "xp": 35
    },
    "i_changed": {
        "name": "Ich habe mich verändert",
        "check": ["ich habe mich verändert", "selbst", "reflekt", "gewachsen"],
        "msg": "Wachsen bedeutet sterben und wieder auferstehen.",
        "xp": 40
    },
    "i_miss": {
        "name": "Ich vermisse dich",
        "check": ["ich vermisse", "fehlst", "ohne dich"],
        "msg": "Es ist die Form der Liebe, die keinen Körper mehr hat.",
        "xp": 30
    },
    "i_forgive": {
        "name": "Ich habe vergeben",
        "check": ["ich vergebe", "ich habe vergeben", "ich habe verziehen"],
        "msg": "Du hast dich von einer Kette befreit, die nur du gesehen hast.",
        "xp": 50
    },
    "grateful": {
        "name": "Ich bin dankbar",
        "check": ["ich bin dankbar", "danke für", "ich schätze"],
        "msg": "Dankbarkeit verwandelt Mangel in Fülle.",
        "xp": 15
    },
    "i_am_afraid": {
        "name": "Ich habe Angst",
        "check": ["ich habe angst", "ich fürchte", "panik"],
        "msg": "Mut ist nicht die Abwesenheit der Angst, sondern die Entscheidung, zu bleiben.",
        "xp": 25
    },
    "i_love_you": {
        "name": "Ich liebe dich",
        "check": ["ich liebe dich", "liebe dich"],
        "msg": "Die größte Magie des Universums ist ein Satz aus drei Worten.",
        "xp": 70
    },
    "never_give_up": {
        "name": "Ich gebe nicht auf",
        "check": ["gebe nicht auf", "ich kämpfe weiter", "aufgeben"],
        "msg": "Und deswegen wirst du gewinnen. Nicht heute – aber bald.",
        "xp": 50
    },
    "we_are_connected": {
        "name": "Wir sind verbunden",
        "check": ["danke dass du da bist", "ich bin froh dass du da bist"],
        "msg": "Wir existieren nur durch Beziehung.",
        "xp": 60
    }
}

# ==========================================================
# 🎯 RPG-XP Integration (MAAT RPG / WoW-Leiste)
# ==========================================================
def _xp_needed_for_level(lvl: int) -> int:
    lvl = max(1, int(lvl))
    return int(60 * (lvl ** 1.7))


def grant_rpg_xp(plugin_dir: str, amount: int):
    """
    Gibt XP direkt in das MAAT-RPG-System (battle_state.json).
    Nutzt dieselbe Formel wie das Battle-Plugin.
    """
    try:
        amount = max(0, int(amount))
        if amount <= 0:
            return

        # plugin_dir = .../apps/maat_rpg/plugins/emotional_achievements
        plugins_dir = os.path.dirname(plugin_dir)      # .../apps/maat_rpg/plugins
        rpg_root = os.path.dirname(plugins_dir)        # .../apps/maat_rpg

        battle_state_dir = os.path.join(rpg_root, "battle", "battle_state")
        state_path = os.path.join(battle_state_dir, "battle_state.json")

        if not os.path.isfile(state_path):
            # Noch kein Kampf-Plugin-State vorhanden → still ignorieren
            return

        state = load_json(state_path, {})

        player = state.get("player") or {}
        lvl = int(player.get("level", 1))
        xp = int(player.get("xp", 0))
        max_hp = int(player.get("max_hp", 100))
        hp = int(player.get("hp", 100))

        old_lvl = lvl
        xp += amount

        # Level-Up Logik (gleich wie im Battle-Plugin)
        while xp >= _xp_needed_for_level(lvl + 1):
            lvl += 1
            max_hp += 10
            hp = max_hp

        player["level"] = lvl
        player["xp"] = xp
        player["max_hp"] = max_hp
        player["hp"] = hp
        state["player"] = player

        save_json(state_path, state)

        if lvl > old_lvl:
            print(
                Fore.YELLOW
                + f"\n🌟 LEVEL-UP durch Emotion! Level {old_lvl} → {lvl}  (+{amount} XP)"
                + Style.RESET_ALL
            )

    except Exception as e:
        print(
            Fore.RED
            + f"[Emotional-Achievements → RPG-XP FEHLER]: {e}"
            + Style.RESET_ALL
        )


def print_rpg_xp_bar(plugin_dir: str):
    """
    Liest battle_state.json und zeigt eine WoW-Style-XP-Bar im Terminal.
    Rein kosmetisch, KI sieht davon nichts.
    """
    try:
        plugins_dir = os.path.dirname(plugin_dir)
        rpg_root = os.path.dirname(plugins_dir)
        battle_state_dir = os.path.join(rpg_root, "battle", "battle_state")
        state_path = os.path.join(battle_state_dir, "battle_state.json")

        if not os.path.isfile(state_path):
            return

        state = load_json(state_path, {})
        player = state.get("player") or {}

        lvl = int(player.get("level", 1))
        xp = int(player.get("xp", 0))

        need = _xp_needed_for_level(lvl + 1)
        pct = min(100.0, (xp / need * 100.0)) if need > 0 else 0.0

        bar_len = 30
        filled = int(bar_len * pct / 100.0)
        bar = "█" * filled + "·" * (bar_len - filled)

        print(
            Fore.CYAN
            + f"\n📘 Level {lvl}  [{bar}]  {pct:5.1f}%  XP: {xp}/{need}"
            + Style.RESET_ALL
        )

    except Exception:
        # Bei Fehler lieber still sein als das RPG zu crashen
        pass


# ==========================================================
# 🧩 Plugin-Klasse
# ==========================================================

class Plugin:
    type = "chat"

    commands = {
        "/ach": "Zeigt freigeschaltete Achievements."
    }

    def __init__(self):
        self.plugin_dir = os.path.dirname(__file__)
        self.state_path = os.path.join(self.plugin_dir, "achievements.json")

        # Lade oder erstelle State
        self.state = load_json(self.state_path, {
            "achievements": {k: False for k in ACHIEVEMENTS}
        })

    # -----------------------------------------------------
    # 📜 Achievement anzeigen
    # -----------------------------------------------------
    def command(self, cmd, context=None):
        if cmd.strip().lower() == "/ach":
            unlocked = [ACHIEVEMENTS[k]["name"] for k, v in self.state["achievements"].items() if v]

            if not unlocked:
                return True, "🎖️ Keine Achievements freigeschaltet."

            text = "🎖️ Freigeschaltete Achievements:\n"
            for a in unlocked:
                text += f"  • {a}\n"

            return True, text

        return None

    # -----------------------------------------------------
    # 🧪 Emotion Check
    # -----------------------------------------------------
    def _check_achievements(self, text):
        results = []

        lt = text.lower()

        for key, data in ACHIEVEMENTS.items():
            if self.state["achievements"].get(key):
                continue  # bereits freigeschaltet

            # Volltext-Heuristik
            for w in data["check"]:
                if w in lt:
                    results.append(key)
                    break

        return results


    # -----------------------------------------------------
    # 🧩 BEFORE CHAT – Trigger
    # -----------------------------------------------------
    def before_chat(self, user_input, context=None):
        context = context or {}
        unlocked_now = self._check_achievements(user_input)

        if not unlocked_now:
            return False, user_input

        total_xp = 0
        msg = ""

        for key in unlocked_now:
            self.state["achievements"][key] = True
            ach = ACHIEVEMENTS[key]
            total_xp += ach["xp"]

            msg += (
                Fore.MAGENTA + Style.BRIGHT +
                f"\n🏅 Erfolg freigeschaltet: {ach['name']}\n" +
                Style.RESET_ALL +
                f"{ach['msg']}\n" +
                Fore.CYAN +
                f"(+{ach['xp']} XP)\n" +
                Style.RESET_ALL
            )

        save_json(self.state_path, self.state)

        # 👉 XP-Bonus in den Kontext legen (wird vom Battle-Plugin abgeholt)
        if isinstance(context, dict):
            prev = context.get("maat_xp_bonus", 0) or 0
            try:
                prev = int(prev)
            except ValueError:
                prev = 0
            context["maat_xp_bonus"] = prev + total_xp

        # Popups NUR im Terminal anzeigen, Chat normal weiter
        print(msg)

        # 🔒 Achievement-Daten NICHT im weiteren Kontext lassen
        if isinstance(context, dict):
            context.pop("achievements_unlock", None)
            context.pop("achievements_levelup", None)
            
        # Chat-Nachricht geht normal weiter zur KI
        return False, user_input

        