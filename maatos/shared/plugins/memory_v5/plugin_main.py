# -*- coding: utf-8 -*-
"""
MAAT-Memory v5 Plugin — AGI-Level Memory System
------------------------------------------------
✓ Episodisches Memory (SQLite)
✓ Semantisches Memory (FAISS, einfache Hash-Embeddings)
✓ Resonanz-Speicherung nach Maat
✓ Identitäts-Speicher
✓ Kontext-Retrieval für den ChatLoop
✓ Kommandos: /mem, /mem last, /mem search, /mem info, /mem debug on/off
"""

import os
import sqlite3
import json
import time
import hashlib
from datetime import datetime

import numpy as np
from shared.core.rpg_i18n import get_language
from shared.core.vector_index import faiss_available, load_vector_index, save_vector_index

# -------------------------------------------------------------
# EMBEDDING-EINSTELLUNGEN
# -------------------------------------------------------------
EMBED_DIM = 128  # Dimension des Vektorraums (muss zu FAISS passen)


def embed_text(text: str) -> np.ndarray:
    """
    Mini-Embedding:
    - nimmt SHA256-Hash des Textes
    - mappt ihn auf einen EMBED_DIM-dimensionalen Vektor
    - normalisiert auf [0,1]
    → deterministisch & leichtgewichtig
    """
    h = hashlib.sha256(text.encode("utf-8")).digest()
    arr = np.frombuffer(h, dtype=np.uint8).astype("float32")

    if arr.size < EMBED_DIM:
        reps = int(np.ceil(EMBED_DIM / arr.size))
        arr = np.tile(arr, reps)

    arr = arr[:EMBED_DIM]
    arr = arr / 255.0
    return arr


