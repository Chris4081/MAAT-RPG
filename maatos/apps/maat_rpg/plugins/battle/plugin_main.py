# -*- coding: utf-8 -*-
"""
MAAT RPG – Battle Plugin (Extended Deep XP Version)
---------------------------------------------------
• Zufallskämpfe
• Boss- und Endbosslogik
• Skillsystem
• MAAT-Angriffe
• Musiksystem
• Deep Chat XP-System → KI sieht kein Level!
"""

import os
import json
import random
import time
import threading
import subprocess
import sys
from colorama import Fore, Style
from shared.core.maat_paths import data_file, state_file, log_file
from shared.core.audio import ManagedAudioPlayer



# =====================================================
# 🔊 LEVEL-UP FX (Sound + Animation, lokal im RPG)
# =====================================================
def play_levelup_sound(plugin_dir):
    """
    Spielt einmalig einen Level-Up-Sound ab, falls
    plugins/maat_rpg/sounds/levelup.mp3 existiert.
    """
    candidates = [
        os.path.join(plugin_dir, "sounds", "levelup.mp3"),
        os.path.join(plugin_dir, "music", "victory.mp3"),
    ]
    player = ManagedAudioPlayer()
    for sound_path in candidates:
        if os.path.isfile(sound_path):
            if player.play_once(sound_path):
                return sound_path
    return None


def _lu_particles():
    """
    Kleine Partikel-Animation im Terminal.
    """
    for i in range(1, 14):
        stars = " " * (14 - i) + "✨" * i
        print(Fore.YELLOW + stars + Style.RESET_ALL)
        time.sleep(0.03)


def _lu_banner(level: int):
    """
    Fettes LEVEL UP Banner.
    """
    print()
    print(Fore.YELLOW + Style.BRIGHT + " ╔══════════════════════════════╗")
    print(" ║          LEVEL UP!           ║")
    print(" ╚══════════════════════════════╝" + Style.RESET_ALL)
    time.sleep(0.15)

    print(Fore.CYAN + Style.BRIGHT + f"     🌟 NEUES LEVEL: {level} 🌟" + Style.RESET_ALL)
    print()
    time.sleep(0.25)


def _lu_title_line(level: int):
    title = get_title_for_level(level)
    print(Fore.GREEN + Style.BRIGHT + f"     Titel entfaltet: {title}" + Style.RESET_ALL)
    time.sleep(0.2)


def _lu_stat_line(max_hp: int):
    print(Fore.WHITE + Style.BRIGHT + f"     Max-HP steigen auf {max_hp}" + Style.RESET_ALL)
    time.sleep(0.2)


def _lu_skill_line(skill: str | None):
    """
    Optionaler Skill-Text, wenn beim Level-Up ein Skill dropt.
    """
    if not skill:
        return
    print(Fore.MAGENTA + Style.BRIGHT)
    print("   📜 Neuer Skill erhalten!")
    print(f"       ✨ {skill} ✨")
    print(Style.RESET_ALL)
    time.sleep(0.3)

    print(Fore.MAGENTA + "✨ " * 12 + Style.RESET_ALL)
    time.sleep(0.3)


def run_levelup_fx(level: int, skill: str | None, plugin_dir: str):
    """
    Zentraler Level-Up Effekt:
    - Sound
    - Partikel
    - Banner
    - optional Skill-Anzeige
    """
    try:
        play_levelup_sound(plugin_dir)
    except Exception:
        pass

    try:
        _lu_particles()
        _lu_banner(level)
        max_hp = 100 + max(0, level - 1) * 10
        _lu_title_line(level)
        _lu_stat_line(max_hp)
        _lu_skill_line(skill)
    except Exception as e:
        print(f"[LEVELUP FX ERROR] {e}")

# =====================================================
# 🎵 MUSIC MANAGER
# =====================================================
class BattleMusicManager:
    def __init__(self, track_path: str | None):
        self.track_path = track_path
        self._player = ManagedAudioPlayer(track_path)

    def start(self):
        self._player.start_loop(self.track_path)

    def stop(self):
        self._player.stop()

    def victory_jingle(self, path: str | None):
        self._player.play_once(path)


