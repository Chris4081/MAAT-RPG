from shared.core.ai_plugin_settings import settings_for, language_for, query_for
from shared.core.maat_style import build_style_prompt, diagnostic_text


class Plugin:
    type = 'chat'
    commands = {}

    def generation_prompt(self, language=None, context=None):
        prompt, self.last_state = build_style_prompt(settings_for(context), query_for(context),
                                                    language=language_for(context, language))
        if self.last_state['enabled'] and self.last_state['debug']:
            import logging
            # Only selected/detected labels, never private messages or prompts.
            logging.getLogger('maat.gui.lifecycle').info('maat_style %s', diagnostic_text(
                settings_for(context), query_for(context), language_for(context, language)).replace('\n', ' | '))
        return prompt
