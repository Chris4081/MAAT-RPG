"""Process-local story perspective; terminal sessions default to Maatis."""
from .maat_paths import state_file

_companion = False


def set_companion_story(enabled):
    global _companion
    _companion = bool(enabled)


def companion_story_active():
    return _companion


def story_state_file():
    return state_file('companion_story_state.json' if _companion else 'story_state.json')
