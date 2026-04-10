# -*- coding: utf-8 -*-
"""
MAAT-RPG Dungeon Plugin — "Tor der Tausend Echos"
-------------------------------------------------
Funktionen:
• Dungeon öffnet sich nach 1000 Nachrichten
• Zufällige Boss-Namen
• 3 Räume + Boss
• Musik optional
"""

import os
import json
import random
from datetime import datetime
import importlib.util
from shared.core.maat_paths import data_file, state_file, log_file
from shared.core.rpg_i18n import get_language


def _lang():
    return get_language(("de", "en"))


def _t(de: str, en: str) -> str:
    return en if _lang() == "en" else de

# =====================================================
# 🔗 BattleCore & MusicManager laden
# =====================================================
def _load_battle_plugin():
    battle_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "battle", "plugin_main.py")
    )

    if not os.path.isfile(battle_path):
        print("⚠️ [Dungeon1000] Battle-Plugin wurde nicht gefunden.")
        return None, None

    spec = importlib.util.spec_from_file_location("maat_battle", battle_path)
    battle_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(battle_mod)

    BattleCore = getattr(battle_mod, "BattleCore", None)
    BattleMusicManager = getattr(battle_mod, "BattleMusicManager", None)
    return BattleCore, BattleMusicManager


BattleCore, BattleMusicManager = _load_battle_plugin()


# =====================================================
# 🧱 STATE
# =====================================================
class Dungeon1000State:
    def __init__(self, base_dir: str):
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        self.path = state_file('state1000.json')
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
                    data = json.load(f)
                    if isinstance(data, dict):
                        merged = self._default()
                        merged.update(data)
                        return merged
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
    "Echo-Warden Xaroth",
    "The Thousand-Faced Oracle",
    "Vox Tenebris",
    "Aurelia der Klanglosen",
    "Shardmaster Velyr",
    "Der Verstummte Titan",
    "Hüterin der Leeren Stimmen",
    "Archon Umbra-Echo",
    "Seraph der Vergessenen Worte",
    "Primarch der Resonanz"
]


def random_boss_name():
    return random.choice(BOSS_NAMES)


# =====================================================
# 🏰 DUNGEON 1000
# =====================================================
class Dungeon1000:
    UNLOCK_AT = 1000

    def __init__(self, base_dir: str, core=None):
        self.base_dir = base_dir
        self.core = core
        self.state = Dungeon1000State(base_dir)

        # Musik
        self.music_theme = os.path.join(base_dir, "music", "dungeon1000_theme.mp3")
        self.boss_theme  = os.path.join(base_dir, "music", "boss1000_theme.mp3")

        self.music_manager = None
        self.boss_music_manager = None

        if BattleMusicManager:
            if os.path.isfile(self.music_theme):
                self.music_manager = BattleMusicManager(self.music_theme)
            if os.path.isfile(self.boss_theme):
                self.boss_music_manager = BattleMusicManager(self.boss_theme)

        # BattleCore
        self.battle_core = None
        if self.core and hasattr(self.core, "battle"):
            self.battle_core = self.core.battle
        elif BattleCore:
            try:
                battle_dir = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "battle")
                )
                self.battle_core = BattleCore(plugin_dir=battle_dir)
                print("✅ [Dungeon1000] BattleCore initialisiert.")
            except Exception as e:
                print("⚠️ [Dungeon1000] Fehler beim Initialisieren:", e)

    # ---------------------------
    def status(self):
        d = self.state.data
        if not d["unlocked"]:
            remain = self.UNLOCK_AT - d["msg"]
            return (
                _t("🔒 **Dungeon 1000: Tor der Tausend Echos**\n", "🔒 **Dungeon 1000: Gate of a Thousand Echoes**\n")
                + f"{_t('Nachrichten', 'Messages')}: {d['msg']} / {self.UNLOCK_AT}\n"
                + f"✨ {_t('Noch', 'Still')} {remain} {_t('bis zur Oeffnung.', 'until it opens.')}\n"
            )
        return (
            _t("🏰 **Dungeon 1000: Tor der Tausend Echos**\n", "🏰 **Dungeon 1000: Gate of a Thousand Echoes**\n")
            + f"Runs: {d['runs']}\n"
            + f"Completed: {d['completed']}\n"
            + f"{_t('Letzter Eintritt', 'Last entry')}: {d['last_entered']}\n"
        )

    # ---------------------------
    def enter(self):
        d = self.state.data
        if not d["unlocked"]:
            remain = self.UNLOCK_AT - d["msg"]
            return _t(
                f"🔒 Das Tor ist noch versiegelt.\n✨ Noch {remain} Nachrichten.",
                f"🔒 The gate is still sealed.\n✨ {remain} messages remaining.",
            )

        d["runs"] += 1
        d["last_entered"] = datetime.now().isoformat(timespec="seconds")
        self.state.save()

        if self.music_manager:
            self.music_manager.start()

        return self._room_1()

    # ---------------------------
    def _room_1(self): return _t("💠 Die Luft flirrt vor alter Magie… `/d1000 next`", "💠 The air shimmers with ancient magic… `/d1000 next`")
    def _room_2(self): return _t("🌪 Fluesternde Schatten testen deinen Willen… `/d1000 next`", "🌪 Whispering shadows test your will… `/d1000 next`")
    def _room_3(self): return _t("🔮 Der Boden pulsiert im Takt der Echos… Boss naht. `/d1000 boss`", "🔮 The floor pulses with the rhythm of echoes… the boss approaches. `/d1000 boss`")

    # ---------------------------
    def boss(self):
        boss = random_boss_name()

        # Dungeon-Theme stoppen
        if self.music_manager:
            self.music_manager.stop()

        intro = _t(
            f"👑 **{boss} erscheint aus der Echo-Sphaere!**\n\n",
            f"👑 **{boss} emerges from the echo sphere!**\n\n",
        )

        if self.battle_core:
            try:
                # 🎵 Musik-Override für BattleCore vorbereiten
                music_cfg = {}
                if os.path.isfile(self.boss_theme):
                    music_cfg["battle"] = self.boss_theme
                    # optional: eigene Victory-Musik
                    # music_cfg["victory"] = os.path.join(self.base_dir, "music", "deep_victory.mp3")

                ctx = {
                    "boss_name": boss,
                    "music": music_cfg,
                }

                result = self.battle_core.run_fight("boss", context=ctx)
            except Exception as e:
                result = _t(f"⚠ Fehler beim Bosskampf: {e}", f"⚠ Error during boss fight: {e}")
        else:
            # Fallback ohne BattleCore
            if self.boss_music_manager:
                self.boss_music_manager.start()
            result = _t(
                f"⚔ (Demo) Boss '{boss}' wurde besiegt!",
                f"⚔ (Demo) Boss '{boss}' was defeated!",
            )
            if self.boss_music_manager:
                self.boss_music_manager.stop()

        d = self.state.data
        d["completed"] = True
        self.state.save()

        # Sicherheit
        if self.music_manager:
            self.music_manager.stop()
        if self.boss_music_manager:
            self.boss_music_manager.stop()

        return intro + result


