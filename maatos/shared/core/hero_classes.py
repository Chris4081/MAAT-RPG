"""Profile-owned class choice after the first unlocked real fight."""
import copy
import json
import os
from pathlib import Path
import tempfile


CLASSES = {
    'robo': ('Robo', 'Maatis mit Antenne und Visier. Talente: Technik, Panzerung und Reaktor.'),
    'engelchen': ('Engelchen', 'Maatis mit Flügeln und Hörnern. Talente: Flügelwind, Schutzengel und Hoffnung.'),
    'magier': ('Magier', 'Maatis mit Zauberhut. Talente: Arkanes Wissen, Resonanzmagie und Schutzrunen.'),
    'priester': ('Priester', 'Maatis mit Robe und Stab. Talente: Heilkunde, Tempelwacht und Lichtpfad.'),
    'puppy': ('Puppy', 'Maatis im Hundekostüm. Talente: Wildfang, flinke Pfoten und treues Herz.'),
}


def selected_class(state):
    record = state.get('hero_class')
    value = record.get('selected') if isinstance(record, dict) else None
    return value if isinstance(value, str) and value in CLASSES else 'normal'


def choice_pending(state):
    record = state.get('hero_class')
    return selected_class(state) == 'normal' and isinstance(record, dict) and bool(record.get('pending'))


def _commit(store, change):
    """Save the entire current battle state atomically; never acknowledge a failed write."""
    candidate = copy.deepcopy(store.state)
    if not isinstance(candidate.get('hero_class'), dict):
        candidate['hero_class'] = {}
    change(candidate['hero_class'])
    path = Path(store.state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.hero-class-', delete=False) as output:
            temporary = output.name
            json.dump(candidate, output, ensure_ascii=False, indent=2)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    store.state['hero_class'] = candidate['hero_class']


def finish_first_fight(store, *, unlocked, demo=False):
    if demo or not unlocked or selected_class(store.state) != 'normal':
        return False
    if not choice_pending(store.state):
        _commit(store, lambda record: record.update(pending=True, first_fight_completed=True))
    return True


def choose_class(store, value):
    if not isinstance(value, str) or value not in CLASSES:
        raise ValueError('Bitte eine der fünf Klassen auswählen.')
    current = selected_class(store.state)
    if current == value:
        return value
    if current != 'normal':
        raise ValueError('Die Klasse ist für dieses Profil bereits gewählt.')
    if not choice_pending(store.state):
        raise ValueError('Die Klassenwahl wird nach dem ersten freigeschalteten Kampf verfügbar.')
    _commit(store, lambda record: record.update(selected=value, pending=False))
    return value
