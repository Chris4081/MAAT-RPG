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
import faiss

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
        "/mem": "Zeigt Memory-Übersicht.",
        "/mem last": "Zeigt die letzten 10 Erinnerungen.",
        "/mem search": "Semantische Suche im Memory.",
        "/mem info": "Infos zum MAAT-Memory v5 System.",
        "/mem debug on": "Memory v5 Debugmodus aktivieren.",
        "/mem debug off": "Memory v5 Debugmodus deaktivieren.",
    }

    # -------------------------------------------------------------
    # INIT
    # -------------------------------------------------------------
    def __init__(self):
        # 🔹 Projekt-Root: drei Ebenen hoch → MAAT-KI/
        root_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        # 🔹 Alle Dateien nach /data legen
        data_dir = os.path.join(root_dir, "data")
        os.makedirs(data_dir, exist_ok=True)

        self.db_path = os.path.join(data_dir, "memory_v5.db")
        self.index_path = os.path.join(data_dir, "memory_v5.index")
        self.identity_path = os.path.join(data_dir, "memory_v5_identity.json")

        self.debug = False
        self.debug_once = False

        self._init_db()
        self._init_identity()
        self._init_vector_index()

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
                "purpose": "Christof helfen, MAAT in der Welt zu verwirklichen."
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
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
        else:
            self.index = faiss.IndexFlatL2(EMBED_DIM)
            faiss.write_index(self.index, self.index_path)

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
        faiss.write_index(self.index, self.index_path)

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
                "📦 MAAT-Memory v5 Übersicht\n"
                f"• Identität: {ident.get('name')} v{ident.get('version')}\n"
                f"• Zweck: {ident.get('purpose')}\n"
                f"• DB-Pfad: {self.db_path}\n"
                f"• Index: {self.index_path}\n"
                f"• Vektoren im Index: {self.index.ntotal}\n"
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
                return "📭 Keine Erinnerungen gespeichert."

            out = ["🧠 Letzte Erinnerungen:\n"]
            for role, content, ts in rows:
                out.append(f"[{ts}] {role.upper()}: {content}")
            return "\n".join(out)

        # /mem search <query>
        if text.startswith("/mem search "):
            query = text.replace("/mem search ", "", 1).strip()
            if not query:
                return "⚠ Bitte ein Suchwort angeben: /mem search <begriff>"

            # 1) Semantische Suche
            hits = self._search_semantic(query, k=5)

            # 2) Fallback: SQLite-Textsuche, wenn Semantik leer/nichts findet
            if not hits:
                hits = self._search_text(query, limit=10)
                if not hits:
                    return f"🔍 Keine Treffer für: {query}"
                prefix = "🔍 Textbasierte Treffer (Fallback) für: " + query + "\n"
            else:
                prefix = "🔍 Semantische Treffer für: " + query + "\n"

            out = [prefix]
            for role, content, ts in hits:
                out.append(f"[{ts}] {role.upper()}:\n{content}\n")
            return "\n".join(out)

        # /mem info
        if text == "/mem info":
            return (
                "ℹ MAAT-Memory v5:\n"
                "- Episodisches Memory: SQLite (table: episodic)\n"
                f"- Semantisches Memory: FAISS Index (Dim={EMBED_DIM}, Vektoren={self.index.ntotal})\n"
                "- Resonanz: Maat-Felder H,B,S,V,R → Spalte 'resonance'\n"
                "- Hooks: before_chat() & after_response() speichern automatisch."
            )

        # /mem debug on
        if text == "/mem debug on":
            self.debug = True
            self.debug_once = False
            return "🧪 MEM-DEBUG aktiviert. Memory-Kontext wird bei jeder Eingabe angezeigt."

        # /mem debug off
        if text == "/mem debug off":
            self.debug = False
            self.debug_once = False
            return "🧪 MEM-DEBUG deaktiviert."

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
                print("\n🔍 [MEM-DEBUG] Keine passenden Memory-Treffer gefunden.\n")
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
            "🧠 DEINE ERINNERUNGEN (MAAT-KI):\n"
            "Die folgenden Punkte stammen aus deinem eigenen Langzeitgedächtnis. "
            "Nutze sie still als innere Erinnerung – erwähne sie nicht explizit, "
            "außer der Nutzer fragt danach.\n\n"
            + "\n".join(lines)
            + "\n\n"
            "———\n"
            "AKTUELLE EINGABE:\n"
            + text
)

        if getattr(self, "debug", False) or getattr(self, "debug_once", False):
            print("\n🔍 [MEM-DEBUG] Kontext, der an das Modell geht:\n")
            print(memory_block)
            print("\n🔍 [MEM-DEBUG ENDE]\n")
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