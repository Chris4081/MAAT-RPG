import os
import unittest
from unittest.mock import patch
from test_live_window import LiveWindowTest, SilentAudio, unlock_test_arena
from test_desktop import APP
from apps.maat_rpg import session_shared
from gui.live_window import LiveWindow

class RandomEncounterTests(unittest.TestCase):
    spin = LiveWindowTest.spin
    def test_random_notice_and_return_from_any_playing_tab(self):
        with patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            unlock_test_arena()
            window=LiveWindow(audio=SilentAudio())
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
            try:
                window.show();self.spin(lambda:window.game.ready)
                window.phase='playing';window._combat_unlocked=True
                window._chat_return_timer.setInterval(10)
                window.navigate(5)
                window.arena.update_state({'enemy_name':'Alter Pharao','enemy_hp':5,'enemy_max_hp':99,'arena_difficulty':'hard'})
                begin={'event':'battle','active':True,'combat_source':'random','enemy_name':'Schattenwächter','enemy_hp':50,'enemy_max_hp':50}
                window.game._handle(dict(begin,enemy_name='',enemy_hp=0,enemy_max_hp=0))
                self.assertEqual(window.stack.currentIndex(),3)
                self.assertFalse(window._battle_active)
                self.assertIsNone(window.arena.stage.name)
                self.assertEqual(window.arena.enemy_name.text(),'')
                self.assertTrue(window.arena.enemy_hp.isHidden())
                self.assertIsNone(window.arena.stage.effect)
                self.assertTrue(window.encounter_stream.running)
                self.assertEqual(window.encounter_stream.timer.interval(),140)
                window.encounter_stream.timer.stop()
                window.encounter_stream.advance()
                self.assertTrue(window.journal.toPlainText().endswith('E'))
                window.navigate(2)
                self.assertEqual(window.stack.currentIndex(),3)
                window.game._handle(begin)
                window.encounter_stream.finish()
                self.assertEqual(window.stack.currentIndex(),3)
                self.spin(lambda:window.stack.currentIndex()==2)
                self.assertTrue(window.encounter_notice.isVisible())
                self.assertEqual(window.arena.stage.name,'Schattenwächter')
                self.assertFalse(window.arena.enemy_hp.isHidden())
                self.assertEqual(window.journal.toPlainText().count('Ein Wesen erscheint …'),1)
                window.game._handle({'event':'busy','value':True})
                window.game._handle({'event':'battle','active':False})
                self.assertTrue(window._chat_return_timer.isActive())
                window.text_stream.append('Die KI setzt ihre Antwort nach dem Kampf fort. '*20)
                window.update_controls()
                self.spin(lambda:window.stack.currentIndex()==3)
                self.assertTrue(window.game.busy)
                self.assertTrue(window.text_stream.running)
                window.game._handle({'event':'busy','value':False})
                window.text_stream.finish()
                self.assertFalse(window.encounter_notice.isVisible())
                self.assertTrue(window.input.hasFocus())
                # Manual arena opened from the arena remains there after completion.
                window.navigate(2)
                window.game._handle(dict(begin,combat_source='arena'))
                self.assertFalse(window.encounter_notice.isVisible())
                window.game._handle({'event':'battle','active':False})
                self.assertFalse(window._return_to_chat)
                self.assertFalse(window._chat_return_timer.isActive())
            finally:
                window.close();APP.processEvents()
