"""Fresh local time through the same transient prompt path as all GGUF models."""
import sqlite3
from shared.core.ai_plugin_settings import settings_for, language_for, query_for
from shared.core.maat_reality_layer import build_reality_prompt


class Plugin:
    type = 'chat'
    commands = {}

    def generation_prompt(self, language=None, context=None):
        settings = settings_for(context)
        if not settings.get('reality_enabled', True):
            return ''
        previous = (context or {}).get('reality_last_activity')
        if callable(previous):
            try:
                previous = previous()
            except (OSError, sqlite3.Error):
                # An unavailable/locked archive must not break ordinary chat.
                previous = None
        return build_reality_prompt(settings, query_for(context), previous,
                                    language=language_for(context, language))
