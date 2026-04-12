# shared/plugins/plugin_loader.py
# -*- coding: utf-8 -*-

import os
import json
import importlib.util
import inspect
from shared.core.rpg_i18n import get_language


def _lang():
    return get_language(("de", "en"))


def _t(de: str, en: str) -> str:
    return en if _lang() == "en" else de


class PluginManager:
    def __init__(self, plugin_roots, config_path=None):
        if isinstance(plugin_roots, str):
            self.plugin_roots = [plugin_roots]
        else:
            self.plugin_roots = list(plugin_roots)

        self.config_path = config_path
        self.plugin_settings = self._load_plugin_settings(config_path)
        self.plugins_chat = []
        self.plugins_stream = []
        self.skipped_plugins = []
        self.loaded_plugin_ids = set()

    def _load_plugin_settings(self, config_path):
        if not config_path or not os.path.isfile(config_path):
            return {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            plugins = data.get("plugins", {})
            return plugins if isinstance(plugins, dict) else {}
        except Exception as e:
            print(_t(f"⚠ Plugin-Konfiguration konnte nicht geladen werden: {e}", f"⚠ Plugin configuration could not be loaded: {e}"))
            return {}

    def _plugin_id_for_path(self, file_path):
        base = os.path.basename(file_path)
        if base == "plugin_main.py":
            return os.path.basename(os.path.dirname(file_path))
        return os.path.splitext(base)[0]

    def _is_enabled(self, plugin_id):
        raw = self.plugin_settings.get(plugin_id, True)
        if isinstance(raw, dict):
            return raw.get("enabled", True)
        return bool(raw)

    # ---------------------------------------------------------
    # LOAD
    # ---------------------------------------------------------
    def load_plugins(self):
        print(_t("🔍 Lade Plugins …", "🔍 Loading plugins …"))

        self.plugins_chat.clear()
        self.plugins_stream.clear()
        self.skipped_plugins.clear()
        self.loaded_plugin_ids.clear()

        for root in self.plugin_roots:
            if not os.path.isdir(root):
                continue

            for entry in sorted(os.listdir(root)):
                if entry.startswith("_"):
                    continue

                path = os.path.join(root, entry)

                # Ordner mit plugin_main.py
                if os.path.isdir(path):
                    candidate = os.path.join(path, "plugin_main.py")
                    if os.path.isfile(candidate):
                        self._load_single(candidate)

                # Direkt plugin_*.py
                elif entry.startswith("plugin_") and entry.endswith(".py"):
                    candidate = path
                    self._load_single(candidate)

        self._print_plugin_summary()

    def _load_single(self, file_path):
        try:
            plugin_id = self._plugin_id_for_path(file_path)
            if plugin_id in self.loaded_plugin_ids:
                print(_t(f"⏭ Doppeltes Plugin übersprungen: {plugin_id}", f"⏭ Duplicate plugin skipped: {plugin_id}"))
                return
            if not self._is_enabled(plugin_id):
                self.skipped_plugins.append(plugin_id)
                print(_t(f"⏭ Plugin deaktiviert: {plugin_id}", f"⏭ Plugin disabled: {plugin_id}"))
                return

            mod_name = "maat_plugin_" + os.path.basename(file_path).replace(".py", "")
            spec = importlib.util.spec_from_file_location(mod_name, file_path)
            if not spec or not spec.loader:
                print(_t(f"⚠ Konnte Modul nicht laden: {file_path}", f"⚠ Could not load module: {file_path}"))
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            PluginClass = getattr(module, "Plugin", None)
            if PluginClass is None or not inspect.isclass(PluginClass):
                return

            inst = PluginClass()
            setattr(inst, "plugin_id", plugin_id)
            ptype = getattr(inst, "type", "chat")

            if ptype == "stream":
                self.plugins_stream.append(inst)
            else:
                self.plugins_chat.append(inst)
            self.loaded_plugin_ids.add(plugin_id)

        except Exception as e:
            print(_t(f"⚠ Plugin-Ladefehler in {file_path}: {e}", f"⚠ Plugin load error in {file_path}: {e}"))

    # ---------------------------------------------------------
    # INFO
    # ---------------------------------------------------------
    def _print_plugin_summary(self):
        print(_t("\n📦 Plugin-Übersicht:", "\n📦 Plugin overview:"))
        print(_t(f"   • Chat-Plugins:     {len(self.plugins_chat)}", f"   • Chat plugins:     {len(self.plugins_chat)}"))
        print(_t(f"   • Streaming-Plugins:{len(self.plugins_stream)}\n", f"   • Streaming plugins:{len(self.plugins_stream)}\n"))
        if self.skipped_plugins:
            print(_t(f"   • Deaktiviert:      {', '.join(sorted(self.skipped_plugins))}\n", f"   • Disabled:         {', '.join(sorted(self.skipped_plugins))}\n"))

    def print_plugin_summary(self):
        self._print_plugin_summary()

    def iter_all_plugins(self):
        return list(self.plugins_chat) + list(self.plugins_stream)

    def get_streaming_plugins(self):
        return list(self.plugins_stream)

    def has_before_final_response(self, context=None):
        for plugin in self.iter_all_plugins():
            final_fn = getattr(plugin, "before_final_response", None)
            if not callable(final_fn):
                continue
            enabled_fn = getattr(plugin, "final_response_guard_enabled", None)
            if callable(enabled_fn):
                try:
                    if not enabled_fn(context):
                        continue
                except TypeError:
                    if not enabled_fn():
                        continue
            return True
        return False

    # ---------------------------------------------------------
    # BEFORE
    # ---------------------------------------------------------
    def handle_before_chat(self, user_input: str, context=None):
        context = context or {}
        current = user_input

        # BEFORE HOOKS (Plugin Processing)
        for plugin in self.plugins_chat:
            before_fn = getattr(plugin, "before_chat", None)
            if callable(before_fn):
                try:
                    result = before_fn(current, context)
                except TypeError:
                    result = before_fn(current)

                if isinstance(result, tuple) and len(result) == 2:
                    h, out = result
                    if h:
                        return True, out or current
                    # wenn nicht handled: current ggf. ersetzen
                    if out is not None:
                        current = out

                elif isinstance(result, str):
                    # falls ein Plugin nur Text zurückgibt
                    current = result

        return False, current

    # ---------------------------------------------------------
    # AUTO-COMMAND REGISTRATION FOR PLUGINS
    # ---------------------------------------------------------
    def register_plugin_commands(self, router):
        """
        Registriert Commands aus ALLEN Plugins:
        1) plugin.commands = { "/cmd": "desc" }
        2) plugin.available_commands = [...]
        3) plugin.command(cmd, context) fallback
        """

        def make_handler(plugin, base_cmd):
            """
            Baut einen Handler, der:
            - aus base_cmd + args den vollen Befehl macht (z.B. "/say on")
            - einen einfachen context mit pm übergibt
            """
            def handler(args):
                # vollen Befehl rekonstruieren
                if args:
                    full_cmd = base_cmd + " " + " ".join(args)
                else:
                    full_cmd = base_cmd

                context = {"pm": self}
                # Versuche neue Signatur (cmd, context)
                try:
                    return plugin.command(full_cmd, context)
                except TypeError:
                    # Fallback für alte Plugins (nur cmd)
                    return plugin.command(full_cmd)
            return handler

        # 🔥 Chat- UND Stream-Plugins einbeziehen
        all_plugins = list(self.plugins_chat) + list(self.plugins_stream)

        for plugin in all_plugins:

            # Variante 1: dict-basierte Commands
            commands_dict = getattr(plugin, "commands", None)
            if isinstance(commands_dict, dict):
                for cmd, desc in commands_dict.items():
                    router.register(
                        cmd,
                        make_handler(plugin, cmd),
                        description=desc
                    )

            # Variante 2: Liste von Kommandos
            commands_list = getattr(plugin, "available_commands", None)
            if isinstance(commands_list, list):
                for cmd in commands_list:
                    router.register(
                        cmd,
                        make_handler(plugin, cmd),
                        description={
                            "de": "Plugin-Befehl",
                            "en": "Plugin command",
                        }
                    )

            # Variante 3: Fallback — command() existiert, aber keine Liste angegeben
            if hasattr(plugin, "command") and not getattr(plugin, "commands", None) and not getattr(plugin, "available_commands", None):
                fallback_cmd = f"/{plugin.__class__.__name__.lower()}"
                router.register(
                    fallback_cmd,
                    make_handler(plugin, fallback_cmd),
                    description={
                        "de": "Fallback-Plugin-Befehl",
                        "en": "Fallback plugin command",
                    }
                )

    # ---------------------------------------------------------
    # AFTER
    # ---------------------------------------------------------
    def handle_after_response(self, reply: str, context=None):
        context = context or {}
        current = reply

        for plugin in self.plugins_chat:
            after_fn = getattr(plugin, "after_response", None)
            if callable(after_fn):
                try:
                    new_text = after_fn(current, context)
                except TypeError:
                    new_text = after_fn(current)

                if new_text is not None:
                    current = new_text

        return current

    def handle_before_final_response(self, reply: str, context=None):
        context = context or {}
        current = reply

        for plugin in self.iter_all_plugins():
            final_fn = getattr(plugin, "before_final_response", None)
            if callable(final_fn):
                enabled_fn = getattr(plugin, "final_response_guard_enabled", None)
                if callable(enabled_fn):
                    try:
                        if not enabled_fn(context):
                            continue
                    except TypeError:
                        if not enabled_fn():
                            continue
                try:
                    new_text = final_fn(current, context)
                except TypeError:
                    new_text = final_fn(current)

                if new_text is not None:
                    current = new_text

        return current

    def handle_after_final_response(self, reply: str, context=None):
        context = context or {}
        for plugin in self.iter_all_plugins():
            final_fn = getattr(plugin, "after_final_response", None)
            if callable(final_fn):
                try:
                    final_fn(reply, context)
                except TypeError:
                    final_fn(reply)
