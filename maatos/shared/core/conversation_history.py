"""Profile-scoped recent dialogue window, independent of permanent archives."""
import json
from .maat_paths import state_file

DEFAULT_MESSAGES = 10
MIN_MESSAGES = 2
MAX_MESSAGES = 20
SETTING = 'chat_history_messages'


def message_limit(settings=None):
    if settings is None:
        try:
            with open(state_file('settings_state.json'), encoding='utf-8') as handle:
                settings = json.load(handle)
        except (OSError, ValueError):
            settings = {}
    value = settings.get(SETTING, DEFAULT_MESSAGES) if isinstance(settings, dict) else DEFAULT_MESSAGES
    try:
        if isinstance(value, bool):
            return DEFAULT_MESSAGES
        return max(MIN_MESSAGES, min(MAX_MESSAGES, int(value)))
    except (ValueError, TypeError, OverflowError):
        return DEFAULT_MESSAGES


def recent_messages(messages, limit=None):
    """Keep system instructions, N previous entries and the current user input."""
    limit = message_limit() if limit is None else message_limit({SETTING: limit})
    dialogue = [i for i, message in enumerate(messages) if message.get('role') != 'system']
    extra = int(bool(dialogue) and messages[dialogue[-1]].get('role') == 'user')
    selected = set(dialogue[-(limit + extra):])
    return [dict(message) for i, message in enumerate(messages)
            if message.get('role') == 'system' or i in selected]
