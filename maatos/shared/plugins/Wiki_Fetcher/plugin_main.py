# -*- coding: utf-8 -*-
"""
MAAT-WikiFetcher v4.2 — DB-Cache + Auto-Kontext + Debug + User-Agent
----------------------------------------------------------------------
✓ Holt Artikel aus deutscher Wikipedia
✓ SQLite-Cache in /data/wiki_cache.db
✓ /wiki <begriff>  → holt aus Cache oder live & speichert
✓ /wiki cache      → zeigt letzte Cache-Einträge
✓ /wiki debug on   → Wiki-Kontext im Terminal anzeigen
✓ /wiki debug off  → Debug aus
✓ /wiki debug once → Debug nur für nächste Eingabe
✓ Auto-Kontext: Wenn im User-Text z. B. "Mona Lisa" vorkommt
  und im Cache ist, wird ein kurzer Wiki-Kontext intern
  vor die Eingabe gehängt.
✓ v4.2: Wikimedia-konformer User-Agent gesetzt
  (Pflicht laut foundation.wikimedia.org/wiki/Policy:API_usage_guidelines)
"""

import os
import sqlite3
import wikipedia
import requests
import re
from datetime import datetime
from shared.core.maat_paths import data_file, state_file, log_file


# ─── Wikimedia User-Agent (Pflicht) ──────────────────────────────────────────
# Wikimedia verlangt einen identifizierenden User-Agent für alle API-Zugriffe.
# Format: "<ProjectName>/<Version> (<URL>; <contact>)"
# Quelle: https://foundation.wikimedia.org/wiki/Policy:API_usage_guidelines
_USER_AGENT = (
    "MAAT-RPG/1.0 "
    "(https://github.com/Chris4081/MAAT-RPG; "
    "https://maat-research.com)"
)

# Wikipedia-Library nutzt intern requests — wir ersetzen die Session
def _patch_wikipedia_session():
    """
    Setzt den Wikimedia-konformen User-Agent auf der internen
    requests.Session der wikipedia-Library.
    Muss einmal beim Import aufgerufen werden.
    """
    try:
        session = requests.Session()
        session.headers.update({"User-Agent": _USER_AGENT})
        wikipedia.session = session
    except Exception as e:
        print(f"[WikiFetcher] Warnung: User-Agent konnte nicht gesetzt werden: {e}")

_patch_wikipedia_session()
# ─────────────────────────────────────────────────────────────────────────────


