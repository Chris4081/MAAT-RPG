"""Terra's route is derived from the real story and battle counters.

No parallel XP/win ledger: random victories advance two half-steps, arena
victories one. Boss defeats retreat five fields; final defeats restart ten.
"""
from functools import lru_cache
import json
from pathlib import Path
from .monster_catalog import BOSS_NAMES, FINAL_NAMES

REGIONS = ('Die Waage der Wüste', 'Gärten der Schöpfung', 'Kristallküste der Resonanz',
           'Sternengebirge des Äons', 'Das Licht von Terra')
CAMPAIGN_SOURCES = {'arena', 'random'}
GOAL = 20
BOSS_RETREAT = 10  # Five map fields, represented by ten arena half-steps.


def localized_snapshot(data, language='de'):
    """Translate presentation only; geometry, opponent IDs and counters stay canonical."""
    if language != 'en':
        return dict(data)
    from .gameplay_i18n import tr
    from .monster_catalog import enemy_display_name
    result=dict(data)
    for key in ('title','subtitle','progress','hint'):
        result[key]=tr(data.get(key,''),language)
    result['regions']=[tr(name,language) for name in data.get('regions',REGIONS)]
    result['goal']=tr(enemy_display_name(data.get('goal',''),language),language)
    position=f"{float(data.get('position',0)):g}"
    kind=data.get('kind')
    if kind=='intro':
        result['progress']=tr('{position}/{end} Nachrichten',language,position=position,end=data['steps'])
    elif kind=='battle':
        boss=int(data['bosses'])+1
        result['subtitle']=tr('Weg zu Boss {boss}/25 · Abschnitt {section}/5',language,boss=boss,section=(boss-1)%5+1)
        result['progress']=(tr('{position}/10 Felder',language,position=position) if data['position']<data['steps']
                            else tr('Boss {boss} bereit',language,boss=boss))
    elif kind=='final':
        final=max(1,int(data['bosses'])//5)
        result['subtitle']=tr('Finaletor {final} · {goal}',language,final=final,goal=result['goal'])
        result['progress']=(tr('{position}/10 Felder · Final-Rückweg',language,position=position)
                            if data.get('retry') and data['position']<data['steps']
                            else tr('Finale {final}/5 bereit',language,final=final))
    return result


def number(value, default=0):
    try: return max(0,int(value))
    except (ValueError,TypeError,OverflowError): return default


@lru_cache(maxsize=1)
def intro_milestones():
    path = Path(__file__).resolve().parents[2]/'apps/maat_rpg/plugins/story_loader/stories/config.json'
    try:
        entries = json.loads(path.read_text(encoding='utf-8'))['stories']
        counts = {number(e['id']):number(e.get('trigger',{}).get('messages')) for e in entries
                  if e.get('trigger',{}).get('type') == 'message_count'}
        end = counts.get(3) or 30
        return end, tuple(sorted({0,end,*(v for k,v in counts.items() if k<=3 and 0<v<=end)}))
    except (OSError,ValueError,KeyError,TypeError):
        return 30,(0,1,10,30)


def pending_final(state):
    stats=state.get('stats',{})
    bosses=number(stats.get('boss_wins'))
    finals=number(stats.get('final_wins'))
    return bosses//5 if bosses and bosses%5==0 and finals<bosses//5 else 0


def next_fight_type(state):
    # The restored world has no sixth finale or automatic twenty-sixth boss.
    # Explicit map replays are selected separately by the encounter caller.
    if number(state.get('stats',{}).get('final_wins'))>=5:
        return 'normal'
    final = pending_final(state)
    progress = number(state.get('stats',{}).get('boss_progress'))
    retry = number(state.get('world',{}).get('final_retry'))
    if final:
        return 'normal' if retry==final and progress<GOAL else 'final'
    return 'boss' if progress>=GOAL else 'normal'


def reset_after_defeat(state, fight_type, context):
    context=context or {}
    if (fight_type not in {'boss','final'} or context.get('combat_source') not in CAMPAIGN_SOURCES
            or context.get('guide_mode') or context.get('title_demo_mode') or context.get('terra_replay')):
        return False
    stats=state.setdefault('stats',{})
    stats['boss_progress']=(max(0,min(GOAL,number(stats.get('boss_progress')))-BOSS_RETREAT)
                            if fight_type=='boss' else 0)
    world=state.setdefault('world',{})
    world['journey_setbacks']=number(world.get('journey_setbacks'))+1
    if fight_type=='final':
        world['final_retry']=pending_final(state) or number(state['stats'].get('final_wins'))+1
    return True


def finish_final_retry(state, context):
    if (context or {}).get('combat_source') not in CAMPAIGN_SOURCES:
        return
    world=state.setdefault('world',{})
    if world.pop('final_retry',0):
        stats=state.setdefault('stats',{})
        stats['boss_progress']=max(0,number(stats.get('boss_progress'))-GOAL)


def snapshot(state, story=None):
    state=state or {};stats=state.get('stats',{});world=state.get('world',{})
    boss_wins=number(stats.get('boss_wins')); final_wins=number(stats.get('final_wins'))
    result=dict(bosses=min(25,boss_wins),finals=min(5,final_wins),regions=list(REGIONS),
                setbacks=number(world.get('journey_setbacks')),checkpoint=number(world.get('last_boss_checkpoint')))
    if not world.get('combat_unlocked'):
        end,checkpoints=intro_milestones()
        messages=number((story or {}).get('messages_total',stats.get('messages_total',0)))
        position=min(end,messages)
        return dict(result,id='awakening',kind='intro',region=0,route=0,title='Das Erwachen in Terra',
            subtitle='Bibliothek · Oase · Tempel des Kampfes',steps=end,position=position,
            checkpoints=list(checkpoints),goal='Kampf-Einführung',
            progress=f'{position}/{end} Nachrichten',
            hint='Schließe die Kampf-Einführung ab.' if position==end else 'Jede Chatnachricht trägt Maatis ein Feld weiter.')
    if final_wins>=5:
        from .terra_replay import targets, pending
        return dict(result,id='terra-restored',kind='complete',region=4,route=31,
            title='Terra erinnert sich',subtitle='Alle fünf Finalgegner sind besiegt.',
            steps=10,position=10,checkpoints=[0,10],goal='Licht der MAAT',
            progress='5/5 Finale · Reise vollendet',hint='Öffne die große Karte und wähle einen Boss für einen weiteren Kampf.',
            replay_targets=targets(), replay_pending=pending(state))
    final=pending_final(state)
    retry=number(world.get('final_retry'))==final if final else False
    region=min(4,(boss_wins-1)//5 if final else boss_wins//5)
    points=min(GOAL,number(stats.get('boss_progress')))
    if final:
        position=points/2 if retry else 10
        goal=FINAL_NAMES[(final-1)%len(FINAL_NAMES)]
        progress=(f'{position:g}/10 Felder · Final-Rückweg' if retry and points<GOAL else f'Finale {final}/5 bereit')
        hint=('Nach der Niederlage: 10 Zufallssiege oder 20 Arenasiege bis zum erneuten Finalversuch.'
              if retry else 'Fünf Bosse bezwungen: Das Finaletor ist geöffnet.')
        return dict(result,id=f'final-{final}',kind='final',region=region,route=final*6,
            title=REGIONS[region],subtitle=f'Finaletor {final} · {goal}',steps=10,
            position=position,checkpoints=[0,10],goal=goal,progress=progress,hint=hint,retry=retry)
    boss=boss_wins+1
    goal=f'{BOSS_NAMES[(boss-1)%len(BOSS_NAMES)]} #{boss}'
    position=points/2
    return dict(result,id=f'boss-{boss}',kind='battle',region=region,route=boss+final_wins,
        title=REGIONS[region],subtitle=f'Weg zu Boss {boss}/25 · Abschnitt {(boss-1)%5+1}/5',
        steps=10,position=position,checkpoints=[0,5,10],goal=goal,
        progress=f'{position:g}/10 Felder' if points<GOAL else f'Boss {boss} bereit',
        hint='1 Zufallssieg = 1 Feld · 2 Arenasiege = 1 Feld. Boss-Niederlage: 5 Felder zurück. Dungeons sind eigene Expeditionen.')
