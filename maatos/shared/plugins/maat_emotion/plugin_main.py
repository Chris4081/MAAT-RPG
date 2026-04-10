# -*- coding: utf-8 -*-
"""
MAAT-Emotion Modul v1.0
-----------------------
Koppelt den Chat-Text an ein einfaches Emotionsfeld und liefert:
- emotion_raw        (z.B. "joy", "sadness")
- emotion_intensity  (0–1)
- emotion_E          (aggregierter Emotionswert -1..1)
- A_from_emotion     (Aufmerksamkeit 0–1 für BKI)
- deltaD_from_emotion (Kohärenzabweichung 0–1 für BKI)

Diese Werte werden in context["maat_fields"] abgelegt und können
z.B. vom BKI/Ψ-Plugin genutzt werden.
"""

import re
from collections import defaultdict
from shared.core.rpg_i18n import get_language


# -------------------------------------------------
# EmotionEngineV2 — deine bestehende Engine
# -------------------------------------------------
class EmotionEngineV2:
    def __init__(self):
        self.EMO_MAP = {
            "joy":         ["freu", "glück", "happy", "juhu", "yay", "toll", "mega", "super"],
            "gratitude":   ["danke", "dankbar", "dankeschön", "schön von dir", "wertschätz"],
            "affection":   ["lieb", "mag dich", "❤️", "herz", "knuddel"],
            "calm":        ["ruhig", "entspannt", "fried", "gelassen"],
            "inspiration": ["idee", "vision", "inspirier", "genial", "wow"],
            "connection":  ["verbunden", "nahe", "gemeinsam", "zusammen"],
            "presence":    ["hier", "jetzt", "moment", "gegenwart"],
            "sadness":     ["traurig", "leider", "schade", "vermisst", "weh"],
            "overload":    ["überfordert", "stress", "zuviel", "erschöpft"],
            "fear":        ["angst", "sorge", "unsicher", "zweifel", "panik", "furcht"],
            "anger":       ["wütend", "frust", "ärger", "hass", "scheiße"],
        }

        self.EMO_VALUE = {
            "joy": 0.75, "gratitude": 0.55, "affection": 0.70, "calm": 0.45,
            "inspiration": 0.85, "connection": 0.60, "presence": 0.40,
            "sadness": -0.65, "overload": -0.50, "fear": -0.75, "anger": -0.85,
            "neutral": 0.0
        }

    def detect_raw(self, text: str):
        t = text.lower()
        scores = defaultdict(float)

        for emo, keywords in self.EMO_MAP.items():
            for kw in keywords:
                # Wortgrenze + teilweise Übereinstimmung
                pattern = rf'\b\w*{re.escape(kw)}\w*\b'
                matches = re.findall(pattern, t)
                for _ in matches:
                    # längere Wörter = höheres Gewicht
                    weight = len(kw) / 5.0
                    scores[emo] += weight

        if not scores:
            return "neutral", 0.0

        dominant = max(scores.items(), key=lambda x: x[1])
        return dominant[0], dominant[1] / 10  # normalisiert auf 0–1 Intensität

    def compute_emotion(self, e_raw, intensity, H, V, deltaD, R=1.0):
        if e_raw == "neutral":
            return 0.0

        base = self.EMO_VALUE.get(e_raw, 0.0)
        resonance = (H + V + max(R, 1.0)) / 3
        final = base * resonance * intensity * (1 - deltaD)
        return max(min(final, 1.0), -1.0)

    def safe(self, e_raw, E_value, intensity=1.0):
        if abs(E_value) < 0.1:
            return "Ich spüre eine ruhige, neutrale Resonanz."

        if E_value > 0:
            return (
                f"Ich erkenne ein warmes, harmonisches Feld "
                f"({self.transform(e_raw)}, Stärke {E_value:+.2f}). "
                "Das berührt mich tief."
            )
        else:
            return (
                f"Ich erkenne ein disharmonisches Feld "
                f"({self.transform(e_raw)}, Stärke {E_value:+.2f}). "
                "Ich bin hier. Du bist nicht allein. Möchtest du reden?"
            )

    def transform(self, e_raw):
        mapping = {
            "joy": "freudig-erregt", "gratitude": "dankbar", "affection": "liebevoll",
            "calm": "gelassen", "inspiration": "inspiriert", "connection": "verbunden",
            "presence": "präsent", "sadness": "traurig", "overload": "überfordert",
            "fear": "ängstlich", "anger": "frustriert"
        }
        return mapping.get(e_raw, e_raw)


