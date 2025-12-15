import os
from datetime import datetime
import json

# plugin_main.py (ganz oben, nach imports)

BASE_QUESTS = [
    {
        "id": "maat_person",
        "name": "Maat-Wert einer Person",
        "desc": "Bitte die MAAT-KI, den Maat-Wert einer historischen Person zu berechnen.",
        "type": "chat_keyword",
        "keywords": ["maat-wert", "harmonie", "balance", "schöpfungskraft"],
        "reward_xp": 25,
        "repeatable": False,
    },
    {
        "id": "first_win",
        "name": "Erster Sieg",
        "desc": "Gewinne einen Kampf im MAAT-RPG.",
        "type": "counter",
        "counter_key": "battle_wins",
        "target": 1,
        "reward_xp": 30,
        "repeatable": False,
    },
    {
        "id": "maat_mona",
        "name": "Maat-Wert der Mona Lisa",
        "desc": "Bitte die MAAT-KI, den Maat-Wert der Mona Lisa zu berechnen.",
        "type": "chat_keyword",
        "keywords": ["mona lisa", "maat-wert der mona lisa"],
        "reward_xp": 35,
    },
    {
        "id": "maat_light",
        "name": "Licht der Harmonie",
        "desc": "Bitte die MAAT-KI, den Maat-Wert von Licht zu erklären.",
        "type": "chat_keyword",
        "keywords": ["maat-wert von licht", "licht"],
        "reward_xp": 35,
    },
    {
        "id": "maat_elements",
        "name": "Vier Elemente der Maat",
        "desc": "Frage die MAAT-KI nach den Maat-Werten von Wasser, Feuer, Erde und Luft.",
        "type": "chat_keyword",
        "keywords": ["maat-wert der elemente", "wasser feuer erde luft"],
        "reward_xp": 45,
    },
    {
        "id": "energy_compare",
        "name": "Energie der Zukunft",
        "desc": "Bitte die MAAT-KI, Solarenergie und Atomkraft nach Maat-Wert zu vergleichen.",
        "type": "chat_keyword",
        "keywords": ["solar vs atomkraft", "maat-wert solar", "maat-wert atomkraft"],
        "reward_xp": 50,
    },
    {
        "id": "maat_all_principles",
        "name": "Fünf Säulen der Maat",
        "desc": "Schreibe eine Nachricht, in der alle fünf Prinzipien vorkommen.",
        "type": "chat_keyword",
        "keywords": [
            "Harmonie",
            "Balance",
            "Schöpfungskraft",
            "Verbundenheit",
            "Respekt",
        ],
        "reward_xp": 80,
    },
]

