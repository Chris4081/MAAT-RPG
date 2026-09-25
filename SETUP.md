# Install and play / Installieren und spielen

## English

Extract the complete game folder to a permanent location on your computer.
Close MAAT RPG before installing or updating.

| System | First launch | Later launches |
| --- | --- | --- |
| **macOS 13.3+ · Intel / Apple Silicon** | Double-click **Install.command**. | Double-click **Start GUI.command**. |
| **Linux · 64-bit Intel/AMD / ARM** | Open a terminal in the game folder and run **`bash setup.sh`**. | Run **`bash "Start Linux.sh"`** or select **MAAT RPG** in the applications menu. |

The setup selects a native Python interpreter, installs the GUI dependencies,
builds the GGUF backend for your processor, checks that Qt and the backend start,
and then opens the game. Select your own GGUF model in the game.
The start scripts also offer this automatic setup when the required environment
is missing. You do not need to activate a Python environment manually.

- **macOS:** Existing native Python 3.10–3.13 is reused. If none is available,
  the setup downloads the official Python 3.13.15 installer, checks its SHA-256
  and macOS signature, and installs it with an administrator password.
  Missing Apple Command Line Tools open Apple's installer; complete that dialog
  and leave the terminal open. Setup waits and continues afterwards.
- **Linux:** On Debian/Ubuntu/Mint, Fedora, Arch and openSUSE, system packages
  are installed through the distribution's package manager. Enter your `sudo`
  password if requested. Run the setup itself **without sudo**.
  Other distributions can use `--skip-system-deps` after their prerequisites
  have been installed manually. A graphical desktop and Python 3.10–3.13 are
  required; x86_64 needs glibc 2.28+, ARM64 needs glibc 2.39+.
- **AI acceleration:** Apple Silicon uses Metal and Apple Accelerate; Intel Macs
  use their native CPU instructions and Apple Accelerate. Linux uses a native
  CPU build with OpenBLAS when available. The setup does not force unsupported
  AVX/AVX2 instructions. Build parallelism is limited to at most four jobs.
- **Offline Wiki:** The optional libzim reader is installed when a matching
  binary package is available. You select your own ZIM later; no archive is downloaded.

The first setup needs internet and can take several minutes, especially while
building the backend on an older computer. Later game starts do not run package
installation. The setup downloads neither a language model nor background music.
The music edition already contains its soundtrack; the GitHub edition does not.

### Existing saves and installation folders

Profiles, chat history, model selections and audio preferences are preserved.
The setup does not import, delete or overwrite your game data.

- macOS environment: `.venv` inside the game folder.
- macOS saves/logs: `~/Library/Application Support/MAAT-RPG/`.
- Linux environment: `~/.local/share/MAAT-RPG/linux-env/`.
- Linux saves/logs: `~/.local/share/MAAT-RPG/` (or below `XDG_DATA_HOME`).

`MAAT_GUI_DATA_ROOT` selects an alternative data folder. On Linux, set it to the
same absolute path for both setup and launch; it also contains `linux-env`.
Keep the game folder in place. Do not copy `.venv` or `linux-env` to another
computer: run setup there so the backend matches its hardware.

### Options and troubleshooting

```bash
bash setup.sh --plan                  # Show the plan without changing anything
bash setup.sh --no-start              # Install without opening the game
bash setup.sh --skip-system-deps      # System prerequisites are already installed
bash setup.sh --rebuild-backend       # Repair/rebuild the native AI backend
bash setup.sh --no-wiki --no-shortcut # Skip optional Wiki and Linux menu entry
```

Use `MAAT_SETUP_PYTHON=python3.12 bash setup.sh` to select an existing native
Python explicitly. Python 3.14 and free-threaded builds are not supported here.
If an existing `.venv` is broken or belongs to another architecture, close the
game, rename **only `.venv`**, and rerun setup. Keep your profiles and models.

Errors remain visible in the terminal; setup logs are in the data folder's
`logs/` directory. A failed setup does not launch the game. Running it again
reuses an already verified backend unless a rebuild is necessary.
If Finder cannot execute the starter, run `bash Install.command` in the game
folder. macOS may require allowing the downloaded script in its security settings.

## Deutsch

Entpacke den vollständigen Spielordner an einen festen Platz auf deinem Rechner.
Schließe MAAT RPG vor der Einrichtung oder einem Update.

| System | Erster Start | Später starten |
| --- | --- | --- |
| **macOS ab 13.3 · Intel / Apple Silicon** | **Install.command** doppelklicken. | **Start GUI.command** doppelklicken. |
| **Linux · 64-Bit Intel/AMD / ARM** | Terminal im Spielordner öffnen und **`bash setup.sh`** ausführen. | **`bash "Start Linux.sh"`** oder **MAAT RPG** im Anwendungsmenü. |

Das Setup wählt natives Python, installiert die GUI-Abhängigkeiten, baut das
GGUF-Backend passend zum Prozessor und prüft den Start von Qt und Backend.
Danach öffnet sich das Spiel; dort wählst du dein eigenes GGUF-Modell aus.
Fehlt beim normalen Start die benötigte Umgebung, richten die Starter sie
ebenfalls automatisch ein. Eine manuelle Aktivierung der Python-Umgebung entfällt.

