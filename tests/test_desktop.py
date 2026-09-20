from PySide6.QtCore import QCoreApplication, QEvent
"""Run: QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'maatos'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
_SANDBOX = tempfile.TemporaryDirectory(prefix='maat-gui-test-')
_home = patch('pathlib.Path.home', return_value=Path(_SANDBOX.name))
_home.start()
from PySide6.QtWidgets import QApplication
from apps.maat_rpg.session_controller import MaatRpgSession
from apps.maat_rpg.session_shared import xp_needed_for_level, write_profile_settings, write_application_language
write_application_language('de')
write_profile_settings(1, {'language': 'de'})
from gui.desktop import MaatWindow
APP = QApplication.instance() or QApplication([])


class DesktopTest(unittest.TestCase):
    def setUp(self):
        self.window = MaatWindow()
        self.s = self.window.session

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(self.window, QEvent.DeferredDelete)
        APP.processEvents()

    def test_navigation_and_render(self):
        self.window.resize(1220, 840)
        self.window.show()
        APP.processEvents()
        for i, name in enumerate(['menu', 'character', 'battle', 'journal', 'settings']):
            self.window.nav_buttons[i].click()
            if i == 2:
                self.window.start_battle.click()
            APP.processEvents()
            self.assertEqual(self.window.stack.currentIndex(), i)
            if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                target = Path(os.environ['MAAT_GUI_SCREENSHOTS'])
                target.mkdir(parents=True, exist_ok=True)
                self.assertTrue(self.window.grab().save(str(target / f'{name}.png')))
        self.window.resize(880, 650)
        APP.processEvents()
        self.assertLessEqual(self.window.minimumSizeHint().width(), 880)

    def test_battle_and_rewards(self):
        p = self.s.get_snapshot().player
        p.xp = xp_needed_for_level(p.level + 1) - 1
        old_level, gold = p.level, p.gold
        self.window.start_battle.click()
        self.assertEqual(self.window.stack.currentIndex(), 2)
        self.assertFalse(self.window.action_buttons['impulse'].isEnabled())
        before = self.s.get_snapshot().battle.enemy_hp
        self.s.handle_battle_action('impulse')
        self.assertEqual(self.s.get_snapshot().battle.enemy_hp, before)
        for _ in range(6):
            self.window.action_buttons['attack'].click()
        self.assertFalse(self.s.get_snapshot().battle.active)
        self.assertEqual(p.gold, gold + 12)
        self.assertEqual(p.level, old_level + 1)
        self.assertIn('besiegt', self.window.battle_log.text())

    def test_retreat_and_empty_potion(self):
        self.s.send_command('/fight')
        p = self.s.get_snapshot().player
        p.potions = 0
        hp = p.hp
        self.s.handle_battle_action('potion')
        self.assertEqual(p.hp, hp)
        gold = p.gold
        self.s.handle_battle_action('escape')
        self.assertFalse(self.s.get_snapshot().battle.active)
        self.assertEqual(p.gold, gold)
        self.assertNotIn('Demo-Gegner ist besiegt', self.window.journal.toPlainText())

    def test_defeat_and_profile_switch(self):
        self.s.send_command('/fight')
        self.s.get_snapshot().player.hp = 1
        self.s.handle_battle_action('attack')
        self.assertFalse(self.s.get_snapshot().battle.active)
        self.assertEqual(self.s.get_snapshot().player.hp, 0)
        self.s.send_command('/fight')
        self.assertGreater(self.s.get_snapshot().player.hp, 0)
        original = self.window.profiles.currentIndex()
        other = (original + 1) % self.window.profiles.count()
        self.window.profiles.setCurrentIndex(other)
        self.assertFalse(self.s.get_snapshot().battle.active)
        self.window.profiles.setCurrentIndex(original)

    def test_chat_plain_text(self):
        self.window.input.setText('<b>hallo</b>')
        self.window.send()
        self.assertIn('<b>hallo</b>', self.window.journal.toPlainText())
        self.window.input.setText('/clear')
        self.window.send()
        self.assertEqual(self.window.journal.toPlainText(), '')


if __name__ == '__main__':
    unittest.main()