class Plugin:
    type = "chat"

    # -----------------------------------------------------
    # COMMANDS – für CommandRouter (/help)
    # -----------------------------------------------------
    commands = {
        "/wiki": {
            "de": "Ruft Wikipedia-Artikel ab und cached sie (/wiki <Begriff>).",
            "en": "Fetches and caches Wikipedia articles (/wiki <term>)."
        },
        "/wiki cache": {
            "de": "Zeigt die letzten Cache-Eintraege.",
            "en": "Shows the latest cache entries."
        },
        "/wiki debug on": {
            "de": "Schaltet Wiki-Debug ein (zeigt Kontext im Terminal).",
            "en": "Turns wiki debug on (shows context in the terminal)."
        },
        "/wiki debug off": {
            "de": "Schaltet Wiki-Debug aus.",
            "en": "Turns wiki debug off."
        },
        "/wiki debug once": {
            "de": "Aktiviert Wiki-Debug nur fuer die naechste Eingabe.",
            "en": "Enables wiki debug only for the next input."
        },
    }

    def __init__(self):
        # Wikipedia auf Deutsch
        wikipedia.set_lang("de")

        # 🔹 Projekt-Root: drei Ebenen hoch → MAAT-KI/
        root_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        # 🔹 Zentrales /data-Verzeichnis
        data_dir = os.path.join(root_dir, "data")
        os.makedirs(data_dir, exist_ok=True)

        # 🔹 Wiki-Cache-DB
        self.db_path = data_file('wiki_cache.db')
        self._init_db()

        # Debug-Flags
        self.debug = False
        self.debug_once = False

    # -----------------------------------------------------
    # COMMAND HANDLER (/wiki ...)
    # -----------------------------------------------------
    def command(self, cmd, context=None):
        """
        Wird vom CommandRouter mit dem vollen Text aufgerufen,
        z.B. "/wiki Mona Lisa" oder "/wiki debug on".
        Erwartet: STRING als Rückgabe.
        """
        if not cmd:
            return None

        text = cmd.strip()
        parts = text.split(maxsplit=2)
        base = parts[0].lower()

        if base != "/wiki":
            return None

        # Nur "/wiki" → Hilfe
        if len(parts) == 1:
            return (
                "📚 MAAT-WikiFetcher\n"
                "Nutze:\n"
                "  • /wiki <Begriff>   – Wikipedia-Artikel holen & cachen\n"
                "  • /wiki cache       – letzte Cache-Einträge anzeigen\n"
                "  • /wiki debug on    – Wiki-Debug an\n"
                "  • /wiki debug off   – Wiki-Debug aus\n"
                "  • /wiki debug once  – Debug nur für die nächste Eingabe\n"
            )

        sub = parts[1].lower()

        # /wiki debug ...
        if sub == "debug":
            if len(parts) < 3:
                return "Nutze: /wiki debug on | off | once"

            mode = parts[2].lower()
            if mode == "on":
                self.debug = True
                self.debug_once = False
                return "🧪 WIKI-DEBUG ist jetzt AKTIV. Wiki-Kontext wird im Terminal angezeigt."
            if mode == "off":
                self.debug = False
                self.debug_once = False
                return "🧪 WIKI-DEBUG wurde deaktiviert."
            if mode == "once":
                self.debug_once = True
                return "🧪 WIKI-DEBUG ist EINMALIG für die nächste Eingabe aktiv."
            return "Nutze: /wiki debug on | off | once"

        # /wiki cache
        if sub == "cache":
            return self._show_cache()

        # Alles andere → als Suchbegriff behandeln
        query = text.replace("/wiki", "", 1).strip()
        if not query:
            return "Nutze: `/wiki <Begriff>`."

        # 1) ZUERST: Cache prüfen
        cached = self._lookup_cache(query)
        if cached:
            title, summary, url = cached
            title = self._clean_title(title)
            return (
                f"📚 **Wikipedia (Cache) – {title}**\n\n"
                f"{summary.strip()}\n\n"
                f"🔗 {url}"
            )

        # 2) Wenn nichts im Cache → live von Wikipedia holen
        page, summary = self._fetch(query)

        if not page or not summary:
            return f"📚 Wikipedia: keine Ergebnisse für **{query.lower()}**."

        title = self._clean_title(page.title)

        # 3) Ergebnis in Cache speichern
        self._save_cache(query, title, summary, page.url)

        return (
            f"📚 **Wikipedia – {title}**\n\n"
            f"{summary.strip()}\n\n"
            f"🔗 {page.url}"
        )

    # -----------------------------------------------------
    # BEFORE CHAT – Auto-Wiki-Kontext bei Stichwörtern
    # -----------------------------------------------------
    def before_chat(self, user_input: str, context=None):
        """
        Wenn der User-Text Begriffe enthält, die im Wiki-Cache
        bekannt sind (z.B. 'Mona Lisa'), werden kurze Snippets
        als interner Kontext vor die Eingabe gehängt.
        """
        text = (user_input or "").strip()
        if not text:
            return (False, user_input)

        hits = self._match_in_text(text)
        if not hits:
            return (False, user_input)

        lines = []
        MAX_SNIPPETS = 3
        MAX_LEN = 300

        for title, summary, url in hits[:MAX_SNIPPETS]:
            clean_title = self._clean_title(title)
            snippet = (summary or "").strip()
            if len(snippet) > MAX_LEN:
                snippet = snippet[:MAX_LEN - 3] + "..."
            lines.append(f"[WIKI: {clean_title}]\n{snippet}\n({url})")

        if not lines:
            return (False, user_input)

        wiki_block = (
            "MAAT-Wiki-Kontext (nur intern für die KI, NICHT wörtlich dem Nutzer anzeigen):\n"
            + "\n\n".join(lines)
            + "\n---\n"
            + text
        )

        if self.debug or self.debug_once:
            print("\n🧪 [WIKI-DEBUG] Kontext, der an das Modell geht:\n")
            print(wiki_block)
            print("\n🧪 [WIKI-DEBUG ENDE]\n")
            self.debug_once = False

        return (False, wiki_block)

    # -----------------------------------------------------
    # DB INIT
    # -----------------------------------------------------
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS wiki_cache (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_query TEXT,
                title     TEXT,
                summary   TEXT,
                url       TEXT,
                ts        TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    # -----------------------------------------------------
    # CACHE LOOKUP
    # -----------------------------------------------------
    def _lookup_cache(self, query):
        q = query.strip().lower()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """
            SELECT title, summary, url
            FROM wiki_cache
            WHERE LOWER(raw_query) = ? OR LOWER(title) = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (q, q),
        )
        row = c.fetchone()
        conn.close()
        return row

    # -----------------------------------------------------
    # MATCH IN TEXT
    # -----------------------------------------------------
    def _match_in_text(self, text, limit=5):
        t = text.lower()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT raw_query, title, summary, url FROM wiki_cache ORDER BY id DESC"
        )
        rows = c.fetchall()
        conn.close()

        matches = []
        for raw_query, title, summary, url in rows:
            if not title and not raw_query:
                continue

            cand_list = []
            if raw_query:
                cand_list.append(raw_query.lower())
            if title:
                cand_list.append(self._clean_title(title).lower())

            for cand in cand_list:
                if cand and cand in t:
                    matches.append((title, summary, url))
                    break

            if len(matches) >= limit:
                break

        return matches

    # -----------------------------------------------------
    # CACHE SAVE
    # -----------------------------------------------------
    def _save_cache(self, query, title, summary, url):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO wiki_cache (raw_query, title, summary, url, ts)
                VALUES (?, ?, ?, ?, ?)
                """,
                (query, title, summary, url, datetime.utcnow().isoformat()),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    # -----------------------------------------------------
    # CACHE LIST
    # -----------------------------------------------------
    def _show_cache(self, limit=10):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                """
                SELECT raw_query, title, url, ts
                FROM wiki_cache
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = c.fetchall()
            conn.close()
        except Exception as e:
            return f"⚠ Fehler beim Lesen des Wiki-Caches: {e}"

        if not rows:
            return "📭 Wiki-Cache ist leer."

        out = ["📚 Letzte Wiki-Cache-Einträge:\n"]
        for raw_query, title, url, ts in rows:
            out.append(f"- [{ts}] {raw_query!r} → {self._clean_title(title)} ({url})")

        return "\n".join(out)

    # -----------------------------------------------------
    # Title Cleaner
    # -----------------------------------------------------
    def _clean_title(self, title):
        if not title:
            return ""
        title = re.sub(r"\(.*?\)", "", title)
        title = title.replace("–", "-")
        return title.strip()

    # -----------------------------------------------------
    # Smart Fetch Routine
    # -----------------------------------------------------
    def _fetch(self, query):
        q = query.strip()

        # 1. Direktversuch
        try:
            summary = wikipedia.summary(q, sentences=3, auto_suggest=True)
            page = wikipedia.page(q, auto_suggest=True)
            return page, summary
        except Exception:
            pass

        # 2. Suche
        try:
            results = wikipedia.search(q)
            if not results:
                return None, None

            best = results[0]
            summary = wikipedia.summary(best, sentences=3, auto_suggest=False)
            page = wikipedia.page(best, auto_suggest=False)
            return page, summary
        except Exception:
            return None, None
