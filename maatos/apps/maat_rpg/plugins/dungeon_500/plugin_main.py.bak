# -*- coding: utf-8 -*-
"""
MAAT-RPG Dungeon Plugin — "Kristallpfad der Fünfhundert"
-------------------------------------------------------
Funktionen:
• Dungeon öffnet sich nach 500 Nachrichten
• Zufällige Boss-Namen (kristall / astral / schall)
• 3 Räume + Boss
• Musik optional (Dungeon-/Boss-Theme)
• Voll kompatibel mit MAAT-RPG BattleCore
"""

import os
import json
import random
from datetime import datetime
import importlib.util

# =====================================================
# 🔗 BattleCore & MusicManager laden
# =====================================================
def _load_battle_plugin():
    battle_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "battle", "plugin_main.py")
    )

    if not os.path.isfile(battle_path):
        print("⚠️ [Dungeon500] Battle-Plugin wurde nicht gefunden:", battle_path)
        return None, None

    try:
        spec = importlib.util.spec_from_file_location("maat_battle", battle_path)
        battle_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(battle_mod)

        BattleCore = getattr(battle_mod, "BattleCore", None)
        BattleMusicManager = getattr(battle_mod, "BattleMusicManager", None)
        return BattleCore, BattleMusicManager
    except Exception as e:
        print("⚠️ [Dungeon500] Fehler beim Laden des Battle-Plugins:", e)
        return None, None


BattleCore, BattleMusicManager = _load_battle_plugin()


# =====================================================
# 🧱 STATE
# =====================================================
class Dungeon500State:
    def __init__(self, base_dir: str):
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        self.path = os.path.join(data_dir, "state500.json")
        self.data = self._load()

    def _default(self):
        return {
            "msg": 0,
            "unlocked": False,
            "runs": 0,
            "completed": False,
            "last_entered": None,
        }

    def _load(self):
        if os.path.isfile(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return self._default()

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)


# =====================================================
# 🧙 BOSSE – Zufällige Namen
# =====================================================
BOSS_NAMES = [
    "Astraelion, Splitter des Himmels",
    "Crystal Warden Seralyth",
    "Der Schallbrecher von Arkona",
    "Vel'Shar, Hüter der Klangklingen",
    "Elyndra, Königin der Glassphäre",
    "Thornak, Resonanz-Brecher",
    "Die 500 Gesichter der Stille",
    "Shardmaster Kyr'Vel",
    "Aionis der Transparente",
    "Echo-Lord Varuun",
]

def random_boss_name():
    return random.choice(BOSS_NAMES)


