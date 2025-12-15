# -*- coding: utf-8 -*-
"""
MAAT-RPG Achievement Plugin (mit Levelsystem + Viewer)
------------------------------------------------------
• Reagiert auf Schlüsselwörter im User-Text
• Vergibt XP + Achievements (einmalig pro Wort)
• Zeigt neue Erfolge am Ende der Antwort
• Befehl /erfolge zeigt freigeschaltete Erfolge
"""

import os
import json
from colorama import Fore, Style

# --------------------------------------------------------
# Wörter + Titel + XP
# --------------------------------------------------------
TRIGGERS = {
    # --- Kern ---
    "ägypten":        ("🌍 Erbe der Pyramiden",             15),
    "leonardo":       ("🎨 Geist des Renaissance-Meisters", 18),
    "liebe":          ("💗 Herz der Schöpfung",             20),
    "magie":          ("🔮 Berührter der Arkana",           14),
    "freunde":        ("🤝 Band der Freundschaft",          16),
    "freundschaft":   ("🤝 Band der Freundschaft",          16),
    "harmonie":       ("🌿 Hüter der Harmonie",             12),
    "balance":        ("⚖️ Wächter der Balance",            12),
    "respekt":        ("🕊️ Stimme des Respekts",            10),
    "freiheit":       ("🕊️ Freiheitsbringer",              18),
    "mona lisa":      ("🖼️ Geheimnis der ewigen Muse",      25),
    "pyramide":       ("🔺 Diener der Geometrie",           14),
    "ki":             ("🤖 Verbündeter der Maschinen",       7),
    "maat":           ("✨ Kind der Ordnung",               15),
    "danke":          ("🙏 Dankbarkeit als Stärke",          9),
    "hallo":          ("😊 Freundliche Begrüßung",           5),
    "tschüss":        ("👋 Der Wanderer zieht weiter",       8),

    # --- Spiritualität & Emotion ---
    "hoffnung":       ("🌟 Flamme der Hoffnung",            18),
    "mut":            ("🦁 Löwe des Mutes",                 14),
    "vertrauen":      ("🤝 Herz des Vertrauens",            16),
    "traum":          ("💤 Träumer der Sterne",             12),
    "seele":          ("✨ Echo der Seele",                 20),

    # --- Menschlichkeit ---
    "familie":        ("👪 Bindung des Blutes",             16),
    "mutter":         ("🌸 Ursprung der Liebe",             20),
    "vater":          ("🛡️ Wächter der Familie",            18),
    "kind":           ("🧒 Hüter der Unschuld",             15),

    # --- Philosophie ---
    "wahrheit":       ("🔍 Sucher der Wahrheit",            17),
    "bewusstsein":    ("🧠 Erwachen des Geistes",           22),
    "ordnung":        ("📐 Architekt der Ordnung",          15),
    "chaos":          ("🔥 Tänzer im Chaos",                15),

    # --- Transformation ---
    "verlust":        ("🎗️ Träger der Erinnerung",          20),
    "trauma":         ("🩹 Überlebender",                   22),
    "angst":          ("😨 Bezwinger der Schatten",         16),

    # --- Ägyptische Mythologie ---
    "osiris":         ("🔱 Erbe von Osiris",                20),
    "isis":           ("🌺 Tochter der Sterne",             20),
    "horus":          ("👁️ Auge des Horus",                22),
    "anubis":         ("🐺 Wächter der Toten",              19),
    "thoth":          ("📚 Schreiber der Götter",           21),

    # --- Kosmos / Wissenschaft ---
    "quantum":        ("⚛️ Kind des Quantenschaos",         18),
    "universum":      ("🌌 Kosmischer Wanderer",            22),
    "dimension":      ("🌀 Reisender der Ebenen",           20),
    "energie":        ("⚡ Meister der Energie",            17),

    # --- Maat-Lore ---
    "aeon":           ("♾️ Kind des Äons",                  20),
    "weltformel":     ("📜 Träger der Formel",              25),
    "stringtheorie":  ("🎸 Geweber der Saiten",             22),

    # --- Spaß ---
    "lol":            ("😂 Lacher im Chaos",                5),
    "haha":           ("😆 Freundlicher Humor",             6),
    "pizza":          ("🍕 Tempel der Kohlenhydrate",       8),
}



