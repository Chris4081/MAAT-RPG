"""Star Covenant rules, saved progress migration, rewards and bilingual native UI."""
import unittest
from collections import deque
from copy import deepcopy
from unittest.mock import Mock
from test_desktop import APP
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from shared.core.maat_coil import StarCoil, migrate_classic_snake
from shared.core.minigames import CATALOG, engine, replay, valid_win, begin_attempt, resolve, begin_practice, resolve_practice, offer
from shared.core.minigame_i18n import game_info
from gui.game_hall import game_dialog


def path_to(game, target):
    queue = deque([(game.body[0], [])]); seen = {game.body[0]}
    while queue:
        position, moves = queue.popleft()
        if position == target:
            return moves
        for action, (dx, dy) in {'L': (-1, 0), 'R': (1, 0), 'U': (0, -1), 'D': (0, 1)}.items():
            nxt = (position[0] + dx, position[1] + dy)
            if nxt not in seen and game.inside(nxt):
                seen.add(nxt); queue.append((nxt, moves + [action]))
    raise AssertionError('Unreachable shrine')


def complete_circuits(game, count=3):
    for _ in range(count):
        for target in (*game.shrines, game.center):
            for action in path_to(game, target):
                game.step(action)
                if game.over and game.reason != 'complete':
                    raise AssertionError((game.score, game.reason))
    return game


