# ================================================================
# maatki.py – MAAT-KI Main Entrypoint (AppLoader Edition)
# ================================================================

import os
import sys

# ----------------------------------------
# ROOT GANZ OBEN DEFINIEREN
# ----------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Apps & Shared Pfade eintragen
APPS_DIR = os.path.join(ROOT, "apps")
SHARED_DIR = os.path.join(ROOT, "shared")

for p in [APPS_DIR, SHARED_DIR]:
    if p not in sys.path:
        sys.path.append(p)

# ----------------------------------------
# MAAT-AppLoader verwenden
# ----------------------------------------
from shared.core.app_loader import choose_and_run_app


if __name__ == "__main__":
    # Sucht automatisch alle apps/**/basic.py
    # und zeigt ein Auswahlmenü an
    choose_and_run_app()