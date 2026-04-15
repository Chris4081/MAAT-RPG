> 🇩🇪 [Deutsch](#-deutsch) · 🇬🇧 [English](#-english)

# 🌿 MAAT-RPG ALPHA  
**macOS • Linux • Local • Offline • Ethical**

**MAAT RPG** is a bilingual, local AI role-playing game in the terminal, based on story, combat, path identity, journal progression and the five principles of MAAT.
### Platforms: 🍎 macOS · 🐧 Linux

### Highlights

- Bilingual German / English interface and story flow
- Reactive path profile with title, rank, and motive
- Guided demo battles and real boss encounters
- Journal, boss codex, quests, and combat progression
- Local GGUF model loading for MAAT-OS / MAAT RPG

## Gameplay Videos

Here's a look at the intro and the battle mode.

[![MAAT RPG Gameplay](https://img.youtube.com/vi/S3gQ0OWYilo/hqdefault.jpg)](https://www.youtube.com/watch?v=S3gQ0OWYilo)

A first look at **MAAT RPG** in action: story flow, bilingual UI, combat, and atmosphere.

[![MAAT RPG Gameplay](https://img.youtube.com/vi/PLjnpm_KtVo/hqdefault.jpg)](https://www.youtube.com/watch?v=PLjnpm_KtVo)

### Links

- Full feature list: [FUNKTIONEN.md](./FUNKTIONEN.md)
- Website [MAAT-RPG](https://maat-research.com/maat-rpg.html)


---

## 🇩🇪 Deutsch

**Ein narratives KI-RPG – angetrieben durch ethische Intelligenz**

MAAT-RPG ist ein lokal laufendes, story-getriebenes Rollenspiel,  
das KI, Ethik und symbolische Entwicklung verbindet.

Im Zentrum stehen die fünf MAAT-Prinzipien:

> **Harmonie · Balance · Schöpfungskraft · Verbundenheit · Respekt**

```
Kein Cloud-Zwang
Keine Accounts
Alles läuft lokal auf deinem Mac
```

---

### ✨ Features

| | Feature | Beschreibung |
|---|---|---|
| 🧠 | **Lokale KI** | llama.cpp / Apple MLX – komplett offline |
| ⚔️ | **Kampfsystem** | Normal / Boss / Final-Kämpfe |
| 🧭 | **Spielwelt** | Dungeons, Quests, Achievements & Level-System |
| 🎶 | **Atmosphäre** | Dynamische Kampfmusik & Cinematic Events |
| 🧩 | **Plugins** | Memory, BKI, Emotion, MAAT-Analyse... |
| 🛡️ | **Stabilität** | Automatisches Kontext-Management (kein Overflow) |
| 🔌 | **Architektur** | MAAT-OS – klar getrennt, erweiterbar, lokal-first |

### 📚 Funktionsübersicht

Die vollständige zweisprachige Übersicht aller Systeme, Features und Kommandos findest du in [FUNKTIONEN.md](./FUNKTIONEN.md).

---

### 🌟 Highlights

- **Bilingual by design**  
  Deutsch und Englisch ziehen sich durch Loader, Menü, Intro, HUD, Shop und Story.

- **Narrative combat with identity**  
  Bosskämpfe reagieren auf Maatis’ Pfadprofil, Auren, Phasen und Entscheidungen.

- **Local-first AI architecture**  
  Modelle, Memory, Analyse und Spielsysteme laufen lokal und modular über MAAT-OS.

- **Guided onboarding**  
  Intro, Guide-Kämpfe und klare Testmodi machen das System zugänglich, ohne den Spielstand zu verfälschen.

- **Reactive worldbuilding**  
  Journal, Boss-Codex, Quests und Konsequenznetz machen Entscheidungen dauerhaft sichtbar.

---

### 🖥️ Systemanforderungen

**Operating Systems**
- ✅ macOS 12+
- ✅ Linux (Ubuntu, Debian, Fedora)
- ? Theoretically: Windows (WSL2 + Python)


**Hardware**
- Mindestens **16 GB RAM** (24 GB empfohlen)
- Ca. **10 GB freier Speicher** (inkl. Modelle)

**Python**
- **Empfohlen: Python 3.11 oder 3.12**
- Python 3.10 kann funktionieren, ist aber nicht die bevorzugte Zielversion
- Python 3.13 wird derzeit **nicht empfohlen**, da einzelne Abhängigkeiten (z. B. `scipy`) bei der Installation scheitern können
- 👉 [python.org/downloads/macos](https://www.python.org/downloads/macos/)

---

### 🚀 Installation

**Option 1 — MAC OS Version Download (empfohlen für Spieler)**

```bash
curl -L https://maat-research.com/data/downloads/MAAT-RPG.zip -o MAAT-RPG.zip
unzip MAAT-RPG.zip
cd MAAT-RPG
xattr -dr com.apple.quarantine "MAAT RPG.app"
open "MAAT RPG.app"
```

**Option 2 — Git Clone (empfohlen für Entwickler auf macOS und Gamer/Entwickler auf Linux)**

```bash
git clone https://github.com/Chris4081/MAAT-RPG.git && cd MAAT-RPG/maatos && bash setup.sh
```

Der Installer bevorzugt automatisch:
- `python3.12`
- dann `python3.11`
- erst danach `python3`

**Wenn dein System standardmäßig Python 3.13 nutzt, installiere am besten Python 3.11 oder 3.12 und starte dann:**

```bash
MAAT_SETUP_PYTHON=python3.11 bash setup.sh
```

**Option 3 — Linux (Ubuntu / Debian)**

```bash
sudo apt update
sudo apt install -y \
    python3.11 python3.11-venv python3.11-dev \
    build-essential cmake \
    ffmpeg mpg123 alsa-utils \
    speech-dispatcher espeak-ng

git clone https://github.com/Chris4081/MAAT-RPG.git
cd MAAT-RPG/maatos
MAAT_SETUP_PYTHON=python3.11 bash setup.sh
```

**Troubleshooting**

Wenn bei der Installation ein Fehler rund um `scipy` auftaucht, verwendest du sehr wahrscheinlich eine ungeeignete Python-Version, oft Python 3.13.

Empfohlene Lösung:

```bash
MAAT_SETUP_PYTHON=python3.11 bash setup.sh
```
---

### 🔐 macOS Sicherheit (Gatekeeper)

Beim ersten Start kann macOS eine Warnung anzeigen,  
da MAAT-RPG lokal & unsigniert ist.

Falls nötig:
1. **Rechtsklick** auf `MAAT-RPG.app`
2. „**Öffnen**" wählen
3. Sicherheitsdialog **bestätigen**

> MAAT-RPG benötigt lediglich **Terminal-Zugriff**, um lokal zu starten.

---

### 📜 Lizenz

**GNU Affero General Public License v3.0 (AGPL-3.0)**

Dieses Projekt ist freie Software.  
Wenn du MAAT-RPG veränderst oder öffentlich anbietest,  
musst du den Quellcode deiner Änderungen ebenfalls offenlegen.

> MAAT-RPG ist ein Forschungs- und Kunstprojekt.  
> Ziel ist Bewusstsein, nicht Ausbeutung.

---

🌿 *MAAT-RPG ist kein Spiel über Macht – sondern über Bedeutung.*

---

## 🇬🇧 English

**A narrative AI-RPG – powered by ethical intelligence**

MAAT-RPG is a locally running, story-driven role-playing game  
that combines AI, ethics and symbolic development.

At its core stand the five MAAT principles:

> **Harmony · Balance · Creativity · Connection · Respect**

```
No cloud required
No accounts
Everything runs locally on your Mac
```

---

### ✨ Features

| | Feature | Description |
|---|---|---|
| 🧠 | **Local AI** | llama.cpp / Apple MLX – fully offline |
| ⚔️ | **Combat System** | Normal / Boss / Final battles |
| 🧭 | **Game World** | Dungeons, Quests, Achievements & Level System |
| 🎶 | **Atmosphere** | Dynamic combat music & cinematic events |
| 🧩 | **Plugins** | Memory, BKI, Emotion, MAAT Analysis... |
| 🛡️ | **Stability** | Automatic context management (no overflow) |
| 🔌 | **Architecture** | MAAT-OS – modular, extensible, local-first |

### 📚 Feature Overview

The full bilingual overview of all systems, features, and commands is available in [FUNKTIONEN.md](./FUNKTIONEN.md).

---

### 🌟 Highlights

- **Bilingual by design**  
  German and English run through the loader, menu, intro, HUD, shop, and story.

- **Narrative combat with identity**  
  Boss encounters react to Maatis' path profile, auras, phases, and decisions.

- **Local-first AI architecture**  
  Models, memory, analysis, and game systems run locally through the modular MAAT-OS structure.

- **Guided onboarding**  
  Intro, guide battles, and clear test modes make the system accessible without distorting progression.

- **Reactive worldbuilding**  
  Journal, boss codex, quests, and the consequence network make decisions persist inside the world.

---

### 🖥️ System Requirements

**macOS**
- macOS **12 Monterey** or newer
- Apple Silicon (M3 / M4 / M5 recommended)
- *(Intel Mac: experimentally supported)*

- Linux (Ubuntu, Debian, Fedora)
- ? Theoretically: Windows (WSL2 + Python)

**Hardware**
- At least **16 GB RAM** (24 GB recommended)
- Approx. **10 GB free storage** (incl. models)

**Python**
- **Recommended: Python 3.11 or 3.12**
- Python 3.10 may work, but it is not the preferred target version
- Python 3.13 is currently **not recommended**, because some dependencies (for example `scipy`) may fail during installation
- 👉 [python.org/downloads/macos](https://www.python.org/downloads/macos/)

---

### Datenquellen
- Wikipedia (CC BY-SA 4.0) via Wikimedia API
- https://foundation.wikimedia.org/wiki/Policy:API_usage_guidelines

## 🎵 Musik

Die Musik in diesem Projekt wurde mit Suno (lizenzierter Account) generiert.

Die Audioinhalte sind für Demonstrations- und Gameplay-Zwecke enthalten.

---
---

### 🚀 Installation

**Option 1 — Download (recommended for MAC OS players)**

```bash
curl -L https://maat-research.com/data/downloads/MAAT-RPG.zip -o MAAT-RPG.zip
unzip MAAT-RPG.zip
cd MAAT-RPG
xattr -dr com.apple.quarantine "MAAT RPG.app"
open "MAAT RPG.app"
```

**Option 2 — Git Clone (recommended for Linux gamers and developers (macOS/Linux)**

```bash
git clone https://github.com/Chris4081/MAAT-RPG.git && cd MAAT-RPG/maatos && bash setup.sh
```

The installer automatically prefers:
- `python3.12`
- then `python3.11`
- and only after that `python3`

**If your system default is Python 3.13, install Python 3.11 or 3.12 first and then run:**

```bash
MAAT_SETUP_PYTHON=python3.11 bash setup.sh
```

**Option 3 — Linux (Ubuntu / Debian)**

```bash
sudo apt update
sudo apt install -y \
    python3.11 python3.11-venv python3.11-dev \
    build-essential cmake \
    ffmpeg mpg123 alsa-utils \
    speech-dispatcher espeak-ng

git clone https://github.com/Chris4081/MAAT-RPG.git
cd MAAT-RPG/maatos
MAAT_SETUP_PYTHON=python3.11 bash setup.sh
```

**Troubleshooting**

If installation fails around `scipy`, you are most likely using an unsupported Python version, often Python 3.13.

Recommended fix:

```bash
MAAT_SETUP_PYTHON=python3.11 bash setup.sh
```

---

### 🔐 macOS Security (Gatekeeper)

On first launch, macOS may show a security warning  
because MAAT-RPG is local & unsigned.

If needed:
1. **Right-click** on `MAAT-RPG.app`
2. Select „**Open**"
3. **Confirm** the security dialog

> MAAT-RPG only requires **Terminal access** to run locally.

---

### 📜 License

**GNU Affero General Public License v3.0 (AGPL-3.0)**

This project is free software.  
If you modify or publicly offer MAAT-RPG,  
you must also release the source code of your changes.

> MAAT-RPG is a research and art project.  
> The goal is awareness, not exploitation.

---

### Data Sources
- Wikipedia (CC BY-SA 4.0) via Wikimedia API
- https://foundation.wikimedia.org/wiki/Policy:API_usage_guidelines

---
## 🎵 Music

Music in this project was generated using Suno (licensed account).

Audio assets are included for demonstration and gameplay purposes.

---
🌿 *MAAT-RPG is not a game about power – but about meaning.*

---

<div align="center">

**[🌐 maat-research.com](https://maat-research.com)**  
&nbsp;·&nbsp;
**[📄 Paper 21](https://maat-research.com)**  


</div>
