"""Canonical, post-campaign boss encounters; never advance the campaign again."""
import json
import os
from pathlib import Path
import tempfile
from .monster_catalog import BOSS_NAMES, FINAL_NAMES


def unlocked(state):
    return bool(state.get('world', {}).get('combat_unlocked')) and state.get('stats', {}).get('final_wins', 0) >= 5


def targets():
    rows = []
    for region in range(5):
        for form, name in enumerate(BOSS_NAMES):
            index = region * 5 + form + 1
            rows.append(dict(id=f'boss-{index}', kind='boss', index=index, region=region,
                             name=f'{name} #{index}', label=f'Boss {index}'))
        index = region + 1
        rows.append(dict(id=f'final-{index}', kind='final', index=index, region=region,
                         name=f'{FINAL_NAMES[region]} (Final {index})', label=f'Finale {index}'))
    return rows


def resolve(state, key):
    if not unlocked(state):
        raise ValueError('Die Bosswahl öffnet sich nach dem fünften Finale.')
    target = next((row for row in targets() if row['id'] == key), None)
    if target is None:
        raise ValueError('Dieser Gegner gehört nicht zur Terra-Karte.')
    return target


def encounter_context(state, key, context=None):
    target = resolve(state, key)
    result = dict(context or {})
    # Preserve player/story hooks, but never inherit a demo or dungeon opponent.
    for field in ('guide_mode', 'title_demo_mode', 'scripted_actions', 'battle_profile',
                  'boss_name', 'music', 'narrative_prepend', 'continuous_dungeon_music', 'arena_difficulty'):
        result.pop(field, None)
    result.update(combat_source='random', terra_replay=target)
    return target['kind'], result


def queue(state_store, key):
    target = resolve(state_store.state, key)
    _save_pending(state_store, target['id'])
    return target


def select_random(state_store):
    """Return to ordinary encounters without changing the chat trigger timer."""
    if not unlocked(state_store.state):
        raise ValueError('Die Bosswahl öffnet sich nach dem fünften Finale.')
    _save_pending(state_store, None)


def _save_pending(store, key):
    world = dict(store.state.get('world', {}))
    if key is None: world.pop('terra_replay_pending', None)
    else: world['terra_replay_pending'] = key
    candidate = dict(store.state, world=world)
    path = Path(store.state_path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as out:
            temporary = out.name
            json.dump(candidate, out, ensure_ascii=False, indent=2)
            out.flush();os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary): os.unlink(temporary)
    if key is None: store.state.setdefault('world', {}).pop('terra_replay_pending', None)
    else: store.state.setdefault('world', {})['terra_replay_pending'] = key


def pending(state):
    try: return resolve(state, state.get('world', {}).get('terra_replay_pending'))
    except ValueError: return None


def take_pending(state_store):
    target = pending(state_store.state)
    if target:
        _save_pending(state_store, None)
    return target
