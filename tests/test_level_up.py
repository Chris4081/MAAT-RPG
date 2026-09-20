"""Level rewards and desktop presentation, using only isolated saves."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_desktop import APP
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit
from apps.maat_rpg.plugins.battle import plugin_main as battle
from shared.core import gui_bridge
from gui.level_up_notice import LevelUpNotice
import test_gui_language as helpers
from apps.maat_rpg import session_shared as shared


class LevelRewardTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='maat-level-reward-')
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.events = []
        gui_bridge.install(lambda kind, **data: self.events.append(dict(event=kind, **data)))
        self.addCleanup(gui_bridge.install, None)

    def test_chat_levelup_keeps_xp_count_hp_and_saved_progress(self):
        plugin = battle.Plugin.__new__(battle.Plugin)
        plugin.plugin_dir = str(self.folder)
        plugin.state = battle.BattleState.__new__(battle.BattleState)
        plugin.state.state = plugin.state._default()
        plugin.state.state_path = str(self.folder/'battle_state.json')
        player = plugin.state.state['player']
        player.update(xp=plugin.state.xp_needed_for_level(2)-1, hp=120, max_hp=120)
        output = io.StringIO()
        with patch.object(battle, 'play_levelup_sound') as sound, \
                patch.object(battle, '_lu_particles') as stars, \
                patch.object(battle, '_battle_ui_language', return_value='en'), redirect_stdout(output):
            plugin._credit_chat_message('We explore Terra together with respect.', {})
        self.assertEqual(player['level'], 2)
        self.assertEqual(player['max_hp'], 130)
        self.assertEqual(plugin.state.state['stats']['messages_total'], 1)
        self.assertEqual(json.loads(Path(plugin.state.state_path).read_text())['player'], player)
        notices = [e for e in self.events if e['event']=='level_up']
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0]['max_hp'], 130)
        self.assertEqual(notices[0]['language'], 'en')
        self.assertNotIn('✨', output.getvalue())
        stars.assert_not_called()
        sound.assert_called_once()

    def test_terminal_animation_and_sound_are_preserved(self):
        gui_bridge.install(None)
        with patch.object(battle, 'play_levelup_sound') as sound, \
                patch.object(battle.time, 'sleep'), redirect_stdout(io.StringIO()) as output:
            battle.run_levelup_fx(2, None, str(self.folder))
        self.assertEqual(output.getvalue().count('✨'), 91)
        self.assertIn('LEVEL UP!', output.getvalue())
        sound.assert_called_once()
        self.assertFalse(self.events)


class LevelNoticeTests(unittest.TestCase):
    def test_notice_renders_in_both_languages_without_stealing_input_or_leaking_timer(self):
        host = QWidget(); layout = QVBoxLayout(host)
        notice = LevelUpNotice(host); entry = QLineEdit(host)
        layout.addWidget(notice); layout.addWidget(entry)
        host.resize(720, 230); host.show(); host.activateWindow()
        APP.processEvents(); entry.setFocus(); APP.processEvents()
        try:
            for language, expected in [('de','Levelaufstieg'), ('en','Level up')]:
                notice.present(dict(level=15, title='Resonance Master', max_hp=240, language=language))
                APP.processEvents()
                self.assertTrue(notice.isVisible())
                self.assertTrue(entry.hasFocus())
                self.assertIn(expected, notice.heading.text())
                self.assertFalse(notice.grab().isNull())
                self.assertEqual(notice.heading.textFormat(), Qt.PlainText)
                self.assertTrue(notice.timer.isActive())
                notice.timer.timeout.emit()
                self.assertTrue(notice.isHidden())
                self.assertFalse(notice.timer.isActive())
            notice.present(dict(level=16, language='en'))
            self.assertIn('16', notice.heading.text())
        finally:
            host.close(); host.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


class LiveLevelTests(unittest.TestCase):
    setUp = helpers.LanguageTests.setUp
    close_windows = helpers.LanguageTests.close_windows
    window = helpers.LanguageTests.window

    def test_partial_chat_stream_level_notice_menu_and_next_input(self):
        shared.write_application_language('en')
        window = self.window()
        window.title_idle.stop()
        window.phase = 'playing'; window.navigate(3)
        window.receive(dict(event='output', text='Your journey continues. ' * 20))
        for _ in range(12): window.text_stream.advance()
        self.assertTrue(window.text_stream.running)
        window.receive(dict(event='level_up', level=2, title='Explorer', max_hp=110, language='en'))
        self.assertTrue(window.level_up_notice.isVisible())
        window.text_stream.finish(); APP.processEvents()
        self.assertEqual(window.journal.toPlainText().count('Level up · Level 2'), 1)
        self.assertIn('Your journey continues.', window.journal.toPlainText())
        self.assertNotIn('✨', window.journal.toPlainText())
        window.navigate(0)
        self.assertTrue(window.level_up_notice.isHidden())
        self.assertFalse(window.level_up_notice.timer.isActive())
        window.phase='playing'; window.navigate(3)
        window.receive(dict(event='output', text='Ready for the next message.'))
        window.text_stream.finish()
        self.assertTrue(window.isVisible())
        self.assertTrue(window.journal.toPlainText().endswith('Ready for the next message.'))
