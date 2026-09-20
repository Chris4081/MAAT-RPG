#!/usr/bin/env python3
"""Portable entry point. Run with Python 3.11+ and requirements-gui.txt."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent / 'maatos'
sys.path.insert(0, str(ROOT))

if __name__ == '__main__':
    try:
        from gui.desktop import main
    except ModuleNotFoundError as exc:
        print(f'GUI-Abhängigkeit fehlt: {exc.name}\nBitte installieren: {sys.executable} -m pip install -r requirements-gui.txt')
        raise SystemExit(1)
    raise SystemExit(main())
