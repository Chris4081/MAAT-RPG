# -*- coding: utf-8 -*-
"""
MAAT-KI CommandRouter v2.2
---------------------------------------
✓ System-Kommandos
✓ Plugin-Kommandos (mit und ohne Argumente)
✓ Alias-System
✓ Beschreibungen
✓ Kompatibel mit MAAT-KI ChatLoop 2.0
✓ Freundliche Fehlermeldung bei unbekannten /Kommandos
"""

from .rpg_i18n import get_language


ROUTER_TEXT = {
    "de": {
        "plugin_command": "Plugin-Befehl",
        "fallback_plugin_command": "Fallback-Plugin-Befehl",
        "plugin_missing_handler": "⚠️ Plugin `{plugin}` hat keinen command()-Handler.",
        "unknown_command": "❓ **Unbekannter Befehl:** `{command}`\nNutze `/help` für alle verfügbaren Kommandos.",
        "system_header": "📘 Verfügbare System-Kommandos:\n",
        "plugin_header": "\n🔌 Plugin-Kommandos:",
    },
    "en": {
        "plugin_command": "Plugin command",
        "fallback_plugin_command": "Fallback plugin command",
        "plugin_missing_handler": "⚠️ Plugin `{plugin}` has no command() handler.",
        "unknown_command": "❓ **Unknown command:** `{command}`\nUse `/help` to see all available commands.",
        "system_header": "📘 Available system commands:\n",
        "plugin_header": "\n🔌 Plugin commands:",
    },
}

class CommandRouter:

    def __init__(self):
        self.commands = {}        # "/help": { handler, desc }
        self.aliases = {}         # "/h": "/help"
        self.plugin_cmd_map = {}  # "/say": { plugin, desc }

    def _lang(self):
        return get_language(tuple(ROUTER_TEXT.keys()))

    def _t(self, key, **kwargs):
        lang = self._lang()
        template = ROUTER_TEXT.get(lang, ROUTER_TEXT["de"]).get(key, ROUTER_TEXT["de"].get(key, key))
        return template.format(**kwargs) if kwargs else template

    def _resolve_desc(self, desc):
        if isinstance(desc, dict):
            lang = self._lang()
            return desc.get(lang) or desc.get("de") or next(iter(desc.values()), "")
        return desc or ""

    # ---------------------------------------------------
    # SYSTEM-COMMAND REGISTRIEREN
    # ---------------------------------------------------
    def register(self, name, handler, aliases=None, description=""):
        self.commands[name] = {
            "handler": handler,
            "desc": description
        }

        if aliases:
            for a in aliases:
                self.aliases[a] = name

    # ---------------------------------------------------
    # PLUGIN-COMMAND REGISTRIEREN
    # ---------------------------------------------------
    def register_plugin_command(self, cmd, plugin_instance, description=""):
        """
        cmd: Basis-Command, z.B. "/say"
        plugin_instance: Plugin object
        """
        self.plugin_cmd_map[cmd] = {
            "plugin": plugin_instance,
            "desc": description or {
                "de": self._t("plugin_command"),
                "en": self._t("plugin_command"),
            }
        }

    # ---------------------------------------------------
    # MATCH?
    # ---------------------------------------------------
    def match(self, user_input):
        """
        Ab jetzt:
        - Alles was mit "/" beginnt, wird als Kommando behandelt.
        - Auch unbekannte Kommandos gehen durch execute(), damit
          eine schöne Fehlermeldung ausgegeben werden kann.
        """
        if not user_input.startswith("/"):
            return False

        # Egal ob bekannt oder nicht → als Command betrachten
        return True

    # ---------------------------------------------------
    # AUSFÜHREN
    # ---------------------------------------------------
    def execute(self, user_input, context=None):
        parts = user_input.split(" ")
        base = parts[0]
        args = parts[1:]

        # Alias-Auflösung
        if base in self.aliases:
            base = self.aliases[base]

        # ---------------------------------------------------
        # 1) SYSTEM-COMMAND
        # ---------------------------------------------------
        if base in self.commands:
            handler = self.commands[base]["handler"]
            res = handler(args)

            # Normalisierung (falls ein Tuple zurückkommt)
            if isinstance(res, tuple):
                res = res[-1]

            return f"{res}" if res else ""

        # ---------------------------------------------------
        # 2) PLUGIN-COMMAND
        # ---------------------------------------------------
        if base in self.plugin_cmd_map:
            plugin = self.plugin_cmd_map[base]["plugin"]

            if hasattr(plugin, "command"):
                res = plugin.command(user_input, context)

                # Normalisierung für (handled, msg)
                if isinstance(res, tuple):
                    if len(res) == 2:
                        _, msg = res
                        res = msg
                    elif len(res) == 1:
                        res = res[0]

                return f"{res}" if res else ""

            return (
                self._t("plugin_missing_handler", plugin=plugin.__class__.__name__)
            )

        # ---------------------------------------------------
        # 3) UNBEKANNTES KOMMANDO
        # ---------------------------------------------------
        clean = base.lstrip("/")

        return (
            self._t("unknown_command", command=clean)
        )

    # ---------------------------------------------------
    # ALLE COMMANDS LISTEN
    # ---------------------------------------------------
    def help_text(self):
        out = [self._t("system_header")]

        # SYSTEM COMMANDS
        for cmd, info in self.commands.items():
            out.append(f"{cmd} — {self._resolve_desc(info['desc'])}")

        # PLUGIN COMMANDS (nur Basis, z.B. /say)
        if self.plugin_cmd_map:
            out.append(self._t("plugin_header"))
            for cmd, info in self.plugin_cmd_map.items():
                out.append(f"{cmd} — {self._resolve_desc(info['desc'])}")

        return "\n".join(out)