# ========================================================
# ACHIEVEMENT PLUGIN
# ========================================================
class Plugin:
    type = "chat"

    commands = {
        "/erfolge": "Zeigt deine freigeschalteten Erfolge.",
    }

    def __init__(self):
        self.plugin_dir = os.path.dirname(__file__)
        self.state_path = os.path.join(self.plugin_dir, "achievements_state.json")
        self.state = self._load()

    # --------------------------------------------------------
    # PERSISTENZ
    # --------------------------------------------------------
    def _load(self):
        if os.path.isfile(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass

        return {
            "unlocked": [],   # Liste: Wörter
            "count": 0,       # Anzahl freigeschaltet
        }

    def _save(self):
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    # --------------------------------------------------------
    # COMMANDS – Erfolge anzeigen
    # --------------------------------------------------------
    def command(self, cmd, context=None):
        c = cmd.strip().lower()

        if c == "/erfolge":
            return True, self._render_achievements()

        return None

    def _render_achievements(self):
        unlocked = self.state["unlocked"]
        total = len(TRIGGERS)

        if not unlocked:
            return (
                "🏆 **Erfolge**\n"
                "\n"
                "Du hast bisher noch keine Erfolge freigeschaltet.\n"
                "Sprich mit Herz, Wissen und Magie – und entdecke sie! ✨"
            )

        lines = []
        lines.append("🏆 **Erfolge**")
        lines.append("")

        for word in unlocked:
            title, reward = TRIGGERS.get(word, ("", 0))
            lines.append(f"✨ {title} (+{reward} XP)")

        lines.append("")
        lines.append(f"📜 Insgesamt freigeschaltet: **{len(unlocked)} / {total}**")
        lines.append(f"⚡ Fortschritt: {int(len(unlocked)/total*100)}%")

        return "\n".join(lines)

    # --------------------------------------------------------
    # BEFORE CHAT – Wörter analysieren + XP ans XP-System
    # --------------------------------------------------------
    def before_chat(self, user_input, context=None):
        context = context or {}
        txt = user_input.lower()
        new_unlocks = []
        total_reward_xp = 0  # gesamte XP aus neuen Erfolgen

        for word, (title, reward) in TRIGGERS.items():
            if word in txt:
                # nur 1× pro Wort
                if word not in self.state["unlocked"]:
                    self.state["unlocked"].append(word)
                    self.state["count"] += 1

                    new_unlocks.append((title, reward))
                    total_reward_xp += reward

        self._save()

        # Neue Achievements für AFTER-RESPONSE anzeigen
        if isinstance(context, dict):
            if new_unlocks:
                context["achievements_unlock"] = new_unlocks

            # 👉 XP-Bonus an dein MAAT-RPG / WoW-XP-System übergeben
            if total_reward_xp > 0:
                prev = context.get("maat_xp_bonus", 0) or 0
                try:
                    prev = int(prev)
                except ValueError:
                    prev = 0
                context["maat_xp_bonus"] = prev + total_reward_xp

        # Chattext ganz normal weiterreichen
        return False, user_input



    # --------------------------------------------------------
    # AFTER RESPONSE – Achievements & Levelups anzeigen
    # --------------------------------------------------------
    def after_response(self, reply, context=None):
        if not context:
            return reply

        unlocks = context.pop("achievements_unlock", [])
        levelups = context.pop("achievements_levelup", [])

        if not unlocks and not levelups:
            return reply

        # ⛔ NICHT an reply anhängen!
        # ✅ Stattdessen direkt ins Terminal drucken

        print("\n🏆 Neuer Erfolg freigeschaltet!")
        for title, reward in unlocks:
            print(f"✨ {title} (+{reward} XP)")

        for lvl in levelups:
            print(f"🌟 Level-Up! Du bist jetzt Level {lvl}!")

        print("")

        return reply

    # --------------------------------------------------------
    # STARTUP
    # --------------------------------------------------------
    def on_startup(self, context=None):
        print("🏆 Achievement-System geladen – /erfolge zeigt deinen Fortschritt.")
