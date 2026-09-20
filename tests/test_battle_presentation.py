"""Narrative boundaries must precede boss/final HUD changes."""
import os
import unittest
from unittest.mock import patch
import test_live_window as helpers
from test_desktop import APP
from apps.maat_rpg import session_shared
from gui.live_window import LiveWindow


class BattlePresentationTests(unittest.TestCase):
    def test_boss_and_final_wait_for_entrance_phase_and_victory(self):
        with patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT': str(session_shared.BASE_APP_SUPPORT_DIR)}):
            helpers.unlock_test_arena()
            window = LiveWindow(audio=helpers.SilentAudio())
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
            try:
                helpers.LiveWindowTest.spin(self, lambda: window.game.ready)
                window.phase = 'playing'
                window._combat_unlocked = True
                window.navigate(2)
                for fight_type in ('boss', 'final'):
                    with self.subTest(fight_type=fight_type):
                        send = window.game._handle
                        send(dict(event='battle', active=True, enemy_name='', combat_source='arena', fight_type=fight_type))
                        self.assertTrue(window.arena.stage.isHidden())
                        self.assertTrue(window.arena.hero_hp.isHidden())
                        send(dict(event='output', text='Das Tor öffnet sich. Der Pharao tritt aus dem Schatten.\n'))
                        window.text_stream.timer.stop()
                        send(dict(event='battle', active=True, enemy_name='Pharao', enemy_hp=200, enemy_max_hp=200, phase=1, fight_type=fight_type))
                        send(dict(event='prompt', id='turn', text='Aktion?', choices=[]))
                        self.assertIsNone(window.game.prompt_id)
                        self.assertIsNone(window.arena.stage.name)
                        window.text_stream.finish()
                        self.assertEqual(window.arena.stage.name, 'Pharao')
                        self.assertFalse(window.arena.hero_hp.isHidden())
                        self.assertFalse(window.arena.resonance.isHidden())
                        self.assertEqual(window.game.prompt_id, 'turn')
                        send(dict(event='prompt_closed', id='turn'))
                        send(dict(event='output', text='Der Pharao entfesselt seine zweite Form.\n'))
                        window.text_stream.timer.stop()
                        send(dict(event='battle', active=True, phase=2, enemy_hp=90))
                        self.assertEqual(window.game.get_snapshot().battle.phase, 1)
                        window.text_stream.finish()
                        self.assertEqual(window.game.get_snapshot().battle.phase, 2)
                        send(dict(event='output', text='Der letzte Treffer trifft sein Ziel.\n'))
                        window.text_stream.timer.stop()
                        send(dict(event='battle', active=False, enemy_hp=0))
                        send(dict(event='story_scene', id='ending', lines=['Das Licht kehrt zurück.'], module='credits', name='Finale', music=None))
                        self.assertTrue(window._battle_active)
                        self.assertEqual(window.phase, 'playing')
                        window.text_stream.finish()
                        self.assertFalse(window._battle_active)
                        self.assertEqual(window.phase, 'story')
                        window.finish_story_scene()
            finally:
                window.close()
                APP.processEvents()
