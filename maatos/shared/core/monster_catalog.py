"""Shared enemy name pools used by combat and the level-50 bestiary."""
import unicodedata
from .boss_art import BOSS_ART, BOSS_MOTIFS, BOSS_EFFECTS, CAMPAIGN_BOSS_COUNT
ENEMY_PREFIXES = ['Schatten', 'Echo', 'Staub', 'Gefallener', 'Verlorener', 'Gebrochener', 'Resonanter', 'Stiller', 'Astraler']
ENEMY_KINDS = ['Wanderer', 'Wächter', 'Bestie', 'Phantom', 'Beobachter', 'Idol', 'Konstrukt', 'Funke',
               'Skarabäus', 'Skorpion', 'Schlange', 'Sandwurm', 'Spinne', 'Falke',
               'Schakal', 'Drache', 'Golem', 'Qualle', 'Motte', 'Fangschrecke']
ENEMY_SUFFIXES = ['', ' der Dissonanz', ' der Leere', ' der Vergessenen Sande', ' des Risses', ' der Echos']
BOSS_NAMES = ['Pharao der Dissonanz', 'Wächter der Gebrochenen Harmonie', 'Archon des Abgrunds', 'Fürst der Zersplitterten Zeit', 'Hüter der Leeren Sonne']
FINAL_NAMES = ['Avatar der Balance', 'Herz der Schöpfung', 'Krone der Resonanz', 'Achse des Äons', 'Licht der MAAT']

PREFIXES_EN = ['Shadow', 'Echo', 'Dust', 'Fallen', 'Lost', 'Broken', 'Resonant', 'Silent', 'Astral']
KINDS_EN = ['Wanderer', 'Warden', 'Beast', 'Phantom', 'Watcher', 'Idol', 'Construct', 'Spark',
            'Scarab', 'Scorpion', 'Serpent', 'Sandworm', 'Spider', 'Falcon',
            'Jackal', 'Dragon', 'Golem', 'Jellyfish', 'Moth', 'Mantis']
SUFFIXES_EN = ['', ' of Dissonance', ' of the Void', ' of the Forgotten Sands', ' of the Rift', ' of Echoes']
BOSSES_EN = ['Pharaoh of Dissonance', 'Warden of Broken Harmony', 'Archon of the Abyss', 'Prince of Shattered Time', 'Keeper of the Empty Sun']
FINALS_EN = ['Avatar of Balance', 'Heart of Creation', 'Crown of Resonance', 'Axis of the Aeon', 'Light of MAAT']

# Canonical regular types share one visual/attack identity across all languages.
KIND_ART = dict(zip(ENEMY_KINDS, ['wanderer', 'guardian', 'beast', 'phantom', 'watcher', 'idol',
    'construct', 'spark', 'scarab', 'scorpion', 'serpent', 'sandworm', 'spider', 'falcon',
    'jackal', 'dragon', 'golem', 'jellyfish', 'moth', 'mantis']))
ENEMY_EFFECTS = {
    'beast':'claw', 'phantom':'wave', 'watcher':'wave', 'archon':'wave',
    'spark':'spark', 'light':'spark', 'pharaoh':'sand', 'wanderer':'sand',
    'avatar':'balance', 'heart':'creation', 'crown':'impulse', 'axis':'impulse',
    'time':'connection', 'sun':'impulse',
    'scarab':'spark', 'scorpion':'claw', 'serpent':'wave', 'sandworm':'sand',
    'spider':'connection', 'falcon':'slash', 'jackal':'claw', 'dragon':'creation',
    'golem':'balance', 'jellyfish':'spark', 'moth':'sand', 'mantis':'slash',
}
EFFECT_LABELS = {
    'slash':('Klingenstoß','Blade strike'), 'claw':('Klauenhieb','Claw strike'),
    'wave':('Resonanzwelle','Resonance wave'), 'spark':('Funkenstoß','Spark discharge'),
    'sand':('Sandwirbel','Sand vortex'), 'balance':('Gewichtsstoß','Weighted strike'),
    'creation':('Schöpfungsflamme','Creation flame'), 'connection':('Fadennetz','Thread web'),
}
ENEMY_EFFECTS.update(BOSS_EFFECTS)
RECENT_KINDS_LIMIT = 5


