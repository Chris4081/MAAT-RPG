# Entwicklerleitfaden / Developer guide

[Deutsch](#deutsch) · [English](#english)

## Deutsch

Dieses Repository enthält MAAT RPG mit grafischer Oberfläche, Terminal-Grundgerüst,
KI-Plugins, Spielmedien und Tests. Hier findest du die wichtigsten Einstiegspunkte,
wenn du das Spiel lokal starten oder daran mitarbeiten möchtest.

### Lokal starten

Folge der [Startanleitung](../GUI-START.md#deutsch) für Linux oder macOS.
Ein experimenteller Windows-Einstieg ist ebenfalls beschrieben. Die Anleitung
führt durch die Python-Umgebung und das zur Hardware passende GGUF-Backend.
Dein Sprachmodell wählst du anschließend im Spiel aus; GGUF-Modelle und optionale
Wikipedia-ZIM-Dateien besorgst du separat.

### Aufbau

| Verzeichnis | Inhalt |
| --- | --- |
| `maatos/gui/` | Desktop-Oberfläche, Ansichten und Grafiken |
| `maatos/apps/maat_rpg/` | Spielablauf, Kämpfe, Quests und RPG-Plugins |
| `maatos/shared/` | Gemeinsame KI-Module, Modelladapter und Plugins |
| `maatos/profiles/` | Mitgelieferte Systemprompts |
| `tests/` | Automatisierte Tests und Testdaten |
| `tools/` | Prüfwerkzeuge sowie Grafik-, Sound- und Paketwerkzeuge |
| `packaging/` | Plattform-Setup, Build-Rezepte und Lizenzbeilagen |
| `gui-preview/` | Grafikübersichten und Entwicklungsansichten |
| `docs/` | Anleitungen, Architektur und Quellenangaben |

Persönliche Spielstände, Einstellungen und Erinnerungen liegen außerhalb des
Repositorys. `maatos/profiles/` enthält die Systemprompts; deine Spielprofile
werden in den [betriebsspezifischen Datenordnern](../GUI-START.md#modelle-und-spielstände)
gespeichert. Nutze bei eigenen Tests `MAAT_GUI_DATA_ROOT` für einen separaten Datenordner.

### Änderungen prüfen

Führe diese Befehle im Repository-Ordner mit deiner eingerichteten Python-Umgebung aus:

```bash
python tools/check_repository.py
python tools/run_source_checks.py
```

Der erste Befehl prüft Syntax, Dateigrößen, lokale Markdown-Links und ausgeschlossene
Dateien. Der zweite führt ausgewählte Tests in getrennten Prozessen mit temporären
Spielständen und Qt ohne sichtbares Fenster aus. Dafür werden die Abhängigkeiten
aus `requirements-gui.txt`, aber kein KI-Modell benötigt.

Einzelne Testmodule lassen sich gezielt auswählen:

```bash
python tools/run_source_checks.py test_maat_coil test_temple_circles
```

Wiki-Integrationstests verwenden eine eigene ZIM über die Umgebungsvariable
`MAAT_TEST_ZIM`; die vorhandenen Fälle erwarten passende deutsche Artikel.
Ohne ZIM werden diese Fälle übersprungen. Die ausgewählten Tests ergänzen
Spieltests und Prüfungen auf der jeweiligen Zielhardware.

Der [GitHub-Workflow](../.github/workflows/source-checks.yml) ist für dieselben
Quellcodeprüfungen bei Pushes und Pull Requests eingerichtet. Zusätzliche Werkzeuge
zur Grafikbearbeitung sind in `requirements-dev.txt` aufgeführt.

### Mitmachen und weiterlesen

Halte Änderungen an Oberfläche und Spieltexten auf Deutsch und Englisch konsistent
und berücksichtige bestehende Spielstände. Hinweise zu Fehlerberichten und Pull
Requests stehen in [CONTRIBUTING.md](../CONTRIBUTING.md).

[Architektur](ARCHITECTURE.md) · [Plugin-API](PLUGIN_API.md) ·
[KI-Plugins](AI_PLUGINS.md) · [Softwarebibliotheken](SOFTWARE_LICENSES.md#deutsch) ·
[Medienquellen und Lizenzen](../QUELLEN_UND_LIZENZEN.md)

## English

This repository contains MAAT RPG's desktop interface, terminal foundation, AI
plugins, game media and tests. Use this guide to find your way around the code
and start contributing.

### Run locally

Follow the [setup guide](../GUI-START.md#english) for Linux or macOS, or the
experimental Windows instructions. It covers the Python environment and the
GGUF backend for your hardware. Select your own model in the game after setup;
GGUF weights and optional Wikipedia ZIM archives are supplied separately.

### Code layout

The desktop UI lives in `maatos/gui/`, game logic and RPG plugins in
`maatos/apps/maat_rpg/`, and shared AI modules and model adapters in `maatos/shared/`.
`maatos/profiles/` holds shipped system prompts. Personal saves, settings and
memories use the external platform data directories described in the setup guide.
Use `MAAT_GUI_DATA_ROOT` to choose a separate directory for your own playtests.

`tests/` contains automated checks; `tools/` contains validation, asset-generation
and packaging scripts. `packaging/` holds platform setup and build recipes,
`gui-preview/` contains artwork previews, and `docs/` contains documentation.

### Check changes

From the repository directory, using your configured Python environment:

```bash
python tools/check_repository.py
python tools/run_source_checks.py
```

The first command checks syntax, file sizes, local Markdown links and excluded
files. The second runs selected tests in isolated processes with temporary game
data and Qt offscreen. It requires `requirements-gui.txt`, but no AI model.
Pass test-module names to run a smaller selection, as shown in the German section.

Set `MAAT_TEST_ZIM` to your own archive for wiki integration tests; the existing
cases expect particular German articles. Those cases are skipped without an archive.
These checks complement manual playtesting and target-device testing.

The [GitHub workflow](../.github/workflows/source-checks.yml) is configured to run
the same source checks on pushes and pull requests. Optional asset-development
dependencies are listed in `requirements-dev.txt`.

### Contribute and explore

Keep German and English UI/game text consistent and preserve existing save data.
See [CONTRIBUTING.md](../CONTRIBUTING.md) for bug reports and pull requests.

[Architecture](ARCHITECTURE.md) · [Plugin API](PLUGIN_API.md) ·
[AI plugins](AI_PLUGINS.md#english) · [Software libraries](SOFTWARE_LICENSES.md#english) ·
[Media sources and licenses](../QUELLEN_UND_LIZENZEN.md#english-credits)
