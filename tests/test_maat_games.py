import itertools
import unittest
from unittest.mock import Mock
from collections import deque
from test_desktop import APP
from shared.core.minigames import engine,valid_win,replay,CATALOG,DIRECTIONS,begin_attempt,resolve
from shared.core.maat_games import INFO
from shared.core.arcade_scores import update_highscore
from gui.game_hall import game_dialog


def solve(game):
    def act(i):game.step(str(i))
    k=game.kind
    if k=='maat_echo':
        while not game.over:
            while game.ticks:game.step('.')
            for i in list(game.sequence):act(i)
    elif k=='maat_balance':
        while not game.over:
            choice=next(c for n in range(6) for c in itertools.combinations(range(5),n) if sum(game.weights[i] for i in c)==game.goal)
            for i in choice:act(i)
            act(5)
    elif k=='maat_creation':
        for i,n in enumerate(game.goal):
            for _ in range(n):act(i)
    elif k=='maat_connection':
        # Traverse the five checkpoint rows in their mirrored order.
        mirrored=game.checkpoints[0]==4
        route=list(range(5))+[9,14]+[13,12,11,10]+[15,20]
        for i in route:act(i//5*5+4-i%5 if mirrored else i)
    elif k in ('maat_respect','maat_numbers'):
        while not game.over:act(game.cells.index('HBSVR'[game.answer] if k=='maat_respect' else game.answer))
    elif k=='maat_towers':
        def hanoi(n,a,b,c):
            if not n:return
            hanoi(n-1,a,c,b);act(a);act(b);hanoi(n-1,c,b,a)
        hanoi(4,0,2,1)
    elif k=='maat_rings':
        counts=next(c for c in itertools.product(range(3),repeat=5) if all((game.cells[i]+c[i]+c[(i-1)%5])%3==0 for i in range(5)))
        for i,n in enumerate(counts):
            for _ in range(n):act(i)


class MaatGamesTests(unittest.TestCase):
    def test_all_puzzles_solvable_and_replay_verified(self):
        for k in INFO:
            for seed in range(20):
                with self.subTest(kind=k,seed=seed):
                    g=engine(k,seed);solve(g)
                    self.assertTrue(g.over);self.assertEqual(g.score,1)
                    self.assertTrue(valid_win(k,seed,g.moves))
                    self.assertFalse(valid_win(k,seed,[]))
                    self.assertFalse(valid_win(k,seed,g.moves+['0']))
                    data={};self.assertTrue(update_highscore(data,k,g,True))
                    self.assertFalse(update_highscore(data,k,g,True))
                    if seed==0:
                        core=Mock(state={'player':{'gold':0},'minigames':{'pending':{'id':1,'game':k,'seed':seed}}})
                        ticket=begin_attempt(core,1)['ticket']
                        self.assertIn('gewonnen',resolve(core,1,g.moves,ticket=ticket))
                        resolve(core,1,g.moves,ticket=ticket)
                        self.assertEqual(core.state['player']['gold'],CATALOG[k][3])
                        core.add_xp.assert_called_once_with(CATALOG[k][2])
    def test_errors_end_attempt_and_pause_hides_echo(self):
        for k in ('maat_numbers','maat_respect'):
            g=engine(k,2)
            for _ in range(3):
                answer='HBSVR'[g.answer] if k=='maat_respect' else g.answer
                g.step(str(next(i for i,v in enumerate(g.cells) if v!=answer)))
            self.assertTrue(g.over);self.assertEqual(g.score,0)
        d=game_dialog('maat_echo',1)
        try:
            d.toggle();self.assertIn('Merke:',d.status.text());self.assertTrue(d.timer.isActive())
            d.pause();self.assertNotIn('Merke:',d.status.text());self.assertFalse(d.timer.isActive())
        finally:d.reject();d.deleteLater();APP.processEvents()
    def test_snake_obstacles_and_runes_and_endless(self):
        g=engine('snake_walls',7);g.body=[(7,3),(6,3),(5,3)];g.direction='R';g.step('R')
        self.assertTrue(g.over);self.assertEqual(g.score,0)
        g=engine('maat_snake',7);cell=next(iter(g.decoys));g.body=[(cell[0]-1,cell[1])];g.direction='R';g.step('R');self.assertTrue(g.over)
        for kind in ('snake_walls','maat_snake'):
            g=engine(kind,7,practice=True)
            self.assertTrue(g.endless)
            # Find safe paths to 16 foods; backend replay must agree beyond the chat target.
            while g.score<16:
                head=g.body[0];queue=deque([(head,[])]);seen={head};route=None
                blocked=set(g.body[1:])|g.walls|set(g.decoys)
                while queue:
                    pos,steps=queue.popleft()
                    if pos==g.food:route=steps;break
                    for action,(dx,dy) in DIRECTIONS.items():
                        nxt=(pos[0]+dx,pos[1]+dy)
                        if 0<=nxt[0]<g.width and 0<=nxt[1]<g.height and nxt not in blocked and nxt not in seen:
                            seen.add(nxt);queue.append((nxt,steps+[action]))
                self.assertIsNotNone(route)
                for action in route:g.step(action)
                self.assertFalse(g.over)
            checked=replay(kind,7,g.moves,practice=True);self.assertIsNotNone(checked);self.assertEqual(checked.score,16)
            self.assertFalse(valid_win(kind,7,g.moves))
    def test_all_ten_native_boards_render(self):
        self.assertEqual(len(CATALOG),23)
        for kind in ['snake_walls','maat_snake',*INFO]:
            d=game_dialog(kind,7,practice=True)
            try:
                d.show();d.toggle();APP.processEvents();self.assertFalse(d.grab().isNull())
                if kind in ('maat_snake','maat_towers','maat_creation'):d.grab().save('/tmp/'+kind+'.png')
            finally:d.reject();d.deleteLater();APP.processEvents()