def choose_enemy_name(state=None, rng=None, kinds=None):
    """Avoid the last five regular silhouettes, persisted in the current save.

    A constrained story pool may be smaller: prefer its least recently seen type.
    Passing no state (e.g. a title demo) never changes a player's history.
    """
    import random
    rng = rng or random
    pool = list(dict.fromkeys(k for k in (ENEMY_KINDS if kinds is None else kinds) if k in KIND_ART))
    if not pool:
        raise ValueError('Enemy pool must contain a known monster kind')
    history = state.get('recent_enemy_kinds', []) if isinstance(state, dict) else []
    history = [k for k in history if isinstance(k, str) and k in KIND_ART][-RECENT_KINDS_LIMIT:] if isinstance(history, list) else []
    candidates = [k for k in pool if k not in history]
    if not candidates:
        oldest = min(max(i for i, seen in enumerate(history) if seen == k) for k in pool)
        candidates = [k for k in pool if max(i for i, seen in enumerate(history) if seen == k) == oldest]
    kind = rng.choice(candidates)
    name = f'{rng.choice(ENEMY_PREFIXES)} {kind}{rng.choice(ENEMY_SUFFIXES)}'
    if isinstance(state, dict):
        state['recent_enemy_kinds'] = (history + [kind])[-RECENT_KINDS_LIMIT:]
    return name

# Exact authored names, rather than substitutions inside arbitrary mod names.
ENEMY_NAMES_EN = dict(zip(ENEMY_KINDS+BOSS_NAMES+FINAL_NAMES, KINDS_EN+BOSSES_EN+FINALS_EN))
for prefix, en_prefix in zip(ENEMY_PREFIXES, PREFIXES_EN):
    for kind, en_kind in zip(ENEMY_KINDS, KINDS_EN):
        for suffix, en_suffix in zip(ENEMY_SUFFIXES, SUFFIXES_EN):
            ENEMY_NAMES_EN[f'{prefix} {kind}{suffix}'] = f'{en_prefix} {en_kind}{en_suffix}'
ENEMY_NAMES_EN.update({
    'Schattenwächter': 'Shadow Warden',
    'Kristall Wächter': 'Crystal Guardian',
    'Wächter der Resonanz': 'Guardian of Resonance',
    'Herr der 500 Schatten': 'Lord of 500 Shadows',
    'Archon der tausend Echos': 'Archon of a Thousand Echoes',
    'Hüter des klingenden Gartens': 'Keeper of the Singing Garden',
    'Richter der Gewichte': 'Judge of Weights',
    'Meister des ersten Funkens': 'Master of the First Spark',
    'Wächter der getrennten Ufer': 'Warden of the Divided Shores',
    'Grenzwächter des Respekts': 'Boundary Warden of Respect',
    'Hüter der fünf Siegel': 'Keeper of the Five Seals',
    'Astraelion, Splitter des Himmels': 'Astraelion, Shard of the Sky',
    'Der Schallbrecher von Arkona': 'The Soundbreaker of Arkona',
    "Vel'Shar, Hüter der Klangklingen": "Vel'Shar, Keeper of the Soundblades",
    'Elyndra, Königin der Glassphäre': 'Elyndra, Queen of the Glass Sphere',
    'Thornak, Resonanz-Brecher': 'Thornak, Resonance Breaker',
    'Die 500 Gesichter der Stille': 'The 500 Faces of Silence',
    'Aionis der Transparente': 'Aionis the Transparent',
    'Aurelia der Klanglosen': 'Aurelia of the Soundless',
    'Der Verstummte Titan': 'The Silenced Titan',
    'Hüterin der Leeren Stimmen': 'Keeper of the Empty Voices',
    'Seraph der Vergessenen Worte': 'Seraph of Forgotten Words',
    'Primarch der Resonanz': 'Primarch of Resonance',
    'Harmoniebrecher': 'Breaker of Harmony',
    'Wächter des Gegengewichts': 'Warden of Counterbalance',
    'Flamme der Schöpfung': 'Flame of Creation',
    'Stimme der Leere': 'Voice of the Void',
    'Richter des Respekts': 'Judge of Respect',
    'Wandernde Dissonanz': 'Wandering Dissonance',
})
_NAMES_DE = {}
for _de, _en in ENEMY_NAMES_EN.items():
    _NAMES_DE.setdefault(_en, _de)


def _name_key(name):
    return ' '.join(unicodedata.normalize('NFC',name).casefold().split())


# Recognise known titles in old saves with decomposed accents or ae/oe/ue.
# Unknown custom names remain untouched; never translate arbitrary substrings.
_ALIASES_DE = {}
for _name in list(ENEMY_NAMES_EN)+list(_NAMES_DE):
    _canonical = _NAMES_DE.get(_name,_name)
    _key = _name_key(_name)
    _ALIASES_DE.setdefault(_key,_canonical)
    _ALIASES_DE.setdefault(_key.replace('ä','ae').replace('ö','oe').replace('ü','ue'),_canonical)


def _name_parts(name):
    import re
    match = re.fullmatch(r'(.*?)( #\d+| \(Final \d+\))?', name)
    return (match[1], match[2] or '') if match else (name, '')


