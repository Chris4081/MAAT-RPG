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
        self.path = state_file('state500.json')
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
                _t("🔒 **Dungeon 500: Kristallpfad der Fuenfhundert**\n", "🔒 **Dungeon 500: Crystal Path of the Five Hundred**\n")
                + f"{_t('Nachrichten', 'Messages')}: {d['msg']} / {self.UNLOCK_AT}\n"
                + f"✨ {_t('Noch', 'Still')} {remain} {_t('bis zur Oeffnung.', 'until it opens.')}\n"
            )

        return (
            _t("🏰 **Dungeon 500: Kristallpfad der Fuenfhundert**\n", "🏰 **Dungeon 500: Crystal Path of the Five Hundred**\n")
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
            remain = max(0, self.UNLOCK_AT - d["msg"])
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
        return (
            _t(
                "💎 Die Kristalle an den Waenden beginnen leise zu singen.\nEin kuehles, blaues Licht erfuellt den Gang.\n👉 Weiter mit: `/d500 next`",
                "💎 The crystals in the walls begin to sing softly.\nA cool blue light fills the corridor.\n👉 Continue with: `/d500 next`",
            )
        )

    def _room_2(self):
        return (
            _t(
                "🔷 Brechende Lichtstrahlen tanzen ueber den Boden wie wandernde Runen.\nDu spuerst, wie der Raum auf deine Schritte reagiert.\n👉 Weiter mit: `/d500 next`",
                "🔷 Shards of light dance across the floor like wandering runes.\nYou can feel the room responding to your steps.\n👉 Continue with: `/d500 next`",
            )
        )

    def _room_3(self):
        return (
            _t(
                "✨ Vor dir erhebt sich ein Tor aus poliertem Glas, in dem sich unzaehlige Welten spiegeln.\nZwischen den Reflexionen flackert eine Silhouette.\n👉 Der Boss wartet: `/d500 boss`",
                "✨ Before you rises a gate of polished glass reflecting countless worlds.\nA silhouette flickers between the reflections.\n👉 The boss awaits: `/d500 boss`",
            )
        )

    # ================================
    # BOSS
    # ================================
    def boss(self):
        # Hintergrundmusik des normalen Dungeons stoppen
        if self.music_manager:
            self.music_manager.stop()

        boss_name = _t("Herr der 500 Schatten", "Lord of 500 Shadows")
        intro = _t(
            f"👑 **{boss_name} tritt aus dem Schattenkreis hervor!**\n\n",
            f"👑 **{boss_name} steps out of the circle of shadows!**\n\n",
        )

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
                result = _t(f"⚠ Fehler beim Bosskampf: {e}", f"⚠ Error during boss fight: {e}")

        else:
            # Fallback: Demo-Kampf ohne BattleCore
            if self.boss_music_manager:
                self.boss_music_manager.start()
            result = _t(
                f"⚔ (Demo) Boss **{boss_name}** wurde besiegt!",
                f"⚔ (Demo) Boss **{boss_name}** was defeated!",
            )
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
        "/d500": {"de": "Dungeon 500 betreten.", "en": "Enter Dungeon 500."},
        "/d500 next": {"de": "Naechsten Raum betreten.", "en": "Enter the next room."},
        "/d500 boss": {"de": "Bosskampf starten.", "en": "Start the boss fight."},
        "/d500 status": {"de": "Status anzeigen.", "en": "Show the status."},
        "/d500 reset": {"de": "Dungeon zuruecksetzen.", "en": "Reset the dungeon."},
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
            return True, _t("⚠ Der Boss wartet bereits. Nutze: `/d500 boss`", "⚠ The boss is already waiting. Use: `/d500 boss`")

        if c == "/d500 boss":
            return True, self.dungeon.boss()

        if c == "/d500 status":
            return True, self.dungeon.status()

        if c == "/d500 reset":
            self.dungeon.state.data = self.dungeon.state._default()
            self.dungeon.state.save()
            self._room_stage = 0
            return True, _t("🔁 Dungeon 500 zurueckgesetzt.", "🔁 Dungeon 500 reset.")
        return None

    def before_chat(self, user_input, context=None):
        """
        Zählt jede Nachricht und schaltet den Dungeon nach 500 Messages frei.
        """
        d = self.dungeon.state.data
        d.setdefault("msg", 0)
        d.setdefault("unlocked", False)
        d["msg"] += 1
        if not d["unlocked"] and d["msg"] >= Dungeon500.UNLOCK_AT:
            d["unlocked"] = True
        self.dungeon.state.save()
        return False, user_input

    def after_response(self, reply, context=None):
        return reply
