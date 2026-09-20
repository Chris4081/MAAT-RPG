"""MAAT100: optional silent quality prompt, with no extra model calls."""
from shared.core.rpg_i18n import load_settings
from shared.plugins.maat_thinking.prompt import build_prompt_block


class Plugin:
    type = 'chat'
    commands = {}

    def generation_prompt(self, language=None, context=None):
        # Read on each generation: toggles apply without model/worker reload.
        enabled = bool(load_settings().get('maat_thinking_enabled', True))
        return build_prompt_block(100 if enabled else 0, language)
