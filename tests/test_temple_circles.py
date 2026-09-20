"""Temple Circles: solvability, replay authority, persistence and native controls."""
import json
import unittest
from copy import deepcopy
from unittest.mock import Mock

from test_desktop import APP
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from shared.core.temple_circles import TempleCircles, migrate_temple_blocks
from shared.core.minigames import (CATALOG, engine, replay, valid_win, offer,
                                  begin_attempt, resolve, begin_practice, resolve_practice)
from shared.core.arcade_scores import record_text
from gui.game_hall import game_dialog


def seal_moves(game):
    moves = []
    for index, ring in enumerate(game.rings):
        clockwise = (game.gate - ring.index(game.rune)) % 5
        moves.extend([str(index) + ('R' if clockwise <= 2 else 'L')] *
                     (clockwise if clockwise <= 2 else 5 - clockwise))
    return moves + ['seal']


def temple_win(seed=7, seals=10, practice=False):
    game = engine('temple_circles', seed, practice=practice)
    for _ in range(seals):
        for move in seal_moves(game):
            game.step(move)
    return game


class TempleCircleTests(unittest.TestCase):
    def test_every_generated_pattern_is_solvable_and_replay_matches(self):
        for seed in range(100):
            game = TempleCircles(seed)
            for seal in range(10):
                self.assertFalse(game.aligned)
                moves = seal_moves(game)
                self.assertLessEqual(len(moves), 7)
                for move in moves: game.step(move)
                self.assertEqual(game.score, seal + 1)
                self.assertEqual(game.focus, 3)
            self.assertTrue(game.over)
            self.assertTrue(valid_win('temple_circles', seed, game.moves))
            checked = replay('temple_circles', seed, game.moves)
            self.assertEqual(checked.rings, game.rings)
            self.assertFalse(valid_win('temple_circles', seed, game.moves[:-1]))
            self.assertIsNone(replay('temple_circles', seed, game.moves + ['seal']))
        self.assertIsNone(replay('temple_circles', 1, ['invalid']))

    def test_alignment_requires_deliberate_activation_and_costs_one_move(self):
        game = TempleCircles(7)
        moves = seal_moves(game)
        for move in moves[:-1]: game.step(move)
        self.assertTrue(game.aligned); self.assertEqual(game.score, 0)
        self.assertEqual(game.remaining, 8 - len(moves) + 1)
        game.step('seal'); self.assertEqual(game.score, 1)
        self.assertEqual(game.remaining, 8)

    def test_wrong_activation_and_exhaustion_spend_focus_and_end_attempt(self):
        game = TempleCircles(7)
        game.step('seal'); self.assertEqual(game.focus, 2)
        self.assertEqual(game.reason, 'alignment')
        for _ in range(8): game.step('0L')
        self.assertEqual(game.focus, 1); self.assertEqual(game.reason, 'moves')
        for _ in range(8): game.step('1R')
        self.assertTrue(game.over); self.assertEqual(game.focus, 0)
        before = deepcopy(game.__dict__)
        game.step('seal')
        self.assertEqual(game.moves, before['moves']); self.assertEqual(game.score, 0)

    def test_endless_harder_budget_stays_solvable_without_currency(self):
        game = temple_win(seals=100, practice=True)
        self.assertFalse(game.over); self.assertEqual(game.score, 100)
        self.assertEqual(game.budget, 7); self.assertEqual(game.focus, 3)
        self.assertEqual(replay('temple_circles', 7, game.moves, practice=True).score, 100)
        self.assertFalse(valid_win('temple_circles', 7, game.moves))
        core = Mock(state={'player': {'gold': 17}, 'minigames': {'discovered': ['temple_circles']}})
        grant = begin_practice(core, 'temple_circles')
        run = temple_win(grant['seed'], seals=1, practice=True)
        resolve_practice(core, grant['ticket'], run.moves)
        resolve_practice(core, grant['ticket'], run.moves)
        self.assertEqual(core.state['minigames']['highscores']['temple_circles']['value'], 1)
        self.assertIn('1 temple seals', record_text('temple_circles', {'value': 1}, 'en'))
        self.assertEqual(core.state['player']['gold'], 17); core.add_xp.assert_not_called()

    def test_migration_keeps_unlocks_wins_old_scores_and_spent_attempts(self):
        state = {'player': {'gold': 90}, 'minigames': {
            'serial': 3, 'last_offer': 25, 'discovered': ['tetris', 'temple_circles'],
            'wins': {'tetris': 4, 'temple_circles': 2},
            'highscores': {'tetris': {'value': 90}, 'temple_circles': {'value': 5}},
            'pending': {'id': 3, 'game': 'tetris', 'seed': 7, 'attempts': 1, 'ticket': 'old'},
            'practice': {'game': 'tetris', 'ticket': 'old-hall'}}}
        core = Mock(state=json.loads(json.dumps(state)))
        self.assertIn('gültig', resolve(core, 3, [], ticket='old'))
        core.add_xp.assert_not_called()
        data = core.state['minigames']
        self.assertEqual(data['discovered'], ['temple_circles'])
        self.assertEqual(data['wins'], {'temple_circles': 6})
        self.assertEqual(data['legacy_highscores']['tetris']['value'], 90)
        self.assertEqual(data['highscores']['temple_circles']['value'], 5)
        self.assertNotIn('practice', data)
        before = deepcopy(core.state); migrate_temple_blocks(core.state)
        self.assertEqual(core.state, before)
        attempt = begin_attempt(core, 3); self.assertEqual(attempt['attempts'], 2)
        self.assertEqual(attempt['game'], 'temple_circles')
        self.assertIsNone(begin_attempt(core, 3))
        self.assertNotIn('tetris', CATALOG); self.assertEqual(len(CATALOG), 23)
        self.assertIsNone(replay('tetris', 7, []))
        with self.assertRaises(ValueError): game_dialog('tetris', 7)
        old = {'minigames': {'serial': 3, 'pending': None, 'last_offer': 25}}
        self.assertIn('temple_circles', offer(old)['discovered'])

    def test_chat_reward_once_after_complete_replay(self):
        core = Mock(state={'player': {'gold': 9}, 'minigames': {'pending': {
            'game': 'temple_circles', 'id': 1, 'seed': 7}}})
        grant = begin_attempt(core, 1)
        moves = temple_win().moves
        resolve(core, 1, moves, ticket=grant['ticket'])
        resolve(core, 1, moves, ticket=grant['ticket'])
        self.assertEqual(core.state['player']['gold'], 34)
        core.add_xp.assert_called_once_with(80)
        self.assertEqual(core.state['minigames']['wins']['temple_circles'], 1)

    def test_bilingual_ui_keyboard_mouse_pause_win_and_no_restart(self):
        dialog = game_dialog('temple_circles', 7, language='en')
        sounds = []; dialog.music_running.connect(sounds.append)
        try:
            dialog.show(); APP.processEvents()
            self.assertIn('Temple Circles', dialog.title.text())
            self.assertIn('Target', dialog.stats.text())
            dialog.toggle(); self.assertTrue(sounds[-1])
            QTest.keyClick(dialog.board, Qt.Key_2)
            QTest.keyClick(dialog.board, Qt.Key_Left)
            self.assertEqual(dialog.game.moves[-1], '1L')
            QTest.keyClick(dialog.board, Qt.Key_Space)
            before = len(dialog.game.moves)
            dialog.turn_buttons[0].click(); QTest.keyClick(dialog.board, Qt.Key_Right)
            self.assertEqual(len(dialog.game.moves), before)
            self.assertFalse(sounds[-1]); dialog.toggle()
            dialog.turn_buttons[3].click(); self.assertEqual(dialog.game.moves[-1], '1R')
            # The two preceding opposite turns return to the initial pattern.
            for _ in range(10):
                for action in seal_moves(dialog.game): dialog.act(action)
            self.assertTrue(dialog.game.over)
            self.assertEqual(dialog.winning_moves, dialog.game.moves)
            self.assertFalse(dialog.timer.isActive()); self.assertFalse(sounds[-1])
            self.assertTrue(dialog.play.isHidden()); dialog.toggle()
            self.assertFalse(dialog.timer.isActive())
            dialog.set_language('de'); self.assertIn('Tempelkreise', dialog.title.text())
            self.assertFalse(dialog.grab().isNull())
        finally:
            dialog.reject(); dialog.deleteLater(); APP.processEvents()


if __name__ == '__main__': unittest.main()