def canonical_enemy_name(name):
    base, suffix = _name_parts(str(name or ''))
    return _ALIASES_DE.get(_name_key(base), base) + suffix


def enemy_display_name(name, language='de'):
    base, suffix = _name_parts(canonical_enemy_name(name))
    return (ENEMY_NAMES_EN.get(base, base) if language == 'en' else base) + suffix


def boss_artwork(name):
    """Resolve a campaign number in either language, without matching custom names."""
    base, suffix = _name_parts(canonical_enemy_name(name))
    if base in BOSS_NAMES and suffix.startswith(' #'):
        number = int(suffix[2:])
        if number in BOSS_ART and base == BOSS_NAMES[(number - 1) % len(BOSS_NAMES)]:
            return BOSS_ART[number]
    return None


def regular_enemy_kind(name):
    """Exact generated-name parsing; authored boss titles keep their own artwork."""
    base, _ = _name_parts(canonical_enemy_name(name))
    if base in KIND_ART:
        return base
    for prefix in ENEMY_PREFIXES:
        if base.startswith(prefix+' '):
            tail = base[len(prefix)+1:]
            for kind in ENEMY_KINDS:
                if tail.startswith(kind) and tail[len(kind):] in ENEMY_SUFFIXES:
                    return kind
    return None

UNLOCK_LEVEL = 50

def entries(language='de'):
    rows=[]
    for name in ENEMY_KINDS:
        rows.append(dict(name=name,category='Gegnertypen',art_name='Schatten '+name,
            details='Zufallskampf und Kampfarena · Leicht, normal oder schwer.\nAuch in passenden Dungeons anzutreffen.\n'
            'Schwäche: wird im Kampf bestimmt und kann wechseln.\n'
            'KP, Schaden und Belohnung hängen vom Spielstand und der Schwierigkeit ab.\n\n'
            'Namensvarianten: '+', '.join(ENEMY_PREFIXES)+'.\n'
            'Beispiel: Schatten '+name+' der Dissonanz.'))
    bosses = [f'{BOSS_NAMES[(i-1)%len(BOSS_NAMES)]} #{i}' for i in range(1, CAMPAIGN_BOSS_COUNT+1)]
    for category,names in [('Bosse',bosses),('Finalgegner',FINAL_NAMES)]:
        for i,name in enumerate(names,1):
            motif = BOSS_MOTIFS.get(i) if category == 'Bosse' else None
            rows.append(dict(name=name,category=category,art_name=name,form_index=i,details=
                (f'Boss {i}/{CAMPAIGN_BOSS_COUNT} · Eigene Kampfgestalt.' if category=='Bosse' else 'Finalform '+str(i)+' · Ein Sieg bringt ein Prinzip zurück.')+
                ('\nÄgyptisches Motiv: '+motif[0]+'.' if motif else '')+
                '\n\nSchwäche: auf die aktuelle Anzeige im Kampf achten; sie kann wechseln.\n'
                'KP und Schaden skalieren mit dem Spielstand.\nSpezialangriffe und Phasen werden im Kampf angekündigt.'))
    if language == 'en':
        for row in rows:
            row['name'] = enemy_display_name(row['name'], language)
            if row['category'] == 'Gegnertypen':
                row['details'] = ('Random encounters and battle arena · Easy, normal or hard.\nAlso found in suitable dungeons.\n'
                    'Weakness: determined in battle and may change.\n'
                    'HP, damage and rewards depend on progression and difficulty.\n\n'
                    'Name variants: '+', '.join(PREFIXES_EN)+'.\n'
                    'Example: '+enemy_display_name(row['art_name']+' der Dissonanz',language)+'.')
            else:
                index = row['form_index']
                motif = BOSS_MOTIFS.get(index) if row['category'] == 'Bosse' else None
                row['details'] = ((f'Boss {index}/{CAMPAIGN_BOSS_COUNT} · Unique battle form.'
                    if row['category'] == 'Bosse' else f'Final form {index} · A victory restores one principle.')+
                    ('\nEgyptian motif: '+motif[1]+'.' if motif else '')+
                    '\n\nWeakness: watch the current battle hint; it may change.\n'
                    'HP and damage scale with progression.\nSpecial attacks and phases are announced in battle.')
    for row in rows:
        if row['category'] == 'Gegnertypen':
            kind = regular_enemy_kind(row['art_name'])
            label = EFFECT_LABELS[ENEMY_EFFECTS.get(KIND_ART[kind], 'slash')][language == 'en']
            row['details'] += ('\n\nAttack animation: ' if language == 'en' else '\n\nAngriffsanimation: ') + label + '.'
    return rows
