"""Persistent optional challenges and deterministic minigame replay validation."""
import random
import secrets
from shared.core.maat_coil import StarCoil, migrate_classic_snake
from shared.core.temple_circles import TempleCircles, migrate_temple_blocks

DIRECTIONS = {'R':(1,0),'L':(-1,0),'U':(0,-1),'D':(0,1)}

class Snake:
    endless=False
    width=20
    height=16
    target=15
    def __init__(self, seed):
        self.rng=random.Random(seed)
        self.body=[(5,8),(4,8),(3,8)]
        self.direction='R'
        self.score=0
        self.over=False
        self.moves=[]
        self.place_food()

    def place_food(self):
        self.food=self.rng.choice([(x,y) for y in range(self.height) for x in range(self.width) if (x,y) not in self.body])

    def step(self, direction):
        if self.over:return
        dx,dy=DIRECTIONS[direction]
        old=DIRECTIONS[self.direction]
        if (dx,dy)==(-old[0],-old[1]):direction=self.direction;dx,dy=old
        self.direction=direction
        self.moves.append(direction)
        head=(self.body[0][0]+dx,self.body[0][1]+dy)
        eating=head==self.food
        if not (0<=head[0]<self.width and 0<=head[1]<self.height) or head in (self.body if eating else self.body[:-1]):
            self.over=True;return
        self.body.insert(0,head)
        if eating:
            self.score+=1
            if self.score==self.target and not self.endless:self.over=True
            else:
                if len(self.body)==self.width*self.height-len(getattr(self,'walls',())):
                    self.body=[(5,8),(4,8),(3,8)];self.direction='R'
                self.place_food()
        else:self.body.pop()
        if not self.endless and len(self.moves)>=10000:self.over=True


class TempleSnake(Snake):
    def __init__(self,seed,maat=False):
        self.maat=maat
        self.walls=set() if maat else {(x,y) for x in (8,14) for y in range(3,13) if y not in (7,8)}
        self.decoys={}
        super().__init__(seed)
    def place_food(self):
        free=[(x,y) for y in range(self.height) for x in range(self.width) if (x,y) not in self.body and (x,y) not in self.walls]
        self.food=self.rng.choice(free);self.decoys={}
        if self.maat:
            free.remove(self.food)
            for rune,cell in zip([r for r in 'HBSVR' if r!='HBSVR'[self.score%5]],self.rng.sample(free,min(4,len(free)))):self.decoys[cell]=rune
    def step(self,direction):
        if self.over:return
        old=DIRECTIONS[self.direction];delta=DIRECTIONS[direction]
        if delta==(-old[0],-old[1]):delta=old;direction=self.direction
        head=(self.body[0][0]+delta[0],self.body[0][1]+delta[1])
        if head in self.walls or head in self.decoys:
            self.moves.append(direction);self.over=True;return
        super().step(direction)
        if not self.over and len(self.body)==self.width*self.height-len(self.walls):
            self.body=[(5,8),(4,8),(3,8)];self.direction='R';self.place_food()


CATALOG={
    'maat_coil':('✦ MAAT-Snake · Sternenbund','3 Bünde: fünf Schreine aktivieren und zum Mittelpunkt zurückkehren',40,15),
    'breakout':('🧱 Siegelbrecher','40 Siegel mit 3 Leben zerstören',60,20),
    'temple_circles':('◎ MAAT · Tempelkreise','10 Tempelsiegel: drei Runenringe ausrichten und aktivieren',80,25),
}

from shared.core.arcade_extra import INFO
CATALOG.update(INFO)
from shared.core.maat_games import INFO as MAAT_INFO
CATALOG.update({'snake_walls':('🐍 Tempelmauer-Snake','15 Früchte zwischen Tempelmauern sammeln',65,25),'maat_snake':('✦ MAAT-Snake','15 Runen in der Reihenfolge H → B → S → V → R sammeln',75,30)})
CATALOG.update(MAAT_INFO)

SNAKE_GAMES={'snake','snake_walls','maat_snake'}
ENDLESS_GAMES=(SNAKE_GAMES-{'snake'})|{'maat_coil','breakout','temple_circles','reflex'}

def engine(kind,seed,practice=False):
    from shared.core.arcade import Breakout
    if kind=='maat_coil':game=StarCoil(seed)
    elif kind=='temple_circles':game=TempleCircles(seed)
    elif kind in MAAT_INFO:
        from shared.core.maat_games import MaatGame
        game=MaatGame(kind,seed)
    elif kind in ('snake_walls','maat_snake'):game=TempleSnake(seed,maat=kind=='maat_snake')
    elif kind in INFO:
        from shared.core.arcade_extra import TempleGame
        game=TempleGame(kind,seed)
    else:game={'snake':Snake,'breakout':Breakout}[kind](seed)
    game.endless=practice and kind in ENDLESS_GAMES|{'snake'}
    return game

