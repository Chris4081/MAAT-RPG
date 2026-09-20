"""Profile-local switches and a stable settings snapshot for one model reply."""
from .rpg_i18n import load_settings, get_language
from .reply_style import DEFAULTS as REPLY_STYLE_DEFAULTS
from .maat_style import STYLE_DEFAULTS

DEFAULTS = {'emotion_enabled': True, 'hallu_mode': False,
            'maat_style_enabled': False, 'maat_identity_enabled': False,
            'reality_enabled': True, 'response_formatting_enabled': True,
            'reply_style_enabled': True}
EMOTION_FIELDS = ('emotion_raw', 'emotion_intensity', 'emotion_E',
                  'A_from_emotion', 'deltaD_from_emotion', 'emotion_safe_text')
SNAPSHOT = '_ai_plugin_settings'


def current_settings():
    saved = load_settings()
    return {**DEFAULTS, **STYLE_DEFAULTS, **REPLY_STYLE_DEFAULTS, **saved}


def settings_for(context=None):
    if isinstance(context, dict) and isinstance(context.get(SNAPSHOT), dict):
        return context[SNAPSHOT]
    return current_settings()


def clear_emotion(context):
    if isinstance(context, dict):
        fields = context.get('maat_fields')
        if isinstance(fields, dict):
            for key in EMOTION_FIELDS:
                fields.pop(key, None)
        meta = context.get('maat_meta')
        if isinstance(meta, dict):
            meta.pop('emotion', None)


def begin_turn(context, user_input):
    context[SNAPSHOT] = current_settings()
    context['_ai_plugin_query'] = str(user_input or '')
    if not context[SNAPSHOT]['emotion_enabled']:
        clear_emotion(context)


def query_for(context):
    context = context or {}
    return str(context.get('_ai_plugin_query', context.get('last_user_input', '')) or '')


def language_for(context=None, language=None):
    context = context or {}
    return (language or context.get('_ai_reply_language') or
            context.get('_ai_generation_state', {}).get('language') or get_language(('de', 'en')))
