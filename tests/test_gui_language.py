"""Global language, silent first screen, profiles, worker and music integration."""
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from test_desktop import APP, ROOT
from test_live_window import SilentAudio
from PySide6.QtCore import QCoreApplication, QEvent
from apps.maat_rpg import session_shared as shared
from gui.live_window import LiveWindow
from gui.live_session import LiveSession
from gui.audio_manager import AudioManager
from audio_fixtures import music_fixture


class ObservedAudio(SilentAudio):
    """Record when the GUI would request menu music, without playing audio."""
    def __init__(self):
        super().__init__()
        self.menu = True
        self.language = 'de'
        self.playing = None
        self.starts = []
        self.owner = None

    def select(self):
        target = self.language if self.menu and self.music_enabled else None
        if target and target != self.playing:
            self.starts.append((target, getattr(self.owner, 'phase', None)))
        self.playing = target

    def location(self, menu, language='de'):
        self.menu, self.language = menu, language
        self.select()

    def set_enabled(self, music, sound):
        self.music_enabled = bool(music)
        self.select()


class LanguageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='maat-language-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = patch.multiple(shared, BASE_APP_SUPPORT_DIR=self.root,
            PROFILES_DIR=self.root/'profiles',
            PROFILE_MANAGER_STATE_PATH=self.root/'state/profile_manager_state.json')
        self.paths.start(); self.addCleanup(self.paths.stop)
        self.env = patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT': str(self.root)})
        self.env.start(); self.addCleanup(self.env.stop)
        self.windows = []
        self.addCleanup(self.close_windows)

    def close_windows(self):
        for window in reversed(self.windows):
            window.game.shutdown(); window.close(); window.deleteLater()
            QCoreApplication.sendPostedEvents(window, QEvent.DeferredDelete)
        APP.processEvents()

    def window(self):
        audio = ObservedAudio()
        window = LiveWindow(audio=audio)
        audio.owner = window
        self.windows.append(window)
        window.show(); APP.processEvents()
        return window

    def ready(self, window):
        if window.phase == 'title' and window._startup_profile_pending:
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
        until = time.monotonic() + 12
        while not window.game.ready and time.monotonic() < until:
            APP.processEvents(); time.sleep(.01)
        self.assertTrue(window.game.ready)
        APP.processEvents(); window.ki_dialog.hide()

    def start_profile(self, window, slot=1):
        window.request_title_start()
        self.assertEqual(window.phase, 'profiles')
        if not shared.profile_slot_exists(slot):
            shared.set_profile_name(slot, 'Test adventure')
        window.choose_profile(slot)
        self.ready(window)

    def test_first_screen_is_silent_language_then_pyramid_then_profile_then_english_intro(self):
        window = self.window()
        self.assertEqual(window.phase, 'language')
        self.assertIsNone(window.game.process)
        self.assertIsNone(shared.application_language())
        self.assertFalse(window.navigation_scroll.isVisible())
        self.assertFalse(window.era.isVisible())
        self.assertFalse(window.language_screen.back.isVisible())
        self.assertEqual(window.audio.starts, [])
        window.apply_audio_settings()
        with patch.object(window.game, 'load_model') as load:
            window.prepare_startup_model(); window.request_title_start(); window.start_title_demo()
            load.assert_not_called()
        self.assertEqual(window.phase, 'language')
        self.assertEqual(window.audio.starts, [])
        window.language_screen.buttons['en'].click()
        self.assertEqual(window.phase, 'title')
        self.assertIsNone(window.game.process)
        self.assertEqual(window.audio.starts, [])
        self.assertFalse(window.music_box.isChecked())
        self.assertEqual(shared.application_language(), 'en')
        self.assertFalse(shared.profile_has_explicit_language(1))
        self.assertEqual(shared.existing_profile_slots(), [])
        self.assertEqual(window.title_screen.start_button.text(), 'PRESS ENTER TO PLAY')
        window.request_title_start()
        self.assertEqual(window.phase, 'profiles')
        self.assertFalse(hasattr(window.profile_screen, 'language_buttons'))
        self.assertNotIn('language', window.profile_screen.note.text())
        with patch('gui.live_window.QInputDialog.getText', return_value=('First journey', True)):
            window.profile_screen.create_button.click()
        self.assertNotEqual(window.phase, 'language')
        self.ready(window)
        self.assertEqual(window.game.get_snapshot().language, 'en')
        window.enter_menu()
        self.assertEqual(window.begin_button.text(), '1   Start game  →')
        self.assertEqual(window.options_button.text(), '2   Options')
        window.navigate(4); window.volume.setValue(42)
        self.assertEqual(window.volume_text.text(), 'Volume 42 %')
        window.begin_game()
        self.assertEqual(window.phase, 'intro')
        self.assertIn('Return of the Principles', window.intro.segments[0])
        event = next(e for e in reversed(window.audio.events) if e.get('owner') == 'native-intro')
        self.assertEqual(Path(event['path']).name, 'Intro_EN.mp3')
        self.assertFalse(Path(event['path']).is_file())  # Soundtrack is optional.
        window.intro.finish()
        self.assertEqual(window.phase, 'perspective')
        self.assertIn('I AM THE AI', window.perspective_screen.cards['companion'].text())

    def test_restart_remembers_global_language_and_profile_switch_never_changes_it(self):
        first = self.window(); first.select_profile_language('en')
        first.close()
        shared.write_profile_settings(1, {'language':'de', 'gui_volume':47})
        shared.write_profile_settings(2, {'language':'de', 'custom':'keep'})
        window = self.window()
        self.assertEqual(window.phase, 'title')
        self.assertFalse(window.game.needs_language_choice)
        self.assertIsNone(window.audio.playing)
        self.start_profile(window)
        window.enter_menu(); window.change_profile(1); self.ready(window)
        self.assertNotEqual(window.phase, 'language')
        self.assertEqual(window.game.get_snapshot().language, 'en')
        # Direct-reading terminal plugins get a compatible mirror on activation.
        self.assertEqual(shared.load_json_file(shared.profile_settings_path(2))['language'], 'en')
        self.assertEqual(shared.load_profile_settings(2)['custom'], 'keep')
        window.change_profile(0); self.ready(window)
        self.assertEqual(window.game.get_snapshot().language, 'en')
        self.assertEqual(shared.load_profile_settings(1)['gui_volume'], 47)
        window.enter_menu(); window.show_profile_choice()
        with patch('gui.live_window.QInputDialog.getText', return_value=('A new adventure', True)):
            window.create_profile()
        self.ready(window)
        self.assertNotEqual(window.phase, 'language')
        self.assertEqual(window.game.get_snapshot().language, 'en')

    def test_settings_change_is_global_silent_during_choice_and_preserves_profile_data(self):
        shared.write_application_language('de')
        # Explicit opt-in still works for installations with their own music.
        shared.write_profile_settings(1, {'gui_volume':61, 'custom':'keep', 'music_enabled':True})
        shared.write_profile_settings(2, {'language':'de', 'custom':'other'})
        window = self.window(); self.start_profile(window)
        old = window.game.process
        window.enter_menu(); window.navigate(4)
        window.language_button.click()
        self.assertEqual(window.phase, 'language')
        self.assertIsNone(window.audio.playing)
        starts = list(window.audio.starts)
        window.apply_audio_settings(); APP.processEvents()
        self.assertEqual(starts, window.audio.starts)
        window.language_screen.buttons['en'].click(); self.ready(window)
        self.assertIsNot(window.game.process, old)
        self.assertEqual(shared.application_language(), 'en')
        self.assertEqual(shared.profile_language(2), 'en')
        self.assertEqual(shared.load_profile_settings(1)['custom'], 'keep')
        self.assertEqual(shared.load_profile_settings(1)['gui_volume'], 61)
        self.assertEqual(window.audio.playing, 'en')
        window.enter_menu(); window.navigate(4)
        window.language_button.click(); window.language_screen.back.click()
        self.assertEqual(window.phase, 'menu')
        self.assertEqual(window.stack.currentIndex(), 4)
        self.assertEqual(shared.application_language(), 'en')
        window.phase = 'playing'; window.navigate(4); window.update_controls()
        self.assertTrue(window.language_button.isEnabled())
        window.language_button.click(); window.language_screen.back.click()
        self.assertEqual(window.phase, 'playing')
        self.assertEqual(window.stack.currentIndex(), 4)

    def test_language_change_does_not_translate_existing_chat_or_input(self):
        window = self.window()
        window.input.setText('Hauptmenü')
        window.journal.setPlainText('Die Welt erinnert sich. Deine Reise beginnt.')
        window.select_profile_language('en')
        window.apply_menu_language()
        self.assertEqual(window.input.text(), 'Hauptmenü')
        self.assertEqual(window.journal.toPlainText(), 'Die Welt erinnert sich. Deine Reise beginnt.')
        self.assertIsNone(window.game.process)

    def test_terminal_music_and_demo_copy_use_global_language_even_with_opposite_profile_value(self):
        from gui.title_screen import TitleDemo
        shared.write_application_language('en')
        shared.write_profile_settings(1, {'language':'de', 'secret':'must-not-copy'})
        demo = TitleDemo()
        with tempfile.TemporaryDirectory() as folder:
            demo.temp = SimpleNamespace(name=folder)
            demo.seed_profile(1)
            saved = json.loads((Path(folder)/'state/settings_state.json').read_text())
            self.assertEqual(saved, {'language':'en'})
            demo.temp = None
        audio = SimpleNamespace(music_enabled=True, _output_unavailable=False, requests={},
            menu=True, language='en', current=None, player=Mock(), native_music=None,
            root=music_fixture(self), status=Mock())
        AudioManager._select(audio)
        self.assertEqual(Path(audio.current[1]).name, 'menu_theme_en.mp3')
        self.assertTrue(Path(audio.current[1]).is_file())
        audio.language='de'; AudioManager._select(audio)
        self.assertEqual(Path(audio.current[1]).name, 'menu_theme.mp3')
        audio.menu=False; AudioManager._select(audio)
        self.assertIsNone(audio.current)

    def test_invalid_choice_and_save_failure_keep_first_screen_silent(self):
        window = self.window()
        self.assertFalse(window.game.set_language('fr', start_worker=False))
        with patch.object(shared, 'write_application_language', side_effect=OSError('storage failure')), \
                patch('gui.live_window.QMessageBox.warning') as warning:
            window.select_profile_language('en')
            warning.assert_called_once()
        self.assertEqual(window.phase, 'language')
        self.assertTrue(window.game.needs_language_choice)
        self.assertIsNone(window.game.process)
        self.assertEqual(window.audio.starts, [])
        self.assertIsNone(shared.application_language())

    def test_existing_profile_language_does_not_skip_first_global_choice_or_reset_progress(self):
        shared.write_profile_settings(1, {'language':'en', 'gui_volume':23, 'gui_perspective':'companion'})
        state=shared.profile_slot_root(1)/'state/battle_state.json'
        state.write_text(json.dumps({'player':{'level':34}, 'stats':{'fights_won':120}}))
        before=state.read_bytes()
        window=self.window()
        self.assertEqual(window.phase,'language')
        self.assertEqual(window.audio.starts,[])
        window.select_profile_language('de')
        self.assertEqual(state.read_bytes(),before)
        self.assertEqual(shared.load_profile_settings(1)['gui_volume'],23)
        self.assertEqual(shared.load_profile_settings(1)['gui_perspective'],'companion')
        self.assertEqual(shared.profile_language(1),'de')
        self.assertIsNone(window.game.process)

    def test_language_storage_is_atomic_and_is_not_removed_with_a_profile(self):
        shared.write_application_language('de')
        before=shared.application_settings_path().read_bytes()
        with patch.object(shared.os,'replace',side_effect=OSError('replacement failed')):
            with self.assertRaises(OSError):shared.write_application_language('en')
        self.assertEqual(shared.application_settings_path().read_bytes(),before)
        self.assertEqual(list(shared.application_settings_path().parent.glob('.app-language-*')),[])
        shared.write_application_language('en')
        shared.set_profile_name(2,'Disposable test')
        shared.delete_profile_slot(2)
        self.assertEqual(shared.application_language(),'en')
        self.assertEqual(shared.existing_profile_slots(),[])


if __name__ == '__main__':
    unittest.main()
