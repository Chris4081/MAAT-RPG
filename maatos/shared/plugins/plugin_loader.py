# shared/plugins/plugin_loader.py
# -*- coding: utf-8 -*-

import os
import importlib.util
import inspect


class PluginManager:
    def __init__(self, plugin_roots):
        if isinstance(plugin_roots, str):
            self.plugin_roots = [plugin_roots]
        else:
            self.plugin_roots = list(plugin_roots)

        self.plugins_chat = []
        self.plugins_stream = []

    # ---------------------------------------------------------
    # LOAD
    # ---------------------------------------------------------
    def load_plugins(self):
        print("🔍 Lade Plugins …")

        self.plugins_chat.clear()
        self.plugins_stream.clear()

        for root in self.plugin_roots:
            if not os.path.isdir(root):
                continue

            for entry in sorted(os.listdir(root)):
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
            mod_name = "maat_plugin_" + os.path.basename(file_path).replace(".py", "")
            spec = importlib.util.spec_from_file_location(mod_name, file_path)
            if not spec or not spec.loader:
                print(f"⚠ Konnte Modul nicht laden: {file_path}")
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            PluginClass = getattr(module, "Plugin", None)
            if PluginClass is None or not inspect.isclass(PluginClass):
                print(f"⚠ Keine Plugin-Klasse in: {file_path}")
                return

            inst = PluginClass()
            ptype = getattr(inst, "type", "chat")

            if ptype == "stream":
                self.plugins_stream.append(inst)
            else:
                self.plugins_chat.append(inst)

        except Exception as e:
            print(f"⚠ Plugin-Ladefehler in {file_path}: {e}")

    # ---------------------------------------------------------
    # INFO
    # ---------------------------------------------------------
    def _print_plugin_summary(self):
        print("\n📦 Plugin-Übersicht:")
        print(f"   • Chat-Plugins:     {len(self.plugins_chat)}")
        print(f"   • Streaming-Plugins:{len(self.plugins_stream)}\n")

    def print_plugin_summary(self):
        self._print_plugin_summary()

    def iter_all_plugins(self):
        return list(self.plugins_chat) + list(self.plugins_stream)

    def get_streaming_plugins(self):
        return list(self.plugins_stream)

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
                        description="Plugin Command"
                    )

            # Variante 3: Fallback — command() existiert, aber keine Liste angegeben
            if hasattr(plugin, "command") and not getattr(plugin, "commands", None) and not getattr(plugin, "available_commands", None):
                fallback_cmd = f"/{plugin.__class__.__name__.lower()}"
                router.register(
                    fallback_cmd,
                    make_handler(plugin, fallback_cmd),
                    description="Fallback Plugin Command"
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