# 🔒 Quests, die erst später freigeschaltet werden (z.B. ab 40 Nachrichten)
LOCKED_QUESTS = [
    {
        "id": "daily_hello",
        "name": "Tägliches Hallo",
        "desc": "Schreibe MAAT-KI an fünf Tagen hintereinander ein Hallo.",
        "type": "daily_streak",
        "required_days": 5,
        "reward_xp": 50,
        "repeatable": True,
        "unlock": {
            "type": "messages",   # ✅ ab X Chatnachrichten freischalten
            "value": 40
        },
    },
    {
        "id": "daily_reflect",
        "name": "Tägliche Reflexion",
        "desc": "Stelle an drei Tagen hintereinander eine Frage zur Selbstreflexion.",
        "type": "daily_streak",
        "days": 3,
        "keyword": "Reflexion",
        "reward_xp": 60,
    },
    {
        "id": "maat_self",
        "name": "Dein eigener Maat-Wert",
        "desc": "Bitte die MAAT-KI, deinen eigenen Maat-Wert zu berechnen.",
        "type": "chat_keyword",
        "keywords": ["meinen maat-wert", "mein maat-wert"],
        "reward_xp": 40,
    },
    {
        "id": "maat_world",
        "name": "Die Maat-Weltformel",
        "desc": "Frage die MAAT-KI nach der Maat-Weltformel und lass sie erklären.",
        "type": "chat_keyword",
        "keywords": ["maat-weltformel"],
        "reward_xp": 45,
    },
    {
        "id": "maat_plp_project",
        "name": "PLP eines Projekts",
        "desc": "Bitte die MAAT-KI, das PLP eines Projekts oder einer Idee zu berechnen.",
        "type": "chat_keyword",
        "keywords": ["PLP eines projekts", "plp berechnen"],
        "reward_xp": 45,
    },
    {
        "id": "maat_elements_compare",
        "name": "Elemente im Gleichgewicht",
        "desc": "Bitte die MAAT-KI, die Maat-Werte von Wasser, Feuer, Erde und Luft zu vergleichen.",
        "type": "chat_keyword",
        "keywords": ["maat-werte von wasser, feuer, erde und luft"],
        "reward_xp": 55,
    },
    {
        "id": "maat_aeon_explain",
        "name": "Äon der Maat",
        "desc": "Frage die MAAT-KI nach einer Erklärung des Äons der Maat.",
        "type": "chat_keyword",
        "keywords": ["äon der maat"],
        "reward_xp": 35,
    },
    {
        "id": "daily_gratitude",
        "name": "Maat-Dankbarkeit",
        "desc": "Schreibe an drei Tagen hintereinander, wofür du dankbar bist.",
        "type": "daily_streak",
        "days": 3,
        "keyword": "dankbar",
        "reward_xp": 60,
    },
    {
        "id": "daily_learning",
        "name": "Tägliche Erkenntnis",
        "desc": "Schreibe an fünf Tagen hintereinander etwas, das du heute gelernt hast.",
        "type": "daily_streak",
        "days": 5,
        "keyword": "heute gelernt",
        "reward_xp": 80,
    },
    {
        "id": "three_wins",
        "name": "Maat-Kämpfer",
        "desc": "Gewinne drei beliebige Kämpfe im MAAT-RPG.",
        "type": "battle_win",
        "target": 3,
        "reward_xp": 70,
    },
    {
        "id": "ten_wins",
        "name": "Hüter der Harmonie",
        "desc": "Gewinne zehn Kämpfe im MAAT-RPG.",
        "type": "battle_win",
        "target": 10,
        "reward_xp": 120,
    },
]

