# 🌿 MAAT-OS
**Modulare Architektur für lokale KI‑Systeme & narrative Anwendungen**

MAAT-OS ist das zugrunde liegende Betriebssystem‑Framework von **MAAT‑RPG**.  
Es verbindet lokale KI‑Backends, Plugin‑Systeme, Kontext‑Management und Spiel‑Logik
zu einer einheitlichen, erweiterbaren Architektur.

Dieses Dokument beschreibt **MAAT‑OS unabhängig vom Spiel**.

---

## 🧭 Philosophie

MAAT‑OS folgt fünf Grundprinzipien:

- **Harmonie** – klare, lesbare Struktur statt Chaos
- **Balance** – Leistung ↔ Verständlichkeit
- **Schöpfungskraft** – Plugins können Neues erschaffen
- **Verbundenheit** – alles läuft über gemeinsamen Kontext
- **Respekt** – lokal, transparent, ohne Zwang

> MAAT‑OS ist kein klassisches OS,  
> sondern ein **Runtime‑Framework für bewusste Systeme**.

---

## 📁 Grundstruktur

```text
maatos/
├── maatki.py
├── apps/
├── shared/
├── models/
├── profiles/
├── data/
├── logs/
└── tools/
```

---

## 🚀 Runtime: maatki.py

Zentrale Runtime:
- Initialisiert Context
- Lädt Profile
- Startet AppLoader
- Initialisiert PluginManager
- Startet ChatLoop

---

## 🧠 Globaler Context

Alle Module teilen sich:

```python
context = {
    "conversation": [],
    "llm": None,
    "pm": PluginManager,
    "command_router": CommandRouter,
    "profile": Profile,
    "rpg": {},
}
```

---

## 🧩 App-System

Apps liegen unter `apps/` und besitzen ein `basic.py` als Einstiegspunkt.

---

## 🔌 Plugin-System

Plugins unterstützen Hooks:
- before_chat
- after_response
- command
- on_startup

---

## 🤖 LLM & Streaming

- llama.cpp (GGUF)
- Apple MLX
- Einheitlicher Streaming‑Layer
- Abbruch & Token‑Hooks

---

## 🧠 Memory & Reflexion

- memory_v5 / memory_v6
- Emotion‑ & Bias‑Erkennung
- Unsicherheits‑Guard

---

## 🧰 Tools

Plugin‑Validator & Debug‑Tools.

---

## 🌿 Zusammenfassung

MAAT‑OS ist ein lokales, modulares KI‑Framework  
für Spiele, Forschung & bewusste Systeme.
