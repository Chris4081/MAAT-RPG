#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import traceback

# -----------------------------------------------------
# 1) Projekt-Root automatisch erkennen
# -----------------------------------------------------
CURRENT = os.path.dirname(os.path.abspath(__file__))          # /tools
ROOT = os.path.dirname(CURRENT)                               # /maatos

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

print("📁 Projekt-Root erkannt:", ROOT)

# -----------------------------------------------------
# 2) PluginManager importieren
# -----------------------------------------------------
try:
    from shared.plugins.plugin_loader import PluginManager
except Exception as e:
    print("❌ FEHLER: Konnte PluginManager nicht importieren.")
    print("Grund:", e)
    print("\nPYTHONPATH:", sys.path)
    sys.exit(1)

# -----------------------------------------------------
# 3) Plugin-Pfade sammeln
# -----------------------------------------------------
APP_PLUGINS = os.path.join(ROOT, "apps", "maat_classic", "plugins")
SHARED_PLUGINS = os.path.join(ROOT, "shared", "plugins")

print("\n🔍 Scanne Plugin-Pfade:")
print("   • App:    ", APP_PLUGINS)
print("   • Shared: ", SHARED_PLUGINS)

# -----------------------------------------------------
# 4) PluginManager initialisieren
# -----------------------------------------------------
try:
    pm = PluginManager([APP_PLUGINS, SHARED_PLUGINS])
    pm.load_plugins()
except Exception:
    print("❌ Fehler beim Laden der Plugins:\n")
    traceback.print_exc()
    sys.exit(1)

print("\n✨ Plugins wurden erfolgreich geladen.\n")

# -----------------------------------------------------
# 5) Plugins testen
# -----------------------------------------------------
print("🔬 Plugin-Kompatibilitätstest läuft…\n")

for p in pm.iter_all_plugins():
    name = p.__class__.__name__
    print(f"   • Teste Plugin: {name}")

    # command()
    if hasattr(p, "command"):
        try:
            result = p.command("/test", context={"test": True})
        except TypeError:
            print(f"     ❌ Falsche Signatur für command()")
        except Exception as e:
            print(f"     ⚠ Fehler in command(): {e}")
        else:
            print(f"     ✔ command() OK")

    # before_chat()
    if hasattr(p, "before_chat"):
        try:
            p.before_chat("test", {})
        except Exception as e:
            print(f"     ⚠ Fehler in before_chat(): {e}")
        else:
            print(f"     ✔ before_chat() OK")

    # after_response()
    if hasattr(p, "after_response"):
        try:
            p.after_response("Antwort", {})
        except Exception as e:
            print(f"     ⚠ Fehler in after_response(): {e}")
        else:
            print(f"     ✔ after_response() OK")

print("\n🌿 Plugin-Scan abgeschlossen.\n")