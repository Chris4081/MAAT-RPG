"""Native dungeon rows survive level/profile/language changes without reconstruction."""
import unittest
from unittest.mock import patch
from test_desktop import APP
from PySide6.QtCore import QCoreApplication, QEvent
from gui.dungeons import Dungeons


class DungeonRefreshTests(unittest.TestCase):
    def setUp(self):
        self.page=Dungeons();self.page.resize(800,650);self.page.show()
        APP.processEvents()

    def tearDown(self):
        self.page.close();self.page.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)

    def test_levels_records_and_language_reuse_existing_widgets_and_connections(self):
        page=self.page;body=page.scroll.widget()
        original={key:row for key,row in page.rows.items()}
        page.set_ready(True)
        selected=[];page.enter_requested.connect(selected.append)
        # Every ordinary level until the first extra catalog row needs no new
        # widget at all, including record updates and English/German changes.
        with patch('gui.dungeons.QPushButton',side_effect=AssertionError('Unexpected button reconstruction')):
            for language in ('en','de','en'):
                page.set_language(language)
                for level in range(1,50):
                    page.update_data(level,{'0':{'completed':level,'best_room':5}})
                    self.assertIs(page.scroll.widget(),body)
                    self.assertEqual(page.rows,original)
                    self.assertEqual(page.buttons[0][0].isEnabled(),level>=10)
                page.buttons[0][0].click()
        self.assertEqual(selected,[0,0,0])
        self.assertEqual(page.buttons[0][0].text(),'Enter dungeon')
        self.assertIn('49',page.rows[0][2].text())

    def test_new_destination_added_once_then_reused_after_profile_switch(self):
        page=self.page
        page.update_data(50,{}, {'best_wave':12,'attempts':2})
        self.assertEqual(len(page.rows),10)
        added=page.rows[9]
        page.set_ready(True)
        self.assertTrue(page.plus_button.isEnabled())
        self.assertIn('12',page.plus_info.text())
        with patch('gui.dungeons.QPushButton',side_effect=AssertionError('Unexpected button reconstruction')):
            page.update_data(1,{})
            self.assertEqual(len(page.buttons),9)
            self.assertTrue(added[0].isHidden())
            self.assertFalse(page.plus_button.isEnabled())
            page.update_data(50,{'9':{'completed':1}})
            self.assertIs(page.rows[9],added)
            self.assertFalse(added[0].isHidden())
