import unittest
from copy import deepcopy
from collections import deque
from unittest.mock import Mock
from test_desktop import APP
from shared.core.minigames import Snake,offer,resolve,DIRECTIONS,begin_attempt
from gui.snake_game import SnakeDialog

class MinigameTests(unittest.TestCase):
    def state(self,n=0):return {'quests':{'meta':{'messages_total':n}},'world':{},'player':{'gold':0}}
    def test_intervals_backlog_and_combat_transition(self):
        s=self.state()
        for n in range(15):
            s['quests']['meta']['messages_total']=n
            self.assertIsNone(offer(s)['pending'])
        for n in [15,20,25,30]:
            s['quests']['meta']['messages_total']=n
            self.assertIsNotNone(offer(s)['pending']);s['minigames']['pending']=None
        s['world']['combat_unlocked']=True
        for n in range(31,61):
            s['quests']['meta']['messages_total']=n
            self.assertIsNone(offer(s)['pending'])
        s['quests']['meta']['messages_total']=61
        pending=offer(s)['pending'];self.assertIsNotNone(pending)
        s['quests']['meta']['messages_total']=200
        self.assertEqual(offer(s)['pending'],pending)
        core=Mock(state=s)
        resolve(core,pending['id'],skip=True)
        self.assertIsNone(offer(s)['pending']);core.add_xp.assert_not_called()
    def winning_moves(self):
        from test_maat_coil import complete_circuits
        from shared.core.maat_coil import StarCoil
        return complete_circuits(StarCoil(7)).moves
    def test_validated_reward_once_and_failed_attempt_retained(self):
        s=self.state(15);offer(s);s['minigames']['pending'].update(seed=7,game='maat_coil')
        core=Mock(state=s)
        first=begin_attempt(core,1)
        resolve(core,1,['U'],ticket=first['ticket'])
        self.assertIsNotNone(s['minigames']['pending']);core.add_xp.assert_not_called()
        moves=self.winning_moves()
        second=begin_attempt(core,1)
        resolve(core,1,moves,ticket=second['ticket'])
        self.assertEqual(s['player']['gold'],15);core.add_xp.assert_called_once_with(40)
        resolve(core,1,moves,ticket=second['ticket'])
        self.assertEqual(s['player']['gold'],15);core.add_xp.assert_called_once()
    def test_collision_and_dialog_timer_shutdown(self):
        g=Snake(1);g.step('L');self.assertEqual(g.direction,'R')
        for _ in range(20):g.step('U')
        self.assertTrue(g.over)
        d=SnakeDialog(7);d.toggle();self.assertTrue(d.timer.isActive())
        d.reject();self.assertFalse(d.timer.isActive());d.deleteLater()

    def test_real_worker_persists_single_reward(self):
        import json
        from pathlib import Path
        from test_live_rpg import Worker
        state=self.state(15)
        state['player'].update(level=5,xp=0)
        offer(state);state['minigames']['pending'].update(seed=7,game='maat_coil')
        worker=Worker(seed={'battle_state.json':state})
        try:
            baseline_xp=json.loads((Path(worker.temp.name)/'state/battle_state.json').read_text())['player']['xp']
            worker.send(op='minigame_start',id=1)
            start=worker.until(lambda e:e['event']=='busy' and not e['value'])
            ticket=next(e['data']['ticket'] for e in start if e['event']=='minigame_started')
            for _ in range(2):
                worker.send(op='minigame',id=1,moves=self.winning_moves(),ticket=ticket)
                events=worker.until(lambda e:e['event']=='busy' and not e['value'])
                self.assertTrue(any(e['event']=='minigame_result' for e in events))
            saved=json.loads((Path(worker.temp.name)/'state/battle_state.json').read_text())
            self.assertEqual(saved['player']['gold'],15)
            self.assertEqual(saved['player']['xp'],baseline_xp+40)
            self.assertIsNone(saved['minigames']['pending'])
        finally:worker.close()
