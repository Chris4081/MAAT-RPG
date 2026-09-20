# -*- coding: utf-8 -*-
"""
MAAT PluginValidator v1.0
-------------------------
Prüft, ob alle Plugins kompatibel mit PluginManager v2.3 sind.
Farbige Ausgabe + genaue Fehlerstellen.
"""

import os
import importlib.util
import inspect
from colorama import Fore, Style

REQUIRED_METHODS = {
    "command": (2, 3),           # (self, cmd) oder (self, cmd, context)
    "before_chat": (2, 3),       # (self, input) oder (self, input, context)
    "after_response": (2, 3),    # (self, reply) oder (self, reply, context)
}

def load_plugin(path):
    """
    Plugin isoliert laden (ohne PluginManager).
    """
    try:
        module_name = "validator_" + os.path.basename(path).replace(".py", "")
        spec = importlib.util.spec_from_file_location(module_name, path)
        if not spec or not spec.loader:
            return None, "spec loader missing"

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        Plugin = getattr(module, "Plugin", None)
        if Plugin is None or not inspect.isclass(Plugin):
            return None, "no Plugin class found"

        return Plugin(), None

    except Exception as e:
        return None, str(e)


def validate_plugin(instance, file_path):
    """
    Prüft eine Plugin-Instanz.
    Gibt Liste von Meldungen zurück.
    """
    results = []

    # 1) type prüfen
    ptype = getattr(instance, "type", None)
    if ptype not in ("chat", "stream"):
        results.append(f"{Fore.RED}✖ Ungültiger type: {ptype}{Style.RESET_ALL}")
    else:
        results.append(f"{Fore.GREEN}✔ type = {ptype}{Style.RESET_ALL}")

    # 2) Methoden testen
    for name, valid_args in REQUIRED_METHODS.items():
        method = getattr(instance, name, None)
        if not callable(method):
            results.append(f"{Fore.YELLOW}⚠ {name}() fehlt (optional){Style.RESET_ALL}")
            continue

        argc = len(inspect.signature(method).parameters)

        if argc in valid_args:
            results.append(f"{Fore.GREEN}✔ {name}(): OK ({argc} Argumente){Style.RESET_ALL}")
        else:
            results.append(
                f"{Fore.RED}✖ {name}(): falsche Signatur ({argc} Argumente, erwartet {valid_args}){Style.RESET_ALL}"
            )

    # 3) Startup-Hook
    if callable(getattr(instance, "on_startup", None)):
        results.append(f"{Fore.GREEN}✔ on_startup(): vorhanden{Style.RESET_ALL}")
    else:
        results.append(f"{Fore.YELLOW}⚠ on_startup() fehlt (optional){Style.RESET_ALL}")

    return results


def scan_plugins(plugin_dirs):
    """
    plugin_dirs: Liste von Ordnern (shared + app)
    """
    print(Fore.CYAN + "🔍 MAAT PluginValidator — Starte Scan...\n" + Style.RESET_ALL)

    for root in plugin_dirs:
        print(Fore.MAGENTA + f"📁 Ordner: {root}" + Style.RESET_ALL)

        if not os.path.isdir(root):
            print(Fore.RED + "   ✖ Ordner existiert nicht.\n")
            continue

        for entry in sorted(os.listdir(root)):
            path = os.path.join(root, entry)

            # Ordner mit plugin_main.py
            if os.path.isdir(path):
                plugin_file = os.path.join(path, "plugin_main.py")
                if os.path.isfile(plugin_file):
                    print(Fore.YELLOW + f"   → Prüfe {entry}/plugin_main.py" + Style.RESET_ALL)
                    instance, err = load_plugin(plugin_file)
                    if err:
                        print(Fore.RED + f"     ✖ Fehler: {err}{Style.RESET_ALL}")
                        continue

                    for line in validate_plugin(instance, plugin_file):
                        print("     " + line)
                    print()

            # plugin_*.py Dateien
            elif entry.startswith("plugin_") and entry.endswith(".py"):
                print(Fore.YELLOW + f"   → Prüfe Datei: {entry}" + Style.RESET_ALL)
                instance, err = load_plugin(path)
                if err:
                    print(Fore.RED + f"     ✖ Fehler: {err}{Style.RESET_ALL}")
                    continue

                for line in validate_plugin(instance, path):
                    print("     " + line)
                print()

    print(Fore.CYAN + "✨ Scan abgeschlossen.\n" + Style.RESET_ALL)