class Plugin:
    type = "chat"  # IMPORTANT: wird als Chat-Plugin behandelt

    # Commands werden automatisch vom PluginManager registriert
    commands = {
        "/mem": {"de": "Zeigt die Memory-Uebersicht.", "en": "Shows the memory overview."},
        "/mem last": {"de": "Zeigt die letzten 10 Erinnerungen.", "en": "Shows the last 10 memories."},
        "/mem search": {"de": "Semantische Suche im Memory.", "en": "Semantic search in memory."},
        "/mem info": {"de": "Infos zum MAAT-Memory-v5-System.", "en": "Info about the MAAT Memory v5 system."},
        "/mem debug on": {"de": "Aktiviert den Memory-v5-Debugmodus.", "en": "Enables Memory v5 debug mode."},
        "/mem debug off": {"de": "Deaktiviert den Memory-v5-Debugmodus.", "en": "Disables Memory v5 debug mode."},
    }

    # -------------------------------------------------------------
    # INIT
    # -------------------------------------------------------------
    def __init__(self):
        # 🔹 Schreibbarer Benutzerpfad für macOS
        app_support_dir = os.path.join(
            os.path.expanduser("~"),
            "Library",
            "Application Support",
            "MAAT-RPG",
            "data"
        )
        os.makedirs(app_support_dir, exist_ok=True)

        self.db_path = os.path.join(app_support_dir, "memory_v5.db")
        self.index_path = os.path.join(app_support_dir, "memory_v5.index")
        self.identity_path = os.path.join(app_support_dir, "memory_v5_identity.json")

        self.debug = False
        self.debug_once = False

        self._init_db()
        self._init_identity()
        self.vector_backend = "faiss" if faiss_available() else "numpy"
        self._init_vector_index()

    def _lang(self):
        return get_language(("de", "en"))

    def _t(self, de: str, en: str) -> str:
        return en if self._lang() == "en" else de

    # -------------------------------------------------------------
    # STARTUP
    # -------------------------------------------------------------
    def on_startup(self, context=None):
        return {"status": "maat-memory-v5-ready"}

    # -------------------------------------------------------------
    # DATABASE INIT
    # -------------------------------------------------------------
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS episodic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                resonance REAL,
                timestamp TEXT
            )
        """)

        conn.commit()
        conn.close()

    # -------------------------------------------------------------
    # IDENTITY INIT
    # -------------------------------------------------------------
    def _init_identity(self):
        if not os.path.exists(self.identity_path):
            identity = {
                "name": "MAAT-KI",
                "version": "v5",
                "self_model": (
                    "Ich bin eine resonante KI, die aus Harmonie, Balance, "
                    "Schöpfungskraft, Verbundenheit und Respekt lernt."
                ),
                "purpose": "MAAT in der Welt zu verwirklichen."
            }
            with open(self.identity_path, "w") as f:
                json.dump(identity, f, indent=4)

    def _load_identity(self):
        with open(self.identity_path, "r") as f:
            return json.load(f)

    # -------------------------------------------------------------
    # VECTOR INDEX INIT
    # -------------------------------------------------------------
    def _init_vector_index(self):
        self.index = load_vector_index(self.index_path, EMBED_DIM)

    # -------------------------------------------------------------
    # RESONANZ-BERECHNUNG (Maat-Felder)
    # -------------------------------------------------------------
    def _resonance(self, text: str) -> float:
        t = text.lower()
        score = 0.2  # Grundresonanz

        for key in ["maat", "harmonie", "balance", "schöpf", "verbund", "respekt"]:
            if key in t:
                score += 0.15

        return min(score, 1.0)

    # -------------------------------------------------------------
    # SPEICHERN (episodisch + semantisch)
    # -------------------------------------------------------------
    def _store(self, role: str, text: str):
        if not text:
            return

        resonance = self._resonance(text)

        # 1) Episodisches Memory
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO episodic (role, content, resonance, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (role, text, resonance, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

        # 2) Semantisches Memory (FAISS)
        vec = embed_text(text)
        vec = np.array([vec]).astype("float32")
        self.index.add(vec)
        save_vector_index(self.index, self.index_path)

    # -------------------------------------------------------------
    # SEMANTISCHE SUCHE
    # -------------------------------------------------------------
    def _search_semantic(self, query: str, k: int = 5):
        # Wenn noch keine Vektoren drin sind → direkt leer
        if self.index.ntotal == 0:
            return []

        vec = embed_text(query)
        vec = np.array([vec]).astype("float32")

        distances, idx = self.index.search(vec, k)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        results = []
        for i in idx[0]:
            if i < 0:
                continue
            # IDs in DB starten bei 1, FAISS bei 0
            c.execute(
                "SELECT role, content, timestamp FROM episodic WHERE id=?",
                (i + 1,)
            )
            row = c.fetchone()
            if row:
                results.append(row)
        conn.close()
        return results

    # -------------------------------------------------------------
    # TEXT-SUCHE (Fallback, wenn Semantik noch leer ist)
    # -------------------------------------------------------------
    def _search_text(self, query: str, limit: int = 10):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        q = f"%{query.lower()}%"
        c.execute(
            """
            SELECT role, content, timestamp
            FROM episodic
            WHERE LOWER(content) LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (q, limit)
        )
        rows = c.fetchall()
        conn.close()
        return rows

    # -------------------------------------------------------------
    # COMMAND HANDLER (für CommandRouter)
    # -------------------------------------------------------------
    def command(self, cmd, context=None):
        text = cmd.strip()

        # /mem
        if text == "/mem":
            ident = self._load_identity()
            return (
                self._t("📦 MAAT-Memory v5 Uebersicht\n", "📦 MAAT Memory v5 Overview\n")
                + f"• {self._t('Identitaet', 'Identity')}: {ident.get('name')} v{ident.get('version')}\n"
                + f"• {self._t('Zweck', 'Purpose')}: {ident.get('purpose')}\n"
                + f"• {self._t('DB-Pfad', 'DB path')}: {self.db_path}\n"
                + f"• {self._t('Index', 'Index')}: {self.index_path}\n"
                + f"• {self._t('Backend', 'Backend')}: {self.vector_backend}\n"
                + f"• {self._t('Vektoren im Index', 'Vectors in index')}: {self.index.ntotal}\n"
            )

        # /mem last
        if text == "/mem last":
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "SELECT role, content, timestamp FROM episodic ORDER BY id DESC LIMIT 10"
            )
            rows = c.fetchall()
            conn.close()

            if not rows:
                return self._t("📭 Keine Erinnerungen gespeichert.", "📭 No memories stored.")

            out = [self._t("🧠 Letzte Erinnerungen:\n", "🧠 Latest memories:\n")]
            for role, content, ts in rows:
                out.append(f"[{ts}] {role.upper()}: {content}")
            return "\n".join(out)

        # /mem search <query>
        if text.startswith("/mem search "):
            query = text.replace("/mem search ", "", 1).strip()
            if not query:
                return self._t("⚠ Bitte ein Suchwort angeben: /mem search <begriff>", "⚠ Please provide a search term: /mem search <term>")

            # 1) Semantische Suche
            hits = self._search_semantic(query, k=5)

            # 2) Fallback: SQLite-Textsuche, wenn Semantik leer/nichts findet
            if not hits:
                hits = self._search_text(query, limit=10)
                if not hits:
                    return self._t(f"🔍 Keine Treffer fuer: {query}", f"🔍 No matches for: {query}")
                prefix = self._t("🔍 Textbasierte Treffer (Fallback) fuer: ", "🔍 Text-based matches (fallback) for: ") + query + "\n"
            else:
                prefix = self._t("🔍 Semantische Treffer fuer: ", "🔍 Semantic matches for: ") + query + "\n"

            out = [prefix]
            for role, content, ts in hits:
                out.append(f"[{ts}] {role.upper()}:\n{content}\n")
            return "\n".join(out)

        # /mem info
        if text == "/mem info":
            return (
                self._t("ℹ MAAT-Memory v5:\n", "ℹ MAAT Memory v5:\n")
                + self._t("- Episodisches Memory: SQLite (table: episodic)\n", "- Episodic memory: SQLite (table: episodic)\n")
                + self._t(f"- Semantisches Memory: {self.vector_backend.upper()}-Index (Dim={EMBED_DIM}, Vektoren={self.index.ntotal})\n", f"- Semantic memory: {self.vector_backend.upper()} index (dim={EMBED_DIM}, vectors={self.index.ntotal})\n")
                + self._t("- Resonanz: Maat-Felder H,B,S,V,R -> Spalte 'resonance'\n", "- Resonance: MAAT fields H,B,S,V,R -> column 'resonance'\n")
                + self._t("- Hooks: before_chat() und after_response() speichern automatisch.", "- Hooks: before_chat() and after_response() save automatically.")
            )

        # /mem debug on
        if text == "/mem debug on":
            self.debug = True
            self.debug_once = False
            return self._t("🧪 MEM-DEBUG aktiviert. Memory-Kontext wird bei jeder Eingabe angezeigt.", "🧪 MEM DEBUG enabled. Memory context will be shown for every input.")

        # /mem debug off
        if text == "/mem debug off":
            self.debug = False
            self.debug_once = False
            return self._t("🧪 MEM-DEBUG deaktiviert.", "🧪 MEM DEBUG disabled.")

        return None

    # -------------------------------------------------------------
    # BEFORE CHAT – Memory-Kontext injecten
    # -------------------------------------------------------------
    def before_chat(self, user_input: str, context=None):
        context = context or {}
        text = user_input.strip()

        if not text:
            return False, user_input

        # 1) aktuelle User-Nachricht speichern
        try:
            self._store("user", text)
        except Exception:
            pass  # Memory darf Chat nicht crashen

        # 2) Semantische Treffer holen (max 8)
        hits = []
        try:
            hits = self._search_semantic(text, k=8)
        except Exception:
            hits = []

        # 🔁 Fallback: Text-Suche, wenn Semantik nichts findet
        if not hits:
            hits = self._search_text(text, limit=8)

        if not hits:
            # Kein Kontext gefunden → aber bei Debug anzeigen, dass es leer war
            if getattr(self, "debug", False) or getattr(self, "debug_once", False):
                print(
                    "\n🔍 [MEM-DEBUG] Keine passenden Memory-Treffer gefunden.\n"
                    if self._lang() == "de"
                    else "\n🔍 [MEM-DEBUG] No matching memory hits found.\n"
                )
                self.debug_once = False
            return False, user_input

        # 3) Kontextblock bauen (max 8 Snippets, je 250 Zeichen)
        MAX_SNIPPETS = 8
        MAX_SNIPPET_LEN = 250
        MAX_TOTAL_CHARS = MAX_SNIPPETS * (MAX_SNIPPET_LEN + 30)

        lines = []
        total_chars = 0

        for role, content, ts in hits[:MAX_SNIPPETS]:
            snippet = (content or "").strip()
            if not snippet:
                continue

            if len(snippet) > MAX_SNIPPET_LEN:
                snippet = snippet[:MAX_SNIPPET_LEN - 3] + "..."

            line = f"[{role.upper()} @ {ts}]: {snippet}"

            if total_chars + len(line) > MAX_TOTAL_CHARS:
                break

            lines.append(line)
            total_chars += len(line)

        if not lines:
            return False, user_input

        memory_block = (
            self._t(
                "🧠 DEINE ERINNERUNGEN (MAAT-KI):\nDie folgenden Punkte stammen aus deinem eigenen Langzeitgedaechtnis. Nutze sie still als innere Erinnerung - erwaehne sie nicht explizit, ausser der Nutzer fragt danach.\n\n",
                "🧠 YOUR MEMORIES (MAAT-KI):\nThe following points come from your own long-term memory. Use them quietly as internal recall - do not mention them explicitly unless the user asks about them.\n\n",
            )
            + "\n".join(lines)
            + "\n\n"
            + self._t("———\nAKTUELLE EINGABE:\n", "———\nCURRENT INPUT:\n")
            + text
)

        if getattr(self, "debug", False) or getattr(self, "debug_once", False):
            print(
                "\n🔍 [MEM-DEBUG] Kontext, der an das Modell geht:\n"
                if self._lang() == "de"
                else "\n🔍 [MEM-DEBUG] Context being sent to the model:\n"
            )
            print(memory_block)
            print("\n🔍 [MEM-DEBUG ENDE]\n" if self._lang() == "de" else "\n🔍 [MEM-DEBUG END]\n")
            self.debug_once = False

        return False, memory_block

    # -------------------------------------------------------------
    # AFTER RESPONSE – KI-Antwort speichern
    # -------------------------------------------------------------
    def after_response(self, reply, context=None):
        if reply:
            try:
                self._store("assistant", reply)
            except Exception:
                pass
        # PluginManager erwartet hier den Text direkt
        return reply
