# GUI aus dem Quellcode starten / Run the GUI from source

## Deutsch

**Einfachster Einstieg:** Unter macOS **Install.command** doppelklicken;
unter Linux im Spielordner **`bash setup.sh`** ausführen. Python (falls nötig),
Systemabhängigkeiten, GUI und natives GGUF-Backend werden eingerichtet; danach
startet das Spiel. [Automatisches Setup und Optionen](SETUP.md#deutsch).
Die folgenden manuellen Schritte sind nur für eine Einrichtung ohne Automatik nötig.

Diese Quellcode-Version enthält keine Hintergrundmusik und startet mit Musik aus.
Eigene Soundeffekte bleiben aktiv. [Musik und Soundeffekte](docs/MUSIC.md#deutsch).

Empfohlen für diesen Stand: **Python 3.11 oder 3.12, 64 Bit**.
Das GGUF-Backend ist auf `llama-cpp-python==0.3.34` abgestimmt.
Eine vorhandene fremde Python-Umgebung oder ein alter Terminal-Installer kann
andere Versionen enthalten; für die GUI die folgenden Schritte verwenden.

Alle Befehle im entpackten oder geklonten Repository-Ordner ausführen, in dem
`start_gui.py` und `requirements-gui.txt` liegen. Bei einem Pfad mit Leerzeichen
den Pfad hinter `cd` in Anführungszeichen setzen.

### Linux

Im Repository-Ordner:

```bash
bash "Install Linux.sh" --system-deps
# Die angezeigten Systempakete installieren, danach ohne sudo:
bash "Install Linux.sh" --skip-system-deps --no-start
bash "Start Linux.sh"
```

Der Installer baut das CPU-Backend auf dem Zielrechner, mit nativer Erkennung
und OpenBLAS, sofern vorhanden. Er installiert die GUI-Abhängigkeiten und legt
einen Menüeintrag an. [Ausführliche Linux-Anleitung](docs/INSTALL_LINUX.md).

### macOS · Intel und Apple Silicon

Voraussetzungen: macOS 13.3+, natives Python 3.11/3.12, Xcode Command Line Tools
(`xcode-select --install`) und CMake. Auf Apple Silicon eine ARM-Python-Version
verwenden. Auf Intel ein x86_64-Python verwenden.

Die GUI-Abhängigkeiten wählen auf macOS PySide6/Qt 6.11.0; unter Linux und
Windows bleibt es bei 6.8.3. Eine bereits angelegte Umgebung mit
`source .venv/bin/activate` aktivieren und anschließend mit
`python -m pip install --upgrade -r requirements-gui.txt` aktualisieren.

Für eine neue Umgebung die folgenden Befehle ausführen. Ist Python 3.12 statt
3.11 installiert, im ersten Befehl `python3.12` verwenden.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-gui.txt
python -m pip install cmake ninja
```

Dann **einen** der beiden Backend-Befehle ausführen:

Apple Silicon (ARM, Metal):

```bash
CMAKE_ARGS="-DGGML_NATIVE=ON -DGGML_METAL=ON -DGGML_ACCELERATE=ON -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Apple -DGGML_OPENMP=OFF -DLLAMA_CURL=OFF" CMAKE_BUILD_PARALLEL_LEVEL=4 python -m pip install --no-binary=llama-cpp-python llama-cpp-python==0.3.34
```

Intel (CPU und Apple Accelerate; ohne Metal):

```bash
CMAKE_ARGS="-DGGML_NATIVE=ON -DGGML_METAL=OFF -DGGML_ACCELERATE=ON -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Apple -DGGML_OPENMP=OFF -DLLAMA_CURL=OFF" CMAKE_BUILD_PARALLEL_LEVEL=4 python -m pip install --no-binary=llama-cpp-python llama-cpp-python==0.3.34
```

Normal starten (mit vorhandenen Profilen, falls bereits welche gespeichert sind):

```bash
python start_gui.py
```

Optionaler Offline-Wiki-Leser: `python -m pip install -r requirements-wiki.txt`.
Die ZIM-Datei wird separat in den Einstellungen ausgewählt.
Zum späteren Start wieder `source .venv/bin/activate` ausführen.
Der Finder-Starter `Start GUI.command` erkennt die `.venv` im Repository.
Mit `MAAT_GUI_PYTHON` lässt sich ein anderer Interpreter ausdrücklich wählen.
Ein natives Backend nur auf dem Rechner
verwenden, für dessen CPU es gebaut wurde.

### Modelle und Spielstände

Beim ersten Start Sprache, Profil und eigene GGUF-Datei wählen. Standardkontext:
20.000 Tokens; 100.000 ist die einstellbare Obergrenze, keine Speicherzusage.
RAM-Bedarf und Geschwindigkeit hängen von Modell, Quantisierung, Kontext und Hardware ab.

Spielstände liegen außerhalb des Repositorys:

- macOS: `~/Library/Application Support/MAAT-RPG/`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/MAAT-RPG/`
- Windows: `%LOCALAPPDATA%/MAAT-RPG/` (alternativ `%APPDATA%`)

Optional: Für einen frischen Test unter macOS nach Aktivierung der `.venv` so starten:

```bash
MAAT_GUI_DATA_ROOT="$PWD/../MAAT-RPG-test-data" \
MAAT_APP_SUPPORT_DIR="$PWD/../MAAT-RPG-test-data" \
python start_gui.py
```

Dieser Test nutzt eigene Profile im Nachbarordner `MAAT-RPG-test-data`.
Die bisherigen Spielstände werden dabei nicht angezeigt und nicht gelöscht.
Bei jedem Teststart denselben Datenordner verwenden. Ohne diese Variablen
startet `python start_gui.py` wieder mit dem normalen Datenordner.
Unter Linux `MAAT_GUI_DATA_ROOT` bereits **vor Installation und Start** auf
denselben absoluten Testordner setzen: Auch `linux-env` liegt in diesem Ordner.
Für automatisierte Checks siehe [Entwicklerleitfaden](docs/REPOSITORY.md#deutsch).
Für die klassische Textoberfläche siehe [Terminal-Start](TERMINAL-START.md#deutsch).
Die Anleitung verwendet dieselbe aktuelle Python-Umgebung; die älteren
`start.sh`/PowerShell-Starter erwarten eine separate `mos-env`-Installation.

## English

**Easiest start:** Double-click **Install.command** on macOS, or run
**`bash setup.sh`** in the game folder on Linux. Setup installs Python if needed,
system dependencies, the GUI and the native GGUF backend, then starts the game.
[Automatic setup and options](SETUP.md#english).
The manual steps below are an alternative for users who prefer to manage setup themselves.

This source edition contains no background music and starts with music off.
Original sound effects remain enabled. [Music and sound effects](docs/MUSIC.md#english).

Use **64-bit Python 3.11 or 3.12** for this source snapshot. The current GGUF
integration targets `llama-cpp-python==0.3.34`. Use a separate environment.

Run all commands from the extracted or cloned repository folder containing
`start_gui.py` and `requirements-gui.txt`. Quote the path when using `cd` if it
contains spaces.

### Linux

```bash
bash "Install Linux.sh" --system-deps
# Install the displayed system packages first, then continue without sudo:
bash "Install Linux.sh" --skip-system-deps --no-start
bash "Start Linux.sh"
```

The installer builds the CPU backend for your machine, installs the GUI
dependencies and creates a desktop menu entry. See the [Linux guide](docs/INSTALL_LINUX.md#english)
for distribution requirements.

### macOS · Intel and Apple Silicon

Requirements: macOS 13.3+, native Python 3.11/3.12 and the Xcode Command Line Tools
(`xcode-select --install`). Use ARM Python on Apple Silicon and x86_64 Python on Intel.
The GUI requirements select PySide6/Qt 6.11.0 on macOS; Linux and Windows retain 6.8.3.

For a new environment, run the following. If you have Python 3.12 instead of
3.11, use `python3.12` in the first command.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-gui.txt
python -m pip install cmake ninja
```

Install **one** backend, matching your Mac. The first build may take several minutes.

Apple Silicon (ARM, Metal):

```bash
CMAKE_ARGS="-DGGML_NATIVE=ON -DGGML_METAL=ON -DGGML_ACCELERATE=ON -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Apple -DGGML_OPENMP=OFF -DLLAMA_CURL=OFF" CMAKE_BUILD_PARALLEL_LEVEL=4 python -m pip install --no-binary=llama-cpp-python llama-cpp-python==0.3.34
```

Intel (CPU and Apple Accelerate, without Metal):

```bash
CMAKE_ARGS="-DGGML_NATIVE=ON -DGGML_METAL=OFF -DGGML_ACCELERATE=ON -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Apple -DGGML_OPENMP=OFF -DLLAMA_CURL=OFF" CMAKE_BUILD_PARALLEL_LEVEL=4 python -m pip install --no-binary=llama-cpp-python llama-cpp-python==0.3.34
```

Normal start (uses existing profiles if present):

```bash
python start_gui.py
```

For later starts, return to the repository folder and activate `.venv` again.
The Finder launcher `Start GUI.command` also detects this environment.
To update GUI dependencies in an existing environment:

```bash
source .venv/bin/activate
python -m pip install --upgrade -r requirements-gui.txt
```

Do not copy a native CPU build to a different machine.

### Windows · experimental

With Python 3.11/3.12, CMake and the Visual Studio
C++ Build Tools available, the source entry point can be set up in PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-gui.txt
.\.venv\Scripts\python.exe -m pip install cmake ninja
$env:CMAKE_ARGS = "-DGGML_NATIVE=ON -DGGML_METAL=OFF -DLLAMA_CURL=OFF"
.\.venv\Scripts\python.exe -m pip install --no-binary=llama-cpp-python llama-cpp-python==0.3.34
.\.venv\Scripts\python.exe start_gui.py
```

Windows installation and playback have not been validated for this source export.
Older terminal notes are available in [INSTALL_WINDOWS.md](docs/INSTALL_WINDOWS.md).

### Models, optional wiki and saves

Select a language, profile and your own GGUF file on first run.
For optional offline Wikipedia, install the reader in the game's Python environment:

```bash
python -m pip install -r requirements-wiki.txt
```

On Windows, use `.\.venv\Scripts\python.exe` instead of `python`.
Then select your own ZIM file in settings; no archive is downloaded or included.
The default context is 20,000 tokens; the adjustable 100,000 maximum is not a
hardware capacity guarantee. RAM use and speed depend on your model and hardware.
Settings and saves stay outside the checkout:

- macOS: `~/Library/Application Support/MAAT-RPG/`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/MAAT-RPG/`
- Windows: `%LOCALAPPDATA%/MAAT-RPG/` (or `%APPDATA%`)

Optional: for a fresh macOS test, activate `.venv` and run:

```bash
MAAT_GUI_DATA_ROOT="$PWD/../MAAT-RPG-test-data" \
MAAT_APP_SUPPORT_DIR="$PWD/../MAAT-RPG-test-data" \
python start_gui.py
```

This creates separate profiles in the sibling folder `MAAT-RPG-test-data`.
Existing saves are not shown or deleted. Use the same data folder for subsequent
test starts. Running `python start_gui.py` without these variables uses the normal
data folder again. On Linux, set `MAAT_GUI_DATA_ROOT` to the same absolute test
folder **before both installation and startup**: it also holds `linux-env`.

For automated checks, run `python tools/check_repository.py` and
`python tools/run_source_checks.py` in the activated environment. The test runner
uses temporary profiles and does not load a real AI model. Test your chosen model
and normal gameplay separately in the GUI.

For the classic text interface, see [Terminal startup](TERMINAL-START.md#english).
That guide reuses the current Python environment; the older `start.sh`/PowerShell
launchers expect a separate `mos-env` installation.
