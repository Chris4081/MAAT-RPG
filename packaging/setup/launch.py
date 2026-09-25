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


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if platform.system() == 'Linux':
        return linux_launcher.main(args)
    if platform.system() != 'Darwin':
        print('This launcher supports macOS/Linux only.', file=sys.stderr)
        return 1
    env = linux_launcher.runtime_environment()
    if '--check' in args:
        env['QT_QPA_PLATFORM'] = 'offscreen'
        check = linux_launcher.QT_CHECK + '\nimport llama_cpp; print("GGUF", llama_cpp.__version__)\n'
        try:
            result = subprocess.run([sys.executable, '-c', check], env=env, timeout=30)
            return result.returncode if result.returncode >= 0 else 128-result.returncode
        except subprocess.TimeoutExpired:
            print('Startprüfung hängt / Startup check timed out.', file=sys.stderr)
            return 1
    os.chdir(game_root())
    os.execve(sys.executable, [sys.executable, '-m', 'gui.desktop', *args], env)


if __name__ == '__main__':
    raise SystemExit(main())
