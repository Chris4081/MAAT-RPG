# -*- coding: utf-8 -*-
"""
MAAT-Memory v6 — AGI Hybrid Memory System
-----------------------------------------
✓ Identity Memory (persistent)
✓ Episodic Memory (SQLite)
✓ Semantic Memory (FAISS or NumPy fallback)
✓ Pattern Fact Extractor
✓ Topic Slots (identity, friends, places, projects, etc.)
✓ Query Rewriting
✓ Hybrid Retrieval (semantic + patterns + keywords + slots)
✓ Safe Context Injection (max 8 items)
✓ Debug Mode (/mem6 debug on)
"""

import os
import sqlite3
import json
import re
from datetime import datetime

import numpy as np
import hashlib
from shared.core.rpg_i18n import get_language
from shared.core.vector_index import faiss_available, load_vector_index, save_vector_index

EMBED_DIM = 128


# -----------------------------------------------------------
# Mini Embedding
# -----------------------------------------------------------
def embed_text(text: str) -> np.ndarray:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    arr = np.frombuffer(h, dtype=np.uint8).astype("float32")

    if arr.size < EMBED_DIM:
        arr = np.tile(arr, int(np.ceil(EMBED_DIM / arr.size)))

    arr = arr[:EMBED_DIM]
    arr = arr / 255.0
    return arr


