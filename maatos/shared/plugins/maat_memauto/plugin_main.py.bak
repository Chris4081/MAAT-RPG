# -*- coding: utf-8 -*-
"""
MAAT-MemAuto Plugin v1.0
------------------------
Einfache, triggerbasierte Erinnerungen nach dem Vorbild deines
Text-Generation-WebUI-Extensions "maat_memauto", angepasst
an das MAAT-KI Plugin-System.

Funktionen:
- Triggert auf Sätze wie:
  "merke dir ...", "erinnere dich ...", "speichere ...", "remember that ..."
- Speichert Memories in: ROOT/data/maat_memauto/memauto.json
- Optional: injiziert einen kleinen sichtbaren Kontext vor die Eingabe
- Kommandos:
/memauto          → Hilfe & Status
/memauto on       → Kontext-Injektion aktivieren
/memauto off      → Kontext-Injektion deaktivieren
/memauto list     → letzte 10 Einträge anzeigen
/memauto clear    → alle Einträge löschen
"""

import os
import json
import re
from datetime import datetime


class Plugin:
    type = "chat"

    # Commands für CommandRouter (/help)
    commands = {
        "/memauto": "MAAT-MemAuto Hilfe & Status",
        "/memauto on": "MemAuto-Kontext-Injektion aktivieren",
        "/memauto off": "MemAuto-Kontext-Injektion deaktivieren",
        "/memauto list": "Letzte 10 Erinnerungen anzeigen",
        "/memauto clear": "Alle MemAuto-Erinnerungen löschen",
    }

    # ------------------------------------------------------------------
    # INIT
    # ------------------------------------------------------------------
    def __init__(self):
        # 🔹 Projekt-Root: drei Ebenen hoch → MAAT-KI/
        root_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )

        # 🔹 Zentrales /data-Verzeichnis
        data_dir = os.path.join(root_dir, "data")
        os.makedirs(data_dir, exist_ok=True)

        # 🔹 MemAuto-JSON direkt in /data
        self.mem_path = os.path.join(data_dir, "memauto.json")

        # Flags
        self.inject_enabled = True
        self.debug = False

        # Bestehende Memories laden (oder leere Liste anlegen)
        self.memories = self._load_memories()

        # Trigger in DE/EN – du kannst sie beliebig erweitern
        self.trigger_patterns = [
            # Deutsch
            r"merke dir(?: bitte)?(?: das| folgendes)?[: ,]+(.+)",
            r"erinnere (?:dich )?(?:bitte )?(?:an|daran)[: ,]+(.+)",
            r"speichere(?: bitte)?[: ,]+(.+)",
            # Englisch
            r"remember (?:this|that)?[: ,]+(.+)",
            r"store (?:this|that)?[: ,]+(.+)"
        ]

    # ------------------------------------------------------------------
    # Speicher-Handling
    # ------------------------------------------------------------------
    def _load_memories(self):
        if not os.path.exists(self.mem_path):
            return []
        try:
            with open(self.mem_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def _save_memories(self):
        try:
            with open(self.mem_path, "w", encoding="utf-8") as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠ [MAAT-MemAuto] Konnte Memories nicht speichern: {e}")

    def _add_memory(self, text, source="user", tags=None):
        if not text:
            return
        entry = {
            "text": text.strip(),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "source": source,
            "tags": tags or []
        }
        self.memories.append(entry)
        self._save_memories()
        if self.debug:
            print(f"[MAAT-MemAuto] Neue Memory gespeichert: {entry['text']}")

    # ------------------------------------------------------------------
    # Trigger-Erkennung
    # ------------------------------------------------------------------
    def _extract_memory_from_text(self, user_input: str):
        """
        Versucht, aus der Eingabe eine Memory-Formulierung zu extrahieren,
        z.B.:
          - "merke dir, dass ich Christof heiße"
          - "remember that I live in Reicholzheim"
        Gibt Memory-Text oder None zurück.
        """
        text = user_input.strip()
        if not text:
            return None

        # 1) Explizite "save: ..." / "mem:" Syntax (optional)
        if text.lower().startswith("save:") or text.lower().startswith("mem:"):
            return text.split(":", 1)[1].strip()

        # 2) Regex-basierte Trigger
        for pattern in self.trigger_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                mem = m.group(1).strip()
                if mem:
                    return mem

        return None

    # ------------------------------------------------------------------
    # Kommandos
    # ------------------------------------------------------------------
    def command(self, cmd: str, context=None):
        c = cmd.strip()

        if c == "/memauto":
            status = "ON" if self.inject_enabled else "OFF"
            return (
                "🧠 MAAT-MemAuto\n"
                f"- Kontext-Injektion: {status}\n"
                f"- Speicherdatei: {self.mem_path}\n"
                f"- Anzahl Erinnerungen: {len(self.memories)}\n"
                "Befehle:\n"
                "  • /memauto on    – Kontext-Injektion aktivieren\n"
                "  • /memauto off   – Kontext-Injektion deaktivieren\n"
                "  • /memauto list  – letzte 10 Memories anzeigen\n"
                "  • /memauto clear – alle Memories löschen\n"
            )

        if c == "/memauto on":
            self.inject_enabled = True
            return "🧠 MAAT-MemAuto: Kontext-Injektion AKTIV."

        if c == "/memauto off":
            self.inject_enabled = False
            return "😌 MAAT-MemAuto: Kontext-Injektion deaktiviert."

        if c == "/memauto list":
            if not self.memories:
                return "📭 Keine MemAuto-Erinnerungen vorhanden."
            out = ["🧠 Letzte MemAuto-Erinnerungen:\n"]
            for entry in self.memories[-10:]:
                out.append(f"[{entry['timestamp']}] {entry['text']}")
            return "\n".join(out)

        if c == "/memauto clear":
            self.memories = []
            self._save_memories()
            return "🗑️ Alle MAAT-MemAuto-Erinnerungen wurden gelöscht."

        return None

    # ------------------------------------------------------------------
    # BEFORE CHAT – Memory-Erkennung + optionale Kontext-Injektion
    # ------------------------------------------------------------------
    def before_chat(self, user_input: str, context=None):
        """
        1) Prüft, ob die Eingabe als Memory gespeichert werden soll (Trigger).
        2) Speichert ggf. die Memory.
        3) Wenn Injektion aktiv: hängt relevante Erinnerungen vor die Eingabe.
        """
        text = user_input.strip()
        if not text:
            return (False, user_input)

        # 1) Memory-Trigger erkennen
        mem_text = self._extract_memory_from_text(text)
        if mem_text:
            self._add_memory(mem_text, source="user")

        # 2) Wenn keine Kontext-Injektion → Eingabe unverändert
        if not self.inject_enabled or not self.memories:
            return (False, user_input)

        # 3) Relevante Erinnerungen wählen (simple Heuristik)
        relevant = self._select_relevant_memories(text, max_items=5)

        if not relevant:
            return (False, user_input)

        # 4) Sichtbaren Kontextblock bauen (ohne „nur intern anzeigen“)
        lines = []
        for entry in relevant:
            lines.append(f"- [{entry['timestamp']}] {entry['text']}")

        mem_block = (
            "MAAT-MemAuto Kontext (Hintergrundwissen über den Nutzer, "
            "das du bei deiner Antwort berücksichtigen kannst):\n"
            + "\n".join(lines)
            + "\n---\n"
            + text
        )

        if self.debug:
            print("\n[MAAT-MemAuto DEBUG] Kontext an Modell:\n")
            print(mem_block)
            print("\n[MAAT-MemAuto DEBUG ENDE]\n")

        # handled=False → andere Plugins dürfen noch ran,
        # user_input wird aber mit mem_block ersetzt
        return (False, mem_block)

    # ------------------------------------------------------------------
    # Relevanz-Heuristik
    # ------------------------------------------------------------------
    def _select_relevant_memories(self, user_input: str, max_items: int = 5):
        """
        Sehr einfache Relevanz-Heuristik:
        - Wörter (>=4 Zeichen) aus dem User-Input
        - Memories, die eines dieser Wörter enthalten, werden bevorzugt
        - Falls nichts matcht → letzte N Einträge
        """
        text = user_input.lower()
        words = [w for w in re.findall(r"\w+", text) if len(w) >= 4]

        if not words:
            return self.memories[-max_items:]

        scored = []
        for entry in self.memories:
            t = entry["text"].lower()
            score = sum(1 for w in words if w in t)
            if score > 0:
                scored.append((score, entry))

        if not scored:
            return self.memories[-max_items:]

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:max_items]]

    # ------------------------------------------------------------------
    # AFTER RESPONSE – hier nichts zu tun
    # ------------------------------------------------------------------
    def after_response(self, reply, context=None):
        return reply