import unittest,json
from pathlib import Path
from unittest.mock import Mock
from copy import deepcopy
from test_desktop import APP
from test_live_rpg import Worker
from shared.core.minigames import offer,begin_attempt,resolve
from gui.snake_game import SnakeDialog
from gui.arcade_game import ArcadeDialog
from gui.temple_circles_game import TempleCirclesDialog

class AttemptTests(unittest.TestCase):
    def test_limit_and_stale_tickets_across_reload(self):
        for kind in ('maat_coil','breakout','temple_circles'):
            state={'player':{'gold':0},'quests':{'meta':{'messages_total':15}}}
            offer(state);state['minigames']['pending']['game']=kind
            core=Mock(state=state)
            first=begin_attempt(core,1)
            # Simulate a crash: reservation survives persisted state without a result.
            core=Mock(state=json.loads(json.dumps(core.state)))
            second=begin_attempt(core,1)
            self.assertEqual(second['attempts'],2)
            self.assertIsNone(begin_attempt(core,1))
            resolve(core,1,[],ticket=first['ticket'])
            self.assertIsNotNone(core.state['minigames']['pending'])
            resolve(core,1,[],ticket=second['ticket'])
            self.assertIsNone(core.state['minigames']['pending'])
            self.assertIsNone(begin_attempt(core,1));core.add_xp.assert_not_called()
            self.assertIsNone(offer(core.state)['pending'])
    def test_dialog_cannot_restart_after_loss(self):
        for d in (SnakeDialog(7),ArcadeDialog('breakout',7),TempleCirclesDialog(7)):
            d.game.over=True;d.tick()
            self.assertTrue(d.play.isHidden())
            original=d.game;d.toggle()
            self.assertIs(d.game,original);self.assertFalse(d.timer.isActive())
            d.reject();d.deleteLater()
    def test_worker_persists_and_consumes_two_attempts(self):
        worker=Worker(seed={'battle_state.json':{'quests':{'meta':{'messages_total':15}}}})
        try:
            for number in (1,2):
                worker.send(op='minigame_start',id=1)
                events=worker.until(lambda e:e['event']=='busy' and not e['value'])
                grant=next(e['data'] for e in events if e['event']=='minigame_started')
                self.assertEqual(grant['attempts'],number)
                saved=json.loads((Path(worker.temp.name)/'state/battle_state.json').read_text())
                self.assertEqual(saved['minigames']['pending']['attempts'],number)
                worker.send(op='minigame',id=1,ticket=grant['ticket'],moves=[])
                worker.until(lambda e:e['event']=='busy' and not e['value'])
            worker.send(op='minigame_start',id=1)
            events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            self.assertIsNone(next(e['data'] for e in events if e['event']=='minigame_started'))
        finally:worker.close()
