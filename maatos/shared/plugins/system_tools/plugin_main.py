# -*- coding: utf-8 -*-
"""
MAAT-SystemControl v3.3
-----------------------------------
Wartungs- & Systembefehle für MAAT-KI:

/model             – interaktiver Modell-Selector (manuelle Auswahl)
/model list        – alle Modelle anzeigen
/model set <name>  – Wunschmodell (für nächsten Start) setzen
/restart           – Hard-Restart (Software neu starten)
/safe-restart      – Speichern + Neustart
/profile reload    – Profile neu laden
/plugins reload    – Plugins neu laden
/sysinfo           – Systemdiagnose
/meminfo           – RAM/VRAM Verbrauch
/update            – git pull + Restart
"""

import os
import sys
import subprocess
import platform
from datetime import datetime

from shared.core.maat_paths import get_models_dir, get_data_dir, get_logs_dir
print("✅ system_tools plugin_main.py importiert")
# Nur Model-Liste aus llm_loader holen
try:
    from shared.core.llm_loader import list_available_models
except Exception:
    list_available_models = None


class Plugin:
    type = "chat"

    commands = {
        "/model": {"de": "Modellverwaltung und Modell-Auswahl.", "en": "Model management and model selection."},
        "/restart": {"de": "Startet die Software neu.", "en": "Restarts the software."},
        "/safe-restart": {"de": "Speichern und neu starten.", "en": "Save and restart."},
        "/profile": {"de": "Profil-Befehle.", "en": "Profile commands."},
        "/plugins": {"de": "Plugin-Management.", "en": "Plugin management."},
        "/sysinfo": {"de": "Systemdiagnose.", "en": "System diagnostics."},
        "/meminfo": {"de": "RAM-/VRAM-Verbrauch.", "en": "RAM/VRAM usage."},
        "/update": {"de": "git pull und Neustart.", "en": "git pull and restart."}
    }

    def __init__(self):
        print("✅ system_tools Plugin initialisiert")
        # root_dir nur noch für git pull / Projektlesepfade
        self.root_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )

        # zentrale Schreib-/Nutzpfade
        self.models_dir = str(get_models_dir())
        self.data_dir = str(get_data_dir())
        self.logs_dir = str(get_logs_dir())

        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)

        self.model_override_path = os.path.join(self.data_dir, "model_override.txt")

    # ----------------------------------------------------------
    # Zentrale Command-Routine
    # ----------------------------------------------------------
    def command(self, cmd, context=None):
        parts = (cmd or "").split()
        if not parts:
            return None

        base = parts[0].lower()

        if base == "/model":
            return self._handle_model(parts)

        if base == "/restart":
            self._restart()
            return "🔄 Neustart wird ausgeführt …"

        if base == "/safe-restart":
            return self._safe_restart()

        if base == "/profile":
            return self._handle_profiles(parts, context)

        if base == "/plugins":
            return self._handle_plugins(parts, context)

        if base == "/sysinfo":
            return self._sysinfo()

        if base == "/meminfo":
            return self._meminfo()

        if base == "/update":
            return self._update()

        return None

    # ----------------------------------------------------------
    # MODEL COMMANDS
    # ----------------------------------------------------------
    def _handle_model(self, parts):
        if len(parts) == 1:
            if list_available_models is None:
                return "❌ list_available_models konnte nicht importiert werden."

            models = list_available_models(self.models_dir)
            if not models:
                return f"❌ Keine .gguf-Modelle im Ordner: {self.models_dir}"

            print("──────────────────────────────────────────────")
            print("🌿 MAAT-KI — Modell auswählen (/model)")
            print("──────────────────────────────────────────────")
            print(f"(Suche in: {self.models_dir})")

            for i, m in enumerate(models, 1):
                print(f"[{i}] {m}")

            while True:
                choice = input("\n🔢 Modell wählen: ").strip()
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(models):
                        chosen = models[idx]
                        full_path = os.path.join(self.models_dir, chosen)

                        print(f"\n📦 Gewähltes Modell: {chosen}\n")

                        try:
                            with open(self.model_override_path, "w", encoding="utf-8") as f:
                                f.write(chosen)
                        except Exception as e:
                            return f"❌ Konnte model_override.txt nicht schreiben: {e}"

                        return (
                            "✅ Modell-Selector abgeschlossen. Gewählt wurde:\n"
                            f"   • {full_path}\n\n"
                            f"Die Auswahl wurde als Wunschmodell gespeichert ({chosen}).\n"
                            f"Bitte führe /restart aus, damit MAAT-KI mit diesem Modell neu startet."
                        )
                except ValueError:
                    pass

                print("⚠ Bitte eine gültige Zahl eingeben.")

        if len(parts) >= 2 and parts[1].lower() == "list":
            if not os.path.isdir(self.models_dir):
                return f"❌ models/ Ordner nicht gefunden: {self.models_dir}"

            models = list_available_models(self.models_dir) if list_available_models else None
            if not models:
                return "📂 Keine Modelle im models/ Ordner gefunden."

            out = ["📚 Verfügbare Modelle:"]
            for e in models:
                out.append(f"  • {e}")
            return "\n".join(out)

        if len(parts) >= 2 and parts[1].lower() == "set":
            if len(parts) < 3:
                return "Nutze: /model set <dateiname_aus_models_ordner>"

            name = parts[2].strip()
            candidate = os.path.join(self.models_dir, name)

            if not os.path.exists(candidate):
                return (
                    f"❌ Modell-Datei '{name}' nicht in {self.models_dir} gefunden.\n"
                    "Nutze zuerst /model list, um alle verfügbaren Modelle zu sehen."
                )

            try:
                with open(self.model_override_path, "w", encoding="utf-8") as f:
                    f.write(name)
                return (
                    f"✅ Wunschmodell **{name}** gespeichert.\n"
                    "Bitte führe /restart aus, damit es beim nächsten Start geladen wird."
                )
            except Exception as e:
                return f"❌ Konnte model_override.txt nicht schreiben: {e}"

        return (
            "📘 Modellverwaltung:\n"
            "  • /model                 – Interaktiver Modell-Selector\n"
            "  • /model list            – Zeigt verfügbare Modelle\n"
            "  • /model set <name>      – Wunschmodell direkt setzen\n"
        )

    # ----------------------------------------------------------
    # RESTART
    # ----------------------------------------------------------
    def _restart(self):
        print("🔄 MAAT-KI wird neu gestartet…")
        python = sys.executable
        os.execv(python, [python] + sys.argv)

    def _safe_restart(self):
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            logpath = os.path.join(self.logs_dir, f"safe_restart_{ts}.log")
            with open(logpath, "w", encoding="utf-8") as f:
                f.write("Safe-Restart at " + str(datetime.now()))
        except Exception:
            pass

        self._restart()
        return "🔒 Safe-Restart wird ausgeführt…"

    # ----------------------------------------------------------
    # PROFILE
    # ----------------------------------------------------------
    def _handle_profiles(self, parts, context):
        if len(parts) == 1:
            return "📂 Profilbefehle: /profile reload"

        sub = parts[1].lower()

        if sub == "reload":
            if not context or not isinstance(context, dict):
                return "❌ Kein Kontext für Profile verfügbar."

            loader = context.get("profile_loader")
            if loader is None:
                return "❌ Kein ProfileLoader im Kontext gefunden."

            if hasattr(loader, "reload_profiles"):
                try:
                    loader.reload_profiles()
                    return "📂 Profile neu geladen."
                except Exception as e:
                    return f"❌ Fehler beim Neu-Laden der Profile: {e}"
            else:
                return "ℹ ProfileLoader unterstützt kein Reload. Bitte MAAT-KI neu starten."

        return "❓ Unbekannter Profilbefehl. Nutze: /profile reload"

    # ----------------------------------------------------------
    # PLUGINS
    # ----------------------------------------------------------
    def _handle_plugins(self, parts, context):
        if len(parts) == 1:
            return "🔌 Pluginbefehle: /plugins reload"

        sub = parts[1].lower()

        if sub == "reload":
            if not context or not isinstance(context, dict):
                return "❌ Kein Kontext für Plugins verfügbar."

            pm = context.get("pm")
            if pm is None:
                return "❌ Kein PluginManager im Kontext."

            try:
                pm.load_plugins()
                return "🔌 Plugins neu geladen."
            except Exception as e:
                return f"❌ Plugin-Reload Fehler: {e}"

        return "❓ Unbekannter Plugins-Befehl. Nutze: /plugins reload"

    # ----------------------------------------------------------
    # SYSTEM INFO
    # ----------------------------------------------------------
    def _sysinfo(self):
        try:
            import psutil
            cpu_cores = psutil.cpu_count(logical=True)
        except Exception:
            cpu_cores = "unbekannt (psutil fehlt?)"

        return (
            "🖥️ **Systeminfo**\n"
            f"• OS: {platform.system()} {platform.release()}\n"
            f"• Python: {platform.python_version()}\n"
            f"• CPU: {platform.processor() or 'unbekannt'}\n"
            f"• Kerne (logisch): {cpu_cores}\n"
            f"• Zeitpunkt: {datetime.now()}\n"
        )

    # ----------------------------------------------------------
    # MEMORY INFO
    # ----------------------------------------------------------
    def _meminfo(self):
        ram_text = "RAM-Info nicht verfügbar (psutil nicht installiert?)"
        gpu_text = ""

        try:
            import psutil
            mem = psutil.virtual_memory()
            used = mem.used / (1024 ** 3)
            total = mem.total / (1024 ** 3)
            ram_text = f"RAM: {used:.2f} / {total:.2f} GB"
        except Exception:
            pass

        try:
            import torch
            if torch.cuda.is_available():
                gpu_mem = torch.cuda.memory_allocated() / (1024 ** 3)
                gpu_total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
                gpu_text = f"\n• VRAM: {gpu_mem:.2f} / {gpu_total:.2f} GB"
        except Exception:
            pass

        return (
            "🧠 **Speicherverbrauch**\n"
            f"• {ram_text}"
            f"{gpu_text}"
        )

    # ----------------------------------------------------------
    # UPDATE (git pull + restart)
    # ----------------------------------------------------------
    def _update(self):
        try:
            out = subprocess.check_output(
                ["git", "pull"],
                stderr=subprocess.STDOUT,
                cwd=self.root_dir
            )
            text = out.decode("utf-8", errors="ignore")
            self._restart()
            return "⬇️ Update ausgeführt:\n" + text
        except Exception as e:
            return f"❌ Update-Fehler: {e}"
