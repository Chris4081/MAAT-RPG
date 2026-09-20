from PySide6.QtCore import QCoreApplication, QEvent
import os
os.environ.setdefault('QT_MEDIA_BACKEND', 'ffmpeg')
from pathlib import Path
import time
import unittest
from test_desktop import APP
from PySide6.QtMultimedia import QAudioBufferOutput, QMediaPlayer
from gui.audio_manager import AudioManager
from audio_fixtures import music_fixture


class AudioTest(unittest.TestCase):
    def test_menu_battle_resume_mute_and_decode(self):
        audio = AudioManager(backend='qt')
        audio.root = music_fixture(self)
        audio.music_enabled = True
        # Decode without routing sound to a physical output during automated tests.
        audio.player.setAudioOutput(None)
        decoded = []
        capture = QAudioBufferOutput(audio)
        capture.audioBufferReceived.connect(lambda buffer: decoded.append(buffer.byteCount()))
        audio.player.setAudioBufferOutput(capture)
        try:
            audio.location(True)
            self.assertEqual(audio.current[0], 'menu')
            deadline = time.monotonic()+5
            while not any(decoded) and time.monotonic()<deadline:
                APP.processEvents()
                time.sleep(.01)
            self.assertTrue(any(decoded), 'Menu MP3 must produce decoded PCM samples')
            decoded.clear()
            path = audio.root / 'battle/music/battle_normal.mp3'
            audio.handle_event({'action':'play', 'owner':'battle', 'path':str(path), 'loop':True})
            self.assertEqual(audio.current[0], 'battle')
            deadline = time.monotonic()+5
            while not any(decoded) and time.monotonic()<deadline:
                APP.processEvents()
                time.sleep(.01)
            self.assertTrue(any(decoded), 'Battle MP3 must produce decoded PCM samples')
            audio.set_enabled(False, False)
            self.assertIsNone(audio.current)
            self.assertEqual(audio.player.playbackState(), QMediaPlayer.StoppedState)
            audio.set_enabled(True, True)
            self.assertEqual(audio.current[0], 'battle')
            audio.handle_event({'action':'stop', 'owner':'battle'})
            self.assertEqual(audio.current[0], 'menu')
            audio.set_volume(19)
            self.assertAlmostEqual(audio.output.volume(), .19, places=5)
        finally:
            audio.close()
            audio.deleteLater()
            QCoreApplication.sendPostedEvents(audio, QEvent.DeferredDelete)
            APP.processEvents()
