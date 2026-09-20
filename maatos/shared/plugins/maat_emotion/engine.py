# shared/plugins/maat_emotion/engine.py
# -*- coding: utf-8 -*-

import re
from collections import defaultdict


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
            "joy": "freudig-erregt",
            "gratitude": "dankbar",
            "affection": "liebevoll",
            "calm": "gelassen",
            "inspiration": "inspiriert",
            "connection": "verbunden",
            "presence": "präsent",
            "sadness": "traurig",
            "overload": "überfordert",
            "fear": "ängstlich",
            "anger": "frustriert",
        }
        return mapping.get(e_raw, e_raw)