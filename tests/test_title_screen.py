from PySide6.QtCore import QCoreApplication, QEvent
import os
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from test_desktop import APP
from test_live_window import SilentAudio
from apps.maat_rpg import session_shared
from gui.live_window import LiveWindow
from gui.title_screen import TitleDemo, TitleScreen

class TitleScreenTest(unittest.TestCase):
    def spin(self, condition, seconds=15):
        end = time.monotonic()+seconds
        while not condition() and time.monotonic()<end:
            APP.processEvents()
            time.sleep(.01)
        self.assertTrue(condition())

    def test_attack_hp_updates_at_visible_effect_and_not_twice(self):
        screen=TitleScreen()
        try:
            screen.present({'event':'battle','enemy_hp':100,'enemy_max_hp':100,'player_hp':80,'player_max_hp':100})
            screen.present({'event':'battle_effect','attacker':'player','attack':'Harmonie','damage':30,'enemy_hp':70,'player_hp':80})
            self.assertEqual(screen.health.value(),70)
            screen.present({'event':'battle_effect','attacker':'enemy','attack':'normal','damage':20,'enemy_hp':70,'player_hp':60})
            self.assertEqual(screen.arena.hero_hp.value(),80)
            for _ in range(7): screen.arena.stage.advance_effect()
            self.assertEqual(screen.arena.hero_hp.value(),60)
            screen.present({'event':'battle','enemy_hp':70,'player_hp':60})
            self.assertEqual(screen.health.value(),70)
            self.assertEqual(screen.arena.hero_hp.value(),60)
        finally:
            screen.arena.stage.clear_effects()
            screen.deleteLater()
            QCoreApplication.sendPostedEvents(screen,QEvent.DeferredDelete)

    def test_title_enter_timeout_and_abort(self):
        with patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            window = LiveWindow(audio=SilentAudio())
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
            try:
                # No navigation frame or empty scroll-area gutter on the first
                # native show, while loading, or after a demo returns to title.
                self.assertTrue(window.navigation_scroll.isHidden())
                window.showMaximized()
                APP.processEvents()
                self.assertFalse(window.navigation_scroll.isVisible())
                self.spin(lambda: window.game.ready)
                self.assertEqual(window.phase, 'title')
                self.assertFalse(window.navigation_scroll.isVisible())
                window.receive({'event':'model','status':'ready','name':'test.gguf'})
                self.assertFalse(window.begin_button.isVisible())
                self.assertFalse(window.profile_badge.isVisible())
                self.assertEqual(window.title_idle.interval(), 20000)
                self.assertEqual(window.title_screen.start_button.text(), 'PRESS ENTER TO PLAY')
                window.title_screen.flash()
                self.assertFalse(window.title_screen.lit)
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    window.title_screen.flash()
                    window.grab().save(str(Path(os.environ['MAAT_GUI_SCREENSHOTS'])/'title-screen.png'))
                QTest.keyClick(window.title_screen, Qt.Key_Return)
                self.assertEqual(window.phase, 'menu')
                self.assertFalse(window.title_idle.isActive())
                window._started = True
                snapshot = window.game.get_snapshot()
                worker = window.game.process
                QTest.mouseClick(window.menu_pyramid, Qt.LeftButton)
                self.assertEqual(window.phase, 'title')
                self.assertIs(window.stack.currentWidget(), window.title_screen)
                self.assertTrue(window.title_idle.isActive())
                self.assertEqual(window.title_idle.interval(), 20000)
                self.assertTrue(window._started)
                self.assertIs(window.game.process, worker)
                self.assertEqual(window.game.get_snapshot(), snapshot)
                window.title_idle.timeout.emit()
                self.assertEqual(window.phase, 'title_demo')
                self.assertFalse(window.navigation_scroll.isVisible())
                self.spin(lambda: window.title_screen.health.maximum() > 1)
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    window.grab().save(str(Path(os.environ['MAAT_GUI_SCREENSHOTS'])/'title-demo.png'))
                private = Path(window.title_demo.temp.name)
                self.assertNotEqual(private, session_shared.BASE_APP_SUPPORT_DIR)
                self.spin(lambda: window.title_demo.finished)
                for _ in range(2000):
                    if window.phase != 'title_demo' or window._demo_return_pending:
                        break
                    window.title_demo.advance()
                self.spin(lambda: window.phase == 'title')
                self.assertEqual(window.phase, 'title')
                self.assertEqual(window.demo_stage, 1)
                self.assertFalse(window.navigation_scroll.isVisible())
                self.assertFalse(private.exists())
                window.start_title_demo()
                private = Path(window.title_demo.temp.name)
                QTest.keyClick(window.title_screen, Qt.Key_Return)
                self.assertEqual(window.phase, 'menu')
                self.assertIsNone(window.title_demo.process)
                self.spin(lambda: not private.exists())
                self.assertFalse(private.exists())
                self.assertFalse(window.game.get_snapshot().battle.active)
                QTest.keyClick(window.menu_pyramid, Qt.Key_Space)
                self.assertEqual(window.phase, 'title')
                QTest.keyClick(window.title_screen, Qt.Key_Return)
                self.assertEqual(window.phase, 'menu')
                self.assertTrue(window._started)
                window.phase='playing';window.navigate(3)
                self.assertTrue(window.navigation_scroll.isVisible())
                self.assertTrue(window.nav_buttons[3].isVisible())
                window.navigate(0)
                self.assertFalse(window.navigation_scroll.isVisible())
                window.show_title()
                self.assertFalse(window.navigation_scroll.isVisible())
                self.assertFalse(window.character_sidebar.isVisible())
            finally:
                window.game.shutdown()
                window.close()
                window.deleteLater()
                QCoreApplication.sendPostedEvents(window, QEvent.DeferredDelete)
                APP.processEvents()

    def test_original_demo_produces_battle_frames_without_player_input(self):
        for stage in range(3):
            with self.subTest(stage=stage):
                runner = TitleDemo()
                try:
                    seen = []
                    runner.presented.connect(seen.append)
                    runner.start(stage)
                    self.spin(lambda: runner.finished, seconds=25)
                    events = seen + list(runner.queue)
                    self.assertFalse([e for e in events if e['event']=='error'])
                    hud=next(e for e in events if e['event']=='battle' and e.get('enemy_name') and 'enemy_max_hp' in e)
                    self.assertEqual(hud['arena_difficulty'],('easy','normal','hard')[stage])
                    screen=TitleScreen()
                    screen.present(hud)
                    self.assertTrue(screen.enemy.text().startswith('● '))
                    self.assertIn('DEMO', screen.arena.difficulty_badge.text())
                    screen.deleteLater()
                    QCoreApplication.sendPostedEvents(screen,QEvent.DeferredDelete)
                    self.assertTrue(any(e['event']=='audio' and e.get('loop') for e in events))
                    effects=[e for e in events if e['event']=='battle_effect']
                    self.assertTrue(effects)
                    self.assertTrue(all('enemy_hp' in e and 'player_hp' in e for e in effects))
                finally:
                    runner.stop()
                    runner.deleteLater()
                    QCoreApplication.sendPostedEvents(runner, QEvent.DeferredDelete)
                    APP.processEvents()
