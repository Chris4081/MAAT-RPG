# 🎮 MAAT-RPG – Technische Dokumentation
**RPG-spezifische Architektur & Gameplay-Systeme**

Dieses Dokument beschreibt **ausschließlich die RPG-spezifischen Komponenten** von MAAT-RPG.  
Grundlagen von MAAT-OS werden hier vorausgesetzt (siehe `MAAT-OS.md`).

---

## 🧭 Überblick

MAAT-RPG ist eine **App auf MAAT-OS**, die folgende Ebenen kombiniert:

- Narrative KI (Dialog & Story)
- Klassisches RPG (Level, HP, Kämpfe)
- Symbolisches Progressionssystem (MAAT-Prinzipien)
- Audio & Cutscenes
- Persistenter Spielzustand

---

## 📁 App-Struktur

```text
apps/maat_rpg/
├── basic.py              # App-Einstiegspunkt
├── app.py                # App-Logik (Menüs, Start)
├── plugin_config.json    # Aktivierte Plugins
└── plugins/              # RPG-spezifische Plugins
```

---

## 🚀 Einstieg: basic.py

`basic.py` definiert die App für den AppLoader.

Typisch:
- Anzeigen des RPG-Menüs
- Initialisierung des RPG-States
- Übergabe an den ChatLoop

---

## 🧠 RPG-State

Der gesamte Spielzustand liegt in:

```python
context["rpg"]
```

### Typische Felder

```python
rpg = {
    "hp": 100,
    "max_hp": 100,
    "level": 1,
    "xp": 0,
    "gold": 0,
    "potions": 1,
    "skills": [],
    "stats": {},
    "flags": {},
}
```

Der State wird:
- automatisch gespeichert
- beim Start geladen
- von Plugins erweitert

---

## 📈 XP- & Level-System

- XP wird über `add_xp(xp)` vergeben
- Level-Up erfolgt automatisch
- Level-Bar wird im Terminal angezeigt
- XP-Quellen:
  - Kämpfe
  - Quests
  - Story-Ereignisse
  - Reflexions-Events

---

## ⚔️ Kampfsystem (BattleCore)

### Kampfarten

- **Normal**
- **Boss**
- **Final**

### Auto-Trigger

- Jeder 10. Sieg → Bosskampf
- Jeder 5. Boss-Sieg → Finalkampf

### Gegner-Skalierung

- Abhängig von Spielerlevel
- Kampfart beeinflusst HP & Schaden

---

## 🧩 MAAT-Angriffe

Angriffe basieren auf den fünf Prinzipien:

- Harmonie
- Balance
- Schöpfungskraft
- Verbundenheit
- Respekt

Diese sind:
- narrative Metaphern
- Gameplay-Mechaniken
- ethische Spiegel

---

## 🔊 Audio-System

### BattleMusicManager

- Eigener Thread/Prozess
- Dynamische Auswahl:
  - Normal
  - Boss
  - Final
  - Victory

Musik liegt in:
```text
plugins/*/music/
```

---

## 🎬 Cutscenes & Story

### Boss-Cutscenes

- `boss_scene_X.py`
- Optionale MP3s
- Werden nach Boss-Siegen getriggert

### Credits

- `credits.py`
- Werden nur einmal abgespielt
- Status via Flag gespeichert

---

## 🧭 Dungeons

Beispiele:
- `dungeon_60`
- `dungeon_500`
- `dungeon_1000`

Jeder Dungeon:
- eigener Plugin-Ordner
- eigener BattleCore
- eigene Musik
- eigener Fortschritt

---

## 🛒 Shop-System

- Befehl: `/shop`
- Items:
  - Heiltränke
- Gold-Logik:
  - Gewinn aus Kämpfen
  - Ausgaben im Shop

---

## 📜 Quest-System

### Quest-Pools

- `BASE_QUESTS`
- `LOCKED_QUESTS`

### Questtypen

- Chat-Keywords
- Counter (z. B. Siege)
- Daily Streaks
- Story-Triggers

### Befehle

- `/quests`
- `/quest accept <id>`
- `/quest info <id>`

---

## 🧠 Story Loader

- Stories als Python-Module
- Sequenzen, Musik & Entscheidungen
- Fortschritt wird persistiert

---

## 🧩 Achievements

- Klassische Achievements
- Emotionale / symbolische Achievements
- Anzeige via `/erfolge`

---

## 🛡️ Kontext-Management

- Soft-Resets nach X Nachrichten
- Story & Bedeutung bleiben erhalten
- Verhindert Context Overflow

---

## 🌿 Design-Ziel

MAAT-RPG ist kein Grind-Spiel.

Es ist:
- eine Reise
- ein Spiegel
- ein Lernraum

> Fortschritt entsteht durch **Bedeutung**,  
> nicht durch Wiederholung.

---


