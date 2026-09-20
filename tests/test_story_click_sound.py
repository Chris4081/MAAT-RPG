import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from test_desktop import APP
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from gui.audio_manager import AudioManager
from gui.intro_screen import IntroScreen
from gui.story_screen import StoryScreen


class StoryClickTests(unittest.TestCase):
    def dispose(self, obj):
        obj.close()
        obj.deleteLater()
        QCoreApplication.sendPostedEvents(obj, QEvent.DeferredDelete)
        APP.processEvents()

    def test_keyboard_artwork_text_and_button_emit_once_per_input(self):
        for screen_type in (IntroScreen, StoryScreen):
            with self.subTest(screen=screen_type.__name__):
                screen = screen_type()
                sounds = []
                screen.audio_requested.connect(lambda e:sounds.append(e) if e.get('action') == 'ui_sound' else None)
                try:
                    screen.show()
                    if isinstance(screen, StoryScreen):
                        screen.start_scene(dict(id='click-test', lines=['Eine Geschichte beginnt.']*6))
                    else:
                        screen.start('de')
                    APP.processEvents()
                    screen.text.setFocus()
                    APP.processEvents()
                    screen.timer.stop()
                    self.assertFalse(sounds)
                    inputs = [lambda:QTest.keyClick(screen.text, Qt.Key_Return),
                              lambda:QTest.keyClick(screen.text, Qt.Key_Enter),
                              lambda:QTest.mouseClick(screen.artwork, Qt.LeftButton),
                              lambda:QTest.mouseClick(screen.text.viewport(), Qt.LeftButton),
                              lambda:QTest.mouseClick(screen.next_button, Qt.LeftButton),
                              lambda:QTest.keyClick(screen.next_button, Qt.Key_Return)]
                    for count, action in enumerate(inputs, 1):
                        action()
                        self.assertEqual(len(sounds), count)
                        self.assertEqual(sounds[-1]['name'], 'story_advance')
                    before = len(sounds)
                    # Holding Enter must not repeatedly advance/read-click pages.
                    QCoreApplication.sendEvent(screen.text, QKeyEvent(QEvent.KeyPress, Qt.Key_Return,
                        Qt.NoModifier, '\r', True, 1))
                    self.assertEqual(len(sounds), before)
                    screen.tick()
                    screen.advance()
                    self.assertEqual(len(sounds), before)
                    screen.cancel()
                    screen.advance_from_input()
                    self.assertEqual(len(sounds), before)
                finally:
                    screen.cancel()
                    self.dispose(screen)

    def test_final_click_follows_scene_audio_cleanup(self):
        screen = StoryScreen()
        events = []
        screen.audio_requested.connect(events.append)
        screen.completed.connect(lambda:events.append({'action':'clear'}))
        try:
            screen.start_scene(dict(id='last', lines=['Ende.']))
            screen.advance()
            events.clear()
            screen.advance_from_input()
            self.assertEqual([e['action'] for e in events], ['stop', 'clear', 'ui_sound'])
            self.assertFalse(screen.running)
        finally:
            screen.cancel()
            self.dispose(screen)

    def test_click_uses_mutable_fx_channel_and_leaves_music_running(self):
        with patch('gui.audio_manager.sys.platform', 'darwin'), \
                patch('gui.audio_manager.shutil.which', return_value='/usr/bin/afplay'):
            audio = AudioManager()
        try:
            with patch.object(audio.native_music, 'play') as music, patch.object(audio.native_fx, 'play') as fx:
                audio.location(True)
                playing = audio.current
                music.reset_mock()
                audio.handle_event({'action':'ui_sound', 'name':'story_advance'})
                fx.assert_called_once()
                path = fx.call_args.args[0]
                self.assertTrue(Path(path).is_file())
                with wave.open(str(path)) as wav:
                    self.assertEqual((wav.getnchannels(), wav.getsampwidth(), wav.getframerate()), (2, 2, 48000))
                    self.assertLess(wav.getnframes()/48000, .2)
                self.assertEqual(audio.current, playing)
                music.assert_not_called()
                audio.set_enabled(True, False)
                audio.handle_event({'action':'ui_sound', 'name':'story_advance'})
                self.assertEqual(fx.call_count, 1)
                audio.set_enabled(False, True)
                audio.set_volume(20)
                audio.handle_event({'action':'ui_sound', 'name':'story_advance'})
                self.assertEqual(fx.call_count, 2)
                self.assertEqual(audio.native_fx.volume, .2)
                self.assertIsNone(audio.current)
        finally:
            self.dispose(audio)
