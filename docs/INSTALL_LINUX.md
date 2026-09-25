# MAAT RPG · Linux GUI / Grafische Linux-Version

## Deutsch

Diese Anleitung richtet das grafische RPG aus dem GitHub-Quellcode ein.
Das Linux-Setup erstellt eine eigene Python-Umgebung, baut das KI-Backend für
deine CPU und legt einen Menüeintrag an. Die Oberfläche bietet Deutsch und Englisch.

### Voraussetzungen

- 64-Bit-Linux: Intel/AMD x86_64 oder ARM64; ein grafischer Desktop.
- Python 3.10–3.13, empfohlen 3.11 oder 3.12.
- Intel/AMD: glibc 2.28 oder neuer; Ubuntu 22.04/24.04 sind passende Ausgangspunkte.
- ARM64: Die verwendeten Qt-Pakete benötigen glibc 2.39, z. B. Ubuntu 24.04.
- Debian, Mint, Fedora, Arch und openSUSE sind grundsätzlich vorgesehen; die
  Paketnamen und Python-Version müssen zur Distribution passen.
- Alpine/musl, 32-Bit-Systeme und deutlich ältere Linux-Versionen werden von
  diesem Setup nicht unterstützt.
- Internet wird einmal für Python-Abhängigkeiten und den KI-Backend-Build
  benötigt. GGUF und optionale ZIM-Dateien wählst du selbst im Spiel aus.

### Installation auf Ubuntu / Mint / Debian

Das Repository über **Code → Download ZIP** herunterladen und entpacken oder
mit Git klonen. Ein Terminal im Ordner mit `Install Linux.sh` und `Start Linux.sh`
öffnen. Den Ordner danach behalten: der Menüeintrag zeigt auf diesen Speicherort.

Ein Befehl genügt; das Setup selbst **ohne sudo** starten:

```bash
bash setup.sh
```

Systempakete werden über die Paketverwaltung eingerichtet; falls nötig, gib dein
Administratorpasswort ein. Danach werden die Python-Umgebung, das native KI-Backend
und ein Menüeintrag **MAAT RPG** angelegt. Zum Abschluss startet das Spiel.
`bash "Install Linux.sh"` ist ein gleichwertiger Einstieg.

