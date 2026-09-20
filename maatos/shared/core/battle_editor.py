"""Endgame battle drafts, compatible with the terminal's battle-profile mods."""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import re
import tempfile
import uuid
from pathlib import Path

from shared.core.maat_paths import get_mods_battle_profiles_dir
from shared.core.mod_support import load_battle_profile_mods
from shared.core.monster_catalog import KIND_ART

ARTS = tuple(dict.fromkeys(KIND_ART.values()))
EFFECTS = ('slash', 'claw', 'wave', 'spark', 'sand', 'balance', 'creation', 'connection', 'respect', 'impulse')
WEAKNESSES = ('', 'Harmonie', 'Balance', 'Schöpfungskraft', 'Verbundenheit', 'Respekt')


def unlocked(state):
    try:
        return int(state.get('stats', {}).get('final_wins', 0)) >= 5
    except (ValueError, TypeError, AttributeError):
        return False


def require_unlocked(state):
    if not unlocked(state):
        raise ValueError('editor_locked')


def number(value, low, high):
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        raise ValueError('editor_numbers') from None
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError('editor_numbers')
    return result


def validate(data):
    if not isinstance(data, dict):
        raise ValueError('editor_invalid')
    name = str(data.get('name', '')).strip()
    if not name or len(name) > 64 or any(ord(c) < 32 for c in name):
        raise ValueError('editor_name')
    art = data.get('art', ARTS[0])
    effect = data.get('effect', 'slash')
    weakness = data.get('weakness', '')
    kind = data.get('fight_type', 'normal')
    if art not in ARTS or effect not in EFFECTS or weakness not in WEAKNESSES or kind not in ('normal', 'boss'):
        raise ValueError('editor_invalid')
    result = dict(name=name, art=art, effect=effect, weakness=weakness, fight_type=kind,
                  hp_mult=number(data.get('hp_mult', 1), .1, 10),
                  damage_mult=number(data.get('damage_mult', 1), .1, 5))
    for key in ('intro', 'victory'):
        result[key] = str(data.get(key, '')).strip()
        if len(result[key]) > 1000:
            raise ValueError('editor_text')
    image = data.get('image', '')
    if image and (not isinstance(image, str) or not re.fullmatch(r'[a-f0-9]{64}\.png', image)):
        raise ValueError('editor_image')
    result['image'] = image
    return result


def portrait_path(key):
    if isinstance(key, str) and re.fullmatch(r'[a-f0-9]{64}\.png', key):
        return get_mods_battle_profiles_dir() / 'assets' / key
    return None


def _atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.draft-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _store_portrait(encoded):
    if not isinstance(encoded, str) or len(encoded) > 2_800_000:
        raise ValueError('editor_image')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise ValueError('editor_image') from None
    # The GUI normalizes imports to PNG before transmission. Check dimensions
    # before decoding in the worker, too, to bound allocation for crafted input.
    if len(raw) < 24 or raw[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('editor_image')
    width, height = int.from_bytes(raw[16:20], 'big'), int.from_bytes(raw[20:24], 'big')
    if not (1 <= width <= 1024 and 1 <= height <= 1024):
        raise ValueError('editor_image')
    from PySide6.QtGui import QImage
    decoded = QImage.fromData(raw, 'PNG')
    if decoded.isNull():
        raise ValueError('editor_image')
    key = hashlib.sha256(raw).hexdigest() + '.png'
    _atomic_write(portrait_path(key), raw)
    return key


def _draft(mod):
    profile = mod['battle_profile']
    enemy = profile.get('enemy') or {}
    visual = profile.get('visual') or {}
    source = Path(mod['source'])
    raw = source.read_bytes()
    editable = (source.parent == get_mods_battle_profiles_dir()
                and bool(re.fullmatch(r'editor_[a-f0-9]{32}', mod['id']))
                and source.name == mod['id'] + '.json'
                and json.loads(raw).get('editor_version') == 1) if source.suffix == '.json' else False
    def bounded(value, low, high):
        try:
            value = float(value)
            return min(high, max(low, value)) if math.isfinite(value) else 1.0
        except (TypeError, ValueError, OverflowError):
            return 1.0
    def lines(value):
        return '\n'.join(x for x in value if isinstance(x, str))[:1000] if isinstance(value, list) else ''
    data = dict(id=mod['id'], name=mod['name'], fight_type=mod['fight_type'] if mod['fight_type'] != 'final' else 'boss',
                hp_mult=bounded(enemy.get('hp_mult', 1), .1, 10), damage_mult=bounded(enemy.get('damage_mult', 1), .1, 5),
                art=visual.get('art', ARTS[0]), effect=visual.get('effect', 'slash'),
                image=visual.get('image', ''), weakness=enemy.get('weakness', ''),
                intro=lines(profile.get('intro_lines')),
                victory=lines(profile.get('victory_lines')), editable=editable,
                revision=hashlib.sha256(raw).hexdigest())
    return data


def catalog(state):
    require_unlocked(state)
    result = []
    for mod in load_battle_profile_mods().values():
        try:
            result.append(_draft(mod))
        except (OSError, ValueError, TypeError, AttributeError):
            continue  # An unsupported third-party profile must not break the page.
    return sorted(result, key=lambda item: item['name'].casefold())


def save(state, data, *, mod_id=None, revision=None):
    require_unlocked(state)
    draft = validate(data)
    root = get_mods_battle_profiles_dir()
    if mod_id:
        if not isinstance(mod_id, str) or not re.fullmatch(r'editor_[a-f0-9]{32}', mod_id):
            raise ValueError('editor_copy')
        path = root / (mod_id + '.json')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != revision:
            raise ValueError('editor_changed')
    else:
        mod_id = 'editor_' + uuid.uuid4().hex
        path = root / (mod_id + '.json')
    if data.get('portrait_png'):
        draft['image'] = _store_portrait(data['portrait_png'])
    if draft['image'] and not portrait_path(draft['image']).is_file():
        raise ValueError('editor_image')
    payload = dict(id=mod_id, name=draft['name'], fight_type=draft['fight_type'],
                   persistent_rewards=False, editor_version=1,
                   battle_profile=dict(boss_name=draft['name'],
                       enemy=dict(hp_mult=draft['hp_mult'], damage_mult=draft['damage_mult'], weakness=draft['weakness']),
                       visual=dict(art=draft['art'], effect=draft['effect'], image=draft['image']),
                       intro_lines=draft['intro'].splitlines(), victory_lines=draft['victory'].splitlines()))
    _atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8'))
    return next(item for item in catalog(state) if item['id'] == mod_id)


def playable(state, mod_id):
    require_unlocked(state)
    mod = load_battle_profile_mods().get(mod_id)
    if not mod:
        raise ValueError('editor_missing')
    # Only normalized editor copies are launched here. Advanced terminal mods
    # retain their existing /fightmod workflow and are never silently rewritten.
    draft = next((item for item in catalog(state) if item['id'] == mod_id), None)
    if not draft or not draft['editable']:
        raise ValueError('editor_copy')
    enemy = mod['battle_profile'].get('enemy') or {}
    validate(dict(draft, hp_mult=enemy.get('hp_mult', 1), damage_mult=enemy.get('damage_mult', 1)))
    return mod
