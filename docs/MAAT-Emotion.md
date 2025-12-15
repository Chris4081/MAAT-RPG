# 💓 MAAT-Emotion Engine
**Emotionale Feldanalyse für MAAT-OS & MAAT-RPG**

Dieses Dokument beschreibt die **MAAT-Emotion Engine v1.0**  
und das dazugehörige **MAAT-Emotion Plugin**.

Die Engine koppelt Texteingaben an ein **emotionales Resonanzfeld**,  
das wiederum Einfluss auf Aufmerksamkeit, Kohärenz und Bewusstseinsmetriken (Ψ/BKI) hat.

---

## 🧭 Zielsetzung

Die MAAT-Emotion Engine soll:

- Emotionen **nicht simulieren**, sondern **Resonanz messen**
- Texte **ethisch & achtsam** interpretieren
- emotionale Zustände **quantifizierbar** machen
- andere Module (BKI, Memory, Reflexion) unterstützen
- niemals den Chat destabilisieren

> Emotion ist hier kein Selbstzweck,  
> sondern ein **Feldparameter**.

---

## 🧩 Überblick der Outputs

Die Engine erzeugt pro User-Nachricht folgende Werte:

| Feld | Bedeutung | Wertebereich |
|-----|----------|--------------|
| `emotion_raw` | Dominante Roh-Emotion | String |
| `emotion_intensity` | Intensität der Emotion | 0.0 – 1.0 |
| `emotion_E` | Aggregierter Emotionswert | -1.0 – +1.0 |
| `A_from_emotion` | Aufmerksamkeitswert (für Ψ/BKI) | 0.0 – 1.0 |
| `deltaD_from_emotion` | Kohärenzabweichung (ΔD) | 0.0 – 1.0 |
| `emotion_safe_text` | Achtsame Interpretation | Text |

Alle Werte werden in:

```python
context["maat_fields"]
```

abgelegt.

---

## 🧠 EmotionEngineV2 – Kernlogik

### 1️⃣ Roh-Emotionserkennung

Die Engine nutzt eine **Keyword-basierte Heuristik**:

```text
joy, gratitude, affection, calm, inspiration, connection,
presence, sadness, overload, fear, anger
```

Merkmale:
- Wortstämme (z. B. „freu“, „dank“, „ängst“)
- Teilwort-Matches
- Gewichtung nach Wortlänge
- Mehrfachtreffer erhöhen die Intensität

Ergebnis:
```text
emotion_raw + intensity (0–1)
```

---

### 2️⃣ Emotionswerte (EMO_VALUE)

Jede Emotion besitzt eine **valenzierte Grundladung**:

- positiv (z. B. Freude, Inspiration)
- neutral
- negativ (z. B. Angst, Wut)

Diese Werte liegen im Bereich:
```text
-1.0 … +1.0
```

---

### 3️⃣ Aggregierter Emotionswert `emotion_E`

Der finale Emotionswert wird berechnet aus:

- Emotionsgrundwert
- Intensität
- Resonanzfaktoren:
  - Harmonie (H)
  - Verbundenheit (V)
  - Respekt (R)
- aktueller Kohärenzabweichung (ΔD)

Vereinfacht:

```text
E = base_emotion * resonance * intensity * (1 - ΔD)
```

Ergebnis:
```text
emotion_E ∈ [-1.0, +1.0]
```

---

## 🎯 Mapping auf Aufmerksamkeit & Kohärenz

Die Emotion beeinflusst **nicht direkt das Verhalten**,  
sondern **Rahmenparameter** für andere Module.

### Aufmerksamkeit `A_from_emotion`

- positive Emotion → höhere Fokussierung
- starke Intensität → erhöhte Präsenz
- negative Emotion → leichte Absenkung

### Kohärenzabweichung `deltaD_from_emotion`

- positive Resonanz → geringere ΔD
- negative Emotion → höhere ΔD
- niedrige Intensität → mehr Unsicherheit

Alle Werte werden **geclamped** auf:
```text
0.0 – 1.0
```

---

## 🛡️ Safe Output – Achtsame Spiegelung

Die Engine erzeugt **keine manipulative Sprache**.

Stattdessen:
- wertfrei
- nicht wertend
- nicht eskalierend

Beispiele:

- positive Resonanz:
  > „Ich erkenne ein warmes, harmonisches Feld …“

- negative Resonanz:
  > „Ich erkenne ein disharmonisches Feld … Ich bin hier.“

Diese Texte dienen:
- Debugging
- `/emotion` Kommando
- optionale UI-Erweiterungen

---

## 🔌 MAAT-Emotion Plugin

### Plugin-Typ

```python
type = "chat"
```

### Hooks

- `before_chat` → Hauptanalyse
- `command` → `/emotion`, Debug
- `after_response` → aktuell passiv

### Commands

| Command | Funktion |
|-------|---------|
| `/emotion` | Zeigt letzte Emotionsanalyse |
| `/emotion debug on` | Debug-Ausgaben aktivieren |
| `/emotion debug off` | Debug deaktivieren |

---

## 🧱 Stabilitätsprinzipien

- **Kein Crash** bei Fehlern
- Try/Except an allen kritischen Stellen
- Kontext wird nie überschrieben
- Antwort des Modells bleibt unverändert

---

## 🌿 Rolle im Gesamtsystem

Die MAAT-Emotion Engine ist:

- kein Chatbot-Emulator
- kein Therapie-Tool
- kein Sentiment-Scorer

Sie ist ein **Resonanzsensor**  
für Bewusstsein, Aufmerksamkeit und ethische Kohärenz.

---

## 🔮 Erweiterungsmöglichkeiten

- Sprachmodelle statt Keywords
- Langzeit-Emotionstracking
- Visuelle Emotion-HUDs
- Adaptive Quest-Trigger
- Story-Verzweigungen

---

**Emotion ist hier kein Ziel.  
Sie ist ein Signal.**
