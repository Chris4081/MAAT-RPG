# Software libraries and licenses / Softwarebibliotheken und Lizenzen

[English](#english) · [Deutsch](#deutsch)

## English

MAAT RPG is built with open-source software. These projects provide the desktop
interface, local AI, offline wiki and supporting tools. Thank you to their authors
and contributors.

This source repository includes the game code and media. Python, Qt and the GGUF
backend are installed separately using the setup instructions. Prebuilt runtimes,
model weights and Wikipedia ZIM archives are not bundled here.

### Main dependencies

| Project | Used for | License |
| --- | --- | --- |
| [CPython](https://www.python.org/) | Python runtime | PSF license and included notices |
| [PySide6 / Shiboken / Qt](https://www.qt.io/development/open-source-lgpl-obligations) | Desktop interface, graphics and multimedia | LGPLv3/GPL, depending on the component |
| [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) / [llama.cpp](https://github.com/ggml-org/llama.cpp) | Local GGUF model loading and inference | MIT |
| [python-libzim](https://github.com/openzim/python-libzim) | Optional Python interface for offline Wikipedia | GPL-3.0-or-later |
| [libzim](https://github.com/openzim/libzim) | Native ZIM reading and search, used by python-libzim | GPL-2.0-or-later |
| [NumPy](https://numpy.org/) | Numerical operations | BSD-3-Clause, plus notices for bundled components |
| [PyYAML](https://pyyaml.org/) | Configuration files | MIT |
| [Requests](https://requests.readthedocs.io/) / [DiskCache](https://grantjenks.com/docs/diskcache/) | HTTP utilities / caching | Apache-2.0 |
| [Jinja2 / MarkupSafe](https://palletsprojects.com/) | Templates and text handling | BSD-3-Clause |
| [Colorama](https://github.com/tartley/colorama) | Terminal colours | BSD-3-Clause |
| [psutil](https://github.com/giampaolo/psutil) | System and resource information | BSD-3-Clause |
| [typing_extensions](https://github.com/python/typing_extensions) | Python typing support | PSF-2.0 |

The setup requirements are recorded in `requirements-gui.txt`,
`requirements-wiki.txt` and the platform setup recipes. The GUI setup guide
specifies the hardware-specific GGUF backend installation.

### Supporting libraries and development tools

Dependencies may also install supporting libraries. These include
[urllib3](https://urllib3.readthedocs.io/) and
[charset-normalizer](https://github.com/jawah/charset_normalizer) under MIT,
[idna](https://github.com/kjd/idna) under BSD-3-Clause, and
[certifi](https://github.com/certifi/python-certifi) under MPL-2.0.
Qt Multimedia may include [FFmpeg](https://ffmpeg.org/legal.html), whose license
is LGPL-2.1-or-later or GPL depending on its build configuration.

Optional artwork tools are listed in `requirements-dev.txt`:
[Pillow](https://github.com/python-pillow/Pillow/blob/main/LICENSE) uses the
PIL/Pillow license (MIT-CMU), and
[SciPy](https://github.com/scipy/scipy/blob/main/LICENSE.txt) uses BSD-3-Clause.
These tools are for working on assets; they are not required to play with the
shipped artwork. Installation tools such as pip and setuptools have their own
MIT licenses and additional notices for vendored components.

### Included TinyLlama template

`CHAT_V1_TEMPLATE` in `maatos/shared/core/tinyllama.py` comes from the
Apache-2.0 TinyLlama Chat v1.0 repository. It supplies a fallback only for
identified v1.0 exports without an embedded template. See the
[attribution](../packaging/licenses/TINYLLAMA-NOTICE.md) and
[Apache-2.0 license](../packaging/licenses/Apache-2.0.txt).
Model weights are not included.

### License information

The MAAT RPG game code is licensed under **GNU AGPL v3**, as provided in
`LICENSE.txt`. Third-party software retains its own copyright and license terms;
the game's license does not replace them. The original license files for the
installed versions also cover any additional components and exceptions.

Supplemental license texts are kept in `packaging/licenses/`, with their sources
and hashes in `SOURCES.json` in that directory. They complement the original
project notices. If you redistribute dependencies as source or binaries, retain
the applicable notices and meet any corresponding-source or installation-information
requirements of their licenses. See the linked upstream projects for their terms.

Artwork, music and sound are documented separately in `QUELLEN_UND_LIZENZEN.md`.
Model weights and ZIM contents have their own licenses; the license of a model
backend or wiki reader does not determine the license of those contents.

## Deutsch

MAAT RPG baut auf freier Software auf. Diese Projekte ermöglichen die grafische
Oberfläche, lokale KI, das Offline-Wiki und die zugehörigen Werkzeuge. Vielen Dank
an ihre Entwicklerinnen, Entwickler und Mitwirkenden.

Dieses Quellcode-Repository enthält den Spielcode und die Spielmedien. Python,
Qt und das GGUF-Backend werden anhand der Startanleitung separat installiert.
Vorgebaute Laufzeiten, Modellgewichte und Wikipedia-ZIM-Archive sind hier nicht enthalten.

### Zentrale Abhängigkeiten

| Projekt | Aufgabe | Lizenz |
| --- | --- | --- |
| [CPython](https://www.python.org/) | Python-Laufzeit | PSF-Lizenz und enthaltene Hinweise |
| [PySide6 / Shiboken / Qt](https://www.qt.io/development/open-source-lgpl-obligations) | Oberfläche, Grafik und Multimedia | LGPLv3/GPL, je nach Bestandteil |
| [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) / [llama.cpp](https://github.com/ggml-org/llama.cpp) | Laden und Ausführen lokaler GGUF-Modelle | MIT |
| [python-libzim](https://github.com/openzim/python-libzim) | Optionaler Python-Zugang zum Offline-Wiki | GPL-3.0-or-later |
| [libzim](https://github.com/openzim/libzim) | Lesen und Durchsuchen von ZIM-Dateien über python-libzim | GPL-2.0-or-later |
| [NumPy](https://numpy.org/) | Numerische Berechnungen | BSD-3-Clause und Hinweise zu eingebundenen Bestandteilen |
| [PyYAML](https://pyyaml.org/) | Konfigurationsdateien | MIT |
| [Requests](https://requests.readthedocs.io/) / [DiskCache](https://grantjenks.com/docs/diskcache/) | HTTP-Hilfsfunktionen / Zwischenspeicher | Apache-2.0 |
| [Jinja2 / MarkupSafe](https://palletsprojects.com/) | Vorlagen und Textverarbeitung | BSD-3-Clause |
| [Colorama](https://github.com/tartley/colorama) | Terminalfarben | BSD-3-Clause |
| [psutil](https://github.com/giampaolo/psutil) | System- und Ressourceninformationen | BSD-3-Clause |
| [typing_extensions](https://github.com/python/typing_extensions) | Python-Typunterstützung | PSF-2.0 |

Die vorgesehenen Abhängigkeiten stehen in `requirements-gui.txt`,
`requirements-wiki.txt` und den jeweiligen Plattform-Installationsrezepten.
Die GUI-Startanleitung beschreibt die zur Hardware passende Installation des
GGUF-Backends.

### Weitere Bibliotheken und Entwicklungswerkzeuge

Bei der Installation kommen weitere Bibliotheken hinzu, darunter
[urllib3](https://urllib3.readthedocs.io/) und
[charset-normalizer](https://github.com/jawah/charset_normalizer) unter MIT,
[idna](https://github.com/kjd/idna) unter BSD-3-Clause sowie
[certifi](https://github.com/certifi/python-certifi) unter MPL-2.0.
Qt Multimedia kann [FFmpeg](https://ffmpeg.org/legal.html) enthalten; dafür gilt
je nach Build-Konfiguration LGPL-2.1-or-later oder GPL.

Optionale Grafikwerkzeuge stehen in `requirements-dev.txt`:
[Pillow](https://github.com/python-pillow/Pillow/blob/main/LICENSE) verwendet die
PIL/Pillow-Lizenz (MIT-CMU),
[SciPy](https://github.com/scipy/scipy/blob/main/LICENSE.txt) steht unter BSD-3-Clause.
Diese Werkzeuge dienen der Arbeit an den Grafiken. Zum Spielen mit den vorhandenen
Grafiken werden sie nicht benötigt. Installationswerkzeuge wie pip und setuptools
haben eigene MIT-Lizenzen und weitere Hinweise zu eingebundenen Komponenten.

### Enthaltene TinyLlama-Vorlage

`CHAT_V1_TEMPLATE` in `maatos/shared/core/tinyllama.py` stammt aus dem
Apache-2.0-Repository von TinyLlama Chat v1.0. Sie dient nur als Ersatz für
erkannte v1.0-Exporte ohne eingebettete Vorlage. Siehe
[Quellenhinweis](../packaging/licenses/TINYLLAMA-NOTICE.md) und
[Apache-2.0-Lizenz](../packaging/licenses/Apache-2.0.txt).
Modellgewichte sind nicht enthalten.

### Lizenzinformationen

Der Spielcode von MAAT RPG steht unter **GNU AGPL v3**, enthalten in `LICENSE.txt`.
Drittanbieter-Software behält ihre eigenen Urheberrechts- und Lizenzbedingungen;
die Spiel-Lizenz ersetzt diese nicht. Maßgeblich sind die ursprünglichen Lizenztexte
der installierten Versionen einschließlich weiterer Bestandteile und Ausnahmen.

Ergänzende Lizenztexte liegen unter `packaging/licenses/`; die dortige
`SOURCES.json` verzeichnet ihre Quellen und Prüfsummen. Sie ergänzen die Hinweise
der ursprünglichen Projekte. Wer Abhängigkeiten als Quellcode oder Binärdateien
weitergibt, muss die jeweils erforderlichen Hinweise erhalten und gegebenenfalls
Quellcode sowie Installationsinformationen bereitstellen. Die verlinkten Projekte
beschreiben ihre Bedingungen.

Grafiken, Musik und Sounds sind separat in `QUELLEN_UND_LIZENZEN.md` dokumentiert.
Modellgewichte und ZIM-Inhalte haben eigene Lizenzen. Die Lizenz des Modell-Backends
oder Wiki-Leseprogramms bestimmt nicht die Lizenz dieser Inhalte.
