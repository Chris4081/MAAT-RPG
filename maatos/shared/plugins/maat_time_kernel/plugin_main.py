# -*- coding: utf-8 -*-
"""
MAAT-TimePerception v3.1
------------------------------------
✓ Zeitbewusstsein
✓ Laufzeitgefühl
✓ Time-Memory (Themen + Abstände)
✓ Speichert jeden User-Input + Timestamp + Keyword-Topic
✓ Abfragebar mit:
    /timelog          → zeigt die letzten 10 Time-Memory-Einträge
    /time topic <x>   → Zeit seit letzter Erwähnung eines Themas
    /time stats       → Statistiken über das Time-Memory
"""

import datetime
import time
import sqlite3
import os
import re
from pathlib import Path
from shared.core.rpg_i18n import get_language

class Plugin:
    type = "chat"

    # -----------------------------------------------------
    # COMMAND LIST → Damit es in /help erscheint!
    # -----------------------------------------------------
    commands = {
        "/time": {"de": "Zeigt die aktuelle Zeit.", "en": "Shows the current time."},
        "/zeit": {"de": "Alias fuer /time.", "en": "Alias for /time."},
        "/runtime": {"de": "Zeit seit der letzten Antwort.", "en": "Time since the last response."},
        "/laufzeit": {"de": "Alias fuer /runtime.", "en": "Alias for /runtime."},
        "/timeinfo": {"de": "Vollstaendiger Zeitkontext.", "en": "Full time context."},
        "/zeitkontext": {"de": "Alias fuer /timeinfo.", "en": "Alias for /timeinfo."},
        "/timelog": {"de": "Zeigt die letzten Time-Memory-Eintraege.", "en": "Shows the latest time-memory entries."},
        "/time topic": {"de": "Zeigt die Zeit seit der letzten Erwaehnung eines Themas.", "en": "Shows the time since a topic was last mentioned."},
        "/time stats": {"de": "Statistiken ueber das Time-Memory.", "en": "Statistics about time memory."},
        "/timestats": {"de": "Alias fuer /time stats.", "en": "Alias for /time stats."}
    }

    def _lang(self):
        return get_language(("de", "en"))

    def _t(self, de: str, en: str) -> str:
        return en if self._lang() == "en" else de

    def __init__(self):
        # Zeitpunkt der letzten Antwort
        self.last_timestamp = time.time()

        # --------------------------------------
        # Schreibbarer Benutzerpfad für macOS
        # --------------------------------------
        app_support_dir = (
            Path.home() / "Library" / "Application Support" / "MAAT-RPG" / "data"
        )
        app_support_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = str(app_support_dir / "time_memory.db")
        self._init_db()

    # -----------------------------------------------------
    # DB INIT
    # -----------------------------------------------------
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                user_input TEXT,
                topic TEXT
            )
        """)

        conn.commit()
        conn.close()

    # -----------------------------------------------------
    # Topic Extraction (einfach, aber effektiv)
    # -----------------------------------------------------
    def _extract_topic(self, text):
        text = text.lower()

        keys = [
            "mona lisa", "maat", "mftoe", "string theorie",
            "oskar", "github", "plugin", "memory",
            "zeit", "bewusstsein", "universum"
        ]

        for k in keys:
            if k in text:
                return k

        # fallback: erstes "wichtigeres" Wort
        m = re.search(r"[a-zA-ZäöüÄÖÜ]{4,}", text)
        return m.group(0).lower() if m else "allgemein"

    # -----------------------------------------------------
    # Speichern ins Time-Memory
    # -----------------------------------------------------
    def _store_time_event(self, user_input):
        # Slash-Kommandos NICHT loggen
        if user_input.strip().startswith("/"):
            return

        topic = self._extract_topic(user_input)
        ts = time.time()

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO log (timestamp, user_input, topic) VALUES (?,?,?)",
            (ts, user_input, topic)
        )
        conn.commit()
        conn.close()

    # -----------------------------------------------------
    # Stats berechnen
    # -----------------------------------------------------
    def _compute_stats(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Gesamtanzahl + min/max Timestamp
        c.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM log")
        row = c.fetchone()
        if not row:
            conn.close()
            return None

        total, t_min, t_max = row
        if not total or t_min is None or t_max is None:
            conn.close()
            return {
                "total": 0,
                "today": 0,
                "avg_gap": None,
                "top_topics": []
            }

        # Events heute
        now = datetime.datetime.now()
        today_start = datetime.datetime(
            year=now.year, month=now.month, day=now.day, hour=0, minute=0, second=0
        )
        ts_today_start = today_start.timestamp()

        c.execute("SELECT COUNT(*) FROM log WHERE timestamp >= ?", (ts_today_start,))
        today_count = c.fetchone()[0] or 0

        # Durchschnittlicher Abstand zwischen Einträgen
        avg_gap = None
        if total > 1:
            # Alle Timestamps holen und echte Gaps mitteln
            c.execute("SELECT timestamp FROM log ORDER BY timestamp ASC")
            ts_rows = [r[0] for r in c.fetchall()]
            gaps = [
                ts_rows[i+1] - ts_rows[i]
                for i in range(len(ts_rows) - 1)
                if ts_rows[i+1] >= ts_rows[i]
            ]
            if gaps:
                avg_gap = sum(gaps) / len(gaps)

        # Top-3 Topics
        c.execute("""
            SELECT topic, COUNT(*) as cnt
            FROM log
            GROUP BY topic
            ORDER BY cnt DESC
            LIMIT 3
        """)
        top_topics = c.fetchall()

        conn.close()

        return {
            "total": total,
            "today": today_count,
            "avg_gap": avg_gap,
            "top_topics": top_topics
        }

    # -----------------------------------------------------
    # COMMAND-HANDLER
    # -----------------------------------------------------
    def command(self, cmd, context=None):
        c = (cmd or "").strip().lower()

        # ------------------------------
        # /time
        # ------------------------------
        if c in ("/time", "/zeit"):
            now = datetime.datetime.now()
            msg = (
                self._t("⏰ **Aktuelle Zeit**\n", "⏰ **Current Time**\n")
                + f"- {self._t('Uhrzeit', 'Time')}: {now.strftime('%H:%M:%S')}\n"
                + f"- {self._t('Datum', 'Date')}:   {now.strftime('%d.%m.%Y')}\n"
                + f"- {self._t('Tag', 'Day')}:     {now.strftime('%A')}\n"
            )
            return msg

        # ------------------------------
        # /runtime
        # ------------------------------
        if c in ("/runtime", "/laufzeit"):
            now_ts = time.time()
            diff = now_ts - self.last_timestamp
            feeling = self._runtime_feeling(diff)
            return (
                self._t("⌛ **Seit letzter Antwort**\n", "⌛ **Since Last Response**\n")
                + f"- {self._t('Sekunden', 'Seconds')}: {diff:.1f}\n"
                + f"- {self._t('Gefuehl', 'Feeling')}:   {feeling}\n"
            )

        # ------------------------------
        # /timeinfo
        # ------------------------------
        if c in ("/timeinfo", "/zeitkontext"):
            now = datetime.datetime.now()
            now_ts = time.time()
            diff = now_ts - self.last_timestamp
            feeling = self._runtime_feeling(diff)

            msg = (
                self._t("🧭 **MAAT-Zeitkontext**\n", "🧭 **MAAT Time Context**\n")
                + f"- {self._t('Uhrzeit', 'Time')}: {now.strftime('%H:%M:%S')}\n"
                + f"- {self._t('Datum', 'Date')}:   {now.strftime('%d.%m.%Y')}\n"
                + f"- {self._t('Tag', 'Day')}:     {now.strftime('%A')}\n"
                + f"- {self._t('Seit letzter Antwort', 'Since last response')}: {diff:.1f} s\n"
                + f"- {self._t('Gefuehl', 'Feeling')}: {feeling}\n"
            )
            return msg

        # ------------------------------
        # /timelog
        # ------------------------------
        if c == "/timelog":
            conn = sqlite3.connect(self.db_path)
            c2 = conn.cursor()
            c2.execute("SELECT timestamp, user_input, topic FROM log ORDER BY id DESC LIMIT 10")
            rows = c2.fetchall()
            conn.close()

            if not rows:
                return self._t("📭 Kein Time-Memory gespeichert.", "📭 No time memory stored.")

            out = [self._t("🧠 **Letzte Time-Memory Eintraege:**\n", "🧠 **Latest Time Memory Entries:**\n")]
            for ts, text, topic in rows:
                dt = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                out.append(f"- [{dt}] ({topic}): {text}")

            return "\n".join(out)

        # ------------------------------
        # /time stats
        # ------------------------------
        if c in ("/time stats", "/timestats"):
            stats = self._compute_stats()
            if not stats or stats["total"] == 0:
                return self._t("📭 Noch keine Time-Memory-Daten vorhanden.", "📭 No time memory data available yet.")

            total = stats["total"]
            today = stats["today"]
            avg_gap = stats["avg_gap"]
            top_topics = stats["top_topics"]

            if avg_gap is None:
                gap_str = self._t("nicht bestimmbar (zu wenige Eintraege)", "not determinable (too few entries)")
            else:
                gap_str = self._t(f"{avg_gap:.1f} Sekunden", f"{avg_gap:.1f} seconds")

            out = [
                self._t("📊 **MAAT Time-Memory Statistiken**", "📊 **MAAT Time Memory Statistics**"),
                f"- {self._t('Gesamtanzahl Events', 'Total events')}: {total}",
                f"- {self._t('Events heute', 'Events today')}:        {today}",
                f"- {self._t('Ø Abstand zw. Events', 'Ø gap between events')}: {gap_str}",
                "",
                self._t("🏷️ Top-Themen:", "🏷️ Top topics:")
            ]

            if top_topics:
                for topic, cnt in top_topics:
                    out.append(self._t(f"  • {topic} — {cnt}× erwaehnt", f"  • {topic} — mentioned {cnt}×"))
            else:
                out.append(self._t("  • keine Themen erkannt", "  • no topics detected"))

            return "\n".join(out)

        # ------------------------------
        # /time topic X
        # ------------------------------
        if c.startswith("/time topic"):
            parts = c.split(" ", 2)
            if len(parts) < 3:
                return self._t("Nutze: `/time topic begriff`", "Use: `/time topic term`")

            topic = parts[2].strip().lower()

            conn = sqlite3.connect(self.db_path)
            c2 = conn.cursor()
            c2.execute("SELECT timestamp FROM log WHERE topic=? ORDER BY id DESC LIMIT 1", (topic,))
            row = c2.fetchone()
            conn.close()

            if not row:
                return self._t(f"❌ Kein Time-Memory fuer Thema **{topic}** gefunden.", f"❌ No time memory found for topic **{topic}**.")

            ts_last = row[0]
            diff = time.time() - ts_last
            feeling = self._runtime_feeling(diff)

            return (
                self._t(f"🧠 **Zeit seit letzter Erwaehnung von '{topic}'**\n", f"🧠 **Time Since Last Mention of '{topic}'**\n")
                + f"- {self._t('Sekunden', 'Seconds')}: {diff:.1f}\n"
                + f"- {self._t('Gefuehl', 'Feeling')}: {feeling}"
            )

        return None  # nicht mein Kommando

    # -----------------------------------------------------
    # BEFORE CHAT → Time-Memory speichern + Kontexte
    # -----------------------------------------------------
    def before_chat(self, user_input, context=None):

        # Time-Memory speichern (nur wenn kein Slash-Command)
        self._store_time_event(user_input)

        # interner Zeit-Kontext (unsichtbar)
        now = datetime.datetime.now()
        diff = time.time() - self.last_timestamp
        feeling = self._runtime_feeling(diff)

        block = (
            "[TIME_CONTEXT]\n"
            + f"{now.strftime('%H:%M:%S')} | {now.strftime('%d.%m.%Y')} | {now.strftime('%A')}\n"
            + self._t(
                f"Seit letzter Antwort: {diff:.1f}s ({feeling})\n",
                f"Since last response: {diff:.1f}s ({feeling})\n",
            )
            + "[/TIME_CONTEXT]"
        )

        if context and "conversation" in context:
            context["conversation"].append({
                "role": "system",
                "content": block
            })

        return (False, user_input)

    # -----------------------------------------------------
    # AFTER CHAT
    # -----------------------------------------------------
    def after_response(self, reply, context=None):
        self.last_timestamp = time.time()
        return reply

    # -----------------------------------------------------
    # Hilfsfunktion: Zeitgefühl
    # -----------------------------------------------------
    def _runtime_feeling(self, diff):
        if diff < 1:
            return "wie ein fließender Moment"
        if diff < 5:
            return "sehr kurz"
        if diff < 20:
            return "ein Augenblick"
        if diff < 60:
            return "ein spürbarer Moment"
        if diff < 180:
            return "eine kleine Weile"
        return "eine längere Pause"
