# -*- coding: utf-8 -*-
"""
MAAT-RPG Dungeon Plugin — "Tor der 60 Stimmen"
--------------------------------------------
Funktionen:
• Dungeon öffnet sich nach 60 Nachrichten
• 3 Räume + Boss
• Spielt Musik (Dungeon/Boss)
• Voll integriert mit BattleCore unter: apps/maat_rpg/plugins/battle/
"""

import os
import json
import textwrap
from datetime import datetime

# =====================================================
# 🔗 BattleCore und BattleMusicManager importieren
# =====================================================
import importlib.util
from shared.core.maat_paths import data_file, state_file, log_file
from shared.core.rpg_i18n import get_language


def _lang():
    return get_language(("de", "en"))


def _t(de: str, en: str) -> str:
    return en if _lang() == "en" else de

def _load_battle_plugin():
    """Versucht BattleCore & MusicManager aus /plugins/battle zu laden."""
    battle_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "battle", "plugin_main.py")
    )

    if not os.path.isfile(battle_path):
        print("⚠️ [Dungeon] Battle-Plugin wurde nicht gefunden:", battle_path)
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
class DungeonState:
    def __init__(self, base_dir: str):
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        self.path = state_file('state.json')
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
# 🏰 DUNGEON
# =====================================================
class Dungeon:
    UNLOCK_AT = 60

    def __init__(self, base_dir: str, core=None):
        self.base_dir = base_dir
        self.core = core
        self.state = DungeonState(base_dir)

        # Musik-Dateien
        self.music_theme = os.path.join(base_dir, "music", "dungeon_theme.mp3")
        self.boss_theme = os.path.join(base_dir, "music", "boss_theme.mp3")

        self.music_manager = None
        self.boss_music_manager = None

        if BattleMusicManager:
            if os.path.isfile(self.music_theme):
                self.music_manager = BattleMusicManager(self.music_theme)
            if os.path.isfile(self.boss_theme):
                self.boss_music_manager = BattleMusicManager(self.boss_theme)

        # BattleCore anbinden
        self.battle_core = None
        if self.core and hasattr(self.core, "battle"):
            self.battle_core = self.core.battle
        elif BattleCore:
            try:
                battle_dir = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "battle")
                )
                self.battle_core = BattleCore(plugin_dir=battle_dir)
                print("✅ [Dungeon] Eigenen BattleCore initialisiert.")
            except Exception as e:
                print("⚠️ [Dungeon] Fehler beim Initialisieren des BattleCore:", e)
                self.battle_core = None

    # ================================
    # STATUS
    # ================================
    def status(self):
        d = self.state.data
        if not d["unlocked"]:
            remain = self.UNLOCK_AT - d["msg"]
            return (
                _t("🔒 **Dungeon: Tor der 60 Stimmen**\n", "🔒 **Dungeon: Gate of 60 Voices**\n")
                + f"{_t('Nachrichten', 'Messages')}: {d['msg']} / {self.UNLOCK_AT}\n"
                + f"✨ {_t('Noch', 'Still')} {remain} {_t('bis zur Oeffnung.', 'until it opens.')}\n"
            )

        return (
            _t("🏰 **Dungeon: Tor der 60 Stimmen**\n", "🏰 **Dungeon: Gate of 60 Voices**\n")
            + f"Runs: {d['runs']}\n"
            + f"Completed: {d['completed']}\n"
            + f"{_t('Letzter Eintritt', 'Last entry')}: {d['last_entered']}\n"
            + f"BattleCore: {(_t('AKTIV ✅', 'ACTIVE ✅') if self.battle_core else _t('FEHLT (Demo) ⚠️', 'MISSING (demo) ⚠️'))}\n"
        )

    # ================================
    # BETRETEN
    # ================================
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

    # ================================
    # RÄUME
    # ================================
    def _room_1(self):
        return _t(
            "🌀 Du betrittst den Tunnel der Stimmen.\n👉 Weiter mit: `/dungeon60 next`",
            "🌀 You enter the tunnel of voices.\n👉 Continue with: `/dungeon60 next`",
        )

    def _room_2(self):
        return _t(
            "🌫 Schatten greifen nach deinem Geist, aber du bleibst standhaft.\n👉 Weiter mit: `/dungeon60 next`",
            "🌫 Shadows reach for your mind, but you remain steadfast.\n👉 Continue with: `/dungeon60 next`",
        )

    def _room_3(self):
        return _t(
            "🔥 Ein Kreis aus goldenen Glyphen bildet den Boden.\n👉 Boss erscheint! `/dungeon60 boss`",
            "🔥 A circle of golden glyphs forms beneath your feet.\n👉 The boss appears! `/dungeon60 boss`",
        )

    # ================================
    # BOSS
    # ================================
    def boss(self):
        if self.music_manager:
            self.music_manager.stop()

        boss_name = _t("Wächter der Resonanz", "Guardian of Resonance")

        intro = _t(
            f"👑 **{boss_name} stellt sich dir in den Weg.**\n\n",
            f"👑 **{boss_name} blocks your path.**\n\n",
        )

        if self.battle_core:
            try:
                music_cfg = {}
                if os.path.isfile(self.boss_theme):
                    music_cfg["battle"] = self.boss_theme  # z.B. dungeon_60/music/boss_theme.mp3

                ctx = {
                    "boss_name": boss_name,
                    "music": music_cfg,
                }
                result = self.battle_core.run_fight("boss", context=ctx)
            except Exception as e:
                result = _t(f"⚠ Fehler beim Kampf: {e}", f"⚠ Error during battle: {e}")
        else:
            if self.boss_music_manager:
                self.boss_music_manager.start()
            result = _t(
                f"⚔ (Demo) Boss **{boss_name}** wurde besiegt!",
                f"⚔ (Demo) Boss **{boss_name}** was defeated!",
            )
            if self.boss_music_manager:
                self.boss_music_manager.stop()

        d = self.state.data
        d["completed"] = True
        self.state.save()

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
        "/dungeon60": {"de": "Dungeon betreten.", "en": "Enter the dungeon."},
        "/dungeon60 next": {"de": "Naechsten Raum betreten.", "en": "Enter the next room."},
        "/dungeon60 boss": {"de": "Bosskampf starten.", "en": "Start the boss fight."},
        "/dungeon60 status": {"de": "Status anzeigen.", "en": "Show the status."},
        "/dungeon60 reset": {"de": "Dungeon zuruecksetzen.", "en": "Reset the dungeon."},
    }

    def __init__(self, plugin_dir=None, core=None):
        if plugin_dir is None:
            plugin_dir = os.path.dirname(__file__)
        self.plugin_dir = plugin_dir
        self.core = core
        self._room_stage = 0
        self.dungeon = Dungeon(base_dir=plugin_dir, core=core)

    def command(self, cmd, context=None):
        c = cmd.strip()
        if c == "/dungeon60":
            self._room_stage = 1
            return True, self.dungeon.enter()
        if c == "/dungeon60 next":
            if self._room_stage == 1:
                self._room_stage = 2
                return True, self.dungeon._room_2()
            if self._room_stage == 2:
                self._room_stage = 3
                return True, self.dungeon._room_3()
            return True, _t("⚠ Boss wartet. `/dungeon60 boss`", "⚠ The boss is waiting. `/dungeon60 boss`")
        if c == "/dungeon60 boss":
            return True, self.dungeon.boss()
        if c == "/dungeon60 status":
            return True, self.dungeon.status()
        if c == "/dungeon60 reset":
            self.dungeon.state.data = self.dungeon.state._default()
            self.dungeon.state.save()
            self._room_stage = 0
            return True, _t("🔁 Dungeon zurueckgesetzt.", "🔁 Dungeon reset.")
        return None

    def before_chat(self, user_input, context=None):
        d = self.dungeon.state.data
        d.setdefault("msg", 0)
        d.setdefault("unlocked", False)
        d["msg"] += 1
        if not d["unlocked"] and d["msg"] >= Dungeon.UNLOCK_AT:
            d["unlocked"] = True
        self.dungeon.state.save()
        return False, user_input

    def after_response(self, reply, context=None):
        return reply