# =====================================================
# 🔌 PLUGIN MAIN
# =====================================================
class Plugin:
    type = "chat"
    commands = {
        "/d1000": {"de": "Dungeon 1000 betreten.", "en": "Enter Dungeon 1000."},
        "/d1000 next": {"de": "Naechsten Raum betreten.", "en": "Enter the next room."},
        "/d1000 boss": {"de": "Bosskampf starten.", "en": "Start the boss fight."},
        "/d1000 status": {"de": "Status anzeigen.", "en": "Show the status."},
        "/d1000 reset": {"de": "Dungeon zuruecksetzen.", "en": "Reset the dungeon."},
    }

    def __init__(self, plugin_dir=None, core=None):
        if plugin_dir is None:
            plugin_dir = os.path.dirname(__file__)
        self.plugin_dir = plugin_dir
        self.core = core
        self._room_stage = 0
        self.dungeon = Dungeon1000(base_dir=plugin_dir, core=core)

    def command(self, cmd, context=None):
        c = cmd.strip()

        if c == "/d1000":
            self._room_stage = 1
            return True, self.dungeon.enter()

        if c == "/d1000 next":
            if self._room_stage == 1:
                self._room_stage = 2
                return True, self.dungeon._room_2()
            if self._room_stage == 2:
                self._room_stage = 3
                return True, self.dungeon._room_3()
            return True, _t("⚠ Boss wartet. `/d1000 boss`", "⚠ The boss is waiting. `/d1000 boss`")

        if c == "/d1000 boss":
            return True, self.dungeon.boss()

        if c == "/d1000 status":
            return True, self.dungeon.status()

        if c == "/d1000 reset":
            self.dungeon.state.data = self.dungeon.state._default()
            self.dungeon.state.save()
            self._room_stage = 0
            return True, _t("🔁 Dungeon 1000 zurueckgesetzt.", "🔁 Dungeon 1000 reset.")

        return None

    def before_chat(self, user_input, context=None):
        d = self.dungeon.state.data
        d.setdefault("msg", 0)
        d.setdefault("unlocked", False)
        d["msg"] += 1
        if not d["unlocked"] and d["msg"] >= Dungeon1000.UNLOCK_AT:
            d["unlocked"] = True
        self.dungeon.state.save()
        return False, user_input

    def after_response(self, reply, context=None):
        return reply
