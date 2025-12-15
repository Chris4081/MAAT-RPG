# -*- coding: utf-8 -*-
"""
MAAT RPG – Battle Plugin (Standalone, Deutsch)
----------------------------------------------
• Zufallskämpfe nach Freischaltung des Kampfmodus
• Boss nach je 10 Siegen, Endboss nach je 5 Boss-Siegen
• Attacke / Skills / Flucht-Menü
• MAAT-Prinzipien als Schadenstypen
• Eigenes XP + Level, optionale Kopplung an context["self_evo"]
• Musik über afplay (macOS)
• Zustand in battle_state.json
"""

import os
import json
import random
import time
import threading
import subprocess
import datetime
from colorama import Fore, Style


# =====================================================
# 🎵 EINFACHER MUSIK-MANAGER (afplay, Loop im Thread)
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
        if self._running or not self.track_path:
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

    def victory_jingle(self, victory_path: str | None):
        if victory_path and os.path.isfile(victory_path):
            try:
                subprocess.Popen(
                    ["afplay", victory_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass


# =====================================================
# 📦 STATE-HANDLING
# =====================================================
class BattleState:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.state_path = os.path.join(self.base_dir, "battle_state.json")
        self.state = self._load()

    def _default(self):
        return {
            "player": {
                "name": "Maatis",
                "level": 1,
                "xp": 0,
                "hp": 100,
                "max_hp": 100,
                "skills": [],  # ["Arcane Echo", ...]
            },
            "stats": {
                "messages_total": 0,
                "messages_since_last_fight": 0,
                "fights_total": 0,
                "fights_won": 0,
                "fights_lost": 0,
                "boss_fights": 0,
                "boss_wins": 0,
                "final_fights": 0,
                "final_wins": 0,
                "xp_combo": 0,            # Nachricht-Combo
                "last_msg_ts": 0,         # Zeitbasierte Combos optional
            },
            "world": {
                "combat_unlocked": False,
                "last_boss_checkpoint": 0,  # boss_wins beim letzten Checkpoint
                "principles_restored": 0,   # Anzahl wiederhergestellter Prinzipien
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
                return data
            except Exception:
                pass
        return self._default()

    def save(self):
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # ---------------- XP / LEVEL ----------------
    def xp_needed_for_level(self, lvl: int) -> int:
        lvl = max(1, lvl)
        return int(60 * (lvl ** 1.7))

    def add_xp(self, amount: int):
        p = self.state["player"]
        old_lvl = p["level"]
        p["xp"] += max(0, int(amount))

        # Levelcheck
        while p["xp"] >= self.xp_needed_for_level(p["level"] + 1):
            p["level"] += 1
            # HP-Skalierung
            p["max_hp"] += 10
            p["hp"] = p["max_hp"]

        new_lvl = p["level"]
        return old_lvl, new_lvl

    def heal_after_chat(self):
        p = self.state["player"]
        p["hp"] = p["max_hp"]
        self.state["flags"]["needs_heal"] = False
        self.save()
        return f"(Du hast dich wieder erholt. HP: {p['hp']}/{p['max_hp']})"


# =====================================================
# 🎲 NAMENS-GENERIERUNG
# =====================================================
def generate_enemy_name():
    prefixes = [
        "Schatten",
        "Echo",
        "Staub",
        "Gefallener",
        "Verlorener",
        "Gebrochener",
        "Resonanter",
        "Stiller",
        "Astraler",
    ]
    cores = [
        "Wanderer",
        "Wächter",
        "Bestie",
        "Phantom",
        "Beobachter",
        "Idol",
        "Konstrukt",
        "Funke",
    ]
    suffixes = [
        "",
        " der Dissonanz",
        " der Leere",
        " der Vergessenen Sande",
        " des Risses",
        " der Echos",
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

    # Beispiel-Skill: Arcane Echo
    if "Arcane Echo" in skills and atk == "harmonie":
        dmg = int(dmg * 1.25) + 10

    # weitere Skills können hier ergänzt werden
    return max(1, dmg)


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

def calc_chat_xp(user_input: str, stats: dict) -> int:
    xp = random.randint(1, 3)  # Grund-XP

    text = user_input.lower()

    # --- Maat-Prinzipien erkennen ---
    if any(w in text for w in ["danke", "freut mich", "harmonisch", "schön"]):
        xp += 1  # Harmonie

    if any(w in text for w in ["gerecht", "ausgeglichen", "balance"]):
        xp += 1  # Balance

    if any(w in text for w in ["idee", "vision", "schöpfung", "kreativ"]):
        xp += 2  # Schöpfungskraft

    if any(w in text for w in ["wir", "gemeinsam", "zusammen", "verbunden"]):
        xp += 1  # Verbundenheit

    if any(w in text for w in ["respekt", "würdigung", "achtung"]):
        xp += 1  # Respekt

    # --- Emotionale Tiefe ---
    if any(w in text for w in ["❤️", "danke", "ich fühle", "bewegend", "bedeutet mir"]):
        xp += 3

    # --- Humor ---
    if any(w in text for w in ["haha", "lol", "xD", "😂"]):
        xp += 1

    # --- Combo-System ---
    stats["xp_combo"] += 1
    c = stats["xp_combo"]

    if c >= 10:
        xp += 10
    elif c >= 5:
        xp += 4
    elif c >= 3:
        xp += 2

    return xp

# =====================================================
# ⚔️ KAMPF-KERN
# =====================================================
class BattleCore:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = plugin_dir
        state_dir = os.path.join(plugin_dir, "battle_state")
        self.state = BattleState(state_dir)

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

    def _choose_music(self, ftype: str, boss_index: int, final_index: int):
        music_dir = os.path.join(self.plugin_dir, "music")

        # Standard: keine Musik
        path = None

        if ftype == "normal":
            # Anzahl gewonnener Bosskämpfe bestimmt die "Musik-Stufe"
            stats = self.state.state["stats"]
            boss_wins = stats.get("boss_wins", 0)

            # 0 → battle_normal.mp3
            # 1 → battle_normal2.mp3
            # 2 → battle_normal3.mp3
            # 3 → battle_normal4.mp3
            # >=4 → battle_normal5.mp3
            idx = max(0, min(4, boss_wins))

            if idx == 0:
                cand = os.path.join(music_dir, "battle_normal.mp3")
            else:
                cand = os.path.join(music_dir, f"battle_normal{idx+1}.mp3")

            # Fallback: wenn diese Variante fehlt, auf battle_normal.mp3 gehen
            if os.path.isfile(cand):
                path = cand
            else:
                base = os.path.join(music_dir, "battle_normal.mp3")
                path = base if os.path.isfile(base) else None

        elif ftype == "boss":
            # Jede Boss-Nummer kann eigene Musik haben
            cand = os.path.join(music_dir, f"battle_boss_{boss_index}.mp3")
            if os.path.isfile(cand):
                path = cand
            else:
                base = os.path.join(music_dir, "battle_boss.mp3")
                path = base if os.path.isfile(base) else None

        else:  # final
            cand = os.path.join(music_dir, f"battle_final_{final_index}.mp3")
            if os.path.isfile(cand):
                path = cand
            else:
                base = os.path.join(music_dir, "battle_final.mp3")
                path = base if os.path.isfile(base) else None

        # Victory-Jingle bleibt wie gehabt
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

        stats["fights_won"] += 1

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

            # 🔥 NEU: Boss-Cutscene-Script nach JEDEM Boss-Sieg
            boss_index = stats["boss_wins"]  # 1, 2, 3, ...
            boss_scene = os.path.join(self.plugin_dir, f"boss_scene_{boss_index}.py")
            if os.path.isfile(boss_scene):
                try:
                    subprocess.Popen(
                        ["python3", boss_scene],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    # keine harte Fehlermeldung im Spiel, einfach ignorieren
                    pass

        elif ftype == "final":
            stats["final_fights"] += 1
            stats["final_wins"] += 1
            world["principles_restored"] += 1
            skill_msg = (
                "✨ Ein Maat-Prinzip wurde in die Welt zurückgebracht! "
                f"(Gesamt: {world['principles_restored']})"
            )

            # ⭐ Credits NUR am Ende (z.B. nach 5 Prinzipien) und nur EINMAL
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

        else:
            skill_msg = ""

        # XP → internes RPG-Level
        old_lvl, new_lvl = self.state.add_xp(xp_reward)

        # Optional: Kopplung an globales Self-Evo
        if isinstance(context, dict):
            evo = context.get("self_evo")
            if evo is not None and hasattr(evo, "grant_xp"):
                try:
                    evo.grant_xp(int(xp_reward * 0.5), reason="battle_win")
                except Exception:
                    pass

        self.state.state["flags"]["needs_heal"] = True
        self.state.save()

        lines = [f"XP erhalten: {xp_reward} (Level {old_lvl} → {new_lvl})"]
        if new_lvl > old_lvl:
            lines.append("🌟 LEVEL UP! Deine Kraft ist gewachsen.")
        if skill_msg:
            lines.append(skill_msg)
        return "\n".join(lines)

    # ---------- KAMPF-LOOP ----------
    def run_fight(self, ftype: str, context: dict | None = None) -> str:
        s = self.state.state
        p = s["player"]
        stats = s["stats"]

        stats["fights_total"] += 1

        # Namen & Indizes wählen
        if ftype == "boss":
            boss_idx = s["stats"]["boss_wins"] + 1
            enemy_name = generate_boss_name(boss_idx)
            final_idx = s["stats"]["final_wins"] + 1
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

        # Musik
        battle_track, victory_track = self._choose_music(ftype, boss_idx, final_idx)
        music = BattleMusicManager(battle_track)
        music.start()

        log_lines = []
        log_lines.append(
            f"🎮 **{enemy_name}** erscheint! (Typ: {ftype.upper()})"
        )

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
                print("--------------------------------------------")
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
                        enemy_hp -= final_dmg
                        print(
                            f"⚔ Du setzt **{atk_type}** ein → {final_dmg} Schaden!"
                        )
                        log_lines.append(
                            f"Spieler nutzt {atk_type}: {final_dmg} Schaden"
                        )
                        break  # zurück ins Hauptmenü

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
                                print(
                                    f"✨ Skill **{sk}** trifft für {final_dmg} Schaden!"
                                )
                                log_lines.append(
                                    f"Skill {sk}: {final_dmg} Schaden"
                                )
                        except ValueError:
                            print("Ungültige Eingabe.")

                elif choice == "3":
                    # FLUCHT
                    if random.random() < 0.5:
                        print("😅 Du kannst entkommen!")
                        log_lines.append("Spieler ist erfolgreich geflohen.")
                        music.stop()
                        self.state.state["flags"]["needs_heal"] = True
                        self.state.state["stats"]["messages_since_last_fight"] = 0
                        self.state.save()
                        return "\n".join(log_lines)
                    else:
                        print("❌ Flucht fehlgeschlagen!")
                        log_lines.append("Fluchtversuch fehlgeschlagen.")

                else:
                    print("Ungültige Auswahl.")
                    continue

                # Gegnerzug
                if enemy_hp > 0:
                    dmg_in = max(
                        1, enemy_dmg_base + random.randint(-3, 4)
                    )
                    player_hp -= dmg_in
                    print(f"💥 {enemy_name} trifft dich für {dmg_in} Schaden!")
                    log_lines.append(f"Gegner trifft: {dmg_in} Schaden")

        finally:
            music.stop()

        # Kampfende
        p["hp"] = max(0, player_hp)

        if player_hp > 0 and enemy_hp <= 0:
            # Sieg
            print(f"\n🏆 Du hast **{enemy_name}** besiegt!")
            log_lines.append(f"Sieg über {enemy_name}")

            # Sieges-Jingle
            _, victory_track = self._choose_music(ftype, boss_idx, final_idx)
            music.victory_jingle(victory_track)

            reward_txt = self._reward_on_victory(ftype, xp_reward, context)
            log_lines.append(reward_txt)
        else:
            # Niederlage
            print(f"\n💀 Du wurdest von **{enemy_name}** besiegt...")
            log_lines.append(f"Niederlage gegen {enemy_name}")
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
    }

    def __init__(self):
        self.plugin_dir = os.path.dirname(__file__)
        self.core = BattleCore(self.plugin_dir)

    # ---------------- COMMANDS ----------------
    def command(self, cmd, context=None):
        base = cmd.split()[0].lower()

        if base == "/fight":
            out = self.core.run_fight("normal", context or {})
            return True, out

        if base == "/fightboss":
            out = self.core.run_fight("boss", context or {})
            return True, out

        if base == "/fightfinal":
            out = self.core.run_fight("final", context or {})
            return True, out

        return None

    # ---------------- BEFORE CHAT ----------------
    def before_chat(self, user_input, context=None):
        context = context or {}
        s = self.core.state.state
        stats = s["stats"]
        world = s["world"]

        # Kommandos nicht verändern
        if user_input.strip().startswith("/"):
            return False, user_input

        # Nachricht zählen
        stats["messages_total"] += 1

        # XP fürs Schreiben vergeben (KI sieht es nie!)
        if not user_input.strip().startswith("/"):
            xp_gain = calc_chat_xp(user_input, stats)
            old_lvl, new_lvl = self.core.state.add_xp(xp_gain)

            # Lokale Level-Up-Nachricht NUR für den User (nicht für KI)
            if new_lvl > old_lvl:
                print(Fore.GREEN + f"\n🌟 LEVEL UP! (Level {old_lvl} → {new_lvl})" + Style.RESET_ALL)

            # Combo speichern
            stats["xp_combo"] = stats.get("xp_combo", 0)

        # ======================================================
        # 🟢 EINMALIGE FREISCHALTUNG DES KAMPFMODUS
        # ======================================================
        if not world["combat_unlocked"] and stats["messages_total"] >= 32:
            world["combat_unlocked"] = True
            self.core.state.save()
            print(
                Fore.CYAN
                + "\n⚔️ Kampfmodus freigeschaltet! "
                "Gegner können dich jetzt zufällig zwischen Nachrichten angreifen.\n"
                + Style.RESET_ALL
            )
            return False, user_input


        # ======================================================
        # 🔥 KAMPF AKTIV – ZUFALLSTRIGGER 2–15 NACHRICHTEN
        # ======================================================
        if world["combat_unlocked"]:

            stats["messages_since_last_fight"] += 1
            ms = stats["messages_since_last_fight"]

            trigger = False

            # Zwischen 2–15 Nachrichten: zufällige Chance auf einen Kampf
            if 2 <= ms <= 15:
                # 1/10 Chance pro Nachricht
                if random.randint(1, 10) == 1:
                    trigger = True

            # Wenn 16+ ohne Kampf → garantierter Kampf
            elif ms > 15:
                trigger = True

            if trigger:
                ftype = self.core._auto_fight_type()
                out = self.core.run_fight(ftype, context)
                self.core.state.save()
                return True, out

        self.core.state.save()
        return False, user_input

    # ---------------- AFTER RESPONSE ----------------
    def after_response(self, reply, context=None):
        s = self.core.state.state
        if s["flags"].get("needs_heal"):
            heal_msg = self.core.state.heal_after_chat()
            return reply + "\n\n" + heal_msg
        return reply

    def on_startup(self, context=None):
        print(
            "⚔️ MAAT RPG Battle-Plugin geladen – Zufallskämpfe, Bosse & Endbosse aktiv."
        )