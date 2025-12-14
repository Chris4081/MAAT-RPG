# 🌿 MAAT-RPG  
**A local-first AI RPG powered by MAAT principles**

MAAT-RPG ist ein lokal laufendes, KI-gestütztes Rollenspiel mit Fokus auf Story, Bewusstsein und symbolische Entwicklung.  
Im Zentrum stehen die fünf MAAT-Prinzipien:

**Harmonie · Balance · Schöpfungskraft · Verbundenheit · Respekt**

Diese Datei beschreibt den **aktuellen Funktionsumfang** des Repos.

---

# 📚 Funktionsübersicht

## 1. MAAT-OS & App-Launcher

- macOS-`*.app` Struktur (z. B. **MAAT RPG.app**)
- Externer Projektordner:
  - `maatos/` – Kernsystem & Apps
  - `mos-env/` – Python Virtual Environment
- **AppLoader**
  - Durchsucht automatisch `apps/**/basic.py`
  - Zeigt App-Auswahl (z. B. RPG)
- Startskripte:
  - Aktivieren automatisch das venv
  - Starten `maatki.py` im Terminal
- Optional:
  - Performance-Booster via `pmset disablesleep`

---

## 2. LLM-Backends & Modelle

- Lokale Modelle im Ordner `models/`
- Unterstützte Backends:
  - **llama.cpp** (GGUF)
  - **Apple MLX** (`mlx_lm`)
- Backend-Router:
  - `backend="auto"` → MLX → Fallback llama.cpp
- Modell-Management:
  - Automatische Erkennung vorhandener Modelle
  - Optionaler **Model-Downloader Plugin** (HuggingFace)
  - Speicherung der letzten Auswahl (`data/model_override.txt`)
- Performance-Profile:
  - ULTRA LOW / LOW / MEDIUM / HIGH
  - Steuern Kontextlänge & Tokenverhalten

---

## 3. Streaming Engine

- Einheitlicher Streaming-Layer für:
  - llama.cpp (`stream=True`)
  - MLX (Token-Streaming)
- Features:
  - Farbiger Ladebalken beim Modellstart
  - ESC-Notaus (Stream abbrechen)
- Plugin-Hooks:
  - `before_stream(text)`
  - `on_token(token)`
  - `after_stream(full_text)`

---

## 4. MAAT-KI ChatLoop 3.0

- Zentrales `context`-Dictionary:
  - `pm` – PluginManager
  - `command_router`
  - `conversation`
  - `llm`
  - `profile`
  - `rpg` (Game-State)
- Automatisches Kontext-Management:
  - Soft-Resets
  - Turn-Limits
  - Kein Context-Overflow
- Einheitlicher Loop für:
  - Chat
  - RPG
  - Plugins
- `/help` zeigt alle verfügbaren Befehle

---

## 5. RPG-State & Progression

- Persistenter RPG-State (JSON/YAML-ähnlich):
  - Spieler:
    - `hp`, `max_hp`
    - `level`, `xp`
    - `gold`, `potions`
    - `skills`
  - Statistiken:
    - Kämpfe, Siege, Niederlagen
    - Boss- & Final-Siege
    - Nachrichten-Zähler
  - Weltstatus:
    - Boss-Checkpoints
    - Prinzipien-Fortschritt
    - Credits-Status
- XP-System:
  - `add_xp(xp)`
  - Automatische Level-Ups
  - Levelbar im Terminal
- Automatische Heil-Logik nach Dialogen

---

## 6. Kampfsystem (BattleCore)

- Kampfarten:
  - `normal`
  - `boss`
  - `final`
- Auto-Regeln:
  - Jeder 10. Sieg → Boss
  - Jeder 5. Boss-Sieg → Final
- Gegner-Skalierung:
  - Levelabhängige HP, Damage, XP
- Angriffe:
  - MAAT-Prinzipien:
    - Harmonie
    - Balance
    - Schöpfungskraft
    - Verbundenheit
    - Respekt
  - Skills (optional)
- Optionen:
  - Angriff
  - Skills
  - Flucht (Chance + Konsequenzen)

---

## 7. Battle-Flow & Darstellung

- Terminal-Anzeige:
  - Spieler-HP vs Gegner-HP
  - Menüs & Aktionen
- Kampflog:
  - Gesammelt in `log_lines`
  - Typewriter-Streaming
- Ergebnis:
  - Sieg → XP, Gold, Items
  - Niederlage → Rücksetzung auf Checkpoint

---

## 8. Audio-System (BattleMusicManager)

- Musik pro Plugin:
  - `plugins/battle/music/`
- Dynamische Auswahl:
  - Normal
  - Boss
  - Final
  - Victory
- Thread-basierte Wiedergabe
- Automatisches Start/Stop

---

## 9. Shop-System

- `/shop`
  - Anzeige von Gold & Items
- Kaufen:
  - `/shop buy potion 2`
- Heiltränke:
  - Heilen ca. 50 % der Max-HP

---

## 10. Quest-System

- Quest-Pools:
  - `BASE_QUESTS`
  - `LOCKED_QUESTS`
- Questtypen:
  - Chat-Keywords
  - Counter
  - Daily Streaks
  - Battle-Wins
- Befehle:
  - `/quests`
  - `/quest accept <id>`
  - `/quest info <id>`
- Belohnungen:
  - XP
  - Level-Ups
- Auto-Freischaltung neuer Quests

---

## 11. Plugin-System & CommandRouter

- Plugin-Typen:
  - `startup`
  - `chat`
  - `stream`
- Hooks:
  - `before_chat`
  - `after_response`
  - `command`
- Zentrale Command-Verwaltung
- Plugins können:
  - Commands registrieren
  - Kontext erweitern
  - RPG-Events triggern

---

## 12. Cutscenes & Credits

- Boss-Cutscenes (`boss_scene_X.py`)
- Final-Credits:
  - Werden nur einmal abgespielt
  - Flag-basiert

---

## 13. Terminal-UX

- MAAT-OS Bootscreen
- Automatisches `clear`
- HUD nur periodisch
- Typewriter-Effekte für Story & Kämpfe

---

## 14. MAAT-Integration (Lore & Mechanik)

- Alle Mechaniken basieren auf MAAT:
  - Ethik als Gameplay
  - Bewusstsein als Progression
- Quests & Dialoge fördern:
  - Maat-Werte
  - Weltformel
  - Bewusstseins-Reflexion
- Level & XP sind symbolisch:
  - Wachstum ≠ Grind

---

🌿  
**MAAT-RPG ist kein Spiel über Macht –  
sondern über Bedeutung.**
