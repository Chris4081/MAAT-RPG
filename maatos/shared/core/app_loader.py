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
from shared.core.rpg_i18n import get_language, set_language

# ROOT = maatos/
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
APPS_DIR = os.path.join(ROOT, "apps")

# Pfad zum Modell-Override (wird von llm_loader benutzt)
DATA_DIR = str(get_data_dir())
MODEL_OVERRIDE_PATH = os.path.join(DATA_DIR, "model_override.txt")
PERF_OVERRIDE_PATH = os.path.join(DATA_DIR, "perf_override.json")

LOADER_TEXT = {
    "de": {
        "lang_title": "Sprache fuer MAAT-OS Loader waehlen",
        "lang_prompt": "Bitte waehlen:",
        "lang_en": "[1] English",
        "lang_de": "[2] German",
        "lang_invalid": "Bitte 1 oder 2 eingeben.",
        "welcome": "🌿 Willkommen in MAAT-OS",
        "subtitle": "KI – App waehlen",
        "terminal_hint": "Es wird empfohlen, das Terminal individuell anzupassen.",
        "setup": "[S] Setup / Modell-Auswahl zuruecksetzen",
        "language": "[L] Language / Sprache",
        "choose": "Bitte waehlen [{default}]: ",
        "invalid_number": "Bitte eine gueltige Zahl eingeben.",
        "invalid_choice": "Ungueltige Auswahl.",
        "chosen_app": "📦 Gewaehlte App: {label} ({module})",
        "no_apps": "❌ Keine Apps (basic.py) unter /apps gefunden!",
        "reset_ok": "\n✅ Start-Auswahl zurueckgesetzt.",
        "reset_next": "Beim naechsten Laden wirst du wieder gefragt nach:",
        "reset_model": "  • Modell",
        "reset_perf": "  • Performance / Kontext\n",
        "deleted": "   geloescht: {path}",
        "reset_none": "\nℹ Es waren keine gespeicherten Start-Einstellungen vorhanden.\n",
        "reset_fail": "⚠ Konnte Datei nicht loeschen: {path}\n{error}",
    },
    "en": {
        "lang_title": "Choose language for the MAAT-OS loader",
        "lang_prompt": "Please choose:",
        "lang_en": "[1] English",
        "lang_de": "[2] German",
        "lang_invalid": "Please enter 1 or 2.",
        "welcome": "🌿 Welcome to MAAT-OS",
        "subtitle": "KI – Choose App",
        "terminal_hint": "It is recommended to customize the terminal to your liking.",
        "setup": "[S] Setup / Reset model selection",
        "language": "[L] Language / Sprache",
        "choose": "Please choose [{default}]: ",
        "invalid_number": "Please enter a valid number.",
        "invalid_choice": "Invalid choice.",
        "chosen_app": "📦 Chosen app: {label} ({module})",
        "no_apps": "❌ No apps (basic.py) found under /apps!",
        "reset_ok": "\n✅ Startup selection reset.",
        "reset_next": "On the next launch you will be asked again for:",
        "reset_model": "  • Model",
        "reset_perf": "  • Performance / context\n",
        "deleted": "   deleted: {path}",
        "reset_none": "\nℹ No saved startup settings were found.\n",
        "reset_fail": "⚠ Could not delete file: {path}\n{error}",
    },
}


def _loader_language() -> str:
    return get_language(tuple(LOADER_TEXT.keys()))


def _lt(key: str, language: str | None = None, **kwargs) -> str:
    lang = language or _loader_language()
    template = LOADER_TEXT.get(lang, LOADER_TEXT["de"]).get(key, LOADER_TEXT["de"].get(key, key))
    return template.format(**kwargs) if kwargs else template


def choose_loader_language() -> str:
    while True:
        print("───────────────────────────────────────────────────────────")
        print("                MAAT-OS Loader Language")
        print("───────────────────────────────────────────────────────────")
        print(_lt("lang_title", language="en"))
        print(_lt("lang_title", language="de"))
        print("")
        print(_lt("lang_prompt", language="en"))
        print("  " + _lt("lang_en", language="en"))
        print("  " + _lt("lang_de", language="en"))
        print("")
        choice = input("> ").strip()
        if choice == "1":
            set_language("en")
            return "en"
        if choice == "2":
            set_language("de")
            return "de"
        print(Fore.RED + _lt("lang_invalid", language="en") + Style.RESET_ALL)

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
                    + _lt("reset_fail", path=path, error=e)
                    + Style.RESET_ALL
                )

    if removed:
        print(Fore.GREEN + _lt("reset_ok") + Style.RESET_ALL)
        print(_lt("reset_next"))
        print(_lt("reset_model"))
        print(_lt("reset_perf"))
        for p in removed:
            print(_lt("deleted", path=p))
        print()
    else:
        print(
            Fore.YELLOW
            + _lt("reset_none")
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
        print(Fore.RED + _lt("no_apps") + Style.RESET_ALL)
        return None

    while True:
        print("───────────────────────────────────────────────────────────")
        print(f"             {_lt('welcome')}")
        print(f"                   {_lt('subtitle')}")
        print(f"    {_lt('terminal_hint')}")
        print("───────────────────────────────────────────────────────────")
        print("")
        for idx, app in enumerate(apps, 1):
            print(f"[{idx}] {app['label']}")

        print("")
        print(_lt("setup"))
        print(_lt("language"))
        print("")

        default_idx = 1

        choice_raw = input(_lt("choose", default=default_idx)).strip()
        choice = choice_raw.lower()

        if choice in ("s", "setup"):
            reset_startup_selection()
            continue
        if choice in ("l", "lang", "language", "sprache"):
            choose_loader_language()
            continue

        if not choice:
            idx = default_idx - 1
        else:
            try:
                idx = int(choice) - 1
            except ValueError:
                print(Fore.RED + _lt("invalid_number") + Style.RESET_ALL)
                continue

        if 0 <= idx < len(apps):
            chosen = apps[idx]
            print(
                Fore.GREEN
                + "\n" + _lt("chosen_app", label=chosen["label"], module=chosen["module_name"]) + "\n"
                + Style.RESET_ALL
            )
            return chosen

        print(Fore.RED + _lt("invalid_choice") + Style.RESET_ALL)


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
    choose_loader_language()
    apps = discover_apps()
    app = choose_app(apps)
    if app is None:
        raise SystemExit(1)
    run_app(app)
