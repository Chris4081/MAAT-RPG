"""Soft reply preferences; models may always end a naturally complete answer."""
from shared.core.ai_plugin_settings import settings_for, language_for
from shared.core.reply_style import build_reply_style_prompt


class Plugin:
    type = 'chat'
    commands = {}

    def generation_prompt(self, language=None, context=None):
        return build_reply_style_prompt(settings_for(context), language_for(context, language))
