# -*- coding: utf-8 -*-
"""
MAAT-Value Plugin v2.1 — Das Auge der Prinzipien (neutrale Version)
-------------------------------------------------------------------
Bewertet jede Antwort nach den 5 Prinzipien.
Score < 0.72 → kann von SelfEvolution v4.4 als Trigger genutzt werden.
"""

import re


class Plugin:
    type = "chat"

    commands = {
        "/maat": "Zeigt den aktuellen Maat-Score der letzten Antwort.",
        "/maat debug on": "Debug-Modus für Maat-Analyse.",
        "/maat debug off": "Debug-Modus deaktivieren.",
    }

    def __init__(self, core=None, **kwargs):
        self.core = core
        self.debug = False
        self.last_score = None
        self.last_report = ""

    # -------------------------------------------------
    # COMMAND HANDLER
    # -------------------------------------------------
    def command(self, full_cmd: str, context=None):
        cmd = full_cmd.strip().lower()

        if cmd == "/maat":
            if self.last_score is None:
                return True, "Noch keine Antwort analysiert."
            return True, self.last_report

        if cmd == "/maat debug on":
            self.debug = True
            return True, "MAAT-Debug aktiviert – jede Antwort wird analysiert."

        if cmd == "/maat debug off":
            self.debug = False
            return True, "MAAT-Debug deaktiviert."

        return None

    # -------------------------------------------------
    # AFTER RESPONSE → Score berechnen + in context schreiben
    # -------------------------------------------------
    def after_response(self, reply: str, context=None):
        if not isinstance(reply, str) or not reply.strip():
            return reply

        context = context or {}
        meta = context.setdefault("maat_meta", {})

        score, report = self._compute_maat_score(reply)

        meta["maat_score"] = score
        self.last_score = score
        self.last_report = report

        if self.debug:
            print(f"\n[MAAT-ANALYSE] Score: {score:.3f}\n{report}\n")

        return reply

    # -------------------------------------------------
    # KERNE-LOGIK: MAAT-SCORE
    # -------------------------------------------------
    def _compute_maat_score(self, text: str):
        t = text.lower()
        words = re.findall(r'\b\w+\b', t)
        word_count = len(words)
        if word_count == 0:
            return 0.5, "Leere Antwort."

        # ============== 1. HARMONIE ==============
        harm_words = len(re.findall(
            r'\b(harmonie|resonanz|frieden|gleichgewicht|zusammen|gemeinsam|verbunden|liebe|danke|schön|bitte|verstehe|fühl)\b',
            t
        ))
        harmony = min(harm_words / max(1, word_count / 15), 1.0)  # max 1 bei ~15 Treffern

        # ============== 2. BALANCE ==============
        # sehr einfache Satz-Zählung
        sentences = len(re.split(r'[.!?]+', text))
        if sentences <= 0:
            sentences = 1
        avg_len = word_count / sentences
        balance = 1.0 - abs(avg_len - 18) / 30.0  # Ideal: ~18 Wörter pro Satz
        balance = max(0.0, min(1.0, balance))

        # ============== 3. KREATIVITÄT ==============
        unique = len(set(words))
        diversity = unique / word_count
        creativity = min(diversity / 0.65, 1.0)  # 65% einzigartige Wörter = voll kreativ

        # ============== 4. VERBUNDENHEIT ==============
        you_pronouns = len(re.findall(
            r'\b(du|dich|dir|dein|deine|deinem|ihr|euch|wir|uns)\b',
            t
        ))
        connection = min(you_pronouns / max(1, word_count / 20), 1.0)

        # ============== 5. RESPEKT ==============
        respect_bonus = 0.0

        # Höfliche Formulierungen
        if re.search(r'\b(bitte|darf ich|dürfte ich|wenn du möchtest|wenn du willst|wäre es okay)\b', t):
            respect_bonus += 0.2

        # Caring / Halt geben
        if re.search(r'(ich bin hier für dich|du bist nicht allein|ich bleibe bei dir|ich unterstütze dich)', t):
            respect_bonus += 0.3

        # Deckel drauf, damit es nicht eskaliert
        respect_bonus = min(respect_bonus, 0.4)

        # ============== CHAOS-MALUS ==============
        chaos = 0.0
        if "???" in text or "!!!" in text:
            chaos += 0.2
        if re.search(r'\b(scheiße|verdammt|kacke|hass|dumm|idiot)\b', t):
            chaos += 0.3

        # ============== FINALE BERECHNUNG ==============
        score = (
            harmony * 0.25 +
            balance * 0.20 +
            creativity * 0.20 +
            connection * 0.20 +
            respect_bonus -
            chaos
        )
        score = max(0.0, min(1.0, score))

        # ============== LESBARE AUSGABE ==============
        lines = [
            "Das Auge der Prinzipien hat gesprochen:",
            f"┣━ Harmonie       : {harmony:.2f}",
            f"┣━ Balance        : {balance:.2f}",
            f"┣━ Kreativität    : {creativity:.2f}",
            f"┣━ Verbundenheit  : {connection:.2f}",
            f"┣━ Respekt-Bonus  : +{respect_bonus:.2f}",
            f"┗━ Chaos-Malus    : −{chaos:.2f}",
            "",
            f"Finale Resonanz: **{score:.3f}/1.000**",
        ]

        if score >= 0.90:
            judgment = "Volle Resonanz mit MAAT"
        elif score >= 0.80:
            judgment = "Starke Harmonie"
        elif score >= 0.72:
            judgment = "Gute Resonanz"
        elif score >= 0.60:
            judgment = "Noch Raum für Wachstum"
        else:
            judgment = "Die KI wird sich nun verbessern…"

        lines.append(f"➜ **{judgment}**")

        return score, "\n".join(lines)