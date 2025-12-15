import re
import math

class EmotionEngine:
    EMO_MAP = {
        "joy": ["freu","happy","glücklich","juhu","cool","yay"],
        "gratitude": ["danke","dankbar"],
        "affection": ["lieb","mag dich","freund"],
        "calm": ["ruhig","entspannt"],
        "inspiration": ["idee","vision","inspir"],
        "connection": ["verbunden","nahe","gemeinsam"],
        "presence": ["hier","jetzt","moment"],
        "sadness": ["traurig","verloren"],
        "overload": ["überfordert","zuviel"],
        "fear": ["angst","unsicher","sorge"],
        "anger": ["wütend","frust","ärger"],
        "neutral": []
    }

    EMO_VALUE = {
        "joy":0.7,"gratitude":0.5,"affection":0.6,"calm":0.4,"inspiration":0.8,
        "connection":0.5,"presence":0.3,"sadness":-0.6,"overload":-0.4,
        "fear":-0.7,"anger":-0.8,"neutral":0.0
    }

    def detect_raw(self, text):
        t = text.lower()
        scores = {e:0 for e in self.EMO_MAP}
        for emo,keys in self.EMO_MAP.items():
            for k in keys:
                scores[emo]+=t.count(k)
        dom = max(scores,key=scores.get)
        return dom if scores[dom]>0 else "neutral"

    def compute_emotion(self, raw, H, V, dD, R=1.0):
        base=self.EMO_VALUE.get(raw,0.0)
        resonance=(H+V+R)/3
        E=base*resonance*(1-dD)
        return max(min(E,1.0),-1.0)

    def safe(self, raw, E):
        if raw=="neutral":
            return f"Ich erkenne ein neutrales Resonanzmuster ({E:.2f})."
        if raw in ["joy","gratitude","affection","inspiration","connection"]:
            return f"Harmonisches Muster ({raw}, {E:.2f})."
        return f"Disharmonisches Muster ({raw}, {E:.2f})."