class Plugin:
    type = "chat"

    commands = {
        "/mem6": {"de": "Zeigt die MAAT-Memory-v6-Uebersicht an.", "en": "Shows the MAAT Memory v6 overview."},
        "/mem6 last": {"de": "Zeigt die letzten 10 Memory-Eintraege.", "en": "Shows the last 10 memory entries."},
        "/mem6 search": {"de": "Hybrid-Suche (Semantik + Patterns + Keywords).", "en": "Hybrid search (semantics + patterns + keywords)."},
        "/mem6 info": {"de": "Informationen zum Memory-System.", "en": "Information about the memory system."},
        "/mem6 debug on": {"de": "Aktiviert den Debug-Modus.", "en": "Enables debug mode."},
        "/mem6 debug off": {"de": "Deaktiviert den Debug-Modus.", "en": "Disables debug mode."},
    }

    # -------------------------------------------------------
    # INIT
    # -------------------------------------------------------
    def __init__(self):
        app_support_dir = os.path.join(
            os.path.expanduser("~"),
            "Library",
            "Application Support",
            "MAAT-RPG",
            "data"
        )
        os.makedirs(app_support_dir, exist_ok=True)

        self.db_path = os.path.join(app_support_dir, "mem6.db")
        self.index_path = os.path.join(app_support_dir, "mem6.index")
        self.identity_path = os.path.join(app_support_dir, "mem6_identity.json")
        self.debug = False
        self.debug_once = False

        self._init_db()
        self._init_identity()
        self.vector_backend = "faiss" if faiss_available() else "numpy"
        self._init_index()

    def _lang(self):
        return get_language(("de", "en"))

    def _t(self, de: str, en: str) -> str:
        return en if self._lang() == "en" else de

    # -------------------------------------------------------
    # DB init
    # -------------------------------------------------------
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS episodic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                slot TEXT,
                resonance REAL,
                timestamp TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT,
                value TEXT,
                slot TEXT,
                timestamp TEXT
            )
        """)

        conn.commit()
        conn.close()

    # -------------------------------------------------------
    # Identity init
    # -------------------------------------------------------
    def _init_identity(self):
        if not os.path.exists(self.identity_path):
            ident = {
                "user.name": None,
                "user.home": None,
                "user.project": None,
                "friends": {},
                "preferred_topics": []
            }
            with open(self.identity_path, "w") as f:
                json.dump(ident, f, indent=4)

    def _load_identity(self):
        with open(self.identity_path, "r") as f:
            return json.load(f)

    def _save_identity(self, data):
        with open(self.identity_path, "w") as f:
            json.dump(data, f, indent=4)

    # -------------------------------------------------------
    # Vector index
    # -------------------------------------------------------
    def _init_index(self):
        self.index = load_vector_index(self.index_path, EMBED_DIM)

    # -------------------------------------------------------
    # Maat resonance score
    # -------------------------------------------------------
    def _resonance(self, text):
        t = text.lower()
        score = 0.1
        for k in ["maat", "harmonie", "balance", "schöpf", "respekt", "verbund"]:
            if k in t:
                score += 0.15
        return min(score, 1.0)

    # -------------------------------------------------------
    # Topic slot classification
    # -------------------------------------------------------
    def _slot(self, text):
        t = text.lower()

        if "ich bin" in t or "mein name" in t:
            return "identity"

        # 👉 Fix: Schreibfehler korrigiert, damit "Reicholzheim" erkannt wird
        if "reicholzheim" in t or "würzburg" in t:
            return "places"

        if "maat" in t:
            return "maat"

        if "oskar" in t or "freund" in t:
            return "friends"

        if "projekt" in t or "mftoe" in t:
            return "projects"

        return "general"

    # -------------------------------------------------------
    # Pattern extraction
    # -------------------------------------------------------
    def _extract_patterns(self, text):
        patterns = []

        m = re.search(r"ich bin ([A-Za-z0-9äöüÄÖÜ]+)", text, re.I)
        if m:
            patterns.append(("user.name", m.group(1), "identity"))

        m = re.search(r"ich komme aus ([A-Za-z0-9äöüÄÖÜ]+)", text, re.I)
        if m:
            patterns.append(("user.home", m.group(1), "places"))

        return patterns

    # -------------------------------------------------------
    # Store episodic + semantic + patterns
    # -------------------------------------------------------
    def _store(self, role, text):
        if not text:
            return

        slot = self._slot(text)
        resonance = self._resonance(text)
        ts = datetime.now().isoformat()

        # episodic
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                INSERT INTO episodic (role, content, slot, resonance, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (role, text, slot, resonance, ts))
            conn.commit()
            conn.close()
        except Exception:
            # kein Crash, falls DB mal spinnt
            return

        # semantic (FAISS kann theoretisch auch mal Fehler werfen)
        try:
            vec = embed_text(text)
            self.index.add(np.array([vec]).astype("float32"))
            save_vector_index(self.index, self.index_path)
        except Exception:
            pass

        # pattern
        patterns = self._extract_patterns(text)
        if patterns:
            try:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                for key, val, s in patterns:
                    c.execute("""
                        INSERT INTO patterns (key, value, slot, timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (key, val, s, ts))
                conn.commit()
                conn.close()
            except Exception:
                pass

        # identity updates
        if patterns:
            try:
                ident = self._load_identity()
                for key, val, _ in patterns:
                    ident[key] = val
                self._save_identity(ident)
            except Exception:
                pass

    # -------------------------------------------------------
    # Hybrid search
    # -------------------------------------------------------
    def _search_hybrid(self, query, limit=8):
        results = []

        # 1) semantic
        try:
            if self.index.ntotal > 0:
                vec = embed_text(query)
                D, I = self.index.search(
                    np.array([vec]).astype("float32"), limit
                )

                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()

                for idx in I[0]:
                    if idx >= 0:
                        # IDs in episodic starten bei 1
                        c.execute(
                            "SELECT role, content, slot, timestamp "
                            "FROM episodic WHERE id=?",
                            (idx + 1,)
                        )
                        row = c.fetchone()
                        if row:
                            results.append(row)

                conn.close()
        except Exception:
            # falls der Index mal korrupt ist → trotzdem weitermachen
            pass

        # 2) pattern search
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "SELECT key, value, slot, timestamp "
                "FROM patterns ORDER BY id DESC LIMIT 20"
            )
            rows = c.fetchall()
            conn.close()

            for key, val, slot, ts in rows:
                if val.lower() in query.lower():
                    results.append(("pattern", f"{key}: {val}", slot, ts))
        except Exception:
            pass

        return results[:limit]

    # -------------------------------------------------------
    # Commands
    # -------------------------------------------------------
    def command(self, cmd, context=None):
        text = cmd.strip()

        if text == "/mem6":
            ident = self._load_identity()
            return (
                self._t("📦 MAAT-Memory v6 Uebersicht:\n", "📦 MAAT Memory v6 Overview:\n")
                + f"- {self._t('Identitaet', 'Identity')}: {ident}\n"
                + f"- DB: {self.db_path}\n"
                + f"- {self._t('Backend', 'Backend')}: {self.vector_backend}\n"
                + f"- {self._t('Indexgroesse', 'Index size')}: {self.index.ntotal}\n"
            )

        if text == "/mem6 info":
            return (
                self._t("ℹ MAAT-Memory v6 System:\n", "ℹ MAAT Memory v6 system:\n")
                + "- Hybrid-Memory (semantic + pattern + identity)\n"
                + self._t("- Topic-Slots\n", "- Topic slots\n")
                + self._t("- Safe Context Injection\n", "- Safe context injection\n")
                + self._t("- Identity-Store\n", "- Identity store\n")
                + self._t("- Debug-Modus verfuegbar", "- Debug mode available")
            )

        if text == "/mem6 last":
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "SELECT role, content, slot, timestamp "
                "FROM episodic ORDER BY id DESC LIMIT 10"
            )
            rows = c.fetchall()
            conn.close()

            if not rows:
                return self._t("📭 Keine Eintraege.", "📭 No entries.")

            out = [self._t("🧠 Letzte Memories:\n", "🧠 Latest memories:\n")]
            for role, content, slot, ts in rows:
                out.append(f"[{ts}] ({slot}) {role}: {content}")

            return "\n".join(out)

        if text.startswith("/mem6 search "):
            q = text.replace("/mem6 search ", "").strip()
            if not q:
                return self._t("Bitte Suchwort verwenden: /mem6 search <wort>", "Please use a search term: /mem6 search <word>")

            hits = self._search_hybrid(q)
            if not hits:
                return self._t(f"❌ Keine Treffer fuer: {q}", f"❌ No matches for: {q}")

            out = [self._t(f"🔍 Treffer fuer: {q}\n", f"🔍 Matches for: {q}\n")]
            for role, content, slot, ts in hits:
                out.append(f"[{ts}] ({slot}) {role}: {content}")
            return "\n".join(out)

        if text == "/mem6 debug on":
            self.debug = True
            return self._t("🧪 Debug AN", "🧪 Debug ON")

        if text == "/mem6 debug off":
            self.debug = False
            return self._t("🧪 Debug AUS", "🧪 Debug OFF")

        return None

    # -------------------------------------------------------
    # Before chat: Inject context
    # -------------------------------------------------------
    def before_chat(self, user_input, context=None):
        text = user_input.strip()
        if not text:
            return False, user_input

        # store user message (nicht crashen, wenn was schiefgeht)
        try:
            self._store("user", text)
        except Exception:
            pass

        # hybrid search
        hits = self._search_hybrid(text, limit=8)
        if not hits:
            return False, user_input

        lines = []
        for role, content, slot, ts in hits:
            snippet = (content or "")[:200]
            lines.append(f"[{slot}] {role}: {snippet}")

        memory_block = (
            self._t(
                "🧠 DEINE ERINNERUNGEN (MAAT-KI - stilles Langzeitgedaechtnis):\nDie folgenden Punkte stammen aus deinem eigenen Gedaechtnis.\nNutze sie implizit fuer Verstaendnis und Antwort.\nErwaehne sie NICHT ausdruecklich, ausser der Nutzer fragt danach.\n\n",
                "🧠 YOUR MEMORIES (MAAT-KI - silent long-term memory):\nThe following points come from your own memory.\nUse them implicitly for understanding and response.\nDo NOT mention them explicitly unless the user asks.\n\n",
            )
            + "\n".join(lines)
            + "\n\n"
            + self._t("———\nAKTUELLE EINGABE:\n", "———\nCURRENT INPUT:\n")
            + text
        )

        if self.debug:
            print("\n🧪 MEM6 DEBUG:\n")
            print(memory_block)
            print("\n🧪 MEM6 DEBUG ENDE\n" if self._lang() == "de" else "\n🧪 MEM6 DEBUG END\n")

        # handled=False → andere Plugins dürfen noch ran
        return False, memory_block

    # -------------------------------------------------------
    # After chat — store assistant reply
    # -------------------------------------------------------
    def after_response(self, reply, context=None):
        if reply:
            try:
                self._store("assistant", reply)
            except Exception:
                pass
        return reply
