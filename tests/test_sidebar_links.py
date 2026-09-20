import os
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from test_desktop import APP
import test_live_window as helpers
from apps.maat_rpg import session_shared
from gui.live_window import LiveWindow
from shared.core.achievement_catalog import snapshot

class SidebarLinksTests(unittest.TestCase):
    def test_destinations_categories_individual_and_guards(self):
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            w=LiveWindow(audio=helpers.SilentAudio())
            w.request_title_start()
            w.choose_profile(w.game._profile_slot())
            try:
                helpers.LiveWindowTest.spin(self,lambda:w.game.ready)
                w.phase='playing';w.navigate(3);w.show();APP.processEvents()
                s=w.character_sidebar
                for widget,page in [(s.hp,1),(s.hp_bar,1),(s.level,1),(s.wins,1),(s.path,1),(s.portrait,1),(s.items,5),(s.dungeon_summary,w.dungeon_index)]:
                    QTest.mouseClick(widget,Qt.LeftButton)
                    self.assertEqual(w.stack.currentIndex(),page)
                    if widget is s.items:self.assertEqual(w.world_tabs.currentIndex(),3)
                data=snapshot({});w.receive({'event':'achievements','data':data})
                QTest.keyClick(s.achievement_heading,Qt.Key_Return)
                self.assertIs(w.world_tabs.currentWidget(),w.achievements)
                s.achievement_categories.linkActivated.emit('category:Kampf')
                self.assertEqual(w.achievements.category.currentText(),'Kampf')
                s.recent_achievements.linkActivated.emit('achievement:combat%3Aboss_no_potion')
                self.assertEqual(w.achievements.category.currentText(),'Alle Kategorien')
                self.assertFalse(w.achievements.rows['combat:boss_no_potion'][0].isHidden())
                w.phase='story';page=w.stack.currentIndex();s.items.setFocus();QTest.keyClick(s.items,Qt.Key_Return)
                self.assertEqual(w.stack.currentIndex(),page)
            finally:w.game.shutdown();w.close();APP.processEvents()