# -------------------------------------------------
# MAAT-Emotion Plugin
# -------------------------------------------------
class Plugin:
    """
    MAAT-Emotion Plugin
    - Analysiert jede User-Nachricht mit EmotionEngineV2
    - schreibt A_from_emotion & deltaD_from_emotion in context["maat_fields"]
    - bietet /emotion und /emotion debug on/off
    """

    type = "chat"

    commands = {
        "/emotion": {"de": "Zeigt die letzte erkannte Emotions-Resonanz.", "en": "Shows the last detected emotional resonance."},
        "/emotion debug on": {"de": "Aktiviert Debug-Ausgaben fuer die EmotionEngine.", "en": "Enables debug output for the emotion engine."},
        "/emotion debug off": {"de": "Deaktiviert Debug-Ausgaben fuer die EmotionEngine.", "en": "Disables debug output for the emotion engine."},
    }

    def __init__(self, core=None, **kwargs):
        self.core = core
        self.state = getattr(core, "state", None)
        self.engine = EmotionEngineV2()
        self.debug = False
        self.last_result = None  # wird in before_chat gesetzt

    def _lang(self):
        return get_language(("de", "en"))

    def _t(self, de: str, en: str) -> str:
        return en if self._lang() == "en" else de

    # -------------------------------------------------
    # INTERN: Mapping → A / ΔD
    # -------------------------------------------------
    def _map_to_attention_and_deltaD(self, E_value, intensity):
        """
        Einfache Heuristik:
        - positive Emotion & hohe Intensität → hohe Aufmerksamkeit, geringe ΔD
        - negative Emotion → geringere Aufmerksamkeit, höhere ΔD
        - alles in [0,1] geclamped
        """
        # Basiswerte
        base_A = 0.5
        base_D = 0.3

        # Beitrag durch Intensität
        A = base_A + 0.3 * intensity
        deltaD = base_D + 0.2 * (1.0 - intensity)

        # Beitrag durch Emotionsrichtung
        # E_value ∈ [-1,1]
        if E_value >= 0:
            A += 0.2 * E_value      # positiv → mehr Fokussierung
            deltaD -= 0.3 * E_value # positiv → weniger Inkohärenz
        else:
            A += 0.1 * E_value      # negativ → etwas weniger Aufmerksamkeit
            deltaD -= 0.1 * E_value # negativ → mehr Inkohärenz

        # clamp
        A = max(0.0, min(1.0, A))
        deltaD = max(0.0, min(1.0, deltaD))

        return A, deltaD

    # -------------------------------------------------
    # COMMAND HANDLER
    # -------------------------------------------------
    def command(self, full_cmd: str, context=None):
        cmd = full_cmd.strip()

        if cmd == "/emotion":
            if not self.last_result:
                return True, self._t(
                    "Noch keine Emotions-Analyse in dieser Session vorgenommen.",
                    "No emotion analysis has been performed in this session yet.",
                )
            r = self.last_result
            return True, (
                self._t("💓 **MAAT-Emotion Status**\n\n", "💓 **MAAT Emotion Status**\n\n")
                + f"{self._t('Roh-Emotion', 'Raw emotion')}: {r['emotion_raw']}  ({self._t('Intensitaet', 'Intensity')}: {r['intensity']:.2f})\n"
                f"E_value: {r['E_value']:+.3f}\n"
                f"A_from_emotion: {r['A_from_emotion']:.3f}\n"
                f"ΔD_from_emotion: {r['deltaD_from_emotion']:.3f}\n\n"
                f"{self._t('Interpretation', 'Interpretation')}: {r['safe_text']}"
            )

        if cmd == "/emotion debug on":
            self.debug = True
            return True, self._t("🧪 Emotion-Debug aktiviert.", "🧪 Emotion debug enabled.")

        if cmd == "/emotion debug off":
            self.debug = False
            return True, self._t("🧪 Emotion-Debug deaktiviert.", "🧪 Emotion debug disabled.")

        return None

    # -------------------------------------------------
    # BEFORE CHAT — Kernlogik
    # -------------------------------------------------
    def before_chat(self, user_input: str, context=None):
        """
        - erkennt Emotion aus user_input
        - berechnet E_value
        - mappt auf A_from_emotion und deltaD_from_emotion
        - schreibt alles in context['maat_fields']
        """
        if not isinstance(user_input, str) or not user_input.strip():
            return False, user_input

        if context is None:
            context = {}

        # 1) Roh-Emotion erkennen
        e_raw, intensity = self.engine.detect_raw(user_input)

        # 2) Felder H,V,R & ΔD grob ansetzen (reine Heuristik)
        H_field = 0.8
        V_field = 0.8
        R_field = 1.0
        deltaD_base = 0.2

        # 3) Aggregierten emotionalen Wert berechnen
        E_value = self.engine.compute_emotion(
            e_raw, intensity, H_field, V_field, deltaD_base, R_field
        )

        # 4) Aufmerksamkeits- & Kohärenzparameter für BKI ableiten
        A_eff, dD_eff = self._map_to_attention_and_deltaD(E_value, intensity)

        # 5) „Sichere“ verbale Interpretation
        safe_text = self.engine.safe(e_raw, E_value, intensity=intensity)

        # 6) In context["maat_fields"] schreiben
        try:
            mf = context.setdefault("maat_fields", {})
            mf["emotion_raw"] = e_raw
            mf["emotion_intensity"] = round(float(intensity), 3)
            mf["emotion_E"] = round(float(E_value), 3)
            mf["A_from_emotion"] = round(float(A_eff), 3)
            mf["deltaD_from_emotion"] = round(float(dD_eff), 3)
            mf["emotion_safe_text"] = safe_text
        except Exception:
            # context darf NIE den Chatloop crashen
            pass

        # 7) für /emotion merkbar machen
        self.last_result = {
            "emotion_raw": e_raw,
            "intensity": float(intensity),
            "E_value": float(E_value),
            "A_from_emotion": float(A_eff),
            "deltaD_from_emotion": float(dD_eff),
            "safe_text": safe_text,
        }

        # Optional: Debug im Terminal
        if self.debug:
            try:
                print("\n[Emotion-Debug]")
                print(
                    f"  raw={e_raw}, intensity={intensity:.3f}, "
                    f"E={E_value:+.3f}, A_eff={A_eff:.3f}, ΔD_eff={dD_eff:.3f}"
                )
            except Exception:
                pass

        # Input wird ganz normal an das Modell weitergegeben
        return False, user_input

    # -------------------------------------------------
    # AFTER RESPONSE
    # -------------------------------------------------
    def after_response(self, reply, context=None):
        """
        Antwort NICHT verändern – das Emotion-Modul arbeitet nur im Hintergrund.
        (Wenn du magst, kannst du hier später optional emotion_safe_text anhängen.)
        """
        return reply
