import unittest
from test_desktop import APP
from shared.core.arcade import Breakout
from test_temple_circles import temple_win
from gui.temple_circles_game import TempleCirclesDialog
from shared.core.minigames import offer,resolve,begin_attempt
from gui.arcade_game import ArcadeDialog
from gui.snake_game import SnakeDialog
from unittest.mock import Mock

def breakout_win():
    g=Breakout(7)
    while not g.over:g.step('L' if g.paddle>g.x+3 else 'R' if g.paddle<g.x-3 else '.')
    return g

class ArcadeTests(unittest.TestCase):
    def test_actual_winning_replays_and_rewards(self):
        for kind,g,xp,gold in [('breakout',breakout_win(),60,20),('temple_circles',temple_win(),80,25)]:
            self.assertGreaterEqual(g.score,g.target,(kind,g.score,len(g.moves)))
            state={'player':{'gold':0},'minigames':{'pending':{'id':1,'game':kind,'seed':7}}}
            core=Mock(state=state)
            ticket=begin_attempt(core,1)['ticket']
            self.assertIn('gewonnen',resolve(core,1,g.moves,ticket=ticket))
            self.assertEqual(state['player']['gold'],gold);core.add_xp.assert_called_once_with(xp)
            resolve(core,1,g.moves,ticket=ticket);core.add_xp.assert_called_once()
    def test_music_stops_for_pause_failure_and_close(self):
        for d in [SnakeDialog(7),ArcadeDialog('breakout',7),TempleCirclesDialog(7)]:
            events=[];d.music_running.connect(events.append)
            d.toggle();self.assertTrue(events[-1]);d.pause();self.assertFalse(events[-1])
            d.toggle();self.assertTrue(events[-1])
            d.game.over=True;d.tick();self.assertFalse(events[-1]);self.assertFalse(d.timer.isActive())
            d.toggle();d.reject();self.assertFalse(events[-1]);self.assertFalse(d.timer.isActive());d.deleteLater()
    def test_breakout_lives(self):
        g=Breakout(1)
        for lives in (2,1,0):g.y=481;g.vy=4;g.step('.');self.assertEqual(g.lives,lives)
        self.assertTrue(g.over)
    def test_offers_discover_catalog_before_repeating(self):
        from shared.core.minigames import CATALOG
        state={'quests':{'meta':{'messages_total':15}}}
        seen=set()
        for i in range(len(CATALOG)):
            state['quests']['meta']['messages_total']=15+i*5
            kind=offer(state)['pending']['game']
            self.assertNotIn(kind,seen)
            seen.add(kind)
            state['minigames']['pending']=None
        self.assertEqual(seen,set(CATALOG))
