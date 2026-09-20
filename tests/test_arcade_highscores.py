import unittest
from unittest.mock import Mock,patch
from test_desktop import APP
from shared.core.minigames import engine,begin_practice,resolve_practice,replay
from test_minigames import MinigameTests
from test_arcade import breakout_win
from test_temple_circles import temple_win
from test_temple_arcade import solution
from gui.game_hall import GameHall,game_dialog

class ArcadeHighscoreTests(unittest.TestCase):
    def test_classic_goals_unchanged_but_hall_continues(self):
        moves={'maat_coil':MinigameTests.winning_moves(self),'breakout':breakout_win().moves,'temple_circles':temple_win().moves}
        for kind,actions in moves.items():
            with self.subTest(kind=kind):
                chat=replay(kind,7,actions);hall=replay(kind,7,actions,practice=True)
                self.assertTrue(chat.over);self.assertFalse(hall.over)
                self.assertEqual(chat.score,hall.score)
                if kind=='breakout':self.assertEqual(hall.wave,2);self.assertEqual(len(hall.bricks),40)
    def test_snake_full_board_starts_new_board_and_reflex_continues(self):
        g=engine('snake',7,practice=True);g.body=[(0,0)]+[(x,y) for y in range(16) for x in range(20) if (x,y) not in ((0,0),(1,0))]
        g.food=(1,0);g.score=316;g.step('R');self.assertFalse(g.over);self.assertEqual(len(g.body),3);self.assertEqual(g.score,317)
        chat=engine('reflex',7);hall=engine('reflex',7,practice=True)
        for _ in range(15):chat.step(str(chat.star));hall.step(str(hall.star))
        self.assertTrue(chat.over);self.assertFalse(hall.over)
        for _ in range(5):hall.step(str(hall.star))
        for _ in range(4):hall.step(str((hall.star+1)%16))
        self.assertTrue(hall.over);self.assertEqual(hall.hits,20)
        checked=replay('reflex',7,hall.moves,practice=True);self.assertEqual(checked.hits,20)
    def test_losing_run_saves_record_once_without_currency(self):
        core=Mock(state={'player':{'gold':100},'minigames':{'discovered':['reflex']}})
        with patch('shared.core.minigames.secrets.randbits',return_value=7):attempt=begin_practice(core,'reflex')
        g=engine('reflex',7,practice=True)
        for _ in range(20):g.step(str(g.star))
        for _ in range(4):g.step(str((g.star+1)%16))
        self.assertIn('Highscore',resolve_practice(core,attempt['ticket'],g.moves))
        self.assertEqual(core.state['minigames']['highscores']['reflex']['value'],20)
        resolve_practice(core,attempt['ticket'],g.moves)
        self.assertEqual(core.state['minigames']['wins']['reflex'],1)
        self.assertEqual(core.state['player']['gold'],100);core.add_xp.assert_not_called()
    def test_puzzle_record_only_for_win_and_lower_is_better(self):
        from shared.core.arcade_scores import update_highscore
        data={};g=solution('memory');g.attempts=10
        self.assertFalse(update_highscore(data,'memory',g,False))
        self.assertTrue(update_highscore(data,'memory',g,True))
        g.attempts=8;self.assertTrue(update_highscore(data,'memory',g,True))
        g.attempts=9;self.assertFalse(update_highscore(data,'memory',g,True))
        self.assertEqual(data['highscores']['memory']['value'],8)
    def test_hall_records_and_dialog_mode(self):
        hall=GameHall(['maat_coil'],lambda *a:None)
        try:
            hall.update_discoveries(['maat_coil'],{'maat_coil':{'value':37}})
            self.assertIn('37 Bünde',hall.records['maat_coil'].text())
            hall.update_discoveries([],{})
            self.assertIn('Noch kein Eintrag',hall.records['maat_coil'].text())
            for kind in ('maat_coil','breakout','temple_circles','reflex'):
                d=game_dialog(kind,7,practice=True)
                self.assertTrue(d.game.endless);d.reject();d.deleteLater()
                d=game_dialog(kind,7);self.assertFalse(d.game.endless);d.reject();d.deleteLater()
        finally:hall.deleteLater();APP.processEvents()
