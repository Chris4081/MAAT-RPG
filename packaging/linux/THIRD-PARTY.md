# Linux dependencies / Linux-Abhängigkeiten

Dieses Quellpaket enthält keine vorgebauten Python-/Qt-/GGUF-Runtimes und keine
GGUF-Modelle oder Wikipedia-ZIM-Archive. `Install Linux.sh` installiert Python-Pakete
und erstellt das GGUF-Backend lokal. Systempakete kommen aus deiner Distribution.
Die auf deinem Rechner tatsächlich installierten Versionen und ihre Lizenzdateien
sind maßgeblich; `requirements.txt` beschreibt die vorgesehenen direkten Abhängigkeiten.

- Python: PSF und enthaltene Drittanbieterhinweise.
- PySide6/Qt/Shiboken: LGPL/GPL je nach Bestandteil; Qt Multimedia kann FFmpeg enthalten.
- llama-cpp-python/llama.cpp: MIT sowie Hinweise eingebundener Bestandteile.
- Optional python-libzim: GPL-3.0-or-later; native libzim upstream: GPL-2.0-or-later.
  Diese Softwarelizenzen sind unabhängig von der Lizenz einer eigenen ZIM.
- Weitere Python-Pakete: ihre jeweiligen Lizenzdateien/Metadaten im installierten
  `site-packages` beachten; dies umfasst auch transitive und eingebettete Abhängigkeiten.

Die zusätzlichen GNU-Lizenztexte und Quellenhinweise liegen im Paket unter `licenses/`.
Sie ersetzen keine versionsgenaue Prüfung installierter Bibliotheken. Wenn du eine
fertig installierte Umgebung selbst weitergibst, müssen deren Lizenz-, Hinweis- und
Quellcodepflichten zusätzlich erfüllt werden. Siehe `WIKI_HINWEISE.md` für eigene Archive.

Grundlagen: [Qt](https://www.qt.io/development/open-source-lgpl-obligations),
[FFmpeg](https://ffmpeg.org/legal.html), [libzim](https://github.com/openzim/libzim).

Eine zweisprachige Übersicht der Softwarebausteine steht in `SOFTWARE_LICENSES.md`.

## English

This source package does not bundle a prebuilt Python/Qt/GGUF runtime, model weights
or ZIM archives. The installer downloads dependencies and builds the backend locally.
The exact installed versions and their notices govern. Dependencies include Python,
Qt/PySide/Shiboken (with FFmpeg where supplied), llama.cpp and optionally libzim;
their transitive and embedded components also have applicable terms.

Standard GNU license texts are provided under `licenses/`. They do not constitute
a complete audit of your installed environment. Redistributing that environment
requires satisfying its applicable notices and corresponding-source obligations.
User-supplied wiki contents remain separate from the GPL-licensed libzim reader.
