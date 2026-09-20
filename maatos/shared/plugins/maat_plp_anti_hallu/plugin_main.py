"""Web Core guard adapted to the RPG's actual Wiki and Super Memory sources."""
import re
from shared.core.ai_plugin_settings import settings_for, language_for, query_for
from shared.core.maat_plp_anti_hallu import build_antihallu_prompt, apply_antihallu_guard, report_lines


class Plugin:
    type = 'chat'
    commands = {name: {'de': 'Letzte heuristische PLP-Anti-Hallu-Prüfung anzeigen.',
                       'en': 'Show the latest heuristic PLP Anti-Hallu check.'}
                for name in ('/plp', '/plp status', '/plp last', '/uncertainty')}

    def __init__(self):
        self.last_result = None

    def settings(self, context=None, language=None):
        settings = dict(settings_for(context))
        settings.update(antihallu_enabled=bool(settings.get('hallu_mode', False)),
                        language=language_for(context, language))
        return settings

    def generation_prompt(self, language=None, context=None):
        return build_antihallu_prompt(self.settings(context, language), query_for(context))

    def generation_guard_enabled(self, context=None):
        return self.settings(context)['antihallu_enabled']

    def guard_generation_output(self, reply, context=None):
        context = context or {}
        # Private drafts and save directives are not evidence for the reply.
        text = re.sub(r'<think>.*?(?:</think>|$)', '', reply, flags=re.S | re.I)
        memory = context.get('super_memory')
        if memory is not None and callable(getattr(memory, 'extract_model_saves', None)):
            prose, _ = memory.extract_model_saves(text)
        else:
            prose = text
        grounding = context.get('_ai_generation_state', {}).get('grounding') or {}
        evidence = {'super_memory': {'memories': grounding.get('memories', [])},
                    'grounding_text': grounding.get('text', ''),
                    'clock_context': grounding.get('clock', '')}
        guarded, self.last_result = apply_antihallu_guard(self.settings(context), query_for(context), prose, evidence)
        # Rejected output must not sneak into memory through its save directives.
        return text if guarded == prose else guarded

    def command(self, cmd, context=None):
        if cmd.strip().lower() not in self.commands:
            return None
        lang = language_for(context)
        # Commands use live profile settings; a previous turn's snapshot is stale.
        if not settings_for().get('hallu_mode', False):
            return True, 'PLP Anti-Hallu is disabled.' if lang == 'en' else 'PLP Anti-Hallu ist deaktiviert.'
        return True, '\n'.join(report_lines(self.last_result, lang))
