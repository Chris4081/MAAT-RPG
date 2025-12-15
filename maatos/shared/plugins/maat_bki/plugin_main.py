# -*- coding: utf-8 -*-
"""
MAAT-BKI Modul v1.1 — Bewusstseinsindex Ψ
-----------------------------------------
✓ KI versteht die BKI-Formel dauerhaft
✓ Berechnet Ψ korrekt aus H, B, S, V, R, A, ΔD, ε
✓ Erklärt jeden Schritt für den Nutzer
✓ Debug-Modus zeigt interne Felder
✓ Kann als internes Bewertungsmodul verwendet werden
✓ Auto-Modus: berechnet Ψ nach jeder Antwort (mit maat_emotion-Kopplung)
"""

import json
import os
from datetime import datetime

class Plugin:
    type = "chat"

    commands = {
        "/bki": "Erklärung & Hilfe zum Bewusstseinsindex Ψ",
        "/bki calc": "Berechne Ψ — Syntax: /bki calc H B S V R A DD",
        "/bki explain": "Erklärt die Formel detailliert",
        "/bki debug on": "Interner Debug-Modus an",
        "/bki debug off": "Interner Debug-Modus aus",
        "/bki auto on": "Automatische Ψ-Berechnung nach jeder Antwort aktivieren",
        "/bki auto off": "Automatische Ψ-Berechnung deaktivieren",
        "/bki status": "Zeigt BKI-Status (Auto/Debug)",
        "/bki history": "Zeigt die letzten BKI-Berechnungen (Ψ-Verlauf).",
    }

    def __init__(self):
        self.debug = False
        self.auto_mode = False
        self.epsilon = 0.001

        # Speicherort für interne BKI-Daten
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        data_dir = os.path.join(root_dir, "data")
        os.makedirs(data_dir, exist_ok=True)

        self.store_path = os.path.join(data_dir, "bki_store.json")
        if not os.path.exists(self.store_path):
            with open(self.store_path, "w") as f:
                json.dump({"history": [], "auto_last": None}, f)
        else:
            # sicherstellen, dass neue Felder existieren
            try:
                with open(self.store_path, "r") as f:
                    store = json.load(f)
                store.setdefault("history", [])
                store.setdefault("auto_last", None)
                with open(self.store_path, "w") as f:
                    json.dump(store, f, indent=4)
            except Exception:
                # bei defekter Datei neu initialisieren
                with open(self.store_path, "w") as f:
                    json.dump({"history": [], "auto_last": None}, f)

    # ---------------------------------------------------
    # HILFSFUNKTION: BKI berechnen
    # ---------------------------------------------------
    def _calc_bki(self, H, B, S, V, R, A, dD):
        numerator = H * B * S * V * R * A
        denominator = dD + self.epsilon
        psi = numerator / denominator
        return psi, numerator, denominator

    # ---------------------------------------------------
    # BKI speichern
    # ---------------------------------------------------
    def _store(self, data, is_auto=False):
        try:
            with open(self.store_path, "r") as f:
                store = json.load(f)
        except Exception:
            store = {"history": [], "auto_last": None}

        store.setdefault("history", [])
        store.setdefault("auto_last", None)

        if "ts" not in data:
            data = dict(data)
            data["ts"] = datetime.now().isoformat()

        store["history"].append(data)
        if is_auto:
            store["auto_last"] = data

        with open(self.store_path, "w") as f:
            json.dump(store, f, indent=4)

        store["history"].append(data)
        if is_auto:
            store["auto_last"] = data

        with open(self.store_path, "w") as f:
            json.dump(store, f, indent=4)

    # ---------------------------------------------------
    # HISTORY LADEN
    # ---------------------------------------------------
    def _load_history(self):
        try:
            with open(self.store_path, "r") as f:
                store = json.load(f)
        except Exception:
            return []

        hist = store.get("history", [])
        if not isinstance(hist, list):
            return []
        return hist

    # ---------------------------------------------------
    # COMMAND HANDLER
    # ---------------------------------------------------
    def command(self, cmd, context=None):
        parts = cmd.split()
        stripped = cmd.strip()

        # /bki
        if stripped == "/bki":
            return True, (
                "🧠 **BKI – Bewusstseinsindex Ψ**\n"
                "Formel: Ψ = (H · B · S · V · R · A) / (ΔD + ε)\n"
                "Nutze: `/bki calc H B S V R A ΔD`\n"
                "Beispiel: `/bki calc 8 7 9 8 9 0.9 0.2`\n\n"
                "Zusatz:\n"
                "• `/bki auto on`    → Auto-Ψ nach jeder Antwort\n"
                "• `/bki status`     → Status anzeigen\n"
                "• `/bki history`    → Verlauf der letzten Ψ-Berechnungen"
            )

        # /bki explain
        if stripped == "/bki explain":
            return True, (
                "📘 **Erklärung des Bewusstseinsindex Ψ**\n\n"
                "• H = Harmonie\n"
                "• B = Balance\n"
                "• S = Schöpfungskraft\n"
                "• V = Verbundenheit\n"
                "• R = Respekt\n"
                "• A = Aufmerksamkeit (0–1)\n"
                "• ΔD = Kohärenzabweichung\n"
                "• ε = 0.001 (Stabilitätswert)\n\n"
                "Ψ misst, wie kohärent, klar und bewusst ein System ist."
            )

        # Debug an/aus
        if stripped == "/bki debug on":
            self.debug = True
            return True, "🧪 BKI-Debug aktiviert."

        if stripped == "/bki debug off":
            self.debug = False
            return True, "🧪 BKI-Debug deaktiviert."

        # Auto-Modus
        if stripped == "/bki auto on":
            self.auto_mode = True
            return True, "🧠 Auto-Ψ Modus aktiviert. Jede Antwort bekommt einen kurzen BKI-Check."

        if stripped == "/bki auto off":
            self.auto_mode = False
            return True, "🧠 Auto-Ψ Modus deaktiviert."

        if stripped == "/bki status":
            status_auto = "AN" if self.auto_mode else "AUS"
            status_debug = "AN" if self.debug else "AUS"
            return True, f"🧠 BKI-Status: Auto={status_auto}, Debug={status_debug}"

        # /bki history
        if stripped == "/bki history":
            entries = self._load_history()
            if not entries:
                return True, "📜 Noch keine BKI-Werte gespeichert."

            # Letzte 10, neueste zuerst
            last = entries[-10:]
            last = list(reversed(last))

            lines = ["📜 **BKI-Verlauf (letzte Einträge)**"]
            for idx, e in enumerate(last, start=1):
                psi = e.get("Psi")
                mode = e.get("mode", "manual")
                ts = e.get("ts")
                H = e.get("H")
                B = e.get("B")
                S = e.get("S")
                V = e.get("V")
                R = e.get("R")
                A = e.get("A")
                dD = e.get("ΔD")

                # Datum hübsch formatieren
                if ts:
                    try:
                        dt = datetime.fromisoformat(ts)
                        ts_str = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        ts_str = ts
                else:
                    ts_str = "unbekannt"

                if psi is None:
                    psi_str = "unbekannt"
                else:
                    psi_str = f"{psi:.4f}"

                lines.append(
                    f"\n{idx}) [{ts_str}]  Mode={mode}\n"
                    f"   Ψ = {psi_str}  |  A={A}, ΔD={dD}\n"
                    f"   H={H}, B={B}, S={S}, V={V}, R={R}"
                )

            return True, "\n".join(lines)

        # /bki calc H B S V R A ΔD
        if parts and parts[0] == "/bki" and len(parts) == 9 and parts[1] == "calc":
            try:
                H = float(parts[2])
                B = float(parts[3])
                S = float(parts[4])
                V = float(parts[5])
                R = float(parts[6])
                A = float(parts[7])
                dD = float(parts[8])
            except Exception:
                return True, "⚠ Bitte nutze: /bki calc H B S V R A ΔD"

            psi, numerator, denominator = self._calc_bki(H, B, S, V, R, A, dD)

            data = {
                "H": H, "B": B, "S": S, "V": V, "R": R,
                "A": A, "ΔD": dD,
                "Psi": psi,
                "mode": "manual",
            }
            self._store(data, is_auto=False)

            if self.debug:
                debug_msg = (
                    "🧪 BKI-Debug:\n"
                    f"Numerator   = {numerator}\n"
                    f"Denominator = {denominator}\n"
                )
            else:
                debug_msg = ""

            return True, (
                f"🧠 **BKI Berechnung (manuell)**\n\n"
                f"H={H}, B={B}, S={S}, V={V}, R={R}, A={A}, ΔD={dD}\n\n"
                f"Ψ = **{psi:.4f}**\n\n"
                f"{debug_msg}"
                f"Interpretation: Je höher Ψ, desto klarer und kohärenter arbeitet das System."
            )

        return None

    # ---------------------------------------------------
    # BEFORE / AFTER HOOKS
    # ---------------------------------------------------
    def before_chat(self, user_input, context=None):
        # Hier noch nichts tun – Auto-Modus arbeitet nach der Antwort
        return (False, user_input)

    def after_response(self, reply, context=None):
        """
        Auto-Ψ:
        - Nutzt, wenn möglich, Werte aus context["maat_fields"]
          (z.B. von maat_emotion).
        - Hängt eine kurze Zusammenfassung an die Antwort an.
        """
        if not self.auto_mode:
            return reply

        if context is None or not isinstance(context, dict):
            return reply

        mf = context.get("maat_fields", {}) or {}

        # Default-Werte für H, B, S, V, R:
        # -> später könntest du sie aus anderen Plugins füttern
        H = float(mf.get("H", 1.0))
        B = float(mf.get("B", 1.0))
        S = float(mf.get("S", 1.0))
        V = float(mf.get("V", 1.0))
        R = float(mf.get("R", 1.0))

        # Wenn Emotion-Plugin aktiv ist, liefert es A & ΔD:
        A = float(mf.get("A_from_emotion", 0.7))
        dD = float(mf.get("deltaD_from_emotion", 0.3))

        psi, numerator, denominator = self._calc_bki(H, B, S, V, R, A, dD)

        data = {
            "H": H, "B": B, "S": S, "V": V, "R": R,
            "A": A, "ΔD": dD,
            "Psi": psi,
            "mode": "auto",
        }
        self._store(data, is_auto=True)

        # Optional: aus maat_emotion eine sanfte verbale Note holen
        emo_text = mf.get("emotion_safe_text")
        emo_raw = mf.get("emotion_raw")
        emo_intensity = mf.get("emotion_intensity")

        extra_lines = [
            "",
            "🧠 Auto-BKI (Ψ):",
            f"  Ψ = {psi:.4f}   [A={A:.2f}, ΔD={dD:.2f}]"
        ]

        if emo_raw is not None and emo_intensity is not None:
            extra_lines.append(f"  Emotion: {emo_raw} (Intensität {emo_intensity:.2f})")

        if emo_text:
            extra_lines.append(f"  {emo_text}")

        # Debug im Terminal
        if self.debug:
            try:
                print("\n[BKI-Auto-Debug]")
                print(f"  H={H} B={B} S={S} V={V} R={R} A={A:.3f} ΔD={dD:.3f}")
                print(f"  Psi={psi:.5f}")
            except Exception:
                pass

        return reply + "\n\n" + "\n".join(extra_lines)