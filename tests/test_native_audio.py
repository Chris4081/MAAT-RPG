import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path
from test_desktop import APP
from PySide6.QtCore import QCoreApplication, QEvent
from gui.native_audio import NativeAudioChannel
from audio_fixtures import music_fixture

class NativeAudioTest(unittest.TestCase):
    def wait_for(self, predicate):
        end = time.monotonic()+5
        while not predicate() and time.monotonic()<end:
            APP.processEvents()
            time.sleep(.01)
        self.assertTrue(predicate())

    def test_loop_switch_stop_and_natural_end(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder)/'fake-afplay'
            executable.write_text('#!/bin/sh\nsleep 0.08\n')
            executable.chmod(0o755)
            channel = NativeAudioChannel(str(executable))
            ended, errors = [], []
            channel.ended.connect(lambda: ended.append(True))
            channel.error.connect(errors.append)
            try:
                channel.play('battle.mp3', True)
                initial = channel.process
                self.wait_for(lambda: channel.process is not initial)
                self.assertFalse(ended)
                channel.play('intro.mp3', False)
                self.wait_for(lambda: bool(ended))
                self.assertIsNone(channel.process)
                channel.play('battle.mp3', True)
                channel.stop()
                self.wait_for(lambda: not channel._retired)
                self.assertIsNone(channel.path)
                self.assertEqual(len(ended), 1)
                self.assertFalse(errors)
            finally:
                channel.close()
                channel.deleteLater()
                QCoreApplication.sendPostedEvents(channel, QEvent.DeferredDelete)
                APP.processEvents()

    def test_mac_manager_uses_native_channel_for_intro(self):
        from gui.audio_manager import AudioManager
        calls = []
        def record(channel, path, loop=False):
            calls.append((path, loop))
        with patch('gui.audio_manager.sys.platform', 'darwin'), patch('gui.audio_manager.shutil.which', return_value='/usr/bin/afplay'):
            audio = AudioManager()
            audio.root = music_fixture(self)
            audio.music_enabled = True
            audio.native_music.play = lambda path, loop=False: calls.append((path, loop))
            try:
                path = audio.root / 'rpg_intro/intro.mp3'
                audio.location(False)
                audio.handle_event({'action':'play', 'owner':'intro', 'path':str(path), 'loop':False})
                self.assertEqual(calls, [(str(path.resolve()), False)])
                self.assertTrue(audio.player.source().isEmpty())
                audio.set_enabled(False, False)
                self.assertIsNone(audio.current)
            finally:
                audio.close()
                audio.deleteLater()
                QCoreApplication.sendPostedEvents(audio, QEvent.DeferredDelete)
                APP.processEvents()
