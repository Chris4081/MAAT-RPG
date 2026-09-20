"""Class talent trees, earned points and combat effects from the current profile.

Points are derived from level and unique completed, non-repeatable combat quests.
Only purchased ranks are persisted: snapshots/restarts cannot award points twice.
"""
from shared.core.hero_classes import CLASSES, selected_class, _commit
from shared.core.progression_i18n import tr

MAX_RANK = 3
TIERS = ((1, 0, 1), (10, 1, 2), (25, 4, 3), (40, 8, 4))
EFFECTS = {
    'attack': ('Prinzipien-Schaden', '%'), 'skill': ('Skill-Schaden', '%'),
    'impulse': ('Impuls-Schaden', '%'), 'crit': ('Krit-Chance', ' Prozentpunkte'),
    'reduction': ('Weniger erlittener Schaden', '%'),
    'focus_heal': ('Fokus-Heilung', '%'), 'focus_guard': ('Fokus-Schild', '%'),
    'start_guard': ('Startschild aus maximalen KP', '%'),
    'start_resonance': ('Startresonanz', ''), 'resonance': ('Resonanz je Aufladung', ''),
    'weakness': ('Zusatzschaden bei Schwachstellentreffern', '%'),
}
# Each class has three connected paths; each row is name + effect per rank.
TREES = {
 'robo': [
  ('Technik', '⚙', [('Servoantrieb', {'attack':3}), ('Zieloptik', {'crit':1}),
    ('Präzisionsmodul', {'skill':4}), ('Überladung', {'attack':3,'skill':4})]),
  ('Panzerung', '◇', [('Schutzplatte', {'start_guard':2}), ('Stahlkern', {'reduction':2}),
    ('Schildgenerator', {'focus_guard':8}), ('Titanherz', {'reduction':2,'start_guard':2})]),
  ('Reaktor', '✦', [('Zündfunke', {'start_resonance':5}), ('Energiekreislauf', {'resonance':1}),
    ('Impulsverstärker', {'impulse':5}), ('Selbstwartung', {'focus_heal':6,'resonance':1})]),
 ],
 'engelchen': [
  ('Flügelwind', '✧', [('Leichter Flug', {'crit':2}), ('Lichtfeder', {'attack':3}),
    ('Himmlischer Blick', {'weakness':4}), ('Sonnenflug', {'attack':3,'crit':1})]),
  ('Schutzengel', '◇', [('Federkleid', {'reduction':1}), ('Flügelschild', {'start_guard':2}),
    ('Schützende Schwingen', {'focus_guard':8}), ('Himmelswacht', {'reduction':2,'start_guard':2})]),
  ('Hoffnung', '✦', [('Sanfter Trost', {'focus_heal':5}), ('Morgenlicht', {'start_resonance':5}),
    ('Mutiges Herz', {'resonance':1}), ('Sternensegen', {'impulse':5,'focus_heal':4})]),
 ],
 'magier': [
  ('Arkanes Wissen', '✧', [('Runenkunde', {'skill':4}), ('Zauberfunke', {'attack':3}),
    ('Schwächen lesen', {'weakness':4}), ('Erzmagier', {'skill':5,'attack':2})]),
  ('Resonanzmagie', '✦', [('Kristallspeicher', {'start_resonance':5}), ('Ätherfluss', {'resonance':1}),
    ('Sternensturm', {'impulse':6}), ('Resonanznova', {'impulse':5,'resonance':1})]),
  ('Schutzrunen', '◇', [('Runenmantel', {'start_guard':2}), ('Schutzkreis', {'focus_guard':8}),
    ('Ätherhaut', {'reduction':1}), ('Lebende Rune', {'reduction':2,'focus_heal':4})]),
 ],
 'priester': [
  ('Heilkunde', '✧', [('Ruhiger Atem', {'focus_heal':6}), ('Andacht', {'focus_guard':8}),
    ('Heilendes Licht', {'focus_heal':8}), ('Quell des Lebens', {'focus_heal':6,'reduction':1})]),
  ('Tempelwacht', '◇', [('Weihesiegel', {'start_guard':2}), ('Standhaftigkeit', {'reduction':2}),
    ('Heiliger Schutz', {'focus_guard':10}), ('Hüter von Terra', {'reduction':2,'start_guard':2})]),
  ('Lichtpfad', '✦', [('Lichtstab', {'attack':3}), ('Wahrhaftiger Blick', {'weakness':4}),
    ('Morgengebet', {'start_resonance':5}), ('Urlicht', {'impulse':6,'skill':4})]),
 ],
 'puppy': [
  ('Wildfang', '✧', [('Spielbiss', {'attack':3}), ('Wache Ohren', {'crit':2}),
    ('Spürnase', {'weakness':3}), ('Wilder Wirbel', {'attack':3,'crit':1})]),
  ('Flinke Pfoten', '◇', [('Pfotenarbeit', {'reduction':2}), ('Deckung suchen', {'focus_guard':6}),
    ('Flauschpanzer', {'start_guard':2}), ('Unermüdlich', {'reduction':2,'start_guard':2})]),
  ('Treues Herz', '✦', [('Verschnaufpause', {'focus_heal':6}), ('Freudensprung', {'start_resonance':5}),
    ('Rudelgefühl', {'resonance':1}), ('Herz von MAAT', {'skill':5,'impulse':5})]),
 ],
}


def count(value):
    return max(0, value) if isinstance(value, int) and not isinstance(value, bool) else 0