class CoilTests(unittest.TestCase):
    def test_replay_validates_real_wins_across_seeds(self):
        for seed in range(20):
            game = complete_circuits(StarCoil(seed))
            self.assertEqual(game.score, 3)
            self.assertTrue(game.over)
            self.assertTrue(valid_win('maat_coil', seed, game.moves))
            self.assertFalse(valid_win('maat_coil', seed, game.moves[:-1]))
            self.assertFalse(valid_win('maat_coil', seed, game.moves + ['R']))
            self.assertIsNone(replay('maat_coil', seed, ['invalid']))
            self.assertEqual(replay('maat_coil', seed, game.moves).shields, game.shields)

    def test_trail_can_cross_and_never_grows_or_scores_food(self):
        game = StarCoil(7)
        for _ in range(16):
            game.step('R'); game.step('L')
        self.assertEqual(game.body[0], game.center)
        self.assertEqual(len(game.body), 7)
        self.assertEqual(game.shields, 3)
        self.assertEqual(game.score, 0)
        for action in path_to(game, game.shrines[0]): game.step(action)
        self.assertEqual(game.charged, {0})
        game.step('D'); game.step('U')
        self.assertEqual(game.charged, {0})
        self.assertEqual(game.score, 0)

    def test_rifts_warn_before_damage_and_sanctuaries_protect(self):
        game = StarCoil(0)
        game.rift_axis = 0; game.rift_offset = 0
        game.body = [(8, 4)]
        game.pulse_age = game.pulse_period - 15
        game.step('D')
        self.assertTrue(game.warning); self.assertFalse(game.dangerous)
        self.assertEqual(game.shields, 3)
        game.pulse_age = game.pulse_period - 5
        game.step('U')
        self.assertTrue(game.dangerous); self.assertEqual(game.shields, 2)
        game.step('D'); self.assertEqual(game.shields, 2)
        self.assertFalse(game.in_rift(game.center))
        self.assertTrue(all(not game.in_rift(s) for s in game.shrines))

    def test_timeouts_end_idle_runs_and_endless_exceeds_chat_goal(self):
        game = StarCoil(7)
        for _ in range(600):
            game.step('R' if game.body[0] == game.center else 'L')
        self.assertTrue(game.over); self.assertEqual(game.reason, 'time')
        self.assertEqual(game.shields, 0)
        hall = engine('maat_coil', 7, practice=True)
        complete_circuits(hall, 4)
        self.assertFalse(hall.over); self.assertEqual(hall.score, 4)
        self.assertEqual(replay('maat_coil', 7, hall.moves, practice=True).score, 4)
        self.assertFalse(valid_win('maat_coil', 7, hall.moves))

    def test_migration_is_idempotent_preserves_progress_not_fruit_score(self):
        state = {'player': {'gold': 123}, 'minigames': {
            'discovered': ['snake', 'maat_snake', 'maat_coil'],
            'wins': {'snake': 7, 'maat_coil': 2},
            'highscores': {'snake': {'value': 90}, 'maat_coil': {'value': 4}},
            'pending': {'id': 12, 'game': 'snake', 'seed': 7, 'attempts': 1, 'ticket': 'old'},
            'practice': {'game': 'snake', 'ticket': 'old-hall'}}}
        migrate_classic_snake(state)
        data = state['minigames']
        self.assertEqual(data['discovered'], ['maat_coil', 'maat_snake'])
        self.assertEqual(data['wins']['maat_coil'], 9)
        self.assertEqual(data['highscores']['maat_coil']['value'], 4)
        self.assertEqual(data['legacy_highscores']['snake']['value'], 90)
        self.assertEqual(data['pending']['attempts'], 1)
        self.assertNotIn('ticket', data['pending']); self.assertNotIn('practice', data)
        again = deepcopy(state); migrate_classic_snake(state); self.assertEqual(state, again)
        core = Mock(state=state)
        grant = begin_attempt(core, 12)
        self.assertEqual(grant['game'], 'maat_coil'); self.assertEqual(grant['attempts'], 2)
        self.assertIsNone(begin_attempt(core, 12))
        self.assertEqual(state['player']['gold'], 123)
        self.assertNotIn('snake', CATALOG); self.assertEqual(len(CATALOG), 23)

    def test_rewards_only_once_and_hall_scores_without_currency(self):
        core = Mock(state={'player': {'gold': 0}, 'minigames': {
            'discovered': ['maat_coil'], 'pending': {'id': 1, 'game': 'maat_coil', 'seed': 7}}})
        ticket = begin_attempt(core, 1)['ticket']
        moves = complete_circuits(StarCoil(7)).moves
        resolve(core, 1, moves, ticket=ticket); resolve(core, 1, moves, ticket=ticket)
        self.assertEqual(core.state['player']['gold'], 15)
        core.add_xp.assert_called_once_with(40)
        attempt = begin_practice(core, 'maat_coil')
        hall = engine('maat_coil', attempt['seed'], practice=True)
        # A short but completed covenant already earns a highscore, never chat currency.
        complete_circuits(hall, 1)
        resolve_practice(core, attempt['ticket'], hall.moves)
        resolve_practice(core, attempt['ticket'], hall.moves)
        self.assertEqual(core.state['minigames']['highscores']['maat_coil']['value'], 1)
        self.assertEqual(core.state['player']['gold'], 15)
        core.add_xp.assert_called_once_with(40)

    def test_ui_translation_render_keyboard_and_timer_lifecycle(self):
        dialog = game_dialog('maat_coil', 7, language='en')
        sounds = []; dialog.music_running.connect(sounds.append)
        try:
            dialog.show(); APP.processEvents()
            self.assertIn('Star Covenant', dialog.title.text())
            self.assertIn('Activate', dialog.hint.text())
            dialog.toggle(); self.assertTrue(dialog.timer.isActive())
            QTest.keyClick(dialog.board, Qt.Key_Left); self.assertEqual(dialog.direction, 'L')
            QTest.keyClick(dialog.board, Qt.Key_Space); self.assertFalse(dialog.timer.isActive())
            self.assertFalse(sounds[-1])
            dialog.set_language('de'); self.assertIn('Sternenbund', dialog.title.text())
            self.assertIn('Aktiviere', dialog.hint.text())
            self.assertFalse(dialog.grab().isNull())
            dialog.game.over = True; dialog.tick(); dialog.toggle()
            self.assertFalse(dialog.timer.isActive()); self.assertTrue(dialog.play.isHidden())
        finally:
            dialog.reject(); self.assertFalse(sounds[-1]); dialog.deleteLater(); APP.processEvents()


if __name__ == '__main__': unittest.main()
