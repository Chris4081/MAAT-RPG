"""Keep macOS Qt plugin discovery working with hidden installation files."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import stat
import sys


def _plugin_roots():
    # Locate the active Python package without loading Qt itself.
    spec = importlib.util.find_spec('PySide6')
    for location in (spec.submodule_search_locations or ()) if spec else ():
        root = Path(location) / 'Qt' / 'plugins'
        if root.is_dir() and not root.is_symlink():
            yield root


def prepare_qt_plugins() -> int:
    """Remove only UF_HIDDEN inside the active PySide6 Qt/plugins directory.

    Qt's plugin scanner skips hidden files. Some macOS installations mark plugin
    directories and dylibs hidden even though Python can read and load them.
    Run before QApplication in each process: the flag can reappear between runs.
    The enclosing .venv, file contents, other flags, signatures and extended
    attributes (including quarantine/provenance) are left intact.
    """
    if sys.platform != 'darwin' or not hasattr(os, 'chflags'):
        return 0
    changed = 0
    for root in _plugin_roots():
        for folder, directories, files in os.walk(root, followlinks=False):
            directories[:] = [name for name in directories
                              if not name.startswith('.') and not (Path(folder) / name).is_symlink()]
            paths = [Path(folder)] + [Path(folder) / name for name in files
                                     if not name.startswith('.') and name.endswith('.dylib')]
            for path in paths:
                try:
                    info = path.lstat()
                    if stat.S_ISLNK(info.st_mode) or not info.st_flags & stat.UF_HIDDEN:
                        continue
                    os.chflags(path, info.st_flags & ~stat.UF_HIDDEN, follow_symlinks=False)
                    changed += 1
                except FileNotFoundError:
                    continue  # A concurrent package update may remove a plugin.
                except OSError as exc:
                    raise RuntimeError(
                        'Qt-Plugin bleibt versteckt / Qt plugin cannot be made visible: '
                        f'{path}. Bitte die Python-Umgebung prüfen / Check the Python environment.'
                    ) from exc
    return changed
