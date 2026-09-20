import unittest
import random
from collections import deque
from copy import deepcopy
from unittest.mock import Mock
from test_desktop import APP
from shared.core.minigames import CATALOG,engine,offer,begin_attempt,resolve
from shared.core.arcade_extra import INFO
from gui.game_hall import GameHall,game_dialog


def solution(kind,seed=7):
    g=engine(kind,seed)
    if kind=='memory':
        for symbol in 'ABCDEFGH':
            for i,c in enumerate(g.cells):
                if c==symbol:g.step(str(i))
    elif kind=='mines':
        g.step('0')
        for i in range(1,25):
            if i not in g.mines:g.step(str(i))
    elif kind=='lights':
        initial=sum(v<<i for i,v in enumerate(g.cells))
        masks=[sum(1<<n for n in [i]+g.neighbors(i)) for i in range(16)]
        for bits in range(1<<16):
            result=initial
            for i in range(16):
                if bits>>i&1:result^=masks[i]
            if not result:
                for i in range(16):
                    if bits>>i&1:g.step(str(i))
                break
    elif kind=='slide':
        start=tuple(g.cells);goal=tuple(list(range(1,9))+[0]);q=deque([start]);parents={start:None}
        while goal not in parents:
            state=q.popleft();z=state.index(0)
            for i in g.neighbors(z):
                cells=list(state);cells[i],cells[z]=cells[z],cells[i];n=tuple(cells)
                if n not in parents:parents[n]=(state,str(i));q.append(n)
        moves=[];s=goal
        while parents[s] is not None:s,a=parents[s];moves.append(a)
        for a in reversed(moves):g.step(a)
    elif kind in ('maze','sokoban'):
        def key(c):return c.player,tuple(sorted(c.boxes))
        q=deque([g]);visited={key(g)}
        while q:
            c=q.popleft()
            if c.over:return c
            for a in 'UDLR':
                n=deepcopy(c);n.step(a)
                if key(n) not in visited:visited.add(key(n));q.append(n)
        raise AssertionError('unsolvable')
    elif kind in ('four','three'):
        for trial in range(1000):
            g=engine(kind,seed);rng=random.Random(trial)
            while not g.over:g.step(str(rng.choice(g.legal())))
            if g.score:return g
    elif kind=='reflex':
        while not g.over:g.step(str(g.star))
    elif kind=='wheel':
        g.step('0')
        while not g.over:g.step('.')
    return g


class TempleArcadeTests(unittest.TestCase):
    def test_ten_games_have_replayable_wins_and_one_reward(self):
        self.assertTrue(set(INFO) <= set(CATALOG))
        for kind in INFO:
            with self.subTest(kind=kind):
                seed=7
                if kind=='wheel':
                    seed=next(s for s in range(50) if solution(kind,s).score)
                g=solution(kind,seed);self.assertEqual(g.score,1)
                core=Mock(state={'player':{'gold':0},'minigames':{'pending':{'id':1,'game':kind,'seed':seed}}})
                ticket=begin_attempt(core,1)['ticket']
                self.assertIn('gewonnen',resolve(core,1,g.moves,ticket=ticket))
                self.assertEqual(core.state['player']['gold'],CATALOG[kind][3])
                resolve(core,1,g.moves,ticket=ticket)
                core.add_xp.assert_called_once_with(CATALOG[kind][2])
    def test_all_discoveries_random_without_repeats_and_migration(self):
        state={'quests':{'meta':{'messages_total':15}}}
        found=[]
        for i in range(len(CATALOG)):
            state['quests']['meta']['messages_total']=15+i*5
            data=offer(state);found.append(data['pending']['game']);state['minigames']['pending']=None
        self.assertEqual(set(found),set(CATALOG));self.assertEqual(len(set(found)),len(CATALOG))
        self.assertEqual(offer(state)['discovered'],found)
        old={'minigames':{'serial':2,'last_offer':20,'pending':None}}
        self.assertEqual(offer(old)['discovered'],['maat_coil','breakout'])
        fresh={};self.assertEqual(offer(fresh)['discovered'],[])
    def test_dialogs_pause_stop_music_and_hall_locks(self):
        hall=GameHall(['wheel'],lambda *args:None)
        try:
            self.assertTrue(hall.buttons['wheel'].isEnabled());self.assertFalse(hall.buttons['maat_coil'].isEnabled())
            for kind in INFO:
                with self.subTest(kind=kind):
                    d=game_dialog(kind,7);audio=[];d.music_running.connect(audio.append)
                    try:
                        d.toggle();self.assertTrue(audio[-1]);d.act('0');d.grab()
                        d.pause();self.assertFalse(audio[-1]);before=list(d.game.moves);d.act('1');self.assertEqual(d.game.moves,before)
                        d.toggle();d.reject();self.assertFalse(d.timer.isActive());self.assertFalse(audio[-1])
                    finally:d.deleteLater()
        finally:hall.deleteLater();APP.processEvents()
    def test_losses_and_attempt_limit(self):
        for kind in INFO:
            core=Mock(state={'player':{'gold':0},'minigames':{'pending':{'id':1,'game':kind,'seed':7}}})
            for _ in range(2):
                attempt=begin_attempt(core,1);resolve(core,1,['invalid'],ticket=attempt['ticket'])
            self.assertIsNone(begin_attempt(core,1));core.add_xp.assert_not_called()

    def test_worker_saves_discovery_and_new_game_reward(self):
        import json
        from pathlib import Path
        from test_live_rpg import Worker
        seed=next(s for s in range(50) if solution('wheel',s).score)
        state={'player':{'gold':0,'level':5,'xp':0},'quests':{'meta':{'messages_total':15}},
               'minigames':{'serial':1,'last_offer':15,'discovered':[],
                            'pending':{'id':1,'seed':seed,'game':'wheel'}}}
        worker=Worker(seed={'battle_state.json':state})
        try:
            worker.send(op='minigame_start',id=1)
            events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            ticket=next(e['data']['ticket'] for e in events if e['event']=='minigame_started')
            worker.send(op='minigame',id=1,ticket=ticket,moves=solution('wheel',seed).moves)
            worker.until(lambda e:e['event']=='busy' and not e['value'])
            saved=json.loads((Path(worker.temp.name)/'state/battle_state.json').read_text())
            self.assertIn('wheel',saved['minigames']['discovered'])
            self.assertEqual(saved['player']['gold'],15)
            self.assertIsNone(saved['minigames']['pending'])
        finally:worker.close()
        restarted=Worker(seed={'battle_state.json':saved})
        try:
            restarted.send(op='models')
            events=restarted.until(lambda e:e['event']=='busy' and not e['value'])
            data=next(e['data'] for e in events if e['event']=='minigame')
            self.assertIn('wheel',data['discovered'])
            self.assertIsNone(data['pending'])
        finally:restarted.close()
