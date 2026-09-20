import sys,tempfile,time,unittest,shlex
from pathlib import Path
from unittest.mock import patch
from test_desktop import APP
import test_native_audio
from PySide6.QtCore import QCoreApplication,QEvent
from gui.native_audio import NativeAudioChannel
from audio_fixtures import music_fixture

def fake_player(path, code):
    # A shebang cannot contain a Python interpreter path with spaces.
    script=path.with_suffix('.py')
    script.write_text(code)
    path.write_text('#!/bin/sh\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(script))+' "$@"\n')
    path.chmod(0o755)

class RecoveryTests(unittest.TestCase):
    wait_for=test_native_audio.NativeAudioTest.wait_for
    def test_same_volume_and_serialized_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            fake=Path(folder)/'audio'
            fake_player(fake, 'import time\ntime.sleep(10)\n')
            c=NativeAudioChannel(str(fake))
            try:
                c.play('first');first=c.process
                c.set_volume(c.volume);self.assertFalse(c.volume_timer.isActive())
                c.play('second')
                self.assertIsNone(c.process)
                self.assertIn(first,c._retired)
                self.wait_for(lambda:c.process is not None)
                self.assertFalse(c._retired)
                for value in (.2,.3,.4):c.set_volume(value)
                self.assertTrue(c.volume_timer.isActive())
                c.stop();APP.processEvents()
                self.assertFalse(c.restart_timer.isActive());self.assertIsNone(c.path)
            finally:
                c.close();c.deleteLater();QCoreApplication.sendPostedEvents(c,QEvent.DeferredDelete);APP.processEvents()
    def test_queue_failure_retries_are_bounded_and_cancelable(self):
        with tempfile.TemporaryDirectory() as folder:
            fake=Path(folder)/'audio';count=Path(folder)/'count'
            fake_player(fake, f'from pathlib import Path\nimport sys\np=Path({str(count)!r})\np.write_text(str(int(p.read_text())+1) if p.exists() else "1")\nprint("Error: AudioQueueStart failed",file=sys.stderr)\nsys.exit(1)\n')
            c=NativeAudioChannel(str(fake));errors=[];c.error.connect(errors.append)
            try:
                c.play('track',True);self.wait_for(lambda:bool(errors))
                self.assertEqual(count.read_text(),'3');self.assertEqual(len(errors),1)
                self.assertIsNone(c.path);self.assertFalse(c.restart_timer.isActive())
                c.play('track');self.wait_for(lambda:c.restart_timer.isActive())
                c.stop();self.assertFalse(c.restart_timer.isActive())
            finally:
                c.close();c.deleteLater();QCoreApplication.sendPostedEvents(c,QEvent.DeferredDelete);APP.processEvents()
    def test_native_failure_switches_music_to_qt(self):
        from gui.audio_manager import AudioManager
        with patch('gui.audio_manager.shutil.which',return_value='/usr/bin/afplay'),patch('gui.audio_manager.sys.platform','darwin'):
            a=AudioManager()
            a.root=music_fixture(self)
            a.music_enabled=True
            try:
                a.native_music.play=lambda *args:None
                with patch.object(a.player,'play') as play:
                    a.location(True)
                    track=a.current[1]
                    a.native_music.error.emit('AudioQueueStart failed')
                    self.assertTrue(a._native_music_failed)
                    self.assertEqual(a.player.source().toLocalFile(),track)
                    play.assert_called_once()
                    with patch.object(a.native_music,'set_volume') as native_volume:
                        a.set_volume(45);native_volume.assert_not_called()
                    self.assertAlmostEqual(a.output.volume(),.45,places=5)
            finally:
                a.close();a.deleteLater();QCoreApplication.sendPostedEvents(a,QEvent.DeferredDelete);APP.processEvents()
