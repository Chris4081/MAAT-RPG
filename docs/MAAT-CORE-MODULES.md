# 🧩 MAAT-OS – Core Module Übersicht
**Grobe Architekturübersicht der zentralen Systemmodule**

Dieses Dokument gibt einen **kompakten Überblick über die wichtigsten Core-Module**
von **MAAT-OS**, unabhängig von konkreten Apps (z. B. MAAT-RPG).

Es dient als **Orientierung** für Entwickler, Reviewer und Mitwirkende.

---

## 🧠 shared/core – Zentrales Nervensystem

### 1️⃣ app_loader.py
**Aufgabe:**  
- Findet verfügbare Apps (`apps/**/basic.py`)
- Zeigt Auswahlmenü
- Startet genau **eine aktive App**

**Warum wichtig:**  
→ Entkoppelt Runtime von Anwendungen

---

### 2️⃣ llm_loader.py
**Aufgabe:**  
- Initialisiert das Sprachmodell
- Wählt Backend & Performance-Profil
- Übergibt LLM-Instanz an den Context

**Abhängigkeiten:**  
- llama.cpp
- mlx_lm

---

### 3️⃣ backend_router.py
**Aufgabe:**  
- Abstraktionsschicht für LLM-Backends
- Modus: `auto`, `llama`, `mlx`
- Fallback-Logik bei Fehlern

**Designziel:**  
→ Ein Codepfad für mehrere KI-Backends

---

### 4️⃣ streaming.py
**Aufgabe:**  
- Einheitliches Token-Streaming
- Typewriter-Effekte
- ESC-Abbruch
- Hooks für Plugins

**Hooks:**  
- before_stream  
- on_token  
- after_stream

---

### 5️⃣ command_router.py
**Aufgabe:**  
- Zentrale Kommandoverarbeitung
- Leitet `/commands` an Plugins weiter
- Unterstützt Subcommands & Argumente

**Beispiel:**  
```
/quest accept 1
```

---

### 6️⃣ memoryV5
**Aufgabe:**  
- Verwaltung des Gesprächsverlaufs
- Soft-Resets
- Kontext-Begrenzung

**Ziel:**  
→ Kein Context Overflow

---

## 🔌 shared/plugins – System-Plugins

### 7️⃣ plugin_loader.py
**Aufgabe:**  
- Lädt Plugins dynamisch
- Trennt Chat- & Stream-Plugins
- Registriert Commands

---

### 8️⃣ plugin_validator.py
**Aufgabe:**  
- Prüft Plugin-Struktur
- Verhindert defekte Plugins
- Erhöht Stabilität

---

### 9️⃣ thinkloop_autothink
**Aufgabe:**  
- Optionales vertieftes Nachdenken
- Adaptive Antworttiefe

---

### 🔟 uncertainty_guard
**Aufgabe:**  
- Schätzt Unsicherheitsrisiken
- Reduziert Halluzinationen
- Unterstützt ehrliche Antworten

---

## 🧠 Bewusstseins- & Reflexionsmodule

### 11️⃣ maat_emotion
- Emotionale Resonanzanalyse
- Liefert A & ΔD
- Grundlage für BKI

---

### 12️⃣ maat_bki
- Berechnet Bewusstseinsindex Ψ
- Auto- & Manual-Modus
- Verlaufsspeicherung

---

### 13️⃣ maat_value
- Berechnet MAAT-Wert
- Ethische Bewertung
- Langzeitorientierung

---

### 14️⃣ maat_reflection_prethought
- Voranalyse von Antworten
- Klarheit, Tiefe, Felder
- Optionaler Denkrahmen

---

## 🕒 Zeit & Entwicklung

### 15️⃣ maat_time_kernel
- Zeitkontext
- Laufzeitmessung
- Themen-Zeitgedächtnis

---

### 16️⃣ self_evolution.py
- XP-Logik
- Zustandsentwicklung
- Lernkurven

---

## 🧠 Memory-Systeme


### 18️⃣ memory_v6
- Hybrid-Suche
- Semantik + Pattern
- Experimentell

---

## 🧰 Tools

### 19️⃣ tools/
- validate_plugins
- context checks
- Entwicklerhilfen

---

## 🌿 Gesamtbild

MAAT-OS besteht aus:

- 🧠 Kern (Runtime & KI)
- 🔌 Plugins (Funktionalität)
- 🎭 Apps (Erlebnis)
- 🌿 Ethik & Bewusstsein (MAAT)

> Kein Modul ist allein sinnvoll.  
> Bedeutung entsteht **im Zusammenspiel**.

---