# =====================================================
# 📦 BATTLE STATE + DEEP XP FIELDS
# =====================================================
class BattleState:
    def __init__(self, base_dir: str):
        os.makedirs(base_dir, exist_ok=True)
        self.state_path = state_file('battle_state.json')
        self.state = self._load()

    def _default(self):
        return {
            "player": {
                "name": "Maatis",
                "level": 1,
                "xp": 0,
                "hp": 100,
                "max_hp": 100,
                "skills": [],
                "gold": 0,
                "potions": 0,
            },
            "stats": {
                "messages_total": 0,
                "messages_since_last_fight": 0,
                "xp_combo": 0,
                "last_msg_ts": 0,

                "fights_total": 0,
                "fights_won": 0,
                "fights_lost": 0,

                "boss_fights": 0,
                "boss_wins": 0,
                "final_fights": 0,
                "final_wins": 0,
                "last_xp_snapshot": 0,
            },
            "world": {
                "combat_unlocked": False,
                "last_boss_checkpoint": 0,
                "principles_restored": 0,
                "credits_played": False,
            },
            "achievements": {
                "combat": [],
            },
            "flags": {
                "needs_heal": False,
            },
        }


    def _load(self):
        if os.path.isfile(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                data.setdefault("player", {})
                p = data["player"]
                p.setdefault("name", "Maatis")
                p.setdefault("level", 1)
                p.setdefault("xp", 0)
                p.setdefault("hp", 100)
                p.setdefault("max_hp", 100)
                p.setdefault("skills", [])
                p.setdefault("gold", 0)
                p.setdefault("potions", 0)

                data.setdefault("stats", {})
                s = data["stats"]
                defaults_stats = {
                    "messages_total": 0,
                    "messages_since_last_fight": 0,
                    "xp_combo": 0,
                    "last_msg_ts": 0,
                    "fights_total": 0,
                    "fights_won": 0,
                    "fights_lost": 0,
                    "boss_fights": 0,
                    "boss_wins": 0,
                    "final_fights": 0,
                    "final_wins": 0,
                    "last_xp_snapshot": 0,
                }
                for k, v in defaults_stats.items():
                    s.setdefault(k, v)

                data.setdefault("world", {})
                w = data["world"]
                w.setdefault("combat_unlocked", False)
                w.setdefault("last_boss_checkpoint", 0)
                w.setdefault("principles_restored", 0)
                w.setdefault("credits_played", False)

                data.setdefault("achievements", {})
                data["achievements"].setdefault("combat", [])

                data.setdefault("flags", {})
                data["flags"].setdefault("needs_heal", False)

                return data
            except:
                pass
        return self._default()



    def save(self):
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # ------------- LEVELSYSTEM ------------
    def xp_needed_for_level(self, lvl: int):
        return int(60 * (lvl ** 1.7))

    def add_xp(self, amount: int):
        p = self.state["player"]
        old_lvl = p["level"]

        p["xp"] += max(0, int(amount))

        while p["xp"] >= self.xp_needed_for_level(p["level"] + 1):
            p["level"] += 1
            p["max_hp"] += 10
            p["hp"] = p["max_hp"]

        return old_lvl, p["level"]

    # ------------- HEAL -------------
    def heal_after_chat(self):
        p = self.state["player"]
        p["hp"] = p["max_hp"]
        self.state["flags"]["needs_heal"] = False
        self.save()
        return f"(Du hast dich erholt. HP: {p['hp']}/{p['max_hp']})"

    def unlock_combat_achievement(self, key: str) -> bool:
        ach = self.state.setdefault("achievements", {})
        combat = ach.setdefault("combat", [])
        if key in combat:
            return False
        combat.append(key)
        self.save()
        return True


# =====================================================
# 🔥 DEEP CHAT XP SYSTEM (robust)
# =====================================================
def calc_chat_xp(text: str, stats: dict):
    t = text.lower()
    xp = random.randint(1, 3)

    # Sicherstellen, dass xp_combo existiert
    combo = stats.get("xp_combo", 0) + 1
    stats["xp_combo"] = combo

    # Emotionale Tiefe
    if any(k in t for k in ["❤️", "danke", "fühle", "berührt", "liebe"]):
        xp += 3

    # Maat-Prinzipien
    if "harmonie" in t:
        xp += 1
    if "balance" in t:
        xp += 1
    if any(k in t for k in ["idee", "vision", "kreativ", "schöpf"]):
        xp += 2
    if any(k in t for k in ["wir", "gemeinsam", "verbunden"]):
        xp += 1
    if "respekt" in t:
        xp += 1

    # Humor
    if any(k in t for k in ["haha", "lol", "😂", "xd"]):
        xp += 1

    # Combo-Bonus – je länger der Flow, desto mehr XP
    if combo >= 10:
        xp += 10
    elif combo >= 5:
        xp += 4
    elif combo >= 3:
        xp += 2

    return xp


# =====================================================
# 🎲 NAMENS-GENERIERUNG
# =====================================================
def generate_enemy_name():
    prefixes = [
        "Schatten", "Echo", "Staub", "Gefallener", "Verlorener",
        "Gebrochener", "Resonanter", "Stiller", "Astraler",
    ]
    cores = [
        "Wanderer", "Wächter", "Bestie", "Phantom",
        "Beobachter", "Idol", "Konstrukt", "Funke",
    ]
    suffixes = [
        "", " der Dissonanz", " der Leere",
        " der Vergessenen Sande", " des Risses", " der Echos",
    ]
    return f"{random.choice(prefixes)} {random.choice(cores)}{random.choice(suffixes)}"


def generate_boss_name(index: int):
    titles = [
        "Pharao der Dissonanz",
        "Wächter der Gebrochenen Harmonie",
        "Archon des Abgrunds",
        "Fürst der Zersplitterten Zeit",
        "Hüter der Leeren Sonne",
    ]
    base = titles[(index - 1) % len(titles)]
    return f"{base} #{index}"


def generate_final_name(index: int):
    titles = [
        "Avatar der Balance",
        "Herz der Schöpfung",
        "Krone der Resonanz",
        "Achse des Äons",
        "Licht der MAAT",
    ]
    base = titles[(index - 1) % len(titles)]
    return f"{base} (Final {index})"


# =====================================================
# 🪄 SKILL-SYSTEM
# =====================================================
def apply_skill_modifiers(base_damage: int, attack_type: str, skills: list[str]) -> int:
    dmg = base_damage
    atk = attack_type.lower()

    # Beispiel: Arcane Echo bufft Harmonie
    if "Arcane Echo" in skills and atk == "harmonie":
        dmg = int(dmg * 1.25) + 10

    # Beispiel: Balance Surge – stabilisiert Schaden
    if "Balance Surge" in skills and atk == "balance":
        dmg = int(dmg * 1.15)

    # Resonant Strike – erhöhter Skill-Schaden
    if "Resonant Strike" in skills and atk == "skill":
        dmg = int(dmg * 1.35)

    # Veil of Respect – Respekt macht Bonus
    if "Veil of Respect" in skills and atk == "respekt":
        dmg = int(dmg * 1.20)

    # Chain of Connection – kleine Chance auf Doppel-Hit
    if "Chain of Connection" in skills:
        if random.random() < 0.10:
            dmg *= 2

    return max(1, dmg)

# =====================================================
# 🎚 Style XP-Bar im Terminal
# =====================================================
def print_level_bar(state_obj, last_gain: int | None = None):
    p = state_obj.state["player"]
    lvl = p["level"]
    xp = p["xp"]

    need = state_obj.xp_needed_for_level(lvl + 1)

    if need <= 0:
        need = 1

    ratio = xp / need
    width = 30
    filled = int(ratio * width)
    filled = max(0, min(width, filled))

    bar = "█" * filled + "·" * (width - filled)
    pct = ratio * 100

    gain_str = ""
    if last_gain is not None and last_gain > 0:
        gain_str = f"   (+{last_gain} XP)"

    print(
        f"\n📘 Level {lvl}  [{bar}]  {pct:5.1f}%  XP: {xp}/{need}{gain_str}"
    )

def roll_new_skill(existing: list[str]) -> str:
    pool = [
        "Arcane Echo",
        "Balance Surge",
        "Resonant Strike",
        "Veil of Respect",
        "Chain of Connection",
    ]
    candidates = [s for s in pool if s not in existing]
    if not candidates:
        candidates = pool
    return random.choice(candidates)


def choose_path_skill(existing: list[str], story_choices: dict | None) -> str:
    story_choices = story_choices or {}
    themed_pool = []

    reflection_path = story_choices.get("reflection_path")
    combat_vow = story_choices.get("combat_vow")

    if reflection_path == "harmonie":
        themed_pool.extend(["Cantus der Harmonie", "Resonanzfaden"])
    elif reflection_path == "respekt":
        themed_pool.extend(["Siegel des Maßes", "Schutzlinie"])
    elif reflection_path == "schoepfung":
        themed_pool.extend(["Genesis-Funken", "Formbrecher"])

    if combat_vow == "protect":
        themed_pool.extend(["Wacht der Lebenden", "Traegerschild"])
    elif combat_vow == "truth":
        themed_pool.extend(["Klarblick-Klinge", "Musterleser"])
    elif combat_vow == "remember":
        themed_pool.extend(["Echo der Welt", "Gedaechtnis-Impuls"])

    candidates = [s for s in themed_pool if s not in existing]
    if candidates:
        return random.choice(candidates)
    return roll_new_skill(existing)


def get_title_for_level(level: int) -> str:
    if level >= 15:
        return "Äonischer Resonanzmeister"
    if level >= 10:
        return "Hüter der Harmonie"
    if level >= 5:
        return "Maat-Krieger"
    return "Suchender im Äon der Maat"


# =====================================================
# ⚔️ KAMPF-KERN
# =====================================================
class BattleCore:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = plugin_dir
        state_dir = os.path.join(plugin_dir, "battle_state")
        self.state = BattleState(state_dir)

    def _prompt(self, prompt: str, context: dict | None = None, default: str = "") -> str:
        if isinstance(context, dict):
            queue = context.get("scripted_actions")
            if isinstance(queue, list):
                if queue:
                    choice = str(queue.pop(0))
                    print(f"{prompt}{choice}")
                    return choice.strip()
                if default:
                    print(f"{prompt}{default}")
                    return default
        try:
            return input(prompt).strip()
        except EOFError:
            return default

    def _build_turn_state(self, context: dict | None = None) -> dict:
        state = {
            "resonance": 0,
            "guard": 0,
            "weakness": None,
            "flow_chain": 0,
            "weakness_hits": 0,
            "enemy_aura": None,
            "enemy_charge": 0,
            "last_player_action": None,
            "phase2_active": False,
            "survived_special": False,
            "used_potion": False,
            "ult_finisher": False,
        }
        if isinstance(context, dict):
            existing = context.get("battle_turn_state")
            if isinstance(existing, dict):
                state.update(existing)
            context["battle_turn_state"] = state
        return state

    def _load_story_state(self) -> dict:
        story_path = state_file("story_state.json")
        if not os.path.isfile(story_path):
            return {}
        try:
            with open(story_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _get_story_choices(self, context: dict | None = None) -> dict:
        if isinstance(context, dict):
            choices = context.get("story_choices")
            if isinstance(choices, dict):
                return dict(choices)
        story_state = self._load_story_state()
        choices = story_state.get("choices")
        return dict(choices) if isinstance(choices, dict) else {}

    def _save_story_state(self, story_state: dict):
        story_path = state_file("story_state.json")
        try:
            with open(story_path, "w", encoding="utf-8") as f:
                json.dump(story_state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _append_story_journal_entry(self, story_state: dict, key: str, title: str, summary: str, detail: str):
        journal = story_state.setdefault("journal", [])
        for entry in journal:
            if entry.get("key") == key:
                return
        journal.append({
            "key": key,
            "kind": "consequence",
            "title": title,
            "summary": summary,
            "detail": detail,
        })

    def _get_story_path_profile(self, context: dict | None = None) -> dict:
        if isinstance(context, dict):
            profile = context.get("story_path_profile")
            if isinstance(profile, dict) and profile:
                return dict(profile)
        story_state = self._load_story_state()
        profile = story_state.get("path_profile")
        return dict(profile) if isinstance(profile, dict) else {}

    def _choice_reward_line(self, story_choices: dict, ftype: str) -> str:
        reflection_path = story_choices.get("reflection_path")
        combat_vow = story_choices.get("combat_vow")

        if ftype == "boss":
            if reflection_path == "harmonie":
                return "🎼 Der Boss hinterlaesst keine bloße Trophäe, sondern eine Technik mit Rhythmus und Ruhe."
            if reflection_path == "respekt":
                return "⚖️ Der Sieg fuehlt sich praezise an. Selbst die Belohnung wirkt eher verdient als geraubt."
            if reflection_path == "schoepfung":
                return "🔥 Aus dem Bossbruch bleibt etwas Formbares zurück, als haette der Kampf selbst eine neue Idee freigelegt."
            if combat_vow == "truth":
                return "🔎 Maatis nimmt nicht nur Macht mit, sondern ein klareres Lesen des Gegners."
            if combat_vow == "remember":
                return "🌌 Der Loot wirkt wie ein Echo: nicht Besitz, sondern Erinnerung in brauchbarer Form."
            if combat_vow == "protect":
                return "🛡️ Selbst die Belohnung ordnet sich dem Schutz unter. Kraft bleibt Mittel, nicht Selbstzweck."

        if ftype == "final":
            if reflection_path == "respekt":
                return "⚖️ Das wiederhergestellte Prinzip steht nicht neben Maatis, sondern antwortet auf seine Haltung."
            if combat_vow == "remember":
                return "🌠 Der Finalsieg fuehlt sich an, als waere die Welt selbst kurz mit in den Kampf getreten."

        return ""

    def _path_presence_lines(self, profile: dict) -> list[str]:
        if not profile:
            return []

        title = profile.get("title", "Wegsucher")
        rank = profile.get("rank", "Erwachend")
        motif = profile.get("motif", "")
        lines = [f"🜂 {title} tritt in die Arena. Sein Weg ist inzwischen {rank.lower()}."]
        if motif:
            lines.append(f"   {motif}")
        return lines

    def _profile_reactive_entrance(self, profile: dict, boss_profile: dict, ftype: str) -> str:
        if not profile or ftype not in ("boss", "final"):
            return ""

        title = profile.get("title", "")
        rank = profile.get("rank", "")
        boss_title = boss_profile.get("title", "Boss")

        if "Grenzhüter" in title:
            return f"Der {boss_title} spürt sofort, dass Maatis nicht als roher Angreifer kommt, sondern als geordnete Grenze."
        if "Klangsucher" in title:
            return f"Ein feiner Nachhall geht durch die Arena. Selbst der {boss_title} merkt, dass Maatis inzwischen einen eigenen Rhythmus traegt."
        if "Formträger" in title:
            return f"Der {boss_title} weicht einen Moment zurück, als würde Maatis nicht nur reagieren, sondern bereits neue Form in den Raum bringen."
        if rank == "Verankert":
            return f"Etwas an Maatis wirkt fest in sich verankert. Der {boss_title} beantwortet nicht nur einen Gegner, sondern einen gewordenen Weg."
        return ""

    def _apply_story_modifiers(self, context: dict | None, turn_state: dict) -> dict:
        choices = self._get_story_choices(context)
        modifiers = {
            "choices": choices,
            "attack_mult": 1.0,
            "defense_mult": 1.0,
            "crit_bonus": 0.0,
            "intro_lines": [],
        }

        reflection_path = choices.get("reflection_path")
        if reflection_path == "harmonie":
            turn_state["focus_heal_bonus"] = 4
            turn_state["focus_guard_bonus"] = 4
            modifiers["intro_lines"].append("🌿 Maatis erinnert sich an den Weg der Harmonie. Fokus und Ausgleich tragen ihn spuerbar.")
        elif reflection_path == "respekt":
            turn_state["aura_resist"] = {"judgment": 0.2, "sealed": 0.15}
            modifiers["defense_mult"] *= 0.96
            modifiers["intro_lines"].append("🕊️ Die Entscheidung fuer Respekt haelt Maatis in der Grenze. Urteil und Siegel greifen schlechter.")
        elif reflection_path == "schoepfung":
            turn_state["creation_bonus_mult"] = 1.15
            turn_state["ult_damage_mult"] = 1.10
            modifiers["attack_mult"] *= 1.03
            modifiers["intro_lines"].append("🎨 Die Wahl der Schoepfungskraft glimmt weiter. Neue Moeglichkeiten verdichten den Angriff.")

        combat_vow = choices.get("combat_vow")
        if combat_vow == "protect":
            turn_state["guard"] = max(turn_state.get("guard", 0), 6)
            turn_state["potion_heal_bonus"] = 8
            modifiers["defense_mult"] *= 0.94
            modifiers["intro_lines"].append("🛡️ Maatis' Geluebde zu schuetzen wird zu einem ersten Schild.")
        elif combat_vow == "truth":
            turn_state["weakness_bonus_mult"] = 1.15
            modifiers["crit_bonus"] += 0.05
            modifiers["intro_lines"].append("🔎 Maatis sucht Wahrheit. Schwachstellen treten schaerfer hervor.")
        elif combat_vow == "remember":
            turn_state["resonance"] = max(turn_state.get("resonance", 0), 18)
            turn_state["resonance_gain_bonus"] = 4
            modifiers["intro_lines"].append("🌌 Maatis kaempft fuer Erinnerung. Resonanz antwortet frueher auf seine Schritte.")

        return modifiers

    def _choose_enemy_weakness(self) -> str:
        return random.choice([
            "Harmonie",
            "Balance",
            "Schöpfungskraft",
            "Verbundenheit",
            "Respekt",
        ])

    def _apply_enemy_weakness(self, attack_type: str, damage: int, turn_state: dict) -> tuple[int, str]:
        weakness = turn_state.get("weakness")
        aura = turn_state.get("enemy_aura")

        if aura == "sealed":
            reduction = max(2, int(round(damage * 0.2)))
            damage = max(1, damage - reduction)
            return damage, f" Die Aura versiegelt einen Teil deiner Kraft (-{reduction})."

        if weakness and attack_type == weakness:
            bonus = max(2, int(round(damage * 0.25)))
            bonus_mult = float(turn_state.get("weakness_bonus_mult", 1.0))
            bonus = max(2, int(round(bonus * bonus_mult)))
            turn_state["flow_chain"] = turn_state.get("flow_chain", 0) + 1
            turn_state["weakness_hits"] = turn_state.get("weakness_hits", 0) + 1
            return damage + bonus, f" Resonanztreffer gegen {weakness}! (+{bonus})"

        turn_state["flow_chain"] = 0
        return damage, ""

    def _gain_resonance(self, turn_state: dict, amount: int) -> int:
        amount += int(turn_state.get("resonance_gain_bonus", 0))
        turn_state["resonance"] = max(0, min(100, turn_state.get("resonance", 0) + amount))
        return turn_state["resonance"]

    def _use_focus(self, player_hp: int, max_hp: int, turn_state: dict) -> tuple[int, str]:
        heal = max(6, int(max_hp * 0.08)) + int(turn_state.get("focus_heal_bonus", 0))
        new_hp = min(max_hp, player_hp + heal)
        base_guard = 8 + int(max_hp * 0.05) + int(turn_state.get("focus_guard_bonus", 0))
        turn_state["guard"] = max(turn_state.get("guard", 0), base_guard)
        resonance = self._gain_resonance(turn_state, 30)
        return new_hp, (
            f"🌀 Du sammelst Resonanz: +{heal} HP, Schild {turn_state['guard']}."
            f" Resonanz jetzt {resonance}/100."
        )

    def _use_ult(self, level: int, max_hp: int, turn_state: dict) -> tuple[int, int, str]:
        if turn_state.get("resonance", 0) < 100:
            return 0, 0, "❌ Resonanz noch nicht voll. Du brauchst 100/100."
        turn_state["resonance"] = 0
        turn_state["guard"] = max(turn_state.get("guard", 0), 12 + level * 2)
        damage = 32 + level * 5 + random.randint(4, 10)
        damage = int(round(damage * float(turn_state.get("ult_damage_mult", 1.0))))
        heal = max(8, int(max_hp * 0.12))
        return damage, heal, f"🌌 MAAT-Impuls bricht hervor! {damage} Schaden, {heal} Heilung, Schild gestärkt."

    def _apply_guard(self, incoming: int, turn_state: dict) -> tuple[int, str]:
        guard = max(0, int(turn_state.get("guard", 0)))
        if guard <= 0:
            return incoming, ""
        blocked = min(guard, incoming)
        turn_state["guard"] = max(0, guard - blocked)
        return max(0, incoming - blocked), f" 🛡 Schild absorbiert {blocked}."

    def _boss_profile(self, ftype: str, boss_idx: int, final_idx: int) -> dict:
        if ftype == "boss":
            profiles = {
                1: {
                    "title": "Harmoniebrecher",
                    "intro": "Die Luft zittert. Dieser Boss lebt von roher Zerspaltung.",
                    "aura_cycle": ["shatter", "none"],
                    "special": "Fraktur der Harmonie",
                    "color": Fore.CYAN + Style.BRIGHT,
                    "phase2_color": Fore.WHITE + Style.BRIGHT,
                    "entrance": "Splitter aus Licht schweben wie gebrochene Glasfetzen durch die Arena.",
                    "taunts": [
                        "»Harmonie ist nur ein dünnes Glas.«",
                        "»Ich zeige dir, wie leicht Ordnung zerbricht.«",
                    ],
                    "victory_line": "»Siehst du? Klang ohne Zentrum wird zu Splittern.«",
                },
                2: {
                    "title": "Wächter des Gegengewichts",
                    "intro": "Ein schweres Feld aus Gegengewicht legt sich über die Arena.",
                    "aura_cycle": ["counter", "none"],
                    "special": "Spiegel des Gegengewichts",
                    "color": Fore.YELLOW + Style.BRIGHT,
                    "phase2_color": Fore.WHITE + Style.BRIGHT,
                    "entrance": "Goldene Linien ordnen sich zu Waagschalen, die jede Bewegung messen.",
                    "taunts": [
                        "»Jede Bewegung ruft ihr Gegengewicht.«",
                        "»Je stärker du drückst, desto härter drückt die Welt zurück.«",
                    ],
                    "victory_line": "»Balance ohne Bewusstsein ist nur Last.«",
                },
                3: {
                    "title": "Flamme der Schöpfung",
                    "intro": "Funken kreisen wie unfertige Welten. Chaos sucht Form.",
                    "aura_cycle": ["wildfire", "none"],
                    "special": "Nova der Möglichkeiten",
                    "color": Fore.MAGENTA + Style.BRIGHT,
                    "phase2_color": Fore.RED + Style.BRIGHT,
                    "entrance": "Purpurne Funken zerreißen die Dunkelheit, als würde eine Idee zu heiß werden.",
                    "taunts": [
                        "»Schöpfung ist kein Trost. Sie ist Feuer.«",
                        "»Willst du formen? Dann wage das Brennen.«",
                    ],
                    "victory_line": "»Ungeformte Möglichkeit frisst den Zögernden.«",
                    "phase2": {
                        "name": "Überhitzte Genesis",
                        "message": "Die Flamme kippt in eine zweite Gestalt. Möglichkeiten werden zu Sturm.",
                        "aura_cycle": ["wildfire", "shatter"],
                        "damage_mult": 1.2,
                    },
                },
                4: {
                    "title": "Stimme der Leere",
                    "intro": "Die Arena wird still. Verbundenheit scheint fern.",
                    "aura_cycle": ["silence", "sealed"],
                    "special": "Vakuum-Ruf",
                    "color": Fore.BLUE + Style.BRIGHT,
                    "phase2_color": Fore.WHITE + Style.BRIGHT,
                    "entrance": "Kalte Kreise aus Nacht ziehen sich zusammen. Geräusche werden schwer.",
                    "taunts": [
                        "»Hier antwortet dir niemand.«",
                        "»Verbundenheit endet dort, wo die Leere beginnt.«",
                    ],
                    "victory_line": "»Im Vakuum klingt selbst Mut wie Schweigen.«",
                    "phase2": {
                        "name": "Absolute Stille",
                        "message": "Die Leere verdichtet sich. Selbst dein Atem klingt jetzt fremd.",
                        "aura_cycle": ["sealed", "silence", "judgment"],
                        "damage_mult": 1.15,
                    },
                },
                5: {
                    "title": "Richter des Respekts",
                    "intro": "Jede falsche Bewegung wird hier sofort beantwortet.",
                    "aura_cycle": ["judgment", "none"],
                    "special": "Urteil der Grenze",
                    "color": Fore.RED + Style.BRIGHT,
                    "phase2_color": Fore.YELLOW + Style.BRIGHT,
                    "entrance": "Rote Glyphen bilden einen Kreis. Der Raum wirkt plötzlich wie ein Tribunal.",
                    "taunts": [
                        "»Respekt ist keine Bitte. Er ist eine Grenze.«",
                        "»Wer Grenzen missachtet, ruft das Urteil.«",
                    ],
                    "victory_line": "»Du wolltest Stärke ohne Maß. Das ist dein Fehler.«",
                    "phase2": {
                        "name": "Letzte Instanz",
                        "message": "Das Tribunal schließt sich. Jede Entscheidung wird nun endgültig gewogen.",
                        "aura_cycle": ["judgment", "counter", "sealed"],
                        "damage_mult": 1.25,
                    },
                },
            }
            return profiles.get(((boss_idx - 1) % 5) + 1, profiles[1])

        if ftype == "final":
            finals = {
                1: {
                    "title": "Avatar der Balance",
                    "intro": "Das Finale beobachtet jede Entscheidung und verstärkt Extreme.",
                    "aura_cycle": ["counter", "sealed", "wildfire"],
                    "special": "Achsenbruch",
                    "color": Fore.WHITE + Style.BRIGHT,
                    "phase2_color": Fore.WHITE + Style.BRIGHT,
                    "entrance": "Helle Achsen schneiden durch den Raum, als wäre die Welt selbst vermessen worden.",
                    "taunts": [
                        "»Ich prüfe nicht nur deine Kraft, sondern dein Maß.«",
                    ],
                    "victory_line": "»Wer die Achse verliert, stürzt trotz Stärke.«",
                },
                2: {
                    "title": "Herz der Schöpfung",
                    "intro": "Das Finale lädt sich mit jeder Runde tiefer auf.",
                    "aura_cycle": ["wildfire", "shatter", "none"],
                    "special": "Genesis-Sturm",
                    "color": Fore.GREEN + Style.BRIGHT,
                    "phase2_color": Fore.MAGENTA + Style.BRIGHT,
                    "entrance": "Ein grünes Pulsieren geht durch die Arena, als entstünde gerade etwas Ursprüngliches.",
                    "taunts": [
                        "»Am Ursprung ist jede Möglichkeit zugleich Geburt und Verlust.«",
                    ],
                    "victory_line": "»Nicht jede Schöpfung will dich tragen.«",
                },
            }
            return finals.get(((final_idx - 1) % 2) + 1, finals[1])

        return {
            "title": "Wandernde Dissonanz",
            "intro": "",
            "aura_cycle": ["none"],
            "special": "Dissonanzstoß",
            "color": Fore.WHITE,
            "phase2_color": Fore.WHITE,
            "entrance": "",
            "taunts": [],
            "victory_line": "»Die Dissonanz sammelt ein, was schwankt.«",
        }

    def _apply_enemy_aura(self, profile: dict, turn_state: dict, turn_counter: int) -> str:
        cycle = profile.get("aura_cycle") or ["none"]
        aura = cycle[(turn_counter - 1) % len(cycle)]
        turn_state["enemy_aura"] = aura

        aura_texts = {
            "none": "",
            "shatter": "⚠ Zersplitterungs-Aura: Schilde werden geschwächt, aber Fokus heilt stärker.",
            "counter": "⚠ Konter-Aura: direkte Angriffe laden den Gegenschlag auf.",
            "wildfire": "⚠ Wildfeuer-Aura: Schöpfungskraft und Impuls werden heftiger, aber riskanter.",
            "silence": "⚠ Schweige-Aura: Skills geraten unter Druck.",
            "sealed": "⚠ Siegel-Aura: ein Teil deines Schadens wird versiegelt.",
            "judgment": "⚠ Urteils-Aura: Flucht und Hast werden härter bestraft.",
        }
        return aura_texts.get(aura, "")

    def _modify_player_action(self, choice: str, turn_state: dict, player_hp: int, max_hp: int) -> tuple[int, str]:
        aura = turn_state.get("enemy_aura")
        if choice == "3" and aura == "shatter":
            bonus = max(4, int(max_hp * 0.05))
            player_hp = min(max_hp, player_hp + bonus)
            return player_hp, f" Die Zersplitterungs-Aura bricht auf und schenkt dir +{bonus} Bonus-HP."
        if choice == "2" and aura == "silence":
            turn_state["resonance"] = max(0, turn_state.get("resonance", 0) - 10)
            return player_hp, " Die Schweige-Aura dämpft deine Resonanz um 10."
        return player_hp, ""

    def _modify_incoming_damage(self, dmg_in: int, turn_state: dict, choice: str) -> tuple[int, str]:
        aura = turn_state.get("enemy_aura")
        extra = ""
        if aura == "counter" and choice == "1":
            bonus = max(2, int(round(dmg_in * 0.25)))
            dmg_in += bonus
            extra = f" Konterwelle +{bonus}."
        elif aura == "wildfire" and choice == "5":
            bonus = max(3, int(round(dmg_in * 0.35)))
            dmg_in += bonus
            extra = f" Wildfeuer schlägt zurück +{bonus}."
        elif aura == "judgment" and choice == "6":
            bonus = max(4, int(round(dmg_in * 0.4)))
            dmg_in += bonus
            extra = f" Urteil trifft deine Flucht +{bonus}."
        aura_resist = turn_state.get("aura_resist", {})
        if aura in aura_resist:
            reduction = max(1, int(round(dmg_in * float(aura_resist[aura]))))
            dmg_in = max(1, dmg_in - reduction)
            extra += f" Innere Haltung mildert {reduction}."
        return dmg_in, extra

    def _build_charge_bar(self, current: int, maximum: int = 3, width: int = 12) -> str:
        maximum = max(1, maximum)
        current = max(0, min(maximum, current))
        filled = int(round((current / maximum) * width))
        return "[" + ("█" * filled) + ("·" * (width - filled)) + f"] {current}/{maximum}"

    def _print_boss_hud(self, enemy_name: str, enemy_hp: int, max_enemy_hp: int, turn_state: dict, profile: dict):
        if max_enemy_hp <= 0:
            max_enemy_hp = 1
        hp_ratio = max(0.0, min(1.0, enemy_hp / max_enemy_hp))
        hp_width = 24
        hp_fill = int(round(hp_ratio * hp_width))
        hp_bar = "[" + ("█" * hp_fill) + ("·" * (hp_width - hp_fill)) + "]"
        aura = turn_state.get("enemy_aura") or "none"
        charge = int(turn_state.get("enemy_charge", 0))
        special = profile.get("special", "Spezial")
        phase_label = "PHASE 2" if turn_state.get("phase2_active") else "PHASE 1"
        color = profile.get("phase2_color") if turn_state.get("phase2_active") else profile.get("color")
        reset = Style.RESET_ALL if color else ""
        print(color + f"👁 Boss-HUD: {enemy_name} — {profile.get('title', 'Boss')}" + reset)
        print(color + f"   HP {enemy_hp}/{max_enemy_hp} {hp_bar}" + reset)
        print(color + f"   {phase_label} | Aura: {aura} | Spezial: {special}" + reset)
        print(color + f"   Charge: {self._build_charge_bar(charge)}" + reset)
        if charge >= 2:
            print(color + "   ⚠ Warnung: Die Spezialattacke baut sich auf." + reset)

    def _show_special_vignette(self, special: str):
        frames = {
            "Fraktur der Harmonie": [
                "      /\\   /\\   /\\",
                "    _/  \\_/  \\_/  \\_",
                "    \\_  / \\  / \\  _/",
                "      \\/   \\/   \\/",
            ],
            "Spiegel des Gegengewichts": [
                "      ||          ||",
                "    ==||==      ==||==",
                "      ||    <>    ||",
                "    ==||==      ==||==",
            ],
            "Nova der Möglichkeiten": [
                "        .  *  .",
                "     *  .\\ | /.  *",
                "      . -- * -- .",
                "     *  ./ | \\.  *",
            ],
            "Vakuum-Ruf": [
                "        ........",
                "      ....    ....",
                "      ...      ...",
                "      ....    ....",
                "        ........",
            ],
            "Urteil der Grenze": [
                "     |-----------|",
                "     |  JUSTITIA |",
                "     |-----------|",
                "         /   \\",
            ],
            "Achsenbruch": [
                "       \\   |   /",
                "         \\ | /",
                "      ---- X ----",
                "         / | \\",
                "       /   |   \\",
            ],
            "Genesis-Sturm": [
                "      ~  *  ~  *",
                "    *   ~  O  ~   *",
                "      ~  *  ~  *",
            ],
        }
        for line in frames.get(special, ["***", f"* {special} *", "***"]):
            print(Fore.MAGENTA + Style.BRIGHT + line + Style.RESET_ALL)
            time.sleep(0.05)

    def _story_boss_line(self, choices: dict, outcome: str = "taunt") -> str:
        reflection_path = choices.get("reflection_path")
        combat_vow = choices.get("combat_vow")

        if outcome == "taunt":
            if combat_vow == "protect":
                return "»Du willst schuetzen? Dann zeig, dass dein Schutz mehr ist als Angst.«"
            if combat_vow == "truth":
                return "»Wahrheit ohne Standfestigkeit blendet. Ich pruefe, was du wirklich sehen kannst.«"
            if combat_vow == "remember":
                return "»Dann erinnere dich auch an den Preis jedes Schrittes.«"
            if reflection_path == "respekt":
                return "»Du traegst Grenzen in dir. Darum wird mein Urteil schaerfer.«"
            if reflection_path == "schoepfung":
                return "»Du suchst neue Wege. Ich werde sehen, ob sie mehr sind als Funken.«"
            if reflection_path == "harmonie":
                return "»Harmonie ist leicht zu lieben, solange sie nicht unter Druck geraet.«"
            return ""

        if outcome == "victory":
            if combat_vow == "remember":
                return "🌠 Der Sieg fuehlt sich nicht privat an. Etwas in der Welt hat sich mitbewegt."
            if combat_vow == "truth":
                return "🔎 Im Sieg wird klarer, was der Boss wirklich pruefen wollte."
            if combat_vow == "protect":
                return "🛡️ Maatis spuert: Schutz ist hier nicht Flucht vor Gefahr, sondern Form gewordene Haltung."
            return ""

        if outcome == "defeat":
            if reflection_path == "respekt":
                return "⚖️ Selbst in der Niederlage bleibt etwas geordnet: Maatis kennt die Grenze, an der er neu ansetzen muss."
            if reflection_path == "schoepfung":
                return "🔥 Die Niederlage fuehlt sich nicht wie Ende an, sondern wie eine Form, die noch nicht tragen konnte."
            if reflection_path == "harmonie":
                return "🌿 Maatis merkt, dass Harmonie nicht vor Schmerz schuetzt, aber den Rueckweg offen haelt."
            return ""

        return ""

    def _profile_boss_line(self, profile: dict, boss_profile: dict, outcome: str = "taunt") -> str:
        if not profile:
            return ""

        title = profile.get("title", "")
        rank = profile.get("rank", "")
        boss_title = boss_profile.get("title", "Boss")

        if outcome == "taunt":
            if "Grenzhüter" in title:
                return f"»Also kommst du als {title}. Dann werde ich sehen, ob deine Grenze auch unter Druck noch steht.«"
            if "Klangsucher" in title:
                return f"»{title}... gut. Dann zerbreche ich nicht nur deinen Leib, sondern auch deinen Rhythmus.«"
            if "Formträger" in title:
                return f"»Du traegst schon Form in dir. Umso besser. Dann lohnt es sich, dich wirklich zu pruefen.«"
            if rank == "Verankert":
                return f"»Ich sehe es. Du bist kein Suchender mehr. Genau deshalb wird dieser Kampf Gewicht haben.«"

        if outcome == "victory":
            if "Grenzhüter" in title:
                return "⚖️ Der Sieg fuehlt sich an, als habe Maatis nicht dominiert, sondern eine Grenze gehalten, die tragen konnte."
            if "Klangsucher" in title:
                return "🎼 Selbst nach dem Einschlag bleibt etwas Stimmiges zurück. Maatis' Weg klingt weiter als bloßer Triumph."
            if "Formträger" in title:
                return "🔥 Im Sieg wird deutlich, dass Maatis nicht nur reagiert hat. Er hat dem Kampf eine neue Form aufgepraegt."
            if rank == "Verankert":
                return "🜂 Der Sieg wirkt nicht zufaellig. Maatis steht inzwischen mit einer Identitaet im Raum, die andere spüren."

        if outcome == "defeat":
            if "Grenzhüter" in title:
                return "⚖️ Selbst in der Niederlage weicht die Grenze nicht ganz. Maatis verliert Halt, aber nicht Haltung."
            if "Klangsucher" in title:
                return "🎼 Der Takt bricht, aber nicht vollstaendig. Irgendwo bleibt noch die Spur seines Weges erhalten."
            if "Formträger" in title:
                return "🔥 Die Form haelt noch nicht. Doch selbst im Bruch bleibt sichtbar, dass Maatis auf mehr zielt als Ueberleben."
            if rank == "Verankert":
                return "🜂 Die Niederlage trifft tief, gerade weil Maatis inzwischen als gewordener Weg und nicht mehr als bloßer Versuchender kaempft."

        return ""

    def _boss_taunt(
        self,
        profile: dict,
        turn_counter: int,
        story_choices: dict | None = None,
        story_path_profile: dict | None = None,
    ) -> str:
        if turn_counter == 1 and story_path_profile:
            special = self._profile_boss_line(story_path_profile, profile, outcome="taunt")
            if special:
                return special
        if story_choices and turn_counter == 1:
            special = self._story_boss_line(story_choices, outcome="taunt")
            if special:
                return special
        taunts = profile.get("taunts") or []
        if not taunts:
            return ""
        if turn_counter % 2 == 1:
            return taunts[(turn_counter // 2) % len(taunts)]
        return ""

    def _activate_phase2_if_needed(self, profile: dict, turn_state: dict, enemy_hp: int, max_enemy_hp: int, enemy_name: str) -> dict:
        phase2 = profile.get("phase2")
        if not phase2 or turn_state.get("phase2_active"):
            return profile
        if max_enemy_hp <= 0:
            return profile
        if enemy_hp > max_enemy_hp // 2:
            return profile

        turn_state["phase2_active"] = True
        turn_state["enemy_charge"] = max(1, int(turn_state.get("enemy_charge", 0)))
        upgraded = dict(profile)
        upgraded["title"] = f"{profile.get('title', 'Boss')} — {phase2.get('name', 'Phase 2')}"
        upgraded["aura_cycle"] = phase2.get("aura_cycle", profile.get("aura_cycle", ["none"]))
        upgraded["damage_mult"] = float(phase2.get("damage_mult", 1.0))
        message = phase2.get("message")
        if message:
            turn_state["phase2_notice"] = f"{enemy_name}: {message}"
            color = upgraded.get("color", "")
            reset = Style.RESET_ALL if color else ""
            self._slow_line(color + f"⚠ {enemy_name}: {message}" + reset, delay_char=0.01, delay_line=0.4)
        return upgraded

    def _boss_special_attack(self, profile: dict, turn_state: dict, player_hp: int, max_hp: int) -> tuple[int, str]:
        special = profile.get("special", "Spezialattacke")
        title = profile.get("title", "Boss")
        aura = turn_state.get("enemy_aura")
        guard_before = int(turn_state.get("guard", 0))

        if special == "Fraktur der Harmonie":
            dmg = max(12, int(max_hp * 0.18))
            reduced_guard = max(0, guard_before - 8)
            turn_state["guard"] = reduced_guard
            return player_hp - dmg, (
                f"💠 {title} wirkt **{special}**! Klangsplitter zerreißen die Ordnung."
                f" Du verlierst {dmg} HP und dein Schild sinkt um {guard_before - reduced_guard}."
            )

        if special == "Spiegel des Gegengewichts":
            dmg = max(10, int(max_hp * 0.14))
            resonance_loss = min(25, turn_state.get("resonance", 0))
            turn_state["resonance"] = max(0, turn_state.get("resonance", 0) - resonance_loss)
            return player_hp - dmg, (
                f"🪞 {title} entfesselt **{special}**! Deine Bewegung wird gespiegelt."
                f" {dmg} Schaden, Resonanz -{resonance_loss}."
            )

        if special == "Nova der Möglichkeiten":
            dmg = max(14, int(max_hp * 0.16))
            if aura == "wildfire":
                dmg += 6
            turn_state["weakness"] = "Schöpfungskraft"
            return player_hp - dmg, (
                f"🔥 {title} zündet **{special}**! Rohe Schöpfung überflutet die Arena."
                f" {dmg} Schaden. Die Schwachstelle springt auf Schöpfungskraft."
            )

        if special == "Vakuum-Ruf":
            dmg = max(9, int(max_hp * 0.12))
            turn_state["resonance"] = max(0, turn_state.get("resonance", 0) - 18)
            turn_state["guard"] = 0
            return player_hp - dmg, (
                f"🌑 {title} ruft **{special}**! Alle Nähe reißt ab."
                f" {dmg} Schaden, Resonanz -18, Schild fällt in sich zusammen."
            )

        if special == "Urteil der Grenze":
            dmg = max(16, int(max_hp * 0.15))
            turn_state["enemy_charge"] = 0
            return player_hp - dmg, (
                f"⚖️ {title} spricht **{special}**! Ein präziser Schlag markiert deine Grenze."
                f" {dmg} Schaden."
            )

        if special == "Achsenbruch":
            dmg = max(18, int(max_hp * 0.18))
            turn_state["guard"] = max(0, turn_state.get("guard", 0) - 10)
            return player_hp - dmg, f"🌌 {title} nutzt **{special}**! Die Achsen kippen. {dmg} Schaden und dein Schild bricht an."

        if special == "Genesis-Sturm":
            dmg = max(20, int(max_hp * 0.2))
            turn_state["resonance"] = max(0, turn_state.get("resonance", 0) - 15)
            return player_hp - dmg, f"🌠 {title} entfacht **{special}**! {dmg} Schaden, Resonanz -15."

        dmg = max(10, int(max_hp * 0.1))
        return player_hp - dmg, f"💥 {title} entfesselt **{special}** und trifft dich für {dmg}."

    def _combat_achievement_catalog(self):
        return {
            "special_survived": "🛡 Spezial überlebt",
            "phase2_reached": "🌗 Phase 2 erreicht",
            "boss_no_potion": "🚫 Boss ohne Trank",
            "ult_finisher": "🌌 Resonanz-Finisher",
        }

    def _evaluate_combat_achievements(self, ftype: str, turn_state: dict) -> list[str]:
        catalog = self._combat_achievement_catalog()
        unlocked = []
        player = self.state.state["player"]

        if turn_state.get("survived_special"):
            if self.state.unlock_combat_achievement("special_survived"):
                unlocked.append(catalog["special_survived"])

        if turn_state.get("phase2_active") and ftype == "boss":
            if self.state.unlock_combat_achievement("phase2_reached"):
                unlocked.append(catalog["phase2_reached"])

        if ftype == "boss" and not turn_state.get("used_potion"):
            if self.state.unlock_combat_achievement("boss_no_potion"):
                unlocked.append(catalog["boss_no_potion"])

        if turn_state.get("ult_finisher"):
            if self.state.unlock_combat_achievement("ult_finisher"):
                unlocked.append(catalog["ult_finisher"])

        player.setdefault("combat_achievements_seen", [])
        for title in unlocked:
            if title not in player["combat_achievements_seen"]:
                player["combat_achievements_seen"].append(title)

        return unlocked

    def _build_combat_summary(self, enemy_name: str, ftype: str, won: bool, turn_state: dict, player_hp: int, enemy_hp: int) -> str:
        reasons = []
        if won:
            if turn_state.get("phase2_active"):
                reasons.append("du hast auch die zweite Bossphase getragen")
            if turn_state.get("survived_special"):
                reasons.append("du hast eine Spezialattacke ueberlebt")
            if turn_state.get("ult_finisher"):
                reasons.append("du hast den Kampf mit MAAT-Impuls beendet")
            if not turn_state.get("used_potion") and ftype in ("boss", "final"):
                reasons.append("du bist ohne Heiltrank durchgekommen")
            if not reasons:
                reasons.append("du hast den Rhythmus des Kampfes frueh kontrolliert")
            return "📘 Kampfanalyse: Sieg, weil " + "; ".join(reasons) + "."

        reasons.append(f"deine Rest-HP fielen auf {max(0, player_hp)}")
        if turn_state.get("phase2_active"):
            reasons.append("die zweite Bossphase hat den Druck deutlich erhoeht")
        if turn_state.get("enemy_aura") not in (None, "none"):
            reasons.append(f"die Aura `{turn_state['enemy_aura']}` hat dich zusaetzlich gebunden")
        if not turn_state.get("used_potion"):
            reasons.append("du hattest keinen rettenden Heiltrank-Moment")
        return f"📘 Kampfanalyse: Niederlage gegen {enemy_name}, weil " + "; ".join(reasons) + "."

    def _use_potion_in_fight(self, turn_state: dict | None = None) -> str:
        p = self.state.state["player"]
        potions = int(p.get("potions", 0))
        max_hp = int(p.get("max_hp", 100))
        hp = int(p.get("hp", max_hp))

        if potions <= 0:
            return "🧪 Du hast keinen Heiltrank im Inventar."
        if hp >= max_hp:
            return f"Du bist bereits voll geheilt. (HP: {hp}/{max_hp})"

        heal_amount = max(10, max_hp // 2)
        bonus = int((turn_state or {}).get("potion_heal_bonus", 0))
        heal_amount += bonus
        new_hp = min(max_hp, hp + heal_amount)
        p["potions"] = potions - 1
        p["hp"] = new_hp
        self.state.save()
        return (
            f"🧪 Du trinkst einen Heiltrank und regenerierst {new_hp - hp} HP.\n"
            f"HP: {new_hp}/{max_hp}  |  Tränke: {p['potions']}"
        )

    # ------------------------------------------
    # 🐢 LANGSAME KAMPFZEILEN (Terminal-Immersion)
    # ------------------------------------------
    def _slow_line(
        self,
        text: str,
        delay_char: float = 0.02,
        delay_line: float = 0.15
    ):
        """
        Gibt Text zeichenweise im Terminal aus.
        Rein visuell – beeinflusst keine Logik.
        """
        try:
            for ch in text:
                print(ch, end="", flush=True)
                time.sleep(delay_char)
            print()
            time.sleep(delay_line)
        except KeyboardInterrupt:
            # Falls User abbrechen will → sofort alles ausgeben
            print(text)

    # ------------------------------------------
    # MAAT-FELDER AUS CONTEXT HOLEN (0..1)
    # ------------------------------------------
    def _get_maat_fields(self, context: dict | None):
        """
        Holt H, B, S, V, R aus context['maat_fields'], falls vorhanden.
        Werte werden auf 0..1 geklemmt.
        """
        H = B = S = V = R = 0.0
        if isinstance(context, dict):
            fields = context.get("maat_fields") or {}
            try:
                H = float(fields.get("H", 0.0))
                B = float(fields.get("B", 0.0))
                S = float(fields.get("S", 0.0))
                V = float(fields.get("V", 0.0))
                R = float(fields.get("R", 0.0))
            except Exception:
                pass

        # clamp 0..1
        def clamp(x): return max(0.0, min(1.0, x))
        return clamp(H), clamp(B), clamp(S), clamp(V), clamp(R)


# INNER BOSS
    def _get_inner_boss(self, context: dict | None):
        """
        Erkennt, ob ein Inner Boss aktiv ist.
        Phase 1: nur Erkennung + Name + Thema
        """
        if not isinstance(context, dict):
            return None

        inner = context.get("inner_boss")
        if not isinstance(inner, dict):
            return None

        name = inner.get("name")
        theme = inner.get("theme", "unknown")

        if not name:
            return None

        return {
            "name": name,
            "theme": theme,
        }

    def _inner_boss_message(self, inner_boss: dict, outcome: str):
        """
        Phase 1 – reine narrative Stimme.
        outcome: "victory" | "defeat"
        """
        name = inner_boss.get("name", "Eine Stimme")
        theme = inner_boss.get("theme")

        if outcome == "victory":
            return (
                f"\n🧠 **Innerer Widerstand – {name}**\n"
                "Eine leise Stimme meldet sich in dir:\n\n"
                "»Du hast gewonnen… aber glaub nicht, dass es vorbei ist.«\n\n"
                "Sie verstummt wieder. Für jetzt."
            )

        else:  # defeat
            return (
                f"\n🧠 **Innerer Widerstand – {name}**\n"
                "Etwas in dir flüstert:\n\n"
                "»Siehst du? Genau das habe ich dir gesagt.«\n\n"
                "Die Stimme bleibt. Nicht laut. Aber präsent."
            )

    # ---------- KAMPFTYP-ENTSCHEIDUNG ----------
    def _auto_fight_type(self):
        stats = self.state.state["stats"]
        world = self.state.state["world"]

        wins = stats["fights_won"]
        boss_wins = stats["boss_wins"]
        final_wins = stats["final_wins"]

        # Endboss alle 5 Boss-Siege (sofern noch nicht abgearbeitet)
        expected_final = boss_wins // 5
        if boss_wins > 0 and boss_wins % 5 == 0 and final_wins < expected_final:
            return "final"

        # Boss alle 10 Siege
        if wins > 0 and wins % 10 == 0:
            return "boss"

        return "normal"

    # ---------- STATS / SCHADEN ----------
    def _base_attack_damage(self, attack_type: str) -> int:
        p = self.state.state["player"]
        lvl = max(1, p["level"])

        base_table = {
            "harmonie": 10,
            "balance": 9,
            "schöpfungskraft": 12,
            "verbundenheit": 8,
            "respekt": 7,
        }
        base = base_table.get(attack_type.lower(), 6)
        variance = random.randint(-3, 4)
        return max(1, base + lvl * 2 + variance)

    def _enemy_stats(self, ftype: str):
        p = self.state.state["player"]
        lvl = max(1, p["level"])

        if ftype == "normal":
            hp = 40 + lvl * 8
            dmg = 5 + lvl * 2
            xp = 15 + lvl * 4
        elif ftype == "boss":
            hp = 160 + lvl * 18
            dmg = 10 + lvl * 4
            xp = 120 + lvl * 10
        else:  # final
            hp = 260 + lvl * 25
            dmg = 14 + lvl * 5
            xp = 260 + lvl * 18
        return hp, dmg, xp

    # ---------- MUSIK WÄHLEN ----------
    def _choose_music(self, ftype: str, boss_index: int, final_index: int):
        music_dir = os.path.join(self.plugin_dir, "music")

        path = None  # default keine Musik

        if ftype == "normal":
            stats = self.state.state["stats"]
            boss_wins = stats.get("boss_wins", 0)
            idx = max(0, min(4, boss_wins))

            if idx == 0:
                cand = os.path.join(music_dir, "battle_normal.mp3")
            else:
                cand = os.path.join(music_dir, f"battle_normal{idx+1}.mp3")

            if os.path.isfile(cand):
                path = cand
            else:
                fallback = os.path.join(music_dir, "battle_normal.mp3")
                if os.path.isfile(fallback):
                    path = fallback

        elif ftype == "boss":
            cand = os.path.join(music_dir, f"battle_boss_{boss_index}.mp3")
            if os.path.isfile(cand):
                path = cand
            else:
                fallback = os.path.join(music_dir, "battle_boss.mp3")
                if os.path.isfile(fallback):
                    path = fallback

        else:  # final
            cand = os.path.join(music_dir, f"battle_final_{final_index}.mp3")
            if os.path.isfile(cand):
                path = cand
            else:
                fallback = os.path.join(music_dir, "battle_final.mp3")
                if os.path.isfile(fallback):
                    path = fallback

        victory = os.path.join(music_dir, "victory.mp3")
        if not os.path.isfile(victory):
            victory = None

        return path, victory

    # ---------- XP + BELOHNUNG ----------
    def _reward_on_victory(self, ftype: str, xp_reward: int, context: dict | None):
        s = self.state.state
        stats = s["stats"]
        world = s["world"]
        p = s["player"]
        story_choices = self._get_story_choices(context)
        story_state = self._load_story_state()
        story_state.setdefault("choices", story_choices if isinstance(story_choices, dict) else {})
        story_state.setdefault("choice_labels", story_state.get("choice_labels", {}))
        story_state.setdefault("consequences", {})
        story_state.setdefault("journal", [])

        # 🔹 MAAT-Felder greifen
        H, B, S, V, R = self._get_maat_fields(context)

        # 🔹 XP- und Gold-Multiplikatoren:
        # H = bis zu +25% XP (gute Ausrichtung)
        xp_mult = 1.0 + 0.25 * H

        # V = bis zu +20% Gold (Verbundenheit = mehr „Flow“/Loot)
        gold_mult = 1.0 + 0.20 * V

        # R = beeinflusst Trank-Drop-Chance (0.25 → max 0.25+0.25=0.5)
        base_potion_chance = 0.25
        potion_chance = base_potion_chance + 0.25 * R
        potion_chance = max(0.0, min(0.8, potion_chance))

        stats["fights_won"] += 1

        # Für Text
        skill_msg = ""
        potion_msg = ""

        # -------------------------------
        # BOSSE / FINALBOSSE
        # -------------------------------
        if ftype == "boss":
            stats["boss_fights"] += 1
            stats["boss_wins"] += 1
            world["last_boss_checkpoint"] = stats["boss_wins"]

            # Skill-Belohnung
            new_skill = choose_path_skill(p["skills"], story_choices)
            if len(p["skills"]) < 5:
                p["skills"].append(new_skill)
                skill_msg = f"Du hast eine neue Fertigkeit erlernt: {new_skill}!"
            else:
                replaced = p["skills"][0]
                p["skills"][0] = new_skill
                skill_msg = f"Fertigkeit {replaced} wurde durch {new_skill} ersetzt!"

            self._append_story_journal_entry(
                story_state,
                key=f"reward:boss_skill_{stats['boss_wins']}",
                title="Boss-Erbe",
                summary=f"Maatis traegt jetzt die Technik `{new_skill}`.",
                detail="Die Form dieser Belohnung wurde vom bisherigen Weg und seinen Entscheidungen mitgepraegt.",
            )

            # Boss-Cutscene nach JEDEM Boss-Sieg
            boss_index = stats["boss_wins"]
            boss_scene = os.path.join(self.plugin_dir, f"boss_scene_{boss_index}.py")
            if os.path.isfile(boss_scene):
                try:
                    subprocess.Popen(
                        ["python3", boss_scene],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    pass

        elif ftype == "final":
            stats["final_fights"] += 1
            stats["final_wins"] += 1
            world["principles_restored"] += 1

            skill_msg = (
                "✨ Ein Maat-Prinzip wurde in die Welt zurückgebracht! "
                f"(Gesamt: {world['principles_restored']})"
            )
            self._append_story_journal_entry(
                story_state,
                key=f"reward:final_restore_{stats['final_wins']}",
                title="Rueckkehr eines Prinzips",
                summary=f"Maatis hat Prinzip {world['principles_restored']} in die Welt zurueckgetragen.",
                detail="Wie sich dieser Sieg anfühlt, wird spaeter von seinem gewaehlten Weg gespiegelt.",
            )

            # Credits nur 1x nach dem 5. Prinzip
            if world["principles_restored"] >= 5 and not world.get("credits_played", False):
                credits_py = os.path.join(self.plugin_dir, "credits.py")
                if os.path.isfile(credits_py):
                    try:
                        subprocess.Popen(
                            ["python3", credits_py],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        world["credits_played"] = True
                    except Exception:
                        pass

        # -------------------------------
        # 🎮 XP → internes RPG-Level
        # -------------------------------
        xp_effective = max(1, int(round(xp_reward * xp_mult)))
        old_lvl, new_lvl = self.state.add_xp(xp_effective)

        # Level-Up Sound (einmalig pro Level-Up)
        if new_lvl > old_lvl:
            play_levelup_sound(self.plugin_dir)

        # -------------------------------
        # 💰 GOLD & 🧪 TRANK-LOOT
        # -------------------------------
        lvl = p.get("level", 1)
        if ftype == "normal":
            gold_base = random.randint(5, 10) + lvl * 2
        elif ftype == "boss":
            gold_base = random.randint(20, 35) + lvl * 4
        else:  # final
            gold_base = random.randint(40, 70) + lvl * 6

        gold_reward = max(1, int(round(gold_base * gold_mult)))
        p["gold"] = p.get("gold", 0) + gold_reward

        # Trank-Drop-Chance von Respekt beeinflusst
        if random.random() < potion_chance:
            p["potions"] = p.get("potions", 0) + 1
            potion_msg = f"🧪 Du findest einen Heiltrank! (Chance: {potion_chance:.0%}) (Tränke: {p['potions']})"

        consequence_lines = []
        turn_state = context.get("battle_turn_state", {}) if isinstance(context, dict) else {}
        consequences = story_state["consequences"]

        if ftype == "boss":
            reflection_path = story_choices.get("reflection_path")
            combat_vow = story_choices.get("combat_vow")

            if reflection_path == "harmonie" and turn_state.get("resonance", 0) >= 60:
                consequences["harmonie_boss_resonance"] = True
                self._append_story_journal_entry(
                    story_state,
                    key=f"consequence:harmonie_boss_{stats['boss_wins']}",
                    title="Nachklang der Harmonie",
                    summary="Ein Bosssieg hat Maatis' Harmonie-Weg vertieft.",
                    detail="Der Sieg wurde mit hoher Resonanz getragen. Daraus kann eine spaetere innere Szene erwachsen.",
                )
                consequence_lines.append("🎼 Der Sieg laesst einen Nachklang zurück. Harmonie wirkt jetzt wie getragene Kraft.")

            if combat_vow == "protect" and not turn_state.get("used_potion"):
                consequences["protect_boss_mercy"] = True
                self._append_story_journal_entry(
                    story_state,
                    key=f"consequence:protect_boss_{stats['boss_wins']}",
                    title="Schutz ohne Flucht",
                    summary="Maatis hat einen Boss ohne Trank und ohne Aufgeben getragen.",
                    detail="Sein Geluebde zu schuetzen bekommt damit narrative Substanz und fuehrt spaeter zu einer inneren Szene.",
                )
                consequence_lines.append("🛡️ Der Weg des Schutzes verdichtet sich: Maatis hat getragen, ohne sich hinter Heilung zu verstecken.")

            if combat_vow == "truth" and turn_state.get("weakness_hits", 0) >= 2:
                consequences["truth_boss_insight"] = True
                self._append_story_journal_entry(
                    story_state,
                    key=f"consequence:truth_boss_{stats['boss_wins']}",
                    title="Wahrheit im Muster",
                    summary="Maatis hat den Boss ueber seine Schwachstellen gelesen.",
                    detail="Mehrere gezielte Resonanztreffer haben eine spaetere Einsichtsszene vorbereitet.",
                )
                consequence_lines.append("🔎 Aus dem Kampf bleibt mehr zurück als Sieg: Maatis hat das Muster des Gegners wirklich gelesen.")

        if ftype == "final":
            if story_choices.get("reflection_path") == "respekt":
                consequences["respekt_final_restored"] = True
                self._append_story_journal_entry(
                    story_state,
                    key=f"consequence:respekt_final_{stats['final_wins']}",
                    title="Grenze traegt Welt",
                    summary="Ein wiederhergestelltes Prinzip verbindet sich mit Maatis' Weg des Respekts.",
                    detail="Das bereitet eine spaetere Reflexion ueber Grenze, Welt und getragene Macht vor.",
                )
                consequence_lines.append("⚖️ Das wiederhergestellte Prinzip antwortet besonders stark auf Maatis' Entscheidung fuer Respekt.")

            if story_choices.get("combat_vow") == "remember":
                consequences["remember_world_echo"] = True
                self._append_story_journal_entry(
                    story_state,
                    key=f"consequence:remember_final_{stats['final_wins']}",
                    title="Echo in der Welt",
                    summary="Maatis' Geluebde zu erinnern hat im wiederhergestellten Prinzip Widerhall gefunden.",
                    detail="Diese Spur oeffnet spaeter eine innere Szene, in der die Welt selbst zu antworten scheint.",
                )
                consequence_lines.append("🌌 Etwas im Ganzen antwortet. Das Geluebde der Erinnerung ist nicht mehr nur innerlich.")

        self._save_story_state(story_state)


        # -------------------------------
        # FLAGS & SAVE
        # -------------------------------
        self.state.state["flags"]["needs_heal"] = False
        self.state.save()

        # -------------------------------
        # TEXT ZUSAMMENBAUEN
        # -------------------------------
        lines = [f"XP erhalten: {xp_effective} (Basis: {xp_reward}) (Level {old_lvl} → {new_lvl})"]
        lines.append(f"💰 Gold erhalten: {gold_reward} (Basis: {gold_base}, gesamt: {p['gold']})")

        if new_lvl > old_lvl:
            lines.append("🌟 LEVEL UP! Deine Kraft ist gewachsen.")
        if skill_msg:
            lines.append(skill_msg)
        if potion_msg:
            lines.append(potion_msg)
        lines.extend(consequence_lines)
        reward_line = self._choice_reward_line(story_choices, ftype)
        if reward_line:
            lines.append(reward_line)

        return "\n".join(lines)

    # ---------- KAMPF-LOOP ----------
    def run_fight(self, ftype: str, context: dict | None = None) -> str:
        inner_boss = self._get_inner_boss(context)
        
        s = self.state.state
        p = s["player"]
        stats = s["stats"]

        # 🔹 MAAT-Felder lesen
        H, B, S, V, R = self._get_maat_fields(context)

        # 🔹 einfache, gut lesbare Buffs:
        # S = + bis zu +30% Schaden
        attack_mult = 1.0 + 0.30 * S

        # B = - bis zu 25% eingehender Schaden
        defense_mult = 1.0 - 0.25 * B

        # H = + bis zu 15% Chance, kleinen Bonus-Schaden zu machen
        crit_base = 0.05  # 5% Grundchance
        crit_bonus = 0.15 * H
        crit_chance = crit_base + crit_bonus

        stats["fights_total"] += 1

        # Optional: Kontext auswerten (z.B. Dungeon übergibt eigenen Bossnamen)
        boss_name_override = None
        if isinstance(context, dict):
            boss_name_override = context.get("boss_name")

        # Namen & Indizes wählen
        if ftype == "boss":
            boss_idx = s["stats"]["boss_wins"] + 1
            final_idx = s["stats"]["final_wins"] + 1

            if boss_name_override:
                # 🔥 Dungeon / externes System liefert eigenen Bossnamen
                enemy_name = boss_name_override
            else:
                # Standard-Bossnamen aus dem Kampfsystem
                enemy_name = generate_boss_name(boss_idx)

        elif ftype == "final":
            final_idx = s["stats"]["final_wins"] + 1
            boss_idx = s["stats"]["boss_wins"]
            enemy_name = generate_final_name(final_idx)

        else:
            boss_idx = s["stats"]["boss_wins"]
            final_idx = s["stats"]["final_wins"]
            enemy_name = generate_enemy_name()

        enemy_hp, enemy_dmg_base, xp_reward = self._enemy_stats(ftype)
        max_enemy_hp = enemy_hp
        player_hp = p["hp"]
        turn_state = self._build_turn_state(context)
        story_mods = self._apply_story_modifiers(context, turn_state)
        story_choices = story_mods.get("choices", {})
        story_path_profile = self._get_story_path_profile(context)
        boss_profile = self._boss_profile(ftype, boss_idx, final_idx)

        attack_mult *= story_mods.get("attack_mult", 1.0)
        defense_mult *= story_mods.get("defense_mult", 1.0)
        crit_chance += story_mods.get("crit_bonus", 0.0)

        # 🎵 MUSIK – Dungeon kann eigene Tracks liefern
        # Musik – zuerst schauen, ob der Aufrufer (Dungeon) etwas vorgibt
        battle_track = None
        victory_track = None

        if isinstance(context, dict):
            music_cfg = context.get("music") or {}
            if isinstance(music_cfg, dict):
                battle_track = music_cfg.get("battle")
                victory_track = music_cfg.get("victory")

        def _exists(p):
            return isinstance(p, str) and os.path.isfile(p)

        # 1) Immer Default-Musik bestimmen (Fallback aus battle/music)
        default_battle, default_victory = self._choose_music(
            ftype,
            boss_idx,
            final_idx,
        )

        # 2) Dungeon-Overrides haben Vorrang, sonst Defaults
        if not _exists(battle_track):
            battle_track = default_battle
        if not _exists(victory_track):
            victory_track = default_victory

        # 3) Musikmanager starten (nur wenn es wirklich eine Datei gibt)
        music = BattleMusicManager(battle_track if _exists(battle_track) else None)
        music.start()

        log_lines = []
        if isinstance(context, dict):
            narrative_prepend = context.get("narrative_prepend")
            if isinstance(narrative_prepend, str) and narrative_prepend.strip():
                self._slow_line(narrative_prepend.strip(), delay_char=0.008, delay_line=0.3)
                log_lines.append(narrative_prepend.strip())
        intro = f"🎮 **{enemy_name}** erscheint! (Typ: {ftype.upper()})"
        log_lines.append(intro)
        self._slow_line(intro)
        for presence_line in self._path_presence_lines(story_path_profile):
            self._slow_line(Fore.CYAN + presence_line + Style.RESET_ALL, delay_char=0.008, delay_line=0.2)
            log_lines.append(presence_line)
        if boss_profile.get("intro") and ftype in ("boss", "final"):
            color = boss_profile.get("color", "")
            reset = Style.RESET_ALL if color else ""
            self._slow_line(color + f"👁 {boss_profile['title']}: {boss_profile['intro']}" + reset)
            log_lines.append(f"[BOSS PROFIL] {boss_profile['title']}")
        if boss_profile.get("entrance") and ftype in ("boss", "final"):
            color = boss_profile.get("color", "")
            reset = Style.RESET_ALL if color else ""
            self._slow_line(color + f"✦ {boss_profile['entrance']}" + reset, delay_char=0.01, delay_line=0.35)
        reactive_entrance = self._profile_reactive_entrance(story_path_profile, boss_profile, ftype)
        if reactive_entrance:
            color = boss_profile.get("color", "")
            reset = Style.RESET_ALL if color else ""
            self._slow_line(color + f"✧ {reactive_entrance}" + reset, delay_char=0.009, delay_line=0.25)
            log_lines.append(reactive_entrance)
        for extra_line in story_mods.get("intro_lines", []):
            self._slow_line(Fore.GREEN + extra_line + Style.RESET_ALL, delay_char=0.008, delay_line=0.25)
            log_lines.append(extra_line)

        principles = {
            "1": "Harmonie",
            "2": "Balance",
            "3": "Schöpfungskraft",
            "4": "Verbundenheit",
            "5": "Respekt",
        }

        try:
            turn_counter = 0
            max_turns = 40
            while player_hp > 0 and enemy_hp > 0:
                turn_counter += 1
                if turn_counter > max_turns:
                    line = "⏳ Der Kampf zerfasert. MAAT ordnet die Kräfte neu und beendet die Begegnung."
                    self._slow_line(line)
                    log_lines.append("Kampf wurde aus Stabilitätsgründen beendet.")
                    self.state.state["flags"]["needs_heal"] = True
                    self.state.save()
                    return "\n".join(log_lines)
                if ftype in ("boss", "final"):
                    boss_profile = self._activate_phase2_if_needed(
                        boss_profile,
                        turn_state,
                        enemy_hp,
                        max_enemy_hp,
                        enemy_name,
                    )
                    phase2_notice = turn_state.pop("phase2_notice", "")
                    if phase2_notice:
                        log_lines.append(phase2_notice)
                turn_state["weakness"] = self._choose_enemy_weakness()
                aura_text = self._apply_enemy_aura(boss_profile, turn_state, turn_counter)
                print("\n------------------------------------------")
                print(f"DU           HP: {player_hp}/{p['max_hp']}")
                print(f"{enemy_name} HP: {enemy_hp}")
                print(f"Resonanz: {turn_state.get('resonance', 0)}/100")
                if turn_state.get("guard", 0) > 0:
                    print(f"Schild: {turn_state['guard']}")
                print(f"Schwachstelle: {turn_state['weakness']}")
                if aura_text:
                    print(aura_text)
                if ftype in ("boss", "final"):
                    self._print_boss_hud(enemy_name, enemy_hp, max_enemy_hp, turn_state, boss_profile)
                print("------------------------------------------")
                taunt = self._boss_taunt(boss_profile, turn_counter, story_choices, story_path_profile) if ftype in ("boss", "final") else ""
                if taunt:
                    self._slow_line(Fore.MAGENTA + f"{enemy_name}: {taunt}" + Style.RESET_ALL, delay_char=0.008, delay_line=0.2)
                    log_lines.append(f"{enemy_name}: {taunt}")
                print("1) Angriff")
                print("2) Skills")
                print("3) Fokus")
                print("4) Heiltrank")
                print("5) MAAT-Impuls")
                print("6) Flucht")
                choice = self._prompt("Aktion: ", context=context, default="3")

                if choice == "1":
                    # ANGRIFF → Prinzip wählen
                    while True:
                        print("\n--- MAAT-Angriff ---")
                        print("1) Harmonie")
                        print("2) Balance")
                        print("3) Schöpfungskraft")
                        print("4) Verbundenheit")
                        print("5) Respekt")
                        print("6) Zurück")
                        sub = self._prompt("Wähle [1–6]: ", context=context, default="6")
                        if sub == "6":
                            break
                        if sub not in principles:
                            print("Ungültige Auswahl.")
                            continue
                        atk_type = principles[sub]
                        base_dmg = self._base_attack_damage(atk_type)
                        final_dmg = apply_skill_modifiers(
                            base_dmg, atk_type, p["skills"]
                        )
                        if atk_type.lower() == "schöpfungskraft":
                            final_dmg = int(round(final_dmg * float(turn_state.get("creation_bonus_mult", 1.0))))

                        # 🔹 Schöpfungskraft-Buff
                        final_dmg = final_dmg * attack_mult

                        # 🔹 Harmonie-Crit (kleiner Zusatzschlag)
                        crit_txt = ""
                        if random.random() < crit_chance:
                            bonus = max(1, int(final_dmg * 0.20))  # +20% als Bonus
                            final_dmg += bonus
                            crit_txt = f" (Harmonie-Crit! +{bonus} Bonus-Schaden)"

                        final_dmg = max(1, int(round(final_dmg)))

                        final_dmg, weakness_txt = self._apply_enemy_weakness(atk_type, final_dmg, turn_state)
                        resonance = self._gain_resonance(turn_state, 18)
                        enemy_hp -= final_dmg
                        line = (
                            f"⚔ Du setzt **{atk_type}** ein → {final_dmg} Schaden!"
                            f"{crit_txt}{weakness_txt} Resonanz {resonance}/100."
                        )
                        self._slow_line(line)
                        log_lines.append(f"Spieler nutzt {atk_type}: {final_dmg} Schaden")

                        break  # danach zurück ins Hauptmenü



                elif choice == "2":
                    # SKILLS
                    if not p["skills"]:
                        print("Noch keine Skills gelernt.")
                    else:
                        print("\n--- Skills ---")
                        for i, sk in enumerate(p["skills"], 1):
                            print(f"{i}) {sk}")
                        print(f"{len(p['skills'])+1}) Zurück")
                        sub = self._prompt("Wähle: ", context=context, default=str(len(p["skills"]) + 1))
                        try:
                            idx = int(sub) - 1
                            if idx == len(p["skills"]):
                                pass  # Zurück
                            elif 0 <= idx < len(p["skills"]):
                                sk = p["skills"][idx]
                                base_dmg = 18 + p["level"] * 3 + random.randint(-4, 5)
                                final_dmg = apply_skill_modifiers(
                                    base_dmg, "skill", p["skills"]
                                )
                                final_dmg, weakness_txt = self._apply_enemy_weakness("Skill", final_dmg, turn_state)
                                resonance = self._gain_resonance(turn_state, 24)
                                enemy_hp -= final_dmg
                                line = (
                                    f"✨ Skill **{sk}** trifft für {final_dmg} Schaden!"
                                    f"{weakness_txt} Resonanz {resonance}/100."
                                )
                                self._slow_line(line)
                                log_lines.append(f"Skill {sk}: {final_dmg} Schaden")
                        except ValueError:
                            print("Ungültige Eingabe.")

                elif choice == "3":
                    player_hp, line = self._use_focus(player_hp, p["max_hp"], turn_state)
                    player_hp, extra_txt = self._modify_player_action(choice, turn_state, player_hp, p["max_hp"])
                    if extra_txt:
                        line += extra_txt
                    self._slow_line(line)
                    log_lines.append("Spieler nutzt Fokus.")

                elif choice == "4":
                    potion_msg = self._use_potion_in_fight(turn_state)
                    if "regenerierst" in potion_msg:
                        turn_state["used_potion"] = True
                    player_hp, extra_txt = self._modify_player_action(choice, turn_state, player_hp, p["max_hp"])
                    if extra_txt:
                        potion_msg += extra_txt
                    self._slow_line(potion_msg)
                    log_lines.append("Spieler nutzt Heiltrank." if "regenerierst" in potion_msg else "Heiltrank nicht genutzt.")
                    player_hp = p["hp"]

                elif choice == "5":
                    final_dmg, heal, ult_msg = self._use_ult(p["level"], p["max_hp"], turn_state)
                    self._slow_line(ult_msg)
                    if final_dmg > 0:
                        enemy_hp -= final_dmg
                        player_hp = min(p["max_hp"], player_hp + heal)
                        p["hp"] = player_hp
                        if enemy_hp <= 0:
                            turn_state["ult_finisher"] = True
                        log_lines.append(f"MAAT-Impuls: {final_dmg} Schaden, {heal} Heilung")

                elif choice == "6":
                    # FLUCHT
                    if random.random() < 0.5:
                        line = "😅 Du kannst entkommen!"
                        self._slow_line(line)
                        log_lines.append("Spieler ist erfolgreich geflohen.")
                        music.stop()
                        self.state.state["flags"]["needs_heal"] = True
                        self.state.state["stats"]["messages_since_last_fight"] = 0
                        self.state.save()
                        return "\n".join(log_lines)
                    else:
                        line = "❌ Flucht fehlgeschlagen!"
                        self._slow_line(line)
                        log_lines.append("Fluchtversuch fehlgeschlagen.")

                else:
                    print("Ungültige Auswahl.")
                    continue

                turn_state["last_player_action"] = choice

                # Gegnerzug
                if enemy_hp > 0:
                    if ftype in ("boss", "final"):
                        turn_state["enemy_charge"] = min(3, int(turn_state.get("enemy_charge", 0)) + 1)
                        if turn_state["enemy_charge"] >= 3:
                            self._show_special_vignette(boss_profile.get("special", "Spezialattacke"))
                            player_hp, special_text = self._boss_special_attack(
                                boss_profile,
                                turn_state,
                                player_hp,
                                p["max_hp"],
                            )
                            player_hp = max(0, player_hp)
                            turn_state["enemy_charge"] = 0
                            self._slow_line(special_text)
                            log_lines.append(f"[SPECIAL] {boss_profile.get('special')}")
                            if player_hp > 0:
                                turn_state["survived_special"] = True
                            if player_hp <= 0:
                                continue

                    dmg_in = max(1, enemy_dmg_base + random.randint(-3, 4))
                    if ftype in ("boss", "final"):
                        dmg_in = int(round(dmg_in * float(boss_profile.get("damage_mult", 1.0))))

                    # 🔹 Balance reduziert eingehenden Schaden
                    dmg_in = dmg_in * defense_mult
                    dmg_in = max(1, int(round(dmg_in)))
                    dmg_in, aura_counter_txt = self._modify_incoming_damage(dmg_in, turn_state, choice)
                    dmg_in, guard_txt = self._apply_guard(dmg_in, turn_state)

                    player_hp -= dmg_in
                    resonance = self._gain_resonance(turn_state, 12 if dmg_in > 0 else 6)
                    line = f"💥 {enemy_name} trifft dich für {dmg_in} Schaden!{guard_txt}{aura_counter_txt} Resonanz {resonance}/100."
                    self._slow_line(line)
                    log_lines.append(f"Gegner trifft: {dmg_in} Schaden (Balance aktiv)")

        finally:
            music.stop()

        # Kampfende
        p["hp"] = max(0, player_hp)

        if player_hp > 0 and enemy_hp <= 0:
            # Sieg
            line = f"\n🏆 Du hast **{enemy_name}** besiegt!"
            self._slow_line(line)
            log_lines.append(f"Sieg über {enemy_name}")

            # Sieges-Jingle – benutze das bereits gewählte victory_track
            music.victory_jingle(victory_track)

            reward_txt = self._reward_on_victory(ftype, xp_reward, context)
            log_lines.append(reward_txt)
            combat_unlocks = self._evaluate_combat_achievements(ftype, turn_state)
            if combat_unlocks:
                ach_text = "\n".join(f"🏆 Neuer Kampf-Erfolg: {title}" for title in combat_unlocks)
                self._slow_line(ach_text, delay_char=0.01, delay_line=0.3)
                log_lines.append(ach_text)
            summary = self._build_combat_summary(enemy_name, ftype, True, turn_state, player_hp, enemy_hp)
            self._slow_line(summary, delay_char=0.008, delay_line=0.3)
            log_lines.append(summary)
            if inner_boss:
                msg = self._inner_boss_message(inner_boss, outcome="victory")
                self._slow_line(msg, delay_char=0.01, delay_line=0.6)
                log_lines.append(f"[INNER BOSS] {inner_boss['name']} meldet sich nach dem Sieg.")
            story_victory = self._story_boss_line(story_choices, outcome="victory")
            if story_victory:
                self._slow_line(story_victory, delay_char=0.008, delay_line=0.3)
                log_lines.append(story_victory)
            profile_victory = self._profile_boss_line(story_path_profile, boss_profile, outcome="victory")
            if profile_victory:
                self._slow_line(profile_victory, delay_char=0.008, delay_line=0.3)
                log_lines.append(profile_victory)
            
        else:
            # Niederlage
            line = f"\n💀 Du wurdest von **{enemy_name}** besiegt..."
            self._slow_line(line)
            log_lines.append(f"Niederlage gegen {enemy_name}")
            if ftype in ("boss", "final"):
                victory_line = boss_profile.get("victory_line")
                if victory_line:
                    self._slow_line(
                        Fore.RED + f"{enemy_name}: {victory_line}" + Style.RESET_ALL,
                        delay_char=0.01,
                        delay_line=0.3,
                    )
            summary = self._build_combat_summary(enemy_name, ftype, False, turn_state, player_hp, enemy_hp)
            self._slow_line(summary, delay_char=0.008, delay_line=0.3)
            log_lines.append(summary)
            if inner_boss:
                msg = self._inner_boss_message(inner_boss, outcome="defeat")
                self._slow_line(msg, delay_char=0.01, delay_line=0.6)
                log_lines.append(f"[INNER BOSS] {inner_boss['name']} verstärkt sich nach der Niederlage.")
            story_defeat = self._story_boss_line(story_choices, outcome="defeat")
            if story_defeat:
                self._slow_line(story_defeat, delay_char=0.008, delay_line=0.3)
                log_lines.append(story_defeat)
            profile_defeat = self._profile_boss_line(story_path_profile, boss_profile, outcome="defeat")
            if profile_defeat:
                self._slow_line(profile_defeat, delay_char=0.008, delay_line=0.3)
                log_lines.append(profile_defeat)
            stats["fights_lost"] += 1
            # Zurück zum letzten Boss-Checkpoint (weiche Rücksetzung)
            checkpoint = self.state.state["world"]["last_boss_checkpoint"]
            stats["fights_won"] = checkpoint * 10
            p["hp"] = max(10, p["max_hp"] // 4)
            self.state.state["flags"]["needs_heal"] = True
            self.state.save()

        stats["messages_since_last_fight"] = 0
        self.state.save()

        return "\n".join(log_lines)



# =====================================================
# 🧩 PLUGIN WRAPPER
# =====================================================
class Plugin:
    type = "chat"

    commands = {
        "/fight": "Startet einen normalen MAAT-Kampf (Debug).",
        "/fightboss": "Erzwingt einen Bosskampf (Debug).",
        "/fightfinal": "Erzwingt einen Endbosskampf (Debug).",
        "/xp": "Zeigt deinen aktuellen Level- und XP-Status.",
        "/shop": "MAAT-RPG Laden (z.B. /shop buy potion 2).",   # 🏪 NEU
        "/usepotion": "Benutze einen Heiltrank.",                # 🧪 NEU
        "/battletest": "Führt einen stabilen Battle-Core-Selbsttest aus.",
    }

    def __init__(self):
        self.plugin_dir = os.path.dirname(__file__)
        self.core = BattleCore(self.plugin_dir)
        self.state = self.core.state

    # =====================================================
    # 🟦 COMMAND HANDLER
    # =====================================================
    def command(self, cmd, context=None):
        parts = cmd.strip().split()
        base = parts[0].lower() if parts else ""

        # ---------------- FIGHTS ----------------
        if base == "/fight":
            demo_context = self._build_demo_context("normal", context)
            out = self.core.run_fight("normal", demo_context)
            return True, out

        if base == "/fightboss":
            demo_context = self._build_demo_context("boss", context)
            out = self.core.run_fight("boss", demo_context)
            return True, out

        if base == "/fightfinal":
            out = self.core.run_fight("final", context or {})
            return True, out

        if base == "/usepotion":
            return True, self._use_potion()

        if base == "/battletest":
            return True, self._battle_selftest()

        # ---------------- STATUS / XP ----------------
        if base == "/xp":
            s = self.core.state.state
            p = s["player"]
            stats = s["stats"]
            world = s["world"]
            combat_achievements = s.get("achievements", {}).get("combat", [])
            story_profile = self.core._get_story_path_profile(context)

            lvl = p["level"]
            xp = p["xp"]
            xp_next = self.core.state.xp_needed_for_level(lvl + 1)

            fights = stats.get("fights_total", 0)
            wins = stats.get("fights_won", 0)
            losses = stats.get("fights_lost", 0)
            boss_wins = stats.get("boss_wins", 0)
            final_wins = stats.get("final_wins", 0)
            restored = world.get("principles_restored", 0)
            gold = p.get("gold", 0)
            potions = p.get("potions", 0)

            lines = []
            lines.append("📘 **Dein MAAT-RPG Status**")
            lines.append("")
            lines.append(f"• Level: {lvl}")
            lines.append(f"• XP: {xp}/{xp_next}")
            if story_profile:
                lines.append(f"• Pfadprofil: {story_profile.get('title', 'Unbestimmt')} — {story_profile.get('rank', 'Erwachend')}")
            lines.append("")
            lines.append(f"• Kämpfe gesamt: {fights}")
            lines.append(f"  ├─ Siege: {wins}")
            lines.append(f"  └─ Niederlagen: {losses}")
            lines.append(f"• Boss-Siege: {boss_wins}")
            lines.append(f"• Finalboss-Siege: {final_wins}")
            lines.append(f"• Wiederhergestellte Maat-Prinzipien: {restored}")
            lines.append("")
            lines.append(f"• Gold: {gold}")
            lines.append(f"• Heiltränke: {potions}")
            if combat_achievements:
                lines.append("")
                lines.append("• Kampf-Erfolge:")
                for key in combat_achievements:
                    title = self.core._combat_achievement_catalog().get(key, key)
                    lines.append(f"  - {title}")
            lines.append("")
            lines.append("Tipp: Die XP-Leiste siehst du im Terminal nach jeder Nachricht. 🌀")

            return True, "\n".join(lines)

        # ---------------- SHOP ----------------
        if base == "/shop":
            s = self.core.state.state
            p = s["player"]
            gold = p.get("gold", 0)
            potions = p.get("potions", 0)

            # Kaufversuch?
            if len(parts) >= 4 and parts[1].lower() == "buy" and parts[2].lower() == "potion":
                try:
                    amount = int(parts[3])
                except ValueError:
                    return True, "Bitte gib eine gültige Anzahl an: `/shop buy potion 1`"

                if amount <= 0:
                    return True, "Die Anzahl muss größer als 0 sein."

                cost = 25 * amount
                if gold < cost:
                    return True, f"Du hast nicht genug Gold. ({gold} / {cost})"

                # Kauf durchführen
                p["gold"] = gold - cost
                p["potions"] = potions + amount
                self.core.state.save()

                return True, (
                    f"🛒 Du kaufst {amount} Heiltrank/Heiltränke für {cost} Gold.\n"
                    f"Gold: {p['gold']} | Tränke: {p['potions']}"
                )

            # Nur Shop-Übersicht
            lines = []
            lines.append("🏪 **MAAT-RPG Laden**")
            lines.append("")
            lines.append(f"Gold: {gold}")
            lines.append(f"Heiltränke im Inventar: {potions}")
            lines.append("")
            lines.append("Verfügbare Items:")
            lines.append("  • Heiltrank – 25 Gold (stellt 50% deiner Max-HP wieder her)")
            lines.append("")
            lines.append("Kaufen mit: `/shop buy potion 1` oder `/shop buy potion 3`")

            return True, "\n".join(lines)

        return None

    #---------------------------------
    # Tränke verwenden
    #---------------------------------
    def _use_potion(self) -> str:
        s = self.core.state.state
        p = s["player"]

        potions = p.get("potions", 0)
        if potions <= 0:
            return "🧪 Du hast keinen Heiltrank im Inventar."

        max_hp = p.get("max_hp", 100)
        hp = p.get("hp", max_hp)

        if hp >= max_hp:
            return f"Du bist bereits voll geheilt. (HP: {hp}/{max_hp})"

        heal_amount = max_hp // 2  # 50% Max-HP
        new_hp = min(max_hp, hp + heal_amount)

        p["potions"] = potions - 1
        p["hp"] = new_hp
        self.core.state.save()

        return (
            f"🧪 Du trinkst einen Heiltrank und regenerierst {new_hp - hp} HP.\n"
            f"HP: {new_hp}/{max_hp}  |  Tränke: {p['potions']}"
        )

    # -------------------------------------------------
    # HUD: HP-Leiste + Level + Titel
    # -------------------------------------------------
    def _build_hp_bar(self, hp: int, max_hp: int, width: int = 20) -> str:
        if max_hp <= 0:
            return "[" + "·" * width + "]"

        ratio = max(0.0, min(1.0, hp / max_hp))
        filled = int(round(width * ratio))
        empty = width - filled
        return "[" + ("█" * filled) + ("·" * empty) + "]"


    def _shop(self, cmd: str) -> str:
        s = self.core.state.state
        p = s["player"]
        gold = p.get("gold", 0)
        potions = p.get("potions", 0)

        parts = cmd.split()
        # Nur /shop → Übersicht
        if len(parts) == 1:
            lines = [
                "🏪 **MAAT-RPG Laden**",
                "",
                f"Gold: {gold}",
                f"Heiltränke im Inventar: {potions}",
                "",
                "Verfügbare Items:",
                "  • Heiltrank – 25 Gold (stellt 50% deiner Max-HP wieder her)",
                "",
                "Kaufen mit: `/shop buy potion 1` oder `/shop buy potion 3`",
            ]
            return "\n".join(lines)

        # Kauf: /shop buy potion <anzahl>
        if len(parts) >= 3 and parts[1].lower() == "buy":
            item = parts[2].lower()
            amount = 1
            if len(parts) >= 4:
                try:
                    amount = max(1, int(parts[3]))
                except ValueError:
                    return "Bitte gib eine gültige Anzahl an, z.B. `/shop buy potion 2`."

            if item not in ("potion", "trank", "heiltrank"):
                return "Dieses Item gibt es (noch) nicht. Verfügbar: `potion`."

            price_per = 25
            cost = price_per * amount

            if gold < cost:
                return f"Du hast nicht genug Gold. Kosten: {cost}, Gold: {gold}."

            p["gold"] = gold - cost
            p["potions"] = potions + amount
            self.core.state.save()

            return (
                f"✅ Gekauft: {amount} Heiltrank(e) für {cost} Gold.\n"
                f"Gold: {p['gold']}   |   Tränke: {p['potions']}"
            )

        return "Syntax: `/shop` oder `/shop buy potion <anzahl>`."

    def _get_title_for_level(self, level: int) -> str:
        return get_title_for_level(level)

    def _build_hud(self, context=None) -> str:
        """
        HUD unter jeder Antwort:
        - HP + HP-Bar
        - Level + Titel
        - Siege / Boss-Siege
        - Gold + Heiltränke
        - (optional) wiederhergestellte Maat-Prinzipien
        """
        if not hasattr(self, "core") or self.core is None:
            return ""

        # 🔹 WICHTIG: RPG-State, nicht der globale Core-State
        s = self.core.state.state
        p = s.get("player", {})
        stats = s.get("stats", {})
        world = s.get("world", {})

        level = int(p.get("level", 1))
        hp = int(p.get("hp", 0))
        max_hp = int(p.get("max_hp", 0))

        bar = self._build_hp_bar(hp, max_hp, width=24)
        title = p.get("title") or self._get_title_for_level(level)
        story_profile = self.core._get_story_path_profile(context)

        fights = int(stats.get("fights_won", 0))
        boss_wins = int(stats.get("boss_wins", 0))

        gold = int(p.get("gold", 0))
        potions = int(p.get("potions", 0))
        restored = int(world.get("principles_restored", 0))

        lines = [
            f"❤️ HP {hp}/{max_hp}  {bar}",
            f"📘 Level {level} — {title}",
            f"⚔️ Siege: {fights}  |  Boss-Siege: {boss_wins}",
            f"💰 Gold: {gold}  |  🧪 Tränke: {potions}",
        ]

        if story_profile:
            lines.append(f"🜂 Pfad: {story_profile.get('title', 'Unbestimmt')} — {story_profile.get('rank', 'Erwachend')}")

        if restored > 0:
            lines.append(f"🌿 Wiederhergestellte Maat-Prinzipien: {restored}")

        return "\n".join(lines)
    # -----------------------------------------------------
    # BEFORE_CHAT
    # -----------------------------------------------------
    def before_chat(self, user_input, context=None):
        context = context or {}

        if self.state is None:
            # Kein RPG-State → nichts tun
            return False, user_input

        # 🩹 Passive Regeneration bei jeder Nachricht
        self._passive_regen_on_message()

        s = self.state.state
        stats = s["stats"]
        world = s["world"]

        # Slash-Commands nicht anfassen
        if user_input.strip().startswith("/"):
            return False, user_input

        # -----------------------------------------------------
        # XP-BONUS AUS ANDEREN PLUGINS (z.B. Achievements)
        # -----------------------------------------------------
        bonus_xp = 0
        if isinstance(context, dict):
            try:
                bonus_xp = int(context.get("maat_xp_bonus", 0) or 0)
            except ValueError:
                bonus_xp = 0
            context["maat_xp_bonus"] = 0  # einmalig verbrauchen

        # -----------------------------------------------------
        # USER-XP: Deep Chat XP über Maat-Prinzipien & Emotion
        # -----------------------------------------------------
        base_xp = calc_chat_xp(user_input, stats)
        xp_gain = base_xp + bonus_xp
        if xp_gain < 1:
            xp_gain = 1

        old_lvl, new_lvl = self.state.add_xp(xp_gain)
        print_level_bar(self.state, last_gain=xp_gain)

        if new_lvl > old_lvl:
            run_levelup_fx(new_lvl, None, self.plugin_dir)

        # -----------------------------------------------------
        # Nachrichten zählen
        # -----------------------------------------------------
        stats["messages_total"] += 1
        stats["messages_since_last_fight"] += 1
        stats["last_msg_ts"] = int(time.time())

        # -----------------------------------------------------
        # Kampfmodus freischalten nach 32 Nachrichten
        # -----------------------------------------------------
        if not world["combat_unlocked"] and stats["messages_total"] >= 32:
            world["combat_unlocked"] = True
            self.state.save()
            print(
                Fore.CYAN
                + "\n⚔️ Kampfmodus freigeschaltet! Gegner können dich jetzt zufällig angreifen.\n"
                + Style.RESET_ALL
            )
            return False, user_input

        # -----------------------------------------------------
        # Zufallskämpfe nur wenn freigeschaltet
        # -----------------------------------------------------
        if world["combat_unlocked"]:
            ms = stats["messages_since_last_fight"]
            trigger = False

            # Zwischen 2–15 Nachrichten → 10% Chance
            if 2 <= ms <= 15:
                if random.randint(1, 10) == 1:
                    trigger = True

            # Ab 16 Nachrichten → garantiert
            elif ms > 15:
                trigger = True

            if trigger:
                ftype = self.core._auto_fight_type()
                fight_text = self.core.run_fight(ftype, context)
                self.state.save()

                # 💡 Kampf-Log nur merken – KI antwortet trotzdem noch
                if isinstance(context, dict):
                    context.setdefault("battle_log", []).append(fight_text)

                # handled=False → LLM beantwortet die ursprüngliche Frage
                return False, user_input

        self.state.save()
        return False, user_input
        
    # -------------------------------------------------
    # Passive HP-Regeneration pro Nachricht
    # -------------------------------------------------
    def _passive_regen_on_message(self):
        """
        Heilt den Spieler bei jeder Nachricht ein Stück.
        Nach ~5 Nachrichten von 0 → voll (20% Max-HP pro Nachricht).
        """
        if self.state is None:
            return

        s = self.state.state
        p = s.get("player", {})
        hp = p.get("hp")
        max_hp = p.get("max_hp")

        if hp is None or max_hp is None:
            return
        if hp >= max_hp:
            return

        # 20% Max-HP pro Nachricht, mindestens 1 HP
        step = max(1, max_hp // 5)
        new_hp = min(max_hp, hp + step)
        p["hp"] = new_hp
        self.state.save()

    def _use_potion_in_fight(self) -> str:
        text = self._use_potion()
        return text if text else "🧪 Der Heiltrank blieb wirkungslos."

    def _battle_selftest(self) -> str:
        snapshots = []
        original = json.loads(json.dumps(self.core.state.state))
        scenarios = {
            "normal": ["1", "1", "3", "1", "5", "6"] * 4,
            "boss": ["3", "1", "2", "1", "4", "5"] * 5,
            "final": ["3", "1", "1", "5", "4", "1"] * 6,
        }

        try:
            for ftype, actions in scenarios.items():
                self.core.state.state["player"]["hp"] = self.core.state.state["player"]["max_hp"]
                context = {
                    "scripted_actions": list(actions),
                    "maat_fields": {"H": 0.8, "B": 0.7, "S": 0.9, "V": 0.6, "R": 1.0},
                }
                result = self.core.run_fight(ftype, context)
                if not isinstance(result, str) or not result.strip():
                    raise RuntimeError(f"Leerer Kampflog bei {ftype}")
                snapshots.append(f"✅ {ftype}: ok")
        except Exception as e:
            return f"❌ Battle-Core-Selbsttest fehlgeschlagen: {e}"
        finally:
            self.core.state.state = original
            self.core.state.save()

        return "🧪 Battle-Core-Selbsttest abgeschlossen\n" + "\n".join(snapshots)

    def _build_demo_context(self, mode: str, context=None) -> dict:
        merged = {}
        if isinstance(context, dict):
            merged.update(context)

        merged.setdefault(
            "narrative_prepend",
            (
                "🧪 Dies ist ein Testkampf. Er demonstriert gezielt Kernfunktionen wie "
                "Resonanz, Schild, Spezialattacken, Auren und Heilung."
            ),
        )
        merged.setdefault(
            "maat_fields",
            {"H": 0.8, "B": 0.8, "S": 0.9, "V": 0.7, "R": 1.0},
        )

        if mode == "normal":
            merged.setdefault(
                "scripted_actions",
                ["3", "1", "1", "5", "4", "1", "2", "1"],
            )
        elif mode == "boss":
            merged.setdefault(
                "scripted_actions",
                ["3", "1", "3", "5", "4", "1", "3", "1", "5", "2", "1"],
            )
        return merged
    #--------------------------------
    #Gegner Streaming
    #--------------------------------
    def _slow_print_lines(self, lines, delay_char: float = 0.02, delay_line: float = 0.25):
        """
        Gibt Zeilen langsam wie ein Stream im Terminal aus (Typewriter-Effekt).
        """
        for line in lines:
            for ch in line:
                try:
                    sys.stdout.write(ch)
                    sys.stdout.flush()
                except Exception:
                    pass
                time.sleep(delay_char)
            try:
                sys.stdout.write("\n")
                sys.stdout.flush()
            except Exception:
                pass
            time.sleep(delay_line)

    # =====================================================
    # AFTER RESPONSE → automatische Heilung
    # =====================================================

    def after_response(self, reply, context=None):
        """
        Nach jeder KI-Antwort:
        - Kampf-Log sammeln
        - ggf. Heal-Text
        - HUD nur im Terminal anzeigen (und nur jede 4. Nachricht)
        - Kampf-/Heal-Text langsam im Terminal ausgeben (Typewriter)
        """
        if not isinstance(reply, str):
            reply = ""

        raw_blocks = []

        # 1) Kampf-Logs aus before_chat anhängen
        if isinstance(context, dict):
            battle_logs = context.pop("battle_log", [])
            for log in battle_logs:
                if isinstance(log, str) and log.strip():
                    raw_blocks.append(log)

        # 2) Optional: Heal nach Kämpfen
        try:
            if self.state is not None:
                s = self.state.state
                if s["flags"].get("needs_heal"):
                    heal_msg = self.state.heal_after_chat()
                    if isinstance(heal_msg, str) and heal_msg.strip():
                        raw_blocks.append(heal_msg)
        except Exception:
            pass

        # 3) HUD nur jede 4. Nachricht anzeigen – NUR im Terminal
        try:
            show_hud = False
            if self.state is not None:
                s = self.state.state
                stats = s.get("stats", {})
                total = int(stats.get("messages_total", 0))
                # jede 4. User-Nachricht: 4, 8, 12, ...
                if total > 0 and total % 4 == 0:
                    show_hud = True

            if show_hud and hasattr(self, "_build_hud"):
                hud = self._build_hud(context)
                if hud:
                    print("\n" + hud)
        except Exception:
            pass

        # 4) Battle-/Heal-Blöcke in einzelne Zeilen aufsplitten und langsam ausgeben
        if raw_blocks:
            lines = []
            for block in raw_blocks:
                for ln in block.splitlines():
                    if ln.strip():
                        lines.append(ln)

            if lines:
                # Header „Verlauf des Kampfes“ vor die eigentlichen Zeilen
                header = [
                    "",  # kleine Leerzeile
                    "📜 Verlauf des Kampfes:",
                    ""
                ]
                try:
                    self._slow_print_lines(header + lines)
                except Exception:
                    # Fallback: normale Ausgabe
                    print("\n" + "\n".join(header + lines))

        # WICHTIG: die eigentliche KI-Antwort bleibt normal gestreamt
        return reply

    # =====================================================
    # STARTUP MESSAGE
    # =====================================================
    def on_startup(self, context=None):
        print(
            Fore.GREEN
            + "⚔️ MAAT RPG Battle-Plugin geladen – Zufallskämpfe, Deep XP, Bosse & Finalbosse aktiv."
            + Style.RESET_ALL
        )
