# -*- coding: utf-8 -*-
"""
MAAT-AppLoader v1.1
-----------------------------------
Findet automatisch alle apps/**/basic.py
und bietet ein Auswahlmenü zum Starten.

Neu:
- [S] Setup: setzt die Modell-Auswahl zurück
  (löscht maatos/data/model_override.txt)
"""

import os
import importlib.util
from colorama import Fore, Style

# ROOT = maatos/
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
APPS_DIR = os.path.join(ROOT, "apps")

# Pfad zum Modell-Override (wird von llm_loader benutzt)
DATA_DIR = os.path.join(ROOT, "data")
MODEL_OVERRIDE_PATH = os.path.join(DATA_DIR, "model_override.txt")


def reset_model_override():
    """
    Löscht die gespeicherte Modell-Auswahl (model_override.txt),
    damit beim nächsten Start eines LLM wieder das Modell-Menü erscheint.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.isfile(MODEL_OVERRIDE_PATH):
        try:
            os.remove(MODEL_OVERRIDE_PATH)
            print(
                Fore.GREEN
                + f"\n✅ Modell-Auswahl zurückgesetzt."
                + Style.RESET_ALL
            )
            print(
                "Beim nächsten Laden eines Modells wirst du wieder nach einem Modell gefragt.\n"
            )
        except Exception as e:
            print(
                Fore.RED
                + f"⚠ Konnte model_override.txt nicht löschen: {e}"
                + Style.RESET_ALL
            )
    else:
        print(
            Fore.YELLOW
            + "\nℹ Es war kein gespeichertes Modell vorhanden (model_override.txt fehlt).\n"
            + Style.RESET_ALL
        )


def discover_apps(apps_dir: str | None = None) -> list[dict]:
    """
    Durchsucht apps/** nach basic.py
    und liefert eine Liste von App-Infos:
    [
      {
        "name": "maat_classic",
        "label": "maat_classic",
        "path": "/.../apps/maat_classic/basic.py",
        "module_name": "apps.maat_classic.basic"
      },
      ...
    ]
    """
    if apps_dir is None:
        apps_dir = APPS_DIR

    apps = []

    for root, dirs, files in os.walk(apps_dir):
        if "basic.py" in files:
            # z.B. root = /.../apps/maat_classic
            rel_root = os.path.relpath(root, ROOT)           # "apps/maat_classic"
            app_name = os.path.basename(root)                # "maat_classic"
            module_name = rel_root.replace(os.sep, ".") + ".basic"
            path = os.path.join(root, "basic.py")

            apps.append({
                "name": app_name,
                "label": app_name.replace("_", " "),
                "path": path,
                "module_name": module_name,
            })

    # Sortiert nach Name, damit Menü stabil bleibt
    return sorted(apps, key=lambda a: a["name"].lower())


def choose_app(apps: list[dict]) -> dict | None:
    """
    Zeigt ein Menü und gibt das gewählte App-Dict zurück.
    Zusätzlich:
    - [S] Setup → Modell-Auswahl zurücksetzen
    """
    if not apps:
        print(Fore.RED + "❌ Keine Apps (basic.py) unter /apps gefunden!" + Style.RESET_ALL)
        return None

    while True:
        print("───────────────────────────────────────────────────────────")
        print("             🌿 Willkommen in MAAT-OS")
        print("                   KI – App wählen")
        print("    Es wird empfohlen, das Terminal individuell anzupassen.")
        print("───────────────────────────────────────────────────────────")
        print("")
        for idx, app in enumerate(apps, 1):
            print(f"[{idx}] {app['label']}")

        print("")
        print("[S] Setup / Modell-Auswahl zurücksetzen")
        print("")

        default_idx = 1

        choice_raw = input(f"Bitte wählen [{default_idx}]: ").strip()
        choice = choice_raw.lower()

        # --- Setup / Reset-Modell ---
        if choice in ("s", "setup"):
            reset_model_override()
            # Danach einfach erneut das Menü anzeigen
            continue

        # --- Leere Eingabe → Default-App ---
        if not choice:
            idx = default_idx - 1
        else:
            try:
                idx = int(choice) - 1
            except ValueError:
                print(Fore.RED + "Bitte eine gültige Zahl eingeben." + Style.RESET_ALL)
                continue

        if 0 <= idx < len(apps):
            chosen = apps[idx]
            print(
                Fore.GREEN
                + f"\n📦 Gewählte App: {chosen['label']} ({chosen['module_name']})\n"
                + Style.RESET_ALL
            )
            return chosen

        print(Fore.RED + "Ungültige Auswahl." + Style.RESET_ALL)


def run_app(app_info: dict):
    """
    Lädt das basic.py Modul der gewählten App dynamisch
    und sucht eine passende Startfunktion:

    - bevorzugt: start_app()
    - sonst: erste Funktion, die mit start_ beginnt (z.B. start_classic)
    """
    module_path = app_info["path"]
    module_name = app_info["module_name"]

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"⚠ Konnte Modul nicht laden: {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # 1) Bevorzugt: start_app()
    start_fn = getattr(module, "start_app", None)
    if callable(start_fn):
        start_fn()
        return

    # 2) Fallback: erste Funktion, die mit "start_" beginnt
    for name in dir(module):
        if name.startswith("start_"):
            cand = getattr(module, name)
            if callable(cand):
                start_fn = cand
                break

    if start_fn is None:
        raise RuntimeError(
            f"⚠ In {module_name} wurde keine Startfunktion gefunden.\n"
            f"Erwarte entweder start_app() oder eine Funktion, die mit 'start_' beginnt."
        )

    start_fn()


def choose_and_run_app():
    """
    Komfortfunktion: Sucht Apps, zeigt Menü, startet gewählte App.
    Wird direkt aus maatki.py aufgerufen.
    """
    apps = discover_apps()
    app = choose_app(apps)
    if app is None:
        raise SystemExit(1)
    run_app(app)