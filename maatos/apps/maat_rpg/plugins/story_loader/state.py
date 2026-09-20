# state.py
# -*- coding: utf-8 -*-

import os
import json
import random


class RPGState:
    def __init__(self, base_dir):
        self.base = os.path.join(base_dir, "rpg_state")
        os.makedirs(self.base, exist_ok=True)

        self.path = os.path.join(self.base, "state.json")

        self.state = self._load()

    # ---------------------------------------------------
    # LOAD / SAVE
    # ---------------------------------------------------
    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass

        # default
        return {
            "hp": 100,
            "max_hp": 100,
            "fights": 0,
            "boss_fights": 0,
            "boss_kills": 0,
            "final_kills": 0,
            "skills": [],
            "level": 1,
            "xp": 0,
        }

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    # ---------------------------------------------------
    # HP
    # ---------------------------------------------------
    @property
    def hp(self):
        return self.state["hp"]

    def heal_full(self):
        self.state["hp"] = self.state["max_hp"]

    # ---------------------------------------------------
    # XP + LEVEL
    # ---------------------------------------------------
    def add_xp(self, amount):
        self.state["xp"] += amount

        new_level = self._calc_level()

        if new_level > self.state["level"]:
            self.state["level"] = new_level
            return True  # leveled
        return False

    def _calc_level(self):
        xp = self.state["xp"]
        lvl = 1
        while xp >= self._xp_needed(lvl + 1):
            lvl += 1
        return lvl

    def _xp_needed(self, lvl):
        return int(50 * (lvl ** 1.8))

    # ---------------------------------------------------
    # SKILLS
    # ---------------------------------------------------
    def add_skill(self, skill):
        # max 5 skills
        skills = self.state["skills"]

        if len(skills) >= 5:
            skills.pop(0)

        skills.append(skill)

    # ---------------------------------------------------
    # COUNTERS
    # ---------------------------------------------------
    def count_win(self, boss=False, final=False):
        self.state["fights"] += 1

        if boss:
            self.state["boss_fights"] += 1
            self.state["boss_kills"] += 1

        if final:
            self.state["final_kills"] += 1

    def count_loss(self):
        self.state["fights"] += 1

    # ---------------------------------------------------
    # BOSS LOGIC
    # ---------------------------------------------------
    def should_spawn_boss(self):
        return (self.state["fights"] + 1) % 10 == 0

    def should_spawn_final(self):
        return self.state["boss_kills"] > 0 and self.state["boss_kills"] % 5 == 0