- **macOS:** Vorhandenes natives Python 3.10–3.13 wird genutzt. Fehlt es,
  lädt das Setup den offiziellen Python-3.13.15-Installer, prüft SHA-256 und
  macOS-Signatur und installiert ihn mit Administratorpasswort.
  Fehlende Apple Command Line Tools werden über Apples Installationsdialog
  eingerichtet. Bestätige diesen und lasse das Terminal offen; danach geht es weiter.
- **Linux:** Debian/Ubuntu/Mint, Fedora, Arch und openSUSE verwenden ihre
  Paketverwaltung für die Systemabhängigkeiten. Falls nötig, gib dein `sudo`-Passwort
  ein. Das Setup selbst **ohne sudo** starten. Bei anderen Distributionen die
  Voraussetzungen manuell installieren und `--skip-system-deps` verwenden.
  Erforderlich sind ein grafischer Desktop, Python 3.10–3.13 und glibc 2.28+
  auf Intel/AMD beziehungsweise glibc 2.39+ auf ARM64.
- **KI-Beschleunigung:** Apple Silicon verwendet Metal und Apple Accelerate;
  Intel-Macs nutzen native CPU-Befehle und Apple Accelerate. Linux erhält einen
  nativen CPU-Build mit OpenBLAS, sofern verfügbar. Nicht unterstützte
  AVX-/AVX2-Befehle werden nicht erzwungen; höchstens vier Build-Jobs laufen parallel.
- **Offline-Wiki:** Der optionale libzim-Leser wird installiert, wenn ein passendes
  Binärpaket verfügbar ist. Eine eigene ZIM wählst du später; kein Archiv wird geladen.

Die erste Einrichtung benötigt Internet und kann mehrere Minuten dauern,
besonders auf älteren Rechnern. Spätere Spielstarts installieren keine Pakete neu.
Modelle und Hintergrundmusik werden nicht heruntergeladen: Die Musikausgabe
enthält ihren Soundtrack bereits, die GitHub-Ausgabe enthält ihn nicht.

### Spielstände und Installationsordner

Profile, Chatverlauf, Modellwahl und Audioeinstellungen bleiben erhalten.
Das Setup importiert, löscht oder überschreibt keine Spieldaten.

- Mac-Umgebung: `.venv` im Spielordner.
- Mac-Spielstände und Logs: `~/Library/Application Support/MAAT-RPG/`.
- Linux-Umgebung: `~/.local/share/MAAT-RPG/linux-env/`.
- Linux-Spielstände und Logs: `~/.local/share/MAAT-RPG/` oder unter `XDG_DATA_HOME`.

Mit `MAAT_GUI_DATA_ROOT` lässt sich ein anderer Datenordner wählen; unter Linux
bei Einrichtung und Start denselben absoluten Pfad verwenden, weil dort auch
`linux-env` liegt. Den Spielordner danach nicht verschieben. `.venv` und
`linux-env` nicht auf andere Rechner kopieren, sondern dort neu einrichten.

### Optionen und Hilfe

```bash
bash setup.sh --plan                  # Nur anzeigen, nichts verändern
bash setup.sh --no-start              # Einrichten, Spiel noch nicht öffnen
bash setup.sh --skip-system-deps      # Systemvoraussetzungen sind bereits vorhanden
bash setup.sh --rebuild-backend       # KI-Backend neu bauen/reparieren
bash setup.sh --no-wiki --no-shortcut # Wiki und Linux-Menüeintrag überspringen
```

Ein bestimmtes natives Python wählst du mit
`MAAT_SETUP_PYTHON=python3.12 bash setup.sh`. Python 3.14 und Free-Threading-Builds
werden hier nicht unterstützt. Ist `.venv` beschädigt oder für eine andere
Architektur erstellt, schließe das Spiel, benenne **nur `.venv`** um und starte
das Setup erneut. Profile und Modelle behalten.

Fehler bleiben im Terminal sichtbar; Setup-Protokolle liegen unter `logs/` im
Datenordner. Bei einem Fehler startet das Spiel nicht. Ein erneuter Versuch
verwendet ein bereits geprüftes Backend wieder, sofern kein Neubau nötig ist.
Wenn der Doppelklick nicht funktioniert: `bash Install.command` im Spielordner
ausführen. macOS kann eine Freigabe des heruntergeladenen Skripts verlangen.

### Setup download sources / Downloadquellen

- [Official Python 3.13.15 macOS installer and checksum](https://www.python.org/downloads/release/python-31315/)
- [Python on macOS](https://docs.python.org/3.13/using/mac.html)
- [Apple Command Line Tools](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools)
- [llama-cpp-python installation](https://llama-cpp-python.readthedocs.io/en/latest/)
- Python packages: [PyPI](https://pypi.org/); Linux system packages: your distribution's repositories.
