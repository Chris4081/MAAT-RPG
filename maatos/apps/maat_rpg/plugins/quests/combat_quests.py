"""Combat milestones read only recorded victories; no demo or inferred kills."""
from shared.core.dungeon_campaign import NAMES


COMBAT_QUESTS = []


def _add(identifier, name, desc, key, target, level, xp, category, en_name, en_desc,
         requires_combat=False):
    COMBAT_QUESTS.append(dict(
        id=identifier, name=name, desc=desc, type='counter', counter_key=key,
        target=target, minimum_level=level, level_tier=level // 2, reward_xp=xp,
        quest_category=category, requires_combat=requires_combat,
        en_name=en_name, en_desc=en_desc,
    ))


for source, targets, names, english_names in (
    ('arena', (5, 20, 50, 100),
     ('Sand unter den Füßen', 'Bewährter Arenakämpfer', 'Die Arena erinnert sich', 'Meister des Sandkreises'),
     ('Feet in the Sand', 'Proven Arena Fighter', 'The Arena Remembers', 'Master of the Sand Circle')),
    ('random', (5, 15, 40, 80),
     ('Wachsam auf dem Weg', 'Zwischen den Schatten', 'Unbeirrbarer Wanderer', 'Wächter der freien Wege'),
     ('Watchful on the Road', 'Among the Shadows', 'Steadfast Wanderer', 'Guardian of the Open Roads')),
):
    place = 'der Kampfarena' if source == 'arena' else 'Zufallsbegegnungen im Chat'
    en_place = 'the arena' if source == 'arena' else 'random chat encounters'
    for i, (target, level, xp) in enumerate(zip(targets, (8, 16, 30, 50), (120, 260, 520, 900))):
        _add(f'combat_{source}_{target}', names[i],
             f'Gewinne insgesamt {target} normale Kämpfe in {place}. Bereits gespeicherte Siege zählen mit; Bosse, Dungeons und die Demo zählen hier nicht.',
             f'{source}_wins', target, level, xp, 'combat', english_names[i],
             f'Win {target} normal battles in {en_place} in total. Recorded wins count; bosses, dungeons and the demo do not.', True)

for target, level, xp, name, en_name in (
    (1, 10, 200, 'Das erste gebrochene Siegel', 'The First Broken Seal'),
    (3, 20, 420, 'Drei Schatten weichen', 'Three Shadows Recede'),
    (5, 35, 750, 'Die fünf Prüfungen', 'The Five Trials'),
    (10, 50, 1300, 'Jenseits der ersten Legende', 'Beyond the First Legend'),
):
    _add(f'combat_boss_{target}', name,
         f'Besiege insgesamt {target} reguläre Bosse. Es zählt der gespeicherte Boss-Siegzähler; Dungeon-Hüter, Finalkämpfe und die Demo sind eigene Prüfungen.',
         'boss_wins', target, level, xp, 'combat', en_name,
         f'Defeat {target} regular bosses in total. Uses recorded boss victories; dungeon guardians, finale battles and the demo are separate trials.', True)

EN_DUNGEONS = (
    'Gate of 60 Voices', 'Crystal Vault', 'Depths of a Thousand Echoes',
    'Gardens of Harmony', 'Scales of the Sunken City', 'Forge of Creation',
    'Bridges of Connection', 'Hall of Respect', 'Heart of the Five Principles',
)
for index, (name, en_name) in enumerate(zip(NAMES, EN_DUNGEONS)):
    level = 10 + 5 * index
    for clears, title, en_title, xp in (
        (1, 'Die fünf Zeichen', 'The Five Signs', 140 + level * 8),
        (3, 'Vertraute Tiefe', 'Familiar Depths', 240 + level * 12),
    ):
        _add(f'dungeon_{index}_clears_{clears}', f'{title} · {name}',
             f'Bezwinge „{name}“ insgesamt {clears}-mal. Ein Abschluss zählt erst nach allen fünf gewonnenen Kämpfen eines Durchlaufs. Abbrüche zählen nicht; frühere gespeicherte Abschlüsse bleiben gültig.',
             f'dungeon_clear:{index}', clears, level, xp, 'dungeon', f'{en_title} · {en_name}',
             f'Complete “{en_name}” {clears} times in total. A clear requires all five victories in one run. Aborted runs do not count; recorded clears remain valid.')

