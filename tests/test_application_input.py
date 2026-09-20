"""Regress the Intel crash path: create/delete buttons while updating the UI."""
import unittest
from unittest.mock import patch
from test_desktop import APP
from PySide6.QtCore import QCoreApplication, QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QWidget, QPushButton
from gui.application_input import ApplicationInputFilter
import test_gui_language as helpers
from apps.maat_rpg import session_shared as shared


class FilterBoundaryTests(unittest.TestCase):
    def test_lifecycle_events_do_not_touch_window_or_widget(self):
        window = QObject()
        guard = ApplicationInputFilter(window)
        for kind in (QEvent.Create, QEvent.Destroy, QEvent.ChildAdded, QEvent.ChildRemoved,
                     QEvent.Paint, QEvent.Polish, QEvent.DeferredDelete):
            self.assertFalse(guard.eventFilter(object(), QEvent(kind)))

    def test_python_error_cannot_escape_into_shiboken_override(self):
        window = QObject()
        def fail(*args): raise RuntimeError('synthetic input-handler failure')
        window.handle_application_input = fail
        guard = ApplicationInputFilter(window)
        with patch('gui.application_input.diagnostic_exception') as log:
            self.assertFalse(guard.eventFilter(window, QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)))
        log.assert_called_once_with('application_input_failed')


class LiveFilterTests(unittest.TestCase):
    setUp = helpers.LanguageTests.setUp
    close_windows = helpers.LanguageTests.close_windows
    window = helpers.LanguageTests.window

    def test_button_construction_and_profile_level_updates_during_partial_output(self):
        shared.write_application_language('en')
        window = self.window()
        window.title_idle.stop()
        window.phase='playing'; window.navigate(3)
        snapshot = window.game.get_snapshot()
        with patch('gui.application_input.diagnostic_exception') as errors:
            for level in range(2, 52):
                window.receive(dict(event='output', text='Your journey continues. ' * 4))
                window.text_stream.advance()
                window.receive(dict(event='level_up', level=level, title='Traveller', max_hp=100+level*10, language='en'))
                snapshot.player.level=level
                snapshot.player.max_hp=100+level*10
                window.apply_snapshot(snapshot)
                window.receive(dict(event='dungeons', level=level, records={'0':{'completed':level, 'best_room':5}}, plus={}))
                # Match the native report's QPushButton construction from a
                # dynamic UI refresh while the global input filter is active.
                panel = QWidget(window)
                for i in range(40): QPushButton(f'Level {level}: talent {i}', panel)
                panel.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                APP.processEvents()
                window.text_stream.finish()
            errors.assert_not_called()
        self.assertTrue(window.isVisible())
        self.assertEqual(window.game.get_snapshot().player.level, 51)
        self.assertIn('Level 51', window.chat_level_text.text())
        self.assertFalse(window.level_up_notice.grab().isNull())