def offer(state):
    migrate_classic_snake(state)
    migrate_temple_blocks(state)
    count=int(state.get('quests',{}).get('meta',{}).get('messages_total',0))
    data=state.setdefault('minigames',{'last_offer':0,'serial':0,'pending':None})
    if 'discovered' not in data:
        # Older saves offered the original three games in a fixed rotation.
        data['discovered']=list(('maat_coil','breakout','temple_circles')[:min(3,int(data.get('serial',0)))])
    discovered=data['discovered']
    existing=data.get('pending')
    if existing and existing.get('game') in CATALOG and existing['game'] not in discovered:
        discovered.append(existing['game'])
    combat=bool(state.get('world',{}).get('combat_unlocked'))
    # On the transition, start a full 30-message interval; no immediate double drop.
    if combat and not data.get('combat_seen'):
        data['combat_seen']=True
        data['combat_anchor']=count
    due=15 if not data['serial'] else max(data['last_offer'],data.get('combat_anchor',0))+ (30 if combat else 5)
    if count>=due and not data['pending']:
        data['serial']+=1
        data['last_offer']=count
        kind=secrets.choice([k for k in CATALOG if k not in discovered] or list(CATALOG))
        data['pending']={'id':data['serial'],'seed':secrets.randbits(32),'game':kind}
        if kind not in discovered:discovered.append(kind)
    return dict(unlocked=count>=15,pending=data['pending'],discovered=list(discovered),highscores=dict(data.get('highscores',{})))


def begin_attempt(core, challenge_id):
    migrate_classic_snake(core.state)
    migrate_temple_blocks(core.state)
    pending=core.state.get('minigames',{}).get('pending')
    if not pending or pending['id']!=challenge_id or pending.get('attempts',0)>=2:
        return None
    pending['attempts']=pending.get('attempts',0)+1
    pending['ticket']=secrets.token_hex(16)
    core.save()  # Reserve before opening the game, including across process restarts.
    return dict(pending)


def resolve(core, challenge_id, moves=None, skip=False, ticket=None):
    migrate_classic_snake(core.state)
    migrate_temple_blocks(core.state)
    data=core.state.setdefault('minigames',{})
    pending=data.get('pending')
    if not pending or pending['id']!=challenge_id:return 'Diese Herausforderung ist nicht mehr offen.'
    won=False
    if not skip:
        if not ticket or pending.get('ticket')!=ticket:return 'Dieser Versuch ist nicht mehr gültig.'
        # Each issued ticket can be submitted only once, even after a failed run.
        pending.pop('ticket',None)
        won=valid_win(pending['game'],pending['seed'],moves)
    exhausted=pending.get('attempts',0)>=2
    if skip or won or exhausted:
        data['pending']=None
        data['last_offer']=int(core.state.get('quests',{}).get('meta',{}).get('messages_total',0))
    if won:
        record_win(data,pending['game'],chat=True,first_try=pending.get('attempts')==1)
        name,goal,xp,gold=CATALOG[pending['game']]
        core.state['player']['gold']=int(core.state['player'].get('gold',0))+gold
        core.add_xp(xp)
    core.save()
    if won:return f'{name} gewonnen! +{xp} EP · +{gold} Gold'
    if skip:return 'Herausforderung übersprungen. Deine Reise geht weiter.'
    if exhausted:return 'Beide Versuche verbraucht. Diese Herausforderung ist beendet.'
    return 'Versuch beendet. Du hast noch einen Versuch für diese Herausforderung.'


def record_win(data,kind,chat=False,first_try=False):
    wins=data.setdefault('wins',{})
    wins[kind]=int(wins.get(kind,0))+1
    if chat:data['chat_wins']=int(data.get('chat_wins',0))+1
    if first_try:data['first_try_wins']=int(data.get('first_try_wins',0))+1


def begin_practice(core,kind):
    migrate_classic_snake(core.state)
    migrate_temple_blocks(core.state)
    data=core.state.setdefault('minigames',{})
    if kind not in CATALOG or kind not in data.get('discovered',[]):return None
    attempt={'game':kind,'seed':secrets.randbits(32),'ticket':secrets.token_hex(16),'practice':True}
    data['practice']=attempt
    core.save()
    return dict(attempt)


def resolve_practice(core,ticket,moves):
    migrate_classic_snake(core.state)
    migrate_temple_blocks(core.state)
    data=core.state.setdefault('minigames',{})
    attempt=data.get('practice')
    if not attempt or not ticket or attempt.get('ticket')!=ticket:return 'Dieser Spielhallen-Versuch ist nicht mehr gültig.'
    data.pop('practice',None)
    game=replay(attempt['game'],attempt['seed'],moves,practice=True)
    if game is None:
        core.save()
        return 'Spielhallen-Ergebnis ungültig · Kein Highscore gespeichert.'
    kind=attempt['game']
    won=(game.hits>=15 if kind=='reflex' else game.score>=game.target)
    if won:record_win(data,kind)
    from shared.core.arcade_scores import update_highscore
    improved=update_highscore(data,kind,game,won)
    text=(CATALOG[kind][0]+' gewonnen! Sieg für deine Erfolge gezählt. ' if won else 'Spielhallen-Versuch beendet. ')
    if improved:text+='🏆 Neuer Highscore! '
    text+='Freies Spielen ohne EP/Gold.'
    core.save()
    return text


def replay(kind,seed,moves,practice=False):
    if not isinstance(moves,list) or (not practice and len(moves)>40000):return None
    try:game=engine(kind,seed,practice=practice)
    except (KeyError,ValueError):return None
    actions=DIRECTIONS if kind in SNAKE_GAMES else game.actions
    for action in moves:
        if not isinstance(action,str) or action not in actions or game.over:return None
        game.step(action)
    return game


def valid_win(kind,seed,moves):
    game=replay(kind,seed,moves)
    return game is not None and game.score>=game.target