Bei älteren CPUs kann der erste Backend-Build mehrere Minuten dauern. Später
**MAAT RPG** im Anwendungsmenü oder `bash "Start Linux.sh"` verwenden.
Mit `--no-start` richtest du nur ein, mit `--skip-system-deps` überspringst du bereits
vorhandene Systempakete. [Alle Setup-Optionen](../SETUP.md#deutsch).

Paketbefehle nur anzeigen, ohne etwas zu installieren:

```bash
bash setup.sh --system-deps
```

Wenn die Distribution bereits Python 3.14 verwendet, zusätzlich Python 3.12
installieren und den passenden Interpreter wählen:

```bash
MAAT_SETUP_PYTHON=python3.12 bash "Install Linux.sh"
```

### KI und ältere Prozessoren

- Intel/AMD nutzt den vorhandenen **GGUF (Intel)**-Adapter; ARM64 den ARM-Adapter
  ohne Apple Metal. Diese Linux-Ausgabe verwendet die CPU.
- llama-cpp-python 0.3.34 wird auf dem Zielrechner mit `GGML_NATIVE=ON` gebaut.
  AVX/AVX2 werden nicht pauschal erzwungen. OpenBLAS wird genutzt, wenn die
  Entwicklungsbibliothek verfügbar ist; ansonsten bleibt der CPU-Fallback.
- Standardkontext bleibt **20.000**. Die Hardwareerkennung begrenzt automatisch
  die Generierungs-Threads auf geeignete verfügbare Kerne. Manuelle Einstellungen,
  Modellspeicherprüfung und Streaming bleiben erhalten.
- Beginne auf dem alten Intel mit einem bereits bewährten kleinen GGUF-Modell.
  Mehr RAM hilft beim Laden größerer Modelle; die Geschwindigkeit hängt von CPU,
  Speicherbandbreite, Modell und Kontext ab.
- Kein GGUF-Modell und keine persönlichen Spielstände sind im Repository enthalten.
- Die erzeugte `linux-env` nicht auf einen anderen Rechner kopieren. Dort das
  Setup erneut ausführen. Zum Reparieren oder nach einem CPU-Wechsel:

```bash
bash "Install Linux.sh" --rebuild-backend
```

### Daten, Ton und Diagnose

Daten und alle zehn Profilplätze liegen standardmäßig in
`~/.local/share/MAAT-RPG`, bei gesetztem `XDG_DATA_HOME` entsprechend darunter.
Die Installation verändert keine bestehenden Spielstände.

Für getrennte Testprofile `MAAT_GUI_DATA_ROOT` vor **Installation und Start** auf
denselben absoluten Ordner setzen. Dort werden auch die Python-Umgebung
`linux-env` und die Testprotokolle abgelegt. Ein anderer Datenordner zeigt andere
Profile; er löscht die bisherigen Spielstände nicht.

- GUI-Musik/Sounds: Qt Multimedia in einem eigenen Audioprozess; Linux-Ausgabe
  über die auf dem Desktop eingerichteten Audio-Geräte.
- TTS: `spd-say`, alternativ `espeak-ng`/`espeak`; die bestehenden Stop-Regeln
  für neue Antworten, Kämpfe und Geschichten bleiben erhalten.
- Offline-Wiki: `libzim` wird optional installiert. Fehlt dafür ein kompatibles
  Paket, läuft das Spiel weiter; Wiki bleibt dann unverfügbar.
- Diagnose ohne Modell-Laden: `bash "Start Linux.sh" --check`
- Protokolle: `~/.local/share/MAAT-RPG/logs/` (`linux-setup-*`, `linux-start-*`,
  `gui-*` und `worker-*`). Das Starter-Protokoll speichert keine Chattexte.
- Bei Wayland-Problemen mit vorhandenem XWayland:
  `QT_QPA_PLATFORM=xcb bash "Start Linux.sh"`
- Bei einem `xcb`-Fehler zuerst die oben genannten Qt-Systembibliotheken prüfen.

## English

This guide sets up the graphical RPG from the GitHub source repository.
The Linux installer creates a separate Python environment, builds the AI backend
for your CPU and adds a desktop menu entry. The interface supports English and German.

**Requirements:** a 64-bit Intel/AMD or ARM64 Linux desktop and Python 3.10–3.13.
The pinned Qt wheels require glibc 2.28+ on x86_64, or 2.39+ on ARM64. Ubuntu
22.04/24.04 is the main x86_64 target; use Ubuntu 24.04 or equivalent for ARM64.
Other glibc distributions are possible with matching system libraries. This
installer does not support Alpine/musl or 32-bit systems.

1. Download the repository with **Code → Download ZIP** and extract it, or clone
   it with Git. Keep the folder: the desktop shortcut will point to it.
2. Open a terminal in the folder containing `Install Linux.sh` and `Start Linux.sh`.
   Run **`bash setup.sh` without sudo**. It installs system packages, the GUI and
   native backend, creates a menu entry and starts the game. Enter your system
   password when requested.
3. Use `--no-start` to install only, or `--skip-system-deps` for manually prepared
   systems. [All setup options](../SETUP.md#english).
4. For later launches, run `bash "Start Linux.sh"` or use the **MAAT RPG** menu entry.
5. Select German/English and your own GGUF model in the game.

The first setup needs internet and builds llama.cpp for the actual CPU, using
OpenBLAS when available. It does not force AVX2 on older processors. Subsequent
starts do not rebuild the backend. This package uses CPU inference on Linux;
Metal remains exclusive to macOS. The default context is still 20,000.

Data/profiles stay in `~/.local/share/MAAT-RPG` (or `$XDG_DATA_HOME/MAAT-RPG`).
Setup preserves existing saves. Do not copy the generated `linux-env` between
machines; run setup again on each machine. Use `--rebuild-backend` for repairs.
No models, ZIM archives or personal saves are bundled. Optional offline-Wiki
installation failure does not prevent the rest of the game from running.

For separate test profiles, set `MAAT_GUI_DATA_ROOT` to the same absolute folder
before **both installation and startup**. This folder also holds `linux-env`
and diagnostic logs. Choosing another data folder shows different profiles;
it does not delete your existing saves.

Use `bash "Start Linux.sh" --check` to diagnose Qt/native library loading without
loading a model. Logs are in the data directory's `logs` folder. For a Wayland
issue, try `QT_QPA_PLATFORM=xcb bash "Start Linux.sh"` if XWayland is installed.

## Aktualisieren / Updating

Das Spiel schließen und den Quellcode aktualisieren oder die neue Version in
einen eigenen Ordner entpacken. Dort `bash "Install Linux.sh"` erneut ausführen.
Das aktualisiert Abhängigkeiten und Menüeintrag. Bei unveränderter CPU und
Backend-Konfiguration wird das vorhandene Backend wiederverwendet.
Die vorhandenen Profile bleiben im gewählten Datenordner erhalten.

Close the game and update the source, or extract the new version into a separate
folder. Run `bash "Install Linux.sh"` there again to update dependencies and the
desktop shortcut. The existing backend is reused when CPU and build settings
match. Profiles remain in the selected data folder.

## Technical references

- [Qt 6.8 Linux library requirements](https://doc.qt.io/qt-6.8/linux-requirements.html)
- [PySide6 6.8.3 platform wheels and Python requirements](https://pypi.org/project/PySide6/6.8.3/)
- [llama-cpp-python build options and OpenBLAS](https://github.com/abetlen/llama-cpp-python#installation)
