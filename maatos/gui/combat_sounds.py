"""Attack and damage cues follow the visible, authoritative combat events."""
from pathlib import Path
from gui.ascii_effects import effect_kind


SOUND_ROOT = Path(__file__).resolve().parent / 'assets/audio/principles-v1'
DAMAGE_SOUND = SOUND_ROOT.parent / 'combat-v1/maatis_hurt.wav'
PRINCIPLE_SOUNDS = {
    'wave': 'h_harmony.wav',
    'balance': 'b_balance.wav',
    'creation': 's_creation.wav',
    'connection': 'v_connection.wav',
    'respect': 'r_respect.wav',
}


def attack_sound(event):
    if event.get('attacker') != 'player':
        return None
    filename = PRINCIPLE_SOUNDS.get(effect_kind(event, 'maatis'))
    return SOUND_ROOT / filename if filename else None


def combat_sound(event):
    if event.get('attacker') == 'enemy':
        try:
            # The HP floor can absorb part or all of an otherwise damaging hit.
            # Prefer the actual before/after HP over the nominal damage number.
            if 'player_hp_before' in event and 'player_hp' in event:
                lost = int(event['player_hp_before']) - int(event['player_hp'])
            else:
                lost = int(event.get('damage', 0))
        except (TypeError, ValueError, OverflowError):
            return None
        return DAMAGE_SOUND if lost > 0 else None
    return attack_sound(event)