class Plugin:
    """
    MAAT-RPG Quest-Plugin
    - Stellt /quests und /quest Kommandos bereit
    - Verknüpft Quest-XP mit dem globalen RPG-XP-System (state.add_xp)
    """

    # Wird vom PluginManager gelesen
    name = "quests"
    description = "Quest- und Achievement-System für MAAT-RPG."

    def __init__(self, core=None, **kwargs):
        """
        core: z.B. der RPG-Core mit .state (Level, XP, Stats, etc.)
        """
        self.core = core
        self.state = getattr(core, "state", None)

        # Kommandos, die in /help auftauchen sollen
        self.commands = {
            "/quests": "Zeigt verfügbare, aktive und abgeschlossene Quests.",
            "/quest": "Quest annehmen oder Details anzeigen (z.B. /quest accept 1).",
        }

        # interner Quest-State
        self._ensure_state()
        self._ensure_default_quests()

    # -------------------------------------------------
    # STATE INITIALISIEREN
    # -------------------------------------------------
    def _ensure_state(self):
        """
        Sorgt dafür, dass im globalen RPG-State ein 'quests'-Block existiert.
        """
        # Fall 1: Kein Core-State → rein interner Speicher
        if self.state is None:
            if not hasattr(self, "qstate") or not isinstance(self.qstate, dict):
                self.qstate = {
                    "available": [],
                    "active": [],
                    "completed": [],
                    "locked": [],
                    "meta": {
                        "messages_total": 0,
                    },
                }
            return

        # Fall 2: Es gibt einen RPG-Core mit state.state
        root = self.state.state  # das große RPG-State-Dict
        q = root.get("quests")
        if not isinstance(q, dict):
            q = {
                "available": [],
                "active": [],
                "completed": [],
                "locked": [],
                "meta": {},
            }
            root["quests"] = q

        # Defaults setzen
        q.setdefault("available", [])
        q.setdefault("active", [])
        q.setdefault("completed", [])
        q.setdefault("locked", [])
        q.setdefault("meta", {})
        q["meta"].setdefault("messages_total", 0)

        self.qstate = q

    # -------------------------------------------------
    # DEFAULT-QUESTS
    # -------------------------------------------------
    def _ensure_default_quests(self):
        """
        Wenn noch nichts definiert ist → BASE_QUESTS + LOCKED_QUESTS eintragen.
        """
        qs = self.qstate

        # Wenn schon irgendwas da ist → nichts überschreiben
        if qs["available"] or qs["active"] or qs["completed"] or qs["locked"]:
            return

        # Hier kommen deine Basis- und Locked-Quests rein
        qs["available"] = [q.copy() for q in BASE_QUESTS]
        qs["locked"]    = [q.copy() for q in LOCKED_QUESTS]
        qs.setdefault("active", [])
        qs.setdefault("completed", [])
        qs.setdefault("meta", {"messages_total": 0})

        if self.state is not None:
            self.state.save()
        

    # -------------------------------------------------
    # COMMAND-API (wird vom CommandRouter verwendet)
    # -------------------------------------------------
    def command(self, full_cmd: str, context=None):
        """
        Wird vom CommandRouter mit dem kompletten String aufgerufen,
        z.B. "/quest accept maat_person".
        """
        parts = full_cmd.strip().split()
        if not parts:
            return False, None

        base = parts[0]
        args = parts[1:]

        if base == "/quests":
            text = self._cmd_list(args)
            return True, text

        if base == "/quest":
            text = self._cmd_quest(args)
            return True, text

        return False, None

    # -------------------------------------------------
    # /quests
    # -------------------------------------------------
    def _cmd_list(self, args):
        """
        /quests
        /quests active
        /quests done
        """
        mode = "all"
        if args:
            if args[0] in ("active", "a"):
                mode = "active"
            elif args[0] in ("done", "completed", "c"):
                mode = "done"

        lines = ["📜 Quests"]

        if mode in ("all", "available"):
            lines.append("\n✨ Verfügbare Quests:")
            if not self.qstate["available"]:
                lines.append("  (Keine)")
            else:
                for i, q in enumerate(self.qstate["available"], start=1):
                    lines.append(
                        f"  {i}) [{q['id']}] {q['name']} — {q['desc']}"
                    )

        if mode in ("all", "active"):
            lines.append("\n🔥 Aktive Quests:")
            if not self.qstate["active"]:
                lines.append("  (Keine)")
            else:
                for i, q in enumerate(self.qstate["active"], start=1):
                    progress = self._quest_progress_text(q)
                    lines.append(
                        f"  {i}) [{q['id']}] {q['name']} — {progress}"
                    )

        if mode in ("all", "done"):
            lines.append("\n🏁 Abgeschlossene Quests:")
            if not self.qstate["completed"]:
                lines.append("  (Noch keine abgeschlossen)")
            else:
                for i, q in enumerate(self.qstate["completed"], start=1):
                    lines.append(f"  {i}) [{q['id']}] {q['name']}")

        return "\n".join(lines)

    # -------------------------------------------------
    # /quest
    # -------------------------------------------------
    def _cmd_quest(self, args):
        """
        /quest                   → kurze Hilfe
        /quest accept <id|nr>    → Quest annehmen
        /quest info <id|nr>      → Details anzeigen
        """
        if not args:
            return (
                "Verwendung:\n"
                "  /quest accept <id|nr>  – Quest annehmen\n"
                "  /quest info <id|nr>    – Quest-Details anzeigen\n"
                "Nutze /quests, um alle IDs und Nummern zu sehen."
            )

        sub = args[0]
        if len(args) > 1:
            qid = args[1]
        else:
            qid = None

        # ----------------------------
        # /quest accept <id|nr>
        # ----------------------------
        if sub == "accept":
            if not qid:
                return "Bitte Quest-ID oder Nummer angeben: /quest accept <id|nr>"

            q = None

            # 1) Zahl → Index in 'available'-Liste
            if qid.isdigit():
                idx = int(qid) - 1
                if 0 <= idx < len(self.qstate["available"]):
                    q = self.qstate["available"][idx]

            # 2) sonst → ID in 'available' suchen
            if q is None:
                q = self._find_quest_in_list(self.qstate["available"], qid)

            if not q:
                return f"Keine verfügbare Quest mit ID/Nummer '{qid}'."

            # nach active verschieben (flache Kopie)
            self.qstate["available"].remove(q)
            active_q = dict(q)
            if active_q.get("type") in ("counter", "daily_streak"):
                active_q["progress"] = 0
            self.qstate["active"].append(active_q)
            return f"✅ Quest '{active_q['name']}' angenommen."

        # ----------------------------
        # /quest info <id|nr>
        # ----------------------------
        if sub == "info":
            if not qid:
                return "Bitte Quest-ID oder Nummer angeben: /quest info <id|nr>"

            q = None

            # 1) Zahl → Index in 'available' (primäre Liste zum Nachschlagen)
            if qid.isdigit():
                idx = int(qid) - 1
                if 0 <= idx < len(self.qstate["available"]):
                    q = self.qstate["available"][idx]

            # 2) Falls noch nichts gefunden → per ID in allen Listen suchen
            if q is None:
                q = (
                    self._find_quest_in_list(self.qstate["available"], qid)
                    or self._find_quest_in_list(self.qstate["active"], qid)
                    or self._find_quest_in_list(self.qstate["completed"], qid)
                )

            if not q:
                return f"Keine Quest mit ID/Nummer '{qid}' gefunden."

            lines = [
                f"📖 Quest: {q['name']}",
                f"ID: {q['id']}",
                f"Beschreibung: {q.get('desc','')}",
                f"Typ: {q.get('type','')}",
                f"Belohnung: {q.get('reward_xp',0)} XP",
            ]
            if q in self.qstate["active"]:
                lines.append(f"Status: AKTIV — {self._quest_progress_text(q)}")
            elif q in self.qstate["completed"]:
                lines.append("Status: ABGESCHLOSSEN")
            else:
                lines.append("Status: VERFÜGBAR")

            return "\n".join(lines)

        return "Unbekanntes Subkommando. Nutze: /quest accept <id|nr> oder /quest info <id|nr>."

        
    # -------------------------------------------------
    # Fortschritts-Text für aktive Quests
    # -------------------------------------------------
    def _quest_progress_text(self, q: dict | None) -> str:
        """
        Gibt einen kurzen Fortschritts-Text für eine aktive Quest zurück.
        Wird von /quests (aktive Quests) und /quest info verwendet.
        """
        if not isinstance(q, dict):
            return ""

        qtype = q.get("type", "")
        name = q.get("name", q.get("id", "Quest"))

        # 🔢 Daily-Streak-Quests (z.B. daily_hello, daily_gratitude, ...)
        if qtype == "daily_streak":
            cur = int(q.get("progress", 0))
            target = int(q.get("required_days") or q.get("days") or 1)
            return f"Fortschritt: {cur}/{target} Tage"

        # ⚔️ Zähler-basierte Quests (first_win, battle_win, three_wins, ten_wins, ...)
        if qtype in ("counter", "battle_win"):
            cur = int(q.get("progress", 0))
            target = int(q.get("target", 1))
            return f"Fortschritt: {cur}/{target}"

        # 💬 Chat-Keyword-Quests (Maat-Wert, Mona Lisa, Licht, etc.)
        if qtype == "chat_keyword":
            return "Hinweis: Erfülle die Bedingung im Chat (Schlüsselwörter verwenden)."

        # Fallback
        return "Aktive Quest"


        
    # -------------------------------------------------
    # LOCKED → AVAILABLE freischalten
    # -------------------------------------------------
    def _check_unlocks(self):
        """
        Prüft LOCKED_QUESTS auf Unlock-Bedingungen.
        Beispiel:
          unlock: { "type": "messages", "value": 40 }
        Sobald meta.messages_total >= value → Quest nach 'available' verschieben.
        """
        meta = self.qstate.get("meta", {})
        total = meta.get("messages_total", 0)

        unlocked = []

        for q in list(self.qstate["locked"]):
            unlock = q.get("unlock")
            if not unlock or not isinstance(unlock, dict):
                continue

            utype = unlock.get("type")
            val = unlock.get("value")

            # 🔓 Freischaltung nach Anzahl Nachrichten
            if utype == "messages" and isinstance(val, int) and total >= val:
                self.qstate["locked"].remove(q)
                self.qstate["available"].append(q)
                unlocked.append(q)

        # optional: State speichern
        if unlocked and self.state is not None:
            try:
                self.state.save()
            except Exception:
                pass

        return unlocked
    # -------------------------------------------------
    # HOOKS FÜR ChatLoop / Pluginsystem
    # -------------------------------------------------
    def before_chat(self, user_input: str, context=None):
        """
        Wird vor dem Model-Call aufgerufen.
        Wir nutzen das, um Daily-Quests, Keyword-Quests
        und Unlocks (z.B. ab 40 Nachrichten) zu prüfen.
        """
        try:
            completed_msgs = []

            # 🔢 Nachrichten-Zähler hochzählen
            meta = self.qstate.setdefault("meta", {})
            meta["messages_total"] = meta.get("messages_total", 0) + 1

            # 🔓 neue Quests freischalten (z.B. ab 40 Nachrichten)
            unlocked = self._check_unlocks()
            for q in unlocked:
                completed_msgs.append(
                    f"✨ Neue Quest freigeschaltet: {q['name']}  (Nutze /quests)"
                )

            # Daily-Hallo
            self._check_daily_hello(user_input, completed_msgs)

            # Keyword-Quests (z.B. 'Maat-Wert')
            self._check_keyword_quests(user_input, completed_msgs)

            if completed_msgs and isinstance(context, dict):
                context.setdefault("quest_messages", []).extend(completed_msgs)

        except Exception:
            # Niemals den Chatloop crashen
            pass

        # handled = False → Input weiter normal verarbeiten
        return False, user_input

    def after_response(self, reply: str, context=None):
        """
        Wird nach der Model-Antwort aufgerufen.
        Wenn Quests abgeschlossen wurden, hängen wir eine kleine Meldung an.
        """
        if not isinstance(context, dict):
            return None

        msgs = context.pop("quest_messages", [])
        if not msgs:
            return None

        extra = "\n\n" + "\n".join(msgs)
        return reply + extra

    # -------------------------------------------------
    # INTERN: Daily & Keyword-Quests
    # -------------------------------------------------
    def _check_daily_hello(self, user_input: str, completed_msgs: list):
        """
        Wenn 'hallo' im Input vorkommt → Daily-Streak prüfen.
        """
        if "hallo" not in user_input.lower():
            return
        if self.state is None:
            return

        s = self.state.state
        stats = s.setdefault("stats", {})
        today = datetime.now().date().isoformat()
        last = stats.get("last_daily_day")

        # bereits heute gezählt
        if last == today:
            return

        # Streak-Logik
        if last is None:
            streak = 1
        else:
            try:
                last_date = datetime.fromisoformat(last).date()
                delta = (datetime.now().date() - last_date).days
                if delta == 1:
                    streak = stats.get("daily_streak", 0) + 1
                else:
                    streak = 1
            except Exception:
                streak = 1

        stats["daily_streak"] = streak
        stats["last_daily_day"] = today

        # Gibt es eine aktive Daily-Quest?
        dq = None
        for q in self.qstate["active"]:
            if q.get("type") == "daily_streak":
                dq = q
                break

        if not dq:
            return

        # Fortschritt erhöhen
        cur = dq.get("progress", 0) + 1
        dq["progress"] = cur

        target = dq.get("required_days", 5)
        if cur >= target:
            self._complete_quest(dq, completed_msgs)

    def _check_keyword_quests(self, user_input: str, completed_msgs: list):
        text = user_input.lower()
        for q in list(self.qstate["active"]):
            if q.get("type") != "chat_keyword":
                continue
            kws = [k.lower() for k in q.get("keywords", [])]
            if any(k in text for k in kws):
                self._complete_quest(q, completed_msgs)

    # -------------------------------------------------
    # Quest-Abschluss + XP
    # -------------------------------------------------
    def _complete_quest(self, quest: dict, completed_msgs: list):
        """
        Verschiebt Quest nach 'completed' und vergibt XP.
        """
        if quest in self.qstate["active"]:
            self.qstate["active"].remove(quest)

        quest["completed_at"] = datetime.now().isoformat()
        self.qstate["completed"].append(quest)

        xp = int(quest.get("reward_xp", 0))
        name = quest.get("name", quest.get("id", "Quest"))
        msg = f"🏆 Quest abgeschlossen: {name}  (+{xp} XP)"
        completed_msgs.append(msg)

        # XP ins RPG-Level-System
        if self.state is not None and hasattr(self.state, "add_xp"):
            try:
                old_lvl, new_lvl = self.state.add_xp(xp)
                if new_lvl > old_lvl:
                    completed_msgs.append(f"🌟 LEVEL UP! Level {old_lvl} → {new_lvl}")
            except Exception:
                pass