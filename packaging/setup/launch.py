#!/usr/bin/env python3
"""Launch with the selected interpreter, independently of source folder layout."""
from __future__ import annotations
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'packaging/linux'))
import launcher as linux_launcher
from setup_linux import game_root


def check_macos(env, qt_platform='cocoa'):
    """Repair visibility and probe Qt in a child before risking the game process."""
    check_env = dict(env, QT_QPA_PLATFORM=qt_platform)
    # Use the very same game module as desktop.py, even in the app-bundle layout.
    # Qt must discover the plugins only after their hidden flags are corrected.
    check = (
        'import sys\n'
        f'sys.path.insert(0, {str(game_root())!r})\n'
        'from gui.qt_runtime import prepare_qt_plugins\n'
        'prepare_qt_plugins()\n'
        + linux_launcher.QT_CHECK
        + '\nimport llama_cpp; print("GGUF", llama_cpp.__version__)\n'
    )
    try:
        result = subprocess.run([sys.executable, '-c', check], env=check_env,
                                capture_output=True, text=True, errors='replace', timeout=25)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f'Startprüfung fehlgeschlagen / Startup check failed: {exc}', file=sys.stderr)
        return False
    if result.returncode:
        print(result.stdout + result.stderr, file=sys.stderr, end='')
        print('MAAT kann die Oberfläche nicht starten / MAAT cannot start its interface.\n'
              'Bitte die Qt-Meldung oben prüfen / Check the Qt message above.\n'
              'Bei fehlenden/beschädigten Dateien: Install.command erneut ausführen.\n'
              'For missing/damaged files: run Install.command again.', file=sys.stderr)
        return False
    print(result.stdout, end='', flush=True)
    return True


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if platform.system() == 'Linux':
        return linux_launcher.main(args)
    if platform.system() != 'Darwin':
        print('This launcher supports macOS/Linux only.', file=sys.stderr)
        return 1
    env = linux_launcher.runtime_environment()
    # An offscreen success does not demonstrate that macOS windows can start.
    if '--check' in args or '--check-offscreen' in args:
        mode = 'cocoa' if '--check' in args else 'offscreen'
        return 0 if check_macos(env, mode) else 1
    if not check_macos(env, env.get('QT_QPA_PLATFORM') or 'cocoa'):
        return 1
    os.chdir(game_root())
    os.execve(sys.executable, [sys.executable, '-m', 'gui.desktop', *args], env)


if __name__ == '__main__':
    raise SystemExit(main())
