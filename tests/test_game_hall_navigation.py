import os
import unittest
from unittest.mock import patch
from test_desktop import APP
import test_live_window as helpers
from apps.maat_rpg import session_shared
from gui.live_window import LiveWindow

class HallNavigationTests(unittest.TestCase):
    def test_hall_is_embedded_and_sidebar_navigation_preserves_unlocks(self):
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            window=LiveWindow(audio=helpers.SilentAudio())
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
            try:
                helpers.LiveWindowTest.spin(self,lambda:window.game.ready)
                window.phase='playing';window.navigate(3)
                window.receive({'event':'minigame','data':{'pending':None,'discovered':['wheel']}})
                window.update_controls()
                sidebar=window.navigation_scroll.widget()
                self.assertIs(window.game_hall_button.parentWidget(),sidebar)
                window.game_hall_button.click()
                self.assertIs(window.stack.currentWidget(),window.game_hall)
                self.assertFalse(window.game_hall.isWindow())
                self.assertTrue(window.game_hall_button.isChecked())
                self.assertTrue(window.game_hall.buttons['wheel'].isEnabled())
                self.assertFalse(window.game_hall.buttons['snake'].isEnabled())
                window.navigate(3)
                self.assertFalse(window.game_hall_button.isChecked())
                window.open_game_hall()
                self.assertIs(window.stack.currentWidget(),window.game_hall)
                self.assertEqual(window.game_hall.discovered,{'wheel'})
                window.show();APP.processEvents()
                window.grab().save('/tmp/maat-hall-embedded.png')
            finally:window.close();APP.processEvents()
