"""Highscore rules for validated arcade runs; lower is better for puzzles."""
SCORE_UNITS={'snake':'Früchte','breakout':'Siegel','temple_circles':'Tempelsiegel','reflex':'Sterne','memory':'Paarversuche','mines':'Klicks','lights':'Züge','slide':'Züge','maze':'Schritte','sokoban':'Schritte','four':'Züge','three':'Züge','wheel':'Glückstreffer'}
from shared.core.minigames import ENDLESS_GAMES
from shared.core.maat_games import INFO
SCORE_UNITS.update({k:'Züge' for k in INFO})
SCORE_UNITS.update(snake_walls='Früchte',maat_snake='Runen',maat_coil='Bünde')
ENDLESS=ENDLESS_GAMES

def update_highscore(data,kind,game,won):
    records=data.setdefault('highscores',{})
    old=records.get(kind)
    if kind=='wheel':
        if not won:return False
        value=int(old['value'])+1 if old else 1
    elif kind in ENDLESS:
        value=game.hits if kind=='reflex' else game.score
        if value<=0 or (old and value<=old['value']):return False
    else:
        if not won:return False
        value=game.attempts if kind in ('memory','lights','slide') else game.steps
        if old and value>=old['value']:return False
    records[kind]={'value':value}
    return True

def record_text(kind,record,language='de'):
    from .minigame_i18n import tr
    rule='mehr ist besser' if kind in ENDLESS else 'gesammelte Gewinne' if kind=='wheel' else 'weniger ist besser · nur Siege'
    value=f"{record['value']} {tr(SCORE_UNITS[kind],language)}" if record else tr('Noch kein Eintrag',language)
    return tr('🏆 Bestleistung: {value}\n{rule}',language,value=value,rule=tr(rule,language))
