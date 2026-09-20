import io
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from test_desktop import APP
from apps.maat_rpg.plugins.battle.plugin_main import BattleCore
from gui.combat_sounds import combat_sound, DAMAGE_SOUND


class DamageEventsTests(unittest.TestCase):
    def test_sound_uses_actual_hp_loss_including_floor_block_and_healing(self):
        for before, after, damage, audible in [(100, 86, 14, True), (5, 1, 80, True),
                (1, 1, 80, False), (100, 100, 0, False), (100, 110, 0, False),
                (100, 100, 80, False)]:
            for kind in ('normal', 'special'):
                with self.subTest(before=before, after=after, kind=kind):
                    event = dict(attacker='enemy', attack=kind, damage=damage,
                                 player_hp_before=before, player_hp=after)
                    self.assertEqual(combat_sound(event), DAMAGE_SOUND if audible else None)
        self.assertTrue(DAMAGE_SOUND.is_file())
        self.assertIsNone(combat_sound(dict(attacker='enemy', damage=0)))
        self.assertIsNone(combat_sound(dict(attacker='enemy', damage='invalid')))
        self.assertIsNone(combat_sound(dict(attacker='player', attack='heal', heal=20)))

    def fight(self, *, hp=1000, kind='normal', blocked=False, protected=False):
        with tempfile.TemporaryDirectory() as folder, redirect_stdout(io.StringIO()):
            core = BattleCore(folder)
            core.state.state = core.state._default()
            core.state.state['player'].update(hp=hp, max_hp=1000)
            core.state.save = Mock()
            core._enemy_stats = lambda kind:(10000, 100, 100)
            core._choose_music = lambda *args:(None, None)
            core._load_story_state = lambda:{}
            core._save_story_state = Mock()
            core._choose_enemy_weakness = lambda:'Respekt'
            core._register_boss_codex_entry = Mock()
            core._slow_line = Mock()
            core._show_special_vignette = Mock()
            core._prompt = Mock(side_effect=['1', '1']*3 + ['6'])
            if blocked:
                core._apply_guard = lambda damage, state:(0, 'Schild absorbiert alles.')
            events = []
            with patch('shared.core.gui_bridge.emit', side_effect=lambda event, **data:events.append(dict(event=event, **data))), \
                    patch('random.random', return_value=0), patch('random.randint', return_value=0), \
                    patch('apps.maat_rpg.plugins.battle.plugin_main.BattleMusicManager'):
                core.run_fight(kind, {'combat_source':'arena', 'fast_output':True, 'no_hp_loss':protected})
            return [e for e in events if e['event']=='battle_effect' and e['attacker']=='enemy']

    def test_real_normal_combat_reports_loss_block_and_one_hp_floor(self):
        for kwargs, audible in [({}, True), ({'blocked':True}, False),
                                ({'protected':True}, False), ({'hp':1}, False), ({'hp':5}, True)]:
            with self.subTest(**kwargs):
                events = self.fight(**kwargs)
                self.assertTrue(events)
                for e in events:
                    self.assertIn('player_hp_before', e)
                    self.assertGreaterEqual(e['player_hp'], 1)
                    self.assertEqual(combat_sound(e) is not None, audible)

    def test_real_boss_and_final_specials_report_authoritative_hp(self):
        for kind in ('boss', 'final'):
            with self.subTest(kind=kind):
                events = self.fight(kind=kind)
                specials = [e for e in events if e['attack']=='special']
                self.assertTrue(specials)
                for e in specials:
                    self.assertGreater(e['player_hp_before'], e['player_hp'])
                    self.assertEqual(combat_sound(e), DAMAGE_SOUND)
