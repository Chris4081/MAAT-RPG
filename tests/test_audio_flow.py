from PySide6.QtCore import QCoreApplication, QEvent, QUrl
import os
import time
import unittest
from unittest.mock import patch
from test_desktop import APP
from apps.maat_rpg import session_shared
from gui.live_window import LiveWindow
from gui.audio_manager import AudioManager
from test_live_window import unlock_test_arena
from PySide6.QtMultimedia import QAudioBufferOutput, QMediaPlayer
from audio_fixtures import music_fixture

class AudioFlowTest(unittest.TestCase):
    def wait_for(self, predicate):
        end = time.monotonic()+10
        while not predicate() and time.monotonic()<end:
            APP.processEvents()
            time.sleep(.01)
        self.assertTrue(predicate())

    def test_music_free_menu_intro_battle_and_optional_track_delayed_stop(self):
        audio = AudioManager(backend='qt')
        audio.player.setAudioOutput(None)
        audio.fx.setAudioOutput(None)
        buffers = []
        capture = QAudioBufferOutput(audio)
        capture.audioBufferReceived.connect(lambda b: buffers.append(b.byteCount()))
        audio.player.setAudioBufferOutput(capture)
        with patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT': str(session_shared.BASE_APP_SUPPORT_DIR)}):
            unlock_test_arena()
            window = LiveWindow(audio=audio)
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
            try:
                window.show()
                self.wait_for(lambda: window.game.ready)
                window.enter_menu()
                self.assertFalse(window.music_box.isChecked())
                self.assertTrue(window.sound_box.isChecked())
                self.assertIsNone(audio.current)
                # Even explicit opt-in must tolerate the omitted soundtrack.
                audio.set_enabled(True, True)
                window.begin_game()
                self.assertEqual(window.phase, 'intro')
                self.assertIsNone(audio.current)
                self.assertEqual(audio.player.playbackState(), QMediaPlayer.StoppedState)
                window.intro.finish()
                window.perspective_screen.cards['adventure'].click()
                window.text_stream.finish()
                buffers.clear()
                window.start_battle.click()
                self.wait_for(lambda: bool(window.game.prompt_id))
                self.assertIsNone(audio.current)
                self.assertFalse(buffers)
                # Optional user music still obeys paced battle-text ownership.
                track=music_fixture(self)/'battle/music/battle_normal.mp3'
                audio.handle_event(dict(action='play',owner='test-battle',path=str(track),loop=True))
                self.wait_for(lambda: any(buffers))
                self.assertTrue(audio.current[2])
                owner = audio.current[0]
                window.text_stream.append('Noch sichtbarer Kampftext')
                window.receive({'event':'audio','action':'stop','owner':owner})
                self.assertEqual(audio.current[0], owner)
                window.text_stream.finish()
                self.assertNotIn(owner, audio.requests)
            finally:
                window.game.shutdown()
                window.close()
                window.deleteLater()
                QCoreApplication.sendPostedEvents(window, QEvent.DeferredDelete)
                # Tear down the decoder before its buffer sink is destroyed.
                audio.player.stop()
                audio.player.setSource(QUrl())
                audio.player.setAudioBufferOutput(None)
                capture.audioBufferReceived.disconnect()
                audio.deleteLater()
                QCoreApplication.sendPostedEvents(audio, QEvent.DeferredDelete)
                APP.processEvents()
