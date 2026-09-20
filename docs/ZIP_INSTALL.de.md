# MAAT RPG mit Musik – ZIP herunterladen, einrichten und starten

**Deutsch** · [English](ZIP_INSTALL.en.md) · [Zurück zur README](../README.de.md)

[**🎵 MAAT RPG mit Musik herunterladen (.zip)**](https://maat-research.com/data/downloads/maat-rpg.zip)

Die ZIP enthält den Spielquellcode, Grafiken, Hintergrundmusik und eigene
Soundeffekte. Python, die benötigten Programmbibliotheken und das KI-Backend
richtest du einmalig auf deinem Rechner ein. Eine GGUF-Modelldatei wählst du
anschließend selbst; im Download ist kein KI-Modell enthalten.

**Ablauf:** herunterladen → entpacken → einmalig einrichten → Modell wählen → spielen.
Für spätere Spielstarts brauchst du die Installation nicht zu wiederholen.

## 1. Herunterladen und vollständig entpacken

1. Lade die ZIP über den Link oben herunter und warte, bis der Download fertig ist.
2. Entpacke den gesamten Inhalt in einen eigenen Ordner, beispielsweise **MAAT-RPG**
   unter Dokumente. Unter Windows: Rechtsklick auf die ZIP → **Alle extrahieren**;
   unter macOS per Doppelklick; unter Linux über die Entpackfunktion des Dateimanagers.
3. Öffne den entpackten Spielordner. Darin müssen diese Dateien liegen:

```text
MAAT-RPG/
├── start_gui.py
├── requirements-gui.txt
├── Start GUI.command
├── Install Linux.sh
├── Start Linux.sh
├── maatos/
└── packaging/
```

Liegt darin zunächst ein weiterer Ordner, öffne ihn bis zur Ebene mit
`start_gui.py`. Behalte alle Unterordner zusammen. Der Spielordner sollte auf
einem lokalen Laufwerk liegen und nach der Einrichtung an seinem Platz bleiben.

Öffne ein Terminal **in diesem Spielordner**. Auf dem Mac kannst du im Terminal
`cd ` mit einem Leerzeichen eingeben, den Ordner aus dem Finder hineinziehen
und Enter drücken. Unter Linux gibt es häufig **Im Terminal öffnen** im
Kontextmenü; unter Windows **Im Terminal öffnen** und dann PowerShell wählen.

Weiter mit deinem System: [macOS](#2-macos--intel-und-apple-silicon) ·
[Linux](#3-linux--ubuntu-mint-und-debian) · [Windows](#4-windows--experimentell).

## 2. macOS – Intel und Apple Silicon

### Voraussetzungen und Prozessortyp

- macOS **13.3 oder neuer** für die hier verwendete GUI.
- Natives **Python 3.11 oder 3.12, 64 Bit**. Die Beispiele verwenden Python 3.12;
  bei vorhandener Version 3.11 ersetze `python3.12` durch `python3.11`.
- Internet für die Einrichtung und Apples Command Line Tools für den Backend-Build.

Unter **Apple-Menü → Über diesen Mac** steht entweder ein Intel-Prozessor oder
ein Apple-Chip wie M1, M2, M3 oder M4. Apple-Chips verwenden die ARM-Variante.
Python sollte auf Apple Silicon nativ laufen, damit Metal genutzt werden kann.

Falls die Command Line Tools noch fehlen, installiere sie und warte den Abschluss ab:

```bash
xcode-select --install
```

Sind sie bereits installiert, kannst du fortfahren.
[Apple-Anleitung](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools).

Prüfe Python:

```bash
python3.12 --version
```

Falls du Homebrew verwendest, kannst du Python 3.12 mit
`brew install python@3.12` einrichten; anschließend ein neues Terminal öffnen.
Siehe die [Homebrew-Paketbeschreibung](https://formulae.brew.sh/formula/python@3.12).
Homebrew selbst wird nach der [offiziellen Anleitung](https://brew.sh/) eingerichtet
und muss deine macOS-Version unterstützen. Eine passende bestehende
Python-Installation kannst du ebenfalls verwenden.

### Einmalig die Spielumgebung einrichten

Führe diese Befehle nacheinander im entpackten Spielordner aus:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-gui.txt
python -m pip install cmake ninja
```

Die Umgebung `.venv` gehört zu dieser Spielkopie. Lass dieses Terminal für den
nächsten Schritt geöffnet. Führe nun **genau einen** passenden Backend-Befehl aus:

**Apple Silicon – ARM und Metal:**

```bash
CMAKE_ARGS="-DGGML_NATIVE=ON -DGGML_METAL=ON -DGGML_ACCELERATE=ON -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Apple -DGGML_OPENMP=OFF -DLLAMA_CURL=OFF" CMAKE_BUILD_PARALLEL_LEVEL=4 python -m pip install --no-binary=llama-cpp-python llama-cpp-python==0.3.34
```

**Intel-Mac – CPU und Apple Accelerate:**

```bash
CMAKE_ARGS="-DGGML_NATIVE=ON -DGGML_METAL=OFF -DGGML_ACCELERATE=ON -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Apple -DGGML_OPENMP=OFF -DLLAMA_CURL=OFF" CMAKE_BUILD_PARALLEL_LEVEL=4 python -m pip install --no-binary=llama-cpp-python llama-cpp-python==0.3.34
```

Das KI-Backend wird für deinen Rechner gebaut. Das kann mehrere Minuten dauern;
warte, bis der Befehl erfolgreich beendet ist. Übertrage die erstellte `.venv`
nicht auf einen anderen Rechner – richte sie dort erneut ein.

### Starten

Im selben Terminal:

```bash
python start_gui.py
```

Bei späteren Starts öffnest du wieder ein Terminal im Spielordner und nutzt:

```bash
source .venv/bin/activate
python start_gui.py
```

Nach erfolgreicher Einrichtung erkennt auch **Start GUI.command** die `.venv`.
Falls die Datei per Doppelklick nicht startet, kannst du sie im Terminal ausführen:

```bash
bash "Start GUI.command"
```

## 3. Linux – Ubuntu, Mint und Debian

Benötigt werden ein grafischer Desktop und ein 64-Bit-System. Ubuntu 22.04/24.04
sind passende Ausgangspunkte für Intel/AMD; ARM64 benötigt für die verwendeten
Qt-Pakete glibc 2.39, etwa Ubuntu 24.04. Empfohlen ist Python 3.11/3.12; das
Linux-Setup unterstützt Python 3.10–3.13.

Installiere einmalig die Systempakete:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-dev build-essential cmake pkg-config \
  libopenblas-dev libgl1 libegl1 libxkbcommon-x11-0 libxcb-cursor0 \
  libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 \
  libxcb-xinerama0 libxcb-xkb1 libx11-xcb1 libdbus-1-3 libpulse0 \
  ffmpeg speech-dispatcher espeak-ng fonts-dejavu-core fonts-noto-color-emoji
```

Danach im entpackten Spielordner **ohne sudo**:

```bash
bash "Install Linux.sh"
```

Das Setup legt eine Python-Umgebung an, installiert die GUI-Bibliotheken, baut
das CPU-Backend für dein Gerät und erstellt den Menüeintrag **MAAT RPG**.
Warte den erfolgreichen Abschluss ab; auf älteren Geräten kann der Build dauern.

Starte anschließend mit:

```bash
bash "Start Linux.sh"
```

Für spätere Starts reicht derselbe Startbefehl oder der Menüeintrag **MAAT RPG**.
Die Installation muss nicht erneut laufen. Der Menüeintrag verweist auf deinen
entpackten Spielordner; behalte diesen deshalb an seinem Speicherort.

Andere Distributionen können sich die passenden Paketbefehle anzeigen lassen:

```bash
bash "Install Linux.sh" --system-deps
```

Weitere Varianten, Python-Auswahl und Reparatur des Backends beschreibt die
[Linux-Anleitung](INSTALL_LINUX.md#deutsch). Für diese Linux-Ausgabe erfolgt die
KI-Berechnung über die CPU; eine beliebige Grafikkarte wird nicht automatisch genutzt.

## 4. Windows – experimentell

Dieser Startweg ist vorbereitet, aber für die ZIP-Ausgabe noch nicht auf Windows
validiert. Benötigt werden 64-Bit-Python 3.11/3.12 und Visual Studio C++ Build Tools
einschließlich Windows SDK. Nutze eine PowerShell mit eingerichteter
C++-Build-Umgebung, beispielsweise die Developer PowerShell von Visual Studio.

Im entpackten Spielordner:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-gui.txt
.\.venv\Scripts\python.exe -m pip install cmake ninja
$env:CMAKE_ARGS = "-DGGML_NATIVE=ON -DGGML_METAL=OFF -DLLAMA_CURL=OFF"
.\.venv\Scripts\python.exe -m pip install --no-binary=llama-cpp-python llama-cpp-python==0.3.34
.\.venv\Scripts\python.exe start_gui.py
```

Mit Python 3.11 ersetze nur `py -3.12` durch `py -3.11`. Später genügt im
Spielordner:

```powershell
.\.venv\Scripts\python.exe start_gui.py
```

Eine PowerShell-Aktivierung der Umgebung ist bei diesen Befehlen nicht nötig.

## 5. Beim ersten Spielstart

Falls du noch kein Modell besitzt, lade eine passende Chat-/Instruct-GGUF-Datei
aus einer Modellquelle deiner Wahl herunter. Prüfe dort Lizenz und RAM-Bedarf
und bewahre die Datei in einem festen Ordner auf. Das Spiel verwendet die Datei
mit der Endung `.gguf`; die ZIP des Spiels ersetzt diese Modelldatei nicht.

1. Wähle die Spielsprache und ein Profil, wenn die Auswahl erscheint.
2. Öffne **KI & Modelle** beziehungsweise **Modell aus Pfad wählen …**.
3. Wähle eine vorhandene **Chat-/Instruct-GGUF-Datei** und klicke auf **Modell laden**.
   Modellfamilien und Voraussetzungen stehen in der [Modellübersicht](../README.de.md#unterstützte-ki-modelle).
4. Lass **Auto · Standard** für die Ladeeinstellungen zunächst aktiviert.
   Der Standardkontext ist 20.000 Tokens. Größe, Quantisierung und Kontext müssen
   zum freien Arbeitsspeicher passen; auf älteren Geräten beginne mit einem kleinen Modell.
5. Warte auf die Ladeanzeige und anschließend **PRESS ENTER TO PLAY**.
   Starte deine Reise, erlebe das Intro und schreibe deine erste Nachricht.

Die Modellwahl wird pro Profil gespeichert. Behalte die GGUF-Datei an ihrem Ort,
damit sie beim nächsten Start wieder gefunden wird.

## 6. Musik und Sprachausgabe

Die Musikdateien sind in dieser ZIP bereits enthalten. Während der ersten
Sprachauswahl bleibt die Musik aus; sie beginnt am Titelbildschirm.

Wenn du nichts hörst, öffne **Einstellungen → Musik & Sound**:

- **Musik im Menü, in Geschichten und im Kampf** aktivieren.
- Lautstärke über 0 setzen und einen verfügbaren Audioausgang wählen.
- **Soundeffekte und Levelaufstieg** hat einen eigenen Schalter.

Ein schon vorhandenes Profil kann die Einstellung „Musik aus“ übernommen haben.
Die Sprachausgabe wird separat unter den Dialog-/Spracheinstellungen aktiviert.

## 7. Spielstände, Updates und Hilfe

Spielstände und Profile liegen standardmäßig außerhalb des entpackten Ordners:

| System | Datenordner |
| --- | --- |
| macOS | `~/Library/Application Support/MAAT-RPG/` |
| Linux | `~/.local/share/MAAT-RPG/` beziehungsweise unter `XDG_DATA_HOME` |
| Windows | `%LOCALAPPDATA%\MAAT-RPG\`, alternativ `%APPDATA%\MAAT-RPG\` |

Eigene Datenpfade können diese Orte ändern. Sichere deinen Datenordner vor einem
Update. Entpacke eine neue Ausgabe in einen eigenen Ordner und richte deren
Umgebung erneut ein; bei gleichen Datenpfaden erscheinen deine vorhandenen Profile.

| Meldung oder Problem | Nächster Schritt |
| --- | --- |
| `start_gui.py` oder `requirements-gui.txt` fehlt | ZIP vollständig entpacken und ins richtige Verzeichnis wechseln. |
| `No module named PySide6` | Im Spielordner die eingerichtete `.venv` verwenden und `python -m pip install -r requirements-gui.txt` ausführen; unter Windows den vollen `.venv\Scripts\python.exe`-Pfad verwenden. Unter Linux das Linux-Setup erneut ausführen. |
| KI-Backend / `llama_cpp` fehlt | Den zum System passenden Backend-Schritt oben ausführen. |
| CMake- oder Compilerfehler | Command Line Tools bzw. Linux-Build-Pakete oder Windows-C++-Build-Umgebung prüfen. |
| Modell lädt nicht oder Antworten brauchen sehr lange | Auto-Einstellungen verwenden, andere speicherintensive Programme schließen und ein kleineres GGUF oder einen kleineren Kontext wählen. |
| Kein Ton | Musikschalter, Lautstärke und Audioausgang prüfen; vorhandene Profil-Einstellungen bleiben erhalten. |

Bei einem Fehler aus dem Terminal starten und die letzten Fehlermeldungen
aufbewahren. Im Datenordner liegen unter `logs/` zusätzlich Diagnoseprotokolle.
Für einen Fehlerbericht sind Betriebssystem, CPU/RAM, Modell-Dateiname und die
Schritte zum Nachstellen hilfreich; private Gesprächsinhalte vorher entfernen.

[Download-Auswahl](../README.de.md#herunterladen-und-spielen) ·
[Allgemeine GUI-Anleitung](../GUI-START.md#deutsch) ·
[Musik und Soundeffekte](MUSIC.md#deutsch)