def grants_quest_point(quest):
    if not isinstance(quest, dict) or not isinstance(quest.get('id'), str) or not quest['id']:
        return False
    if quest.get('daily_reset') or quest.get('repeatable') or quest.get('type') == 'daily_streak':
        return False
    key = str(quest.get('counter_key', ''))
    return (quest.get('quest_category') in ('combat', 'dungeon', 'dungeon_plus')
            or quest.get('type') == 'battle_win'
            or key in ('battle_wins', 'fights_won', 'fights_total', 'fights',
                       'arena_wins', 'random_wins', 'boss_wins', 'final_wins')
            or key.startswith('dungeon_'))


def catalog(class_id, language='de'):
    entries = []
    for branch, (title, icon, nodes) in enumerate(TREES.get(class_id, [])):
        for tier, (name, effects) in enumerate(nodes):
            level, quests, cost = TIERS[tier]
            entries.append(dict(id=f'{class_id}:{branch}:{tier}', name=tr(name,language), effects=effects,
                branch=branch, branch_name=tr(title,language), icon=icon, tier=tier, level=level,
                quests=quests, cost=cost, max_rank=MAX_RANK,
                requires=f'{class_id}:{branch}:{tier-1}' if tier else None))
    return entries


def effect_text(effects, language='de'):
    return ' · '.join(f'+{value:g}{tr(EFFECTS[key][1],language)} {tr(EFFECTS[key][0],language)}'
                      for key, value in effects.items() if value)


def snapshot(state, language='de'):
    class_id = selected_class(state)
    unlocked = class_id in CLASSES
    level = max(1, count(state.get('player', {}).get('level', 1)))
    completed = state.get('quests', {}).get('completed', [])
    quest_ids = {q['id'] for q in completed if grants_quest_point(q)}
    earned = level + len(quest_ids) if unlocked else 0
    hero = state.get('hero_class')
    record = hero.get('talents', {}) if isinstance(hero, dict) else {}
    saved = record.get('ranks', {}) if isinstance(record, dict) else {}
    saved = saved if isinstance(saved, dict) else {}
    nodes = catalog(class_id, language)
    ranks, spent = {}, 0
    for node in nodes:
        rank = min(MAX_RANK, count(saved.get(node['id'])))
        valid = (level >= node['level'] and len(quest_ids) >= node['quests']
                 and (not node['requires'] or ranks.get(node['requires'], 0) >= 2))
        if valid and spent + rank*node['cost'] <= earned:
            ranks[node['id']] = rank
            spent += rank*node['cost']
    bonuses = {}
    for node in nodes:
        rank = ranks.get(node['id'], 0)
        reasons = []
        if level < node['level']: reasons.append(f"Level {node['level']}")
        if len(quest_ids) < node['quests']: reasons.append(tr('Kampfquests {done}/{target}',language,done=len(quest_ids),target=node['quests']))
        if node['requires'] and ranks.get(node['requires'], 0) < 2:
            reasons.append(tr('Vorgänger auf Rang 2',language))
        if earned-spent < node['cost']: reasons.append(tr('{cost} Talentpunkte',language,cost=node['cost']))
        node.update(rank=rank, description=tr('{effect} pro Rang',language,effect=effect_text(node['effects'],language)),
                    can_buy=rank < MAX_RANK and not reasons,
                    reason=tr('Ausgebaut',language) if rank == MAX_RANK else ' · '.join(reasons))
        for key, value in node['effects'].items():
            bonuses[key] = bonuses.get(key, 0) + value*rank
    return dict(unlocked=unlocked, class_id=class_id, class_name=tr(CLASSES.get(class_id, ('Maatis Normal',))[0],language),
                level=level, quest_points=len(quest_ids), level_points=level if unlocked else 0,
                earned=earned, spent=spent, available=earned-spent, nodes=nodes,
                bonuses=bonuses, bonus_text=effect_text(bonuses,language), ranks=ranks)


def buy(store, identifier, *, expected_rank, class_id, language='de'):
    data = snapshot(store.state, language)
    if not data['unlocked'] or class_id != data['class_id']:
        raise ValueError(tr('Wähle zuerst deine Klasse; die Talente gehören zu diesem Profil.',language))
    node = next((n for n in data['nodes'] if n['id'] == identifier), None)
    if node is None: raise ValueError(tr('Dieses Talent gehört nicht zu deiner Klasse.',language))
    if type(expected_rank) is not int or expected_rank != node['rank']:
        raise ValueError(tr('Der Talentrang hat sich geändert. Bitte erneut auswählen.',language))
    if not node['can_buy']: raise ValueError(node['reason'])
    ranks = dict(data['ranks'])
    ranks[identifier] = node['rank']+1
    _commit(store, lambda record: record.update(talents={'version': 1, 'ranks': ranks}))
    return tr('{name} · Rang {rank}/{max_rank} gelernt · −{cost} Talentpunkte',language,name=node['name'],rank=node['rank']+1,max_rank=MAX_RANK,cost=node['cost'])


def combat_bonuses(state, context=None):
    if (context or {}).get('title_demo_mode') or (context or {}).get('guide_mode') or (context or {}).get('combat_source') == 'demo':
        return {}
    return snapshot(state)['bonuses']


def amplify(amount, bonuses, key):
    return max(0, round(amount * (1 + bonuses.get(key, 0)/100)))


def reduce_damage(amount, turn_state):
    if amount <= 0: return 0
    reduction = min(40, turn_state.get('talents', {}).get('reduction', 0))
    return max(1, round(amount*(1-reduction/100)))


def begin_fight(state, turn_state, context=None):
    bonuses = combat_bonuses(state, context)
    turn_state['talents'] = bonuses
    turn_state['guard'] = turn_state.get('guard', 0) + round(state['player']['max_hp']*bonuses.get('start_guard', 0)/100)
    turn_state['resonance'] = min(100, turn_state.get('resonance', 0)+bonuses.get('start_resonance', 0))
    return bonuses
