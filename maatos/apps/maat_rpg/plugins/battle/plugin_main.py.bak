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



# =====================================================
# 🔊 LEVEL-UP FX (Sound + Animation, lokal im RPG)
# =====================================================
def play_levelup_sound(plugin_dir):
    """
    Spielt einmalig einen Level-Up-Sound ab, falls
    plugins/maat_rpg/sounds/levelup.mp3 existiert.
    """
    sound_path = os.path.join(plugin_dir, "sounds", "levelup.mp3")
    if os.path.isfile(sound_path):
        try:
            # afplay = macOS, läuft im Hintergrund
            subprocess.Popen(
                ["afplay", sound_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


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
        _lu_skill_line(skill)
    except Exception as e:
        print(f"[LEVELUP FX ERROR] {e}")

# =====================================================
# 🎵 MUSIC MANAGER
# =====================================================
class BattleMusicManager:
    def __init__(self, track_path: str | None):
        self.track_path = track_path
        self._running = False
        self._thread = None

    def _loop(self):
        while self._running:
            if self.track_path and os.path.isfile(self.track_path):
                try:
                    subprocess.call(
                        ["afplay", self.track_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    time.sleep(1)
            else:
                time.sleep(1)

    def start(self):
        if not self.track_path or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        try:
            subprocess.call(
                ["killall", "afplay"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def victory_jingle(self, path: str | None):
        if path and os.path.isfile(path):
            try:
                subprocess.Popen(
                    ["afplay", path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass


# =====================================================
# 📦 BATTLE STATE + DEEP XP FIELDS
# =====================================================
class BattleState:
    def __init__(self, base_dir: str):
        os.makedirs(base_dir, exist_ok=True)
        self.state_path = os.path.join(base_dir, "battle_state.json")
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


# =====================================================
# ⚔️ KAMPF-KERN
# =====================================================
class BattleCore:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = plugin_dir
        state_dir = os.path.join(plugin_dir, "battle_state")
        self.state = BattleState(state_dir)

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
            new_skill = roll_new_skill(p["skills"])
            if len(p["skills"]) < 5:
                p["skills"].append(new_skill)
                skill_msg = f"Du hast eine neue Fertigkeit erlernt: {new_skill}!"
            else:
                replaced = p["skills"][0]
                p["skills"][0] = new_skill
                skill_msg = f"Fertigkeit {replaced} wurde durch {new_skill} ersetzt!"

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
        player_hp = p["hp"]

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
        intro = f"🎮 **{enemy_name}** erscheint! (Typ: {ftype.upper()})"
        log_lines.append(intro)
        self._slow_line(intro)

        principles = {
            "1": "Harmonie",
            "2": "Balance",
            "3": "Schöpfungskraft",
            "4": "Verbundenheit",
            "5": "Respekt",
        }

        try:
            while player_hp > 0 and enemy_hp > 0:
                print("\n------------------------------------------")
                print(f"DU           HP: {player_hp}/{p['max_hp']}")
                print(f"{enemy_name} HP: {enemy_hp}")
                print("------------------------------------------")
                print("1) Angriff")
                print("2) Skills")
                print("3) Flucht")
                choice = input("Aktion: ").strip()

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
                        sub = input("Wähle [1–6]: ").strip()
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

                        # 🔹 Schöpfungskraft-Buff
                        final_dmg = final_dmg * attack_mult

                        # 🔹 Harmonie-Crit (kleiner Zusatzschlag)
                        crit_txt = ""
                        if random.random() < crit_chance:
                            bonus = max(1, int(final_dmg * 0.20))  # +20% als Bonus
                            final_dmg += bonus
                            crit_txt = f" (Harmonie-Crit! +{bonus} Bonus-Schaden)"

                        final_dmg = max(1, int(round(final_dmg)))

                        enemy_hp -= final_dmg
                        line = f"⚔ Du setzt **{atk_type}** ein → {final_dmg} Schaden!"
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
                        sub = input("Wähle: ").strip()
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
                                enemy_hp -= final_dmg
                                line = f"✨ Skill **{sk}** trifft für {final_dmg} Schaden!"
                                self._slow_line(line)
                                log_lines.append(f"Skill {sk}: {final_dmg} Schaden")
                        except ValueError:
                            print("Ungültige Eingabe.")

                elif choice == "3":
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

                # Gegnerzug
                if enemy_hp > 0:
                    dmg_in = max(1, enemy_dmg_base + random.randint(-3, 4))

                    # 🔹 Balance reduziert eingehenden Schaden
                    dmg_in = dmg_in * defense_mult
                    dmg_in = max(1, int(round(dmg_in)))

                    player_hp -= dmg_in
                    line = f"💥 {enemy_name} trifft dich für {dmg_in} Schaden!"
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
            if inner_boss:
                msg = self._inner_boss_message(inner_boss, outcome="victory")
                self._slow_line(msg, delay_char=0.01, delay_line=0.6)
                log_lines.append(f"[INNER BOSS] {inner_boss['name']} meldet sich nach dem Sieg.")
            
        else:
            # Niederlage
            line = f"\n💀 Du wurdest von **{enemy_name}** besiegt..."
            self._slow_line(line)
            log_lines.append(f"Niederlage gegen {enemy_name}")
            if inner_boss:
                msg = self._inner_boss_message(inner_boss, outcome="defeat")
                self._slow_line(msg, delay_char=0.01, delay_line=0.6)
                log_lines.append(f"[INNER BOSS] {inner_boss['name']} verstärkt sich nach der Niederlage.")
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
            out = self.core.run_fight("normal", context or {})
            return True, out

        if base == "/fightboss":
            out = self.core.run_fight("boss", context or {})
            return True, out

        if base == "/fightfinal":
            out = self.core.run_fight("final", context or {})
            return True, out

        if base == "/usepotion":
            return True, self._use_potion()

        # ---------------- STATUS / XP ----------------
        if base == "/xp":
            s = self.core.state.state
            p = s["player"]
            stats = s["stats"]
            world = s["world"]

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
        """
        Einfaches Titel-System nach Level.
        Kannst du später beliebig verändern.
        """
        if level >= 15:
            return "Äonischer Resonanzmeister"
        elif level >= 10:
            return "Hüter der Harmonie"
        elif level >= 5:
            return "Maat-Krieger"
        else:
            return "Suchender im Äon der Maat"

    def _build_hud(self) -> str:
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
            print(
                Fore.YELLOW
                + f"\n🌟 DU STEIGST AUF! Level {old_lvl} → {new_lvl}"
                + Style.RESET_ALL
            )

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
                hud = self._build_hud()
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