# =====================================================
# 🏰 DUNGEON 500
# =====================================================
class Dungeon500:
    UNLOCK_AT = 500

    def __init__(self, base_dir: str, core=None):
        self.base_dir = base_dir
        self.core = core
        self.state = Dungeon500State(base_dir)

        # Musik-Dateien (optional)
        self.music_theme = os.path.join(base_dir, "music", "crystal_theme.mp3")
        self.boss_theme = os.path.join(base_dir, "music", "crystal_boss.mp3")

        self.music_manager = None
        self.boss_music_manager = None

        if BattleMusicManager:
            if os.path.isfile(self.music_theme):
                self.music_manager = BattleMusicManager(self.music_theme)
            if os.path.isfile(self.boss_theme):
                self.boss_music_manager = BattleMusicManager(self.boss_theme)

        # BattleCore anbinden
        self.battle_core = None
        if self.core is not None and hasattr(self.core, "battle"):
            # Wenn dein Core bereits einen BattleCore besitzt
            self.battle_core = self.core.battle
        elif BattleCore is not None:
            # Fallback: eigenen BattleCore instanzieren
            try:
                battle_dir = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "battle")
                )
                self.battle_core = BattleCore(plugin_dir=battle_dir)
                print("✅ [Dungeon500] Eigenen BattleCore initialisiert.")
            except Exception as e:
                print("⚠️ [Dungeon500] Fehler beim Initialisieren des BattleCore:", e)
                self.battle_core = None

    # ================================
    # STATUS
    # ================================
    def status(self):
        d = self.state.data
        if not d["unlocked"]:
            remain = max(0, self.UNLOCK_AT - d["msg"])
            return (
                f"🔒 **Dungeon 500: Kristallpfad der Fünfhundert**\n"
                f"Nachrichten: {d['msg']} / {self.UNLOCK_AT}\n"
                f"✨ Noch {remain} bis zur Öffnung.\n"
            )

        return (
            f"🏰 **Dungeon 500: Kristallpfad der Fünfhundert**\n"
            f"Runs: {d['runs']}\n"
            f"Completed: {d['completed']}\n"
            f"Letzter Eintritt: {d['last_entered']}\n"
            f"BattleCore: {'AKTIV ✅' if self.battle_core else 'FEHLT (Demo) ⚠️'}\n"
        )

    # ================================
    # BETRETEN
    # ================================
    def enter(self):
        d = self.state.data

        if not d["unlocked"]:
            remain = max(0, self.UNLOCK_AT - d["msg"])
            return f"🔒 Das Tor ist noch versiegelt.\n✨ Noch {remain} Nachrichten."

        d["runs"] += 1
        d["last_entered"] = datetime.now().isoformat(timespec="seconds")
        self.state.save()

        if self.music_manager:
            self.music_manager.start()

        return self._room_1()

    # ================================
    # RÄUME
    # ================================
    def _room_1(self):
        return (
            "💎 Die Kristalle an den Wänden beginnen leise zu singen.\n"
            "Ein kühles, blaues Licht erfüllt den Gang.\n"
            "👉 Weiter mit: `/d500 next`"
        )

    def _room_2(self):
        return (
            "🔷 Brechende Lichtstrahlen tanzen über den Boden wie wandernde Runen.\n"
            "Du spürst, wie der Raum auf deine Schritte reagiert.\n"
            "👉 Weiter mit: `/d500 next`"
        )

    def _room_3(self):
        return (
            "✨ Vor dir erhebt sich ein Tor aus poliertem Glas, in dem sich unzählige Welten spiegeln.\n"
            "Zwischen den Reflexionen flackert eine Silhouette.\n"
            "👉 Der Boss wartet: `/d500 boss`"
        )

    # ================================
    # BOSS
    # ================================
    def boss(self):
        # Hintergrundmusik des normalen Dungeons stoppen
        if self.music_manager:
            self.music_manager.stop()

        boss_name = "Herr der 500 Schatten"
        intro = f"👑 **{boss_name} tritt aus dem Schattenkreis hervor!**\n\n"

        if self.battle_core:
            try:
                # Musikpfade absolut erzeugen
                music_cfg = {}
                if os.path.isfile(self.boss_theme):
                    music_cfg["battle"] = self.boss_theme   # d500 Bossmusik

                # Victory-Jingle für Dungeon 500:
                victory_path = os.path.join(self.base_dir, "music", "victory_500.mp3")
                if os.path.isfile(victory_path):
                    music_cfg["victory"] = victory_path

                # Kontext an BattleCore übergeben
                ctx = {
                    "boss_name": boss_name,
                    "music": music_cfg,
                }

                # WICHTIG: BattleCore verwendet NUR die Musik aus dem Kontext
                result = self.battle_core.run_fight("boss", context=ctx)

            except Exception as e:
                result = f"⚠ Fehler beim Bosskampf: {e}"

        else:
            # Fallback: Demo-Kampf ohne BattleCore
            if self.boss_music_manager:
                self.boss_music_manager.start()
            result = f"⚔ (Demo) Boss **{boss_name}** wurde besiegt!"
            if self.boss_music_manager:
                self.boss_music_manager.stop()

        # Dungeon-Status updaten
        d = self.state.data
        d["completed"] = True
        self.state.save()

        return intro + result


# =====================================================
# 🔌 PLUGIN MAIN
# =====================================================
class Plugin:
    type = "chat"
    commands = {
        "/d500": "Dungeon 500 betreten",
        "/d500 next": "Nächsten Raum betreten",
        "/d500 boss": "Bosskampf starten",
        "/d500 status": "Status anzeigen",
        "/d500 reset": "Dungeon zurücksetzen",
    }

    def __init__(self, plugin_dir=None, core=None):
        if plugin_dir is None:
            plugin_dir = os.path.dirname(__file__)
        self.plugin_dir = plugin_dir
        self.core = core
        self._room_stage = 0
        self.dungeon = Dungeon500(base_dir=plugin_dir, core=core)

    def command(self, cmd, context=None):
        c = cmd.strip()

        if c == "/d500":
            self._room_stage = 1
            return True, self.dungeon.enter()

        if c == "/d500 next":
            if self._room_stage == 1:
                self._room_stage = 2
                return True, self.dungeon._room_2()
            if self._room_stage == 2:
                self._room_stage = 3
                return True, self.dungeon._room_3()
            return True, "⚠ Der Boss wartet bereits. Nutze: `/d500 boss`"

        if c == "/d500 boss":
            return True, self.dungeon.boss()

        if c == "/d500 status":
            return True, self.dungeon.status()

        if c == "/d500 reset":
            self.dungeon.state.data = self.dungeon.state._default()
            self.dungeon.state.save()
            self._room_stage = 0
            return True, "🔁 Dungeon 500 zurückgesetzt."
        return None

    def before_chat(self, user_input, context=None):
        """
        Zählt jede Nachricht und schaltet den Dungeon nach 500 Messages frei.
        """
        d = self.dungeon.state.data
        d["msg"] += 1
        if not d["unlocked"] and d["msg"] >= Dungeon500.UNLOCK_AT:
            d["unlocked"] = True
        self.dungeon.state.save()
        return False, user_input

    def after_response(self, reply, context=None):
        return reply