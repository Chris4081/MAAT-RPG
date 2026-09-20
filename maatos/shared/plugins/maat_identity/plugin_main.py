from shared.core.ai_plugin_settings import settings_for, language_for, query_for
from shared.core.maat_identity import build_identity_prompt


class Plugin:
    type = 'chat'
    commands = {}

    def generation_prompt(self, language=None, context=None):
        return build_identity_prompt(settings_for(context), query_for(context),
                                     language=language_for(context, language), context=context)
