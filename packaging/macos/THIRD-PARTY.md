# Bundled runtime components / Mitgelieferte Bibliotheken

MAAT-RPG's source and license are included in this app. The runtime remains
dynamically linked and is located in `Contents/Resources/runtimes`; it can be
inspected and replaced for development. Existing package license files and
distribution metadata are retained. Where upstream wheels lack full license
texts, a supplement is included under `Documentation/licenses/`.

- Python 3.11, PSF license and bundled dependency notices:
  https://www.python.org/ and https://github.com/astral-sh/python-build-standalone
- PySide6 / Qt 6.8.3, LGPL/GPL and other licenses per bundled module:
  https://www.qt.io/licensing/open-source-lgpl-obligations
  Source: https://download.qt.io/archive/qt/6.8/6.8.3/
- FFmpeg libraries included with Qt Multimedia, LGPL-2.1-or-later plus applicable
  component notices: https://ffmpeg.org/legal.html
  The inspected binaries contain build configurations referencing `FFmpeg-n7.1`.
  Exact corresponding source, patches and build recipes remain to be verified;
  this is not a claim that current Qt documentation matches these binaries.
- llama-cpp-python 0.3.34 and llama.cpp, MIT:
  https://github.com/abetlen/llama-cpp-python and https://github.com/ggml-org/llama.cpp
- Python libzim 3.10.0: GPL-3.0-or-later; native libzim upstream: GPL-2.0-or-later.
  The ARM version API reports native libzim 9.7.0; the Intel probe was not executable
  on the inspection host. This does not yet identify exact corresponding sources.
  https://github.com/openzim/python-libzim and https://github.com/openzim/libzim
- NumPy, BSD; PyYAML, MIT; Requests, Apache-2.0; Colorama, BSD;
  Jinja2/MarkupSafe, BSD; DiskCache, Apache-2.0; typing_extensions, PSF;
  urllib3, MIT; certifi, MPL-2.0; charset-normalizer, MIT; idna, BSD.

The Python package version does not by itself identify the native libzim source
revision. Python, NumPy and other packages can contain additional bundled components;
their original notices also apply. The project does not own these third-party works.

**Audit status:** Standard license texts are included, but exact corresponding
sources, required build/installation information and all component-specific notices
are not yet fully verified. The source URLs above are upstream references, not a
complete source bundle or a written source offer. This applies to test distributions
too; describing a package as private does not waive license obligations.

Full LGPLv3 and its incorporated GPLv3 text are supplied in `licenses/`, along with
GPLv2, LGPLv2.1 and existing Python/llama notices. No commercial Qt license is claimed.
Users' rights to modify/replace LGPL libraries, including reverse engineering needed
to debug those modifications, must not be restricted by project terms.

No GGUF model weights or Wikipedia archive is included. The libzim software license
still applies independently of user-supplied archive content. See `WIKI_HINWEISE.md`.

The bilingual `SOFTWARE_LICENSES.md` in this documentation folder describes the
software components in more detail, including bundled Qt add-ons and native wiki dependencies.

## Deutsch

Das Paket verwendet freie Bibliotheken mit eigenen Lizenzbedingungen, unter anderem
Qt/PySide/Shiboken, FFmpeg, Python, llama.cpp und libzim. Vorhandene Lizenzdateien bleiben
erhalten; zusätzliche vollständige Standardtexte liegen unter `licenses/`.
Die genauen Bibliotheksquellen, erforderlichen Build-/Installationsinformationen und
sämtliche speziellen Drittanbieterhinweise sind noch nicht vollständig geprüft.
Die obigen Links sind keine vollständige Quellcodebereitstellung und kein schriftliches
Quellcodeangebot. Auch Testweitergaben müssen die einschlägigen Bedingungen einhalten.
Das Recht, LGPL-Bibliotheken zu ändern/ersetzen und dafür erforderliches Reverse
Engineering durchzuführen, wird durch die Projekthinweise nicht eingeschränkt.
Modelle und ZIM-Inhalte sind nicht enthalten; die mitgelieferte libzim-Bibliothek
hat trotzdem eigene GPL-Pflichten. Siehe auch `WIKI_HINWEISE.md`.
