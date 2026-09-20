import os
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt,QEvent
from PySide6.QtTest import QTest
from test_desktop import APP
import test_live_window as helpers
from apps.maat_rpg import session_shared
from shared.core.minigames import CATALOG
from gui.live_window import LiveWindow

class EmbeddedMinigameTests(unittest.TestCase):
    def test_all_games_embedded_return_and_submit_once(self):
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            audio=helpers.SilentAudio();w=LiveWindow(audio=audio)
            w.request_title_start()
            w.choose_profile(w.game._profile_slot())
            try:
                helpers.LiveWindowTest.spin(self,lambda:w.game.ready)
                w.phase='playing';w.show();APP.processEvents()
                baseline=w.stack.count()
                with patch.object(w,'submit_minigame') as submit:
                    for kind in CATALOG:
                        with self.subTest(kind=kind):
                            w._minigame_grant=dict(game=kind,seed=7,ticket=kind,practice=True)
                            w.run_minigame_attempt();g=w._active_minigame['widget']
                            self.assertFalse(g.isWindow());self.assertIs(g.window(),w)
                            self.assertIs(w.stack.currentWidget(),g)
                            APP.processEvents()
                            self.assertFalse(w.input.isEnabled())
                            w.navigate(3);self.assertIs(w.stack.currentWidget(),g)
                            if kind=='maat_coil':
                                QTest.keyClick(g.board,Qt.Key_Down);self.assertEqual(g.direction,'D')
                                w.grab().save('/tmp/maat-embedded-coil.png')
                            if kind=='temple_circles':
                                QTest.keyClick(g.board,Qt.Key_3);QTest.keyClick(g.board,Qt.Key_Right)
                                self.assertEqual(g.game.moves[-1],'2R')
                            if kind=='maze':
                                before=len(g.game.moves);QTest.keyClick(g.tiles[0],Qt.Key_Right);self.assertEqual(len(g.game.moves),before+1)
                            g.reject();self.assertIsNone(w._active_minigame)
                            self.assertIs(w.stack.currentWidget(),w.game_hall)
                            self.assertFalse(g.timer.isActive());self.assertEqual(w.stack.count(),baseline)
                            self.assertEqual(submit.call_args.args[0]['op'],'hall_result')
                            count=submit.call_count;w.finish_minigame(g);self.assertEqual(submit.call_count,count)
                            self.assertEqual(audio.events[-1]['action'],'stop')
                    w._minigame_grant=dict(game='memory',seed=7,ticket='chat',id=2,attempts=2)
                    w.run_minigame_attempt();g=w._active_minigame['widget'];APP.processEvents()
                    QTest.keyClick(g,Qt.Key_Escape)
                    self.assertEqual(w.stack.currentIndex(),3)
                    self.assertEqual(submit.call_args.args[0]['op'],'minigame')
                    self.assertEqual(submit.call_args.args[0]['ticket'],'chat')
            finally:w.close();APP.processEvents()

    def test_main_window_close_stops_embedded_game_without_duplicate_submission(self):
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            w=LiveWindow(audio=helpers.SilentAudio())
            w.request_title_start()
            w.choose_profile(w.game._profile_slot())
            helpers.LiveWindowTest.spin(self,lambda:w.game.ready)
            w.phase='playing';w.show()
            w._minigame_grant=dict(game='reflex',seed=7,ticket='close',practice=True)
            w.run_minigame_attempt();g=w._active_minigame['widget'];APP.processEvents()
            with patch.object(w,'submit_minigame') as submit:
                w.close();self.assertIsNone(w._active_minigame);self.assertFalse(g.timer.isActive());submit.assert_not_called()
            APP.processEvents()
