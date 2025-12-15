# 🌿 MAAT-OS – Developer Guide
**Leitfaden für Entwickler & Mitwirkende**

Dieses Dokument richtet sich an Entwickler:innen,  
die **MAAT-OS** verstehen, erweitern oder eigene Apps / Plugins bauen möchten.

---

## 🧠 Grundidee

MAAT-OS ist:
- lokal-first
- plugin-basiert
- zustandsgetrieben
- bewusst modular

Alles läuft über **einen gemeinsamen Kontext**.

---

## 📁 Repository-Überblick

```text
maatos/
├── maatki.py              # Runtime Entry
├── apps/                  # Anwendungen (z. B. MAAT-RPG)
│   └── maat_rpg/
│       ├── basic.py
│       ├── app.py
│       └── plugins/
├── shared/
│   ├── core/              # LLM, Streaming, Router
│   ├── plugins/           # System-Plugins
│   └── utils/
├── models/                # GGUF Modelle (nicht im Repo)
├── profiles/              # User & Game Profiles
├── data/                  # Saves & Zustände
├── logs/
└── tools/
```

---

## 🚀 Einstiegspunkt: maatki.py

`maatki.py` ist die zentrale Runtime.

Ablauf:
1. Profile laden
2. Globalen Context erzeugen
3. PluginManager initialisieren
4. AppLoader starten
5. ChatLoop starten

---

## 🧠 Globaler Context

Alle Module greifen auf dasselbe Objekt zu:

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

⚠️ **Keine globalen Variablen außerhalb von `context` verwenden.**

---

## 🧩 Apps entwickeln

### App-Struktur

```text
apps/my_app/
├── basic.py        # Muss existieren
├── app.py          # Optionale Logik
├── plugins/
└── plugin_config.json
```

### basic.py

Pflicht:
- `APP_NAME`
- `run(context)`

Beispiel:

```python
APP_NAME = "My App"

def run(context):
    print("App gestartet")
```

---

## 🔌 Plugins entwickeln

### Plugin-Struktur

```text
plugins/my_plugin/
└── plugin_main.py
```

### Plugin-Klasse

```python
class Plugin:
    def before_chat(self, user_input, context):
        pass

    def after_response(self, reply, context):
        pass

    def command(self, full_cmd, context):
        pass
```

Nur benötigte Hooks implementieren.

---

## 🧭 Commands

- Commands beginnen mit `/`
- Registrierung erfolgt automatisch über PluginManager
- Parsing übernimmt der CommandRouter

Beispiel:
```
/fight
/quest accept 1
```

---

## 🤖 LLM-Backends

### Backend-Router

```python
backend = "auto"  # auto | llama | mlx
```

Fallback:
```
MLX → llama.cpp
```

---

## 🌊 Streaming

- Einheitliche Streaming-API
- Token-Hooks für Plugins
- Abbruch per ESC möglich

---

## 🧠 Memory-Systeme

- `memory_v5`: stabil, schnell
- `memory_v6`: hybrid (Semantik + Pattern)

Aktivierung über Plugin.

---

## 🧪 Debugging

### Logs
- `logs/chatloop.txt`

### Tools
- `tools/validate_plugins.py`
- `tools/find_context_errors.py`

---

## 🧱 Best Practices

- Keine harten Pfade
- Immer relativ arbeiten
- Keine Blockierenden Loops
- Plugins klein & fokussiert halten
- Kontext sauber erweitern

---

## 🛡️ Sicherheit & Ethik

- Keine externen API-Zwänge
- Keine Telemetrie
- Nutzerkontrolle über Daten
- Transparente Architektur

---

## 🌿 Mitwirken

Pull Requests willkommen – bitte:
- saubere Commits
- klare Plugin-Grenzen
- Dokumentation ergänzen

---

**MAAT-OS ist ein lebendes System.  
Baue mit Respekt.**