for key, target, level, xp, name, en_name in (
    ('dungeon_clears', 5, 20, 400, 'Rückkehr mit fünf Siegeln', 'Returning with Five Seals'),
    ('dungeon_clears', 15, 40, 1000, 'Kartograf der Tiefe', 'Cartographer of the Depths'),
    ('dungeon_unique', 3, 20, 500, 'Drei Wege unter Terra', 'Three Paths beneath Terra'),
    ('dungeon_unique', 9, 50, 1500, 'Alle Tore stehen offen', 'Every Gate Stands Open'),
):
    unique = key == 'dungeon_unique'
    desc = (f'Schließe {target} verschiedene Dungeons vollständig ab. Jeder Ort zählt einmal.' if unique
            else f'Schließe insgesamt {target} Dungeon-Durchläufe ab. Wiederholte Abschlüsse desselben Ortes zählen mit.')
    en_desc = (f'Fully clear {target} different dungeons. Each location counts once.' if unique
               else f'Complete {target} dungeon runs in total. Repeated clears of the same location count.')
    _add(f'{key}_{target}', name, desc + ' Dungeon+ zählt separat.', key, target, level, xp,
         'dungeon', en_name, en_desc + ' Dungeon+ is counted separately.')

for target, xp, name, en_name in (
    (5, 300, 'Unter dem letzten Siegel', 'Beneath the Last Seal'),
    (10, 500, 'Zehn Kreise tiefer', 'Ten Circles Deeper'),
    (20, 800, 'Atem der endlosen Tiefe', 'Breath of the Endless Depths'),
    (35, 1200, 'Standhaft im Dunkel', 'Steadfast in the Dark'),
    (50, 1700, 'Licht jenseits der fünfzigsten Welle', 'Light beyond the Fiftieth Wave'),
):
    _add(f'dungeon_plus_wave_{target}', name,
         f'Gewinne in Dungeon+ mindestens {target} Wellen in einem einzigen Durchlauf. Es zählt dein gespeicherter Rekord, nicht nur das Betreten der Welle.',
         'dungeon_plus_best', target, 50, xp, 'dungeon_plus', en_name,
         f'Win at least {target} Dungeon+ waves in a single run. Uses your saved victory record, not merely entering a wave.')
_add('dungeon_plus_total_100', 'Hundert Echos der Tiefe',
     'Gewinne insgesamt 100 Wellen in Dungeon+. Siege aus mehreren Durchläufen zählen zusammen; eine spätere Flucht löscht sie nicht.',
     'dungeon_plus_wins', 100, 50, 2200, 'dungeon_plus', 'A Hundred Echoes of the Depths',
     'Win 100 Dungeon+ waves in total. Victories across several runs add up; fleeing later does not erase them.')


def progress_counters(root):
    """Old profiles need no migration or guessed encounter history."""
    def count(value):
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError, OverflowError):
            return 0

    stats = root.get('stats') or {}
    counters = {key: count(stats.get(key)) for key in ('arena_wins', 'random_wins', 'boss_wins')}
    runs = root.get('dungeon_runs') or {}
    clears = {str(key): count(record.get('completed')) for key, record in runs.items() if isinstance(record, dict)}
    counters.update({f'dungeon_clear:{key}': value for key, value in clears.items()})
    for index in range(len(NAMES)):
        counters.setdefault(f'dungeon_clear:{index}', 0)
    counters['dungeon_clears'] = sum(clears.values())
    counters['dungeon_unique'] = sum(value > 0 for value in clears.values())
    plus = root.get('dungeon_plus') or {}
    counters['dungeon_plus_best'] = count(plus.get('best_wave'))
    counters['dungeon_plus_wins'] = count(plus.get('total_wins'))
    return counters
