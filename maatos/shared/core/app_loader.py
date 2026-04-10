# -*- coding: utf-8 -*-
"""
MAAT-AppLoader v1.1
-----------------------------------
Findet automatisch alle apps/**/basic.py
und bietet ein Auswahlmenü zum Starten.

Neu:
- [S] Setup: setzt die Modell-Auswahl zurück
  (löscht model_override.txt im zentralen data-Ordner)
"""

import os
import importlib.util
from colorama import Fore, Style
from shared.core.maat_paths import get_data_dir

# ROOT = maatos/
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
APPS_DIR = os.path.join(ROOT, "apps")

# Pfad zum Modell-Override (wird von llm_loader benutzt)
DATA_DIR = str(get_data_dir())
MODEL_OVERRIDE_PATH = os.path.join(DATA_DIR, "model_override.txt")
PERF_OVERRIDE_PATH = os.path.join(DATA_DIR, "perf_override.json")

def reset_startup_selection():
    """
    Löscht:
    - model_override.txt
    - perf_override.json

    Dadurch wird beim nächsten Start wieder
    Modell + Performance neu abgefragt.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    removed = []

    for path in [MODEL_OVERRIDE_PATH, PERF_OVERRIDE_PATH]:
        if os.path.isfile(path):
            try:
                os.remove(path)
                removed.append(path)
            except Exception as e:
                print(
                    Fore.RED
                    + f"⚠ Konnte Datei nicht löschen: {path}\n{e}"
                    + Style.RESET_ALL
                )

    if removed:
        print(Fore.GREEN + "\n✅ Start-Auswahl zurückgesetzt." + Style.RESET_ALL)
        print("Beim nächsten Laden wirst du wieder gefragt nach:")
        print("  • Modell")
        print("  • Performance / Kontext\n")
        for p in removed:
            print(f"   gelöscht: {p}")
        print()
    else:
        print(
            Fore.YELLOW
            + "\nℹ Es waren keine gespeicherten Start-Einstellungen vorhanden.\n"
            + Style.RESET_ALL
        )

def discover_apps(apps_dir: str | None = None) -> list[dict]:
    """
    Durchsucht apps/** nach basic.py
    und liefert eine Liste von App-Infos.
    """
    if apps_dir is None:
        apps_dir = APPS_DIR

    apps = []

    for root, dirs, files in os.walk(apps_dir):
        if "basic.py" in files:
            rel_root = os.path.relpath(root, ROOT)
            app_name = os.path.basename(root)
            module_name = rel_root.replace(os.sep, ".") + ".basic"
            path = os.path.join(root, "basic.py")

            apps.append({
                "name": app_name,
                "label": app_name.replace("_", " "),
                "path": path,
                "module_name": module_name,
            })

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

        if choice in ("s", "setup"):
            reset_startup_selection()
            continue

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
    und sucht eine passende Startfunktion.
    """
    module_path = app_info["path"]
    module_name = app_info["module_name"]

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"⚠ Konnte Modul nicht laden: {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    start_fn = getattr(module, "start_app", None)
    if callable(start_fn):
        start_fn()
        return

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