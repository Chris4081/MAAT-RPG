import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from PySide6.QtCore import QTimer, QCoreApplication, QEvent, QUrl
from PySide6.QtMultimedia import QMediaPlayer
from test_desktop import APP
from gui.audio_process import AudioProcess


class AudioIsolationTests(unittest.TestCase):
    def spin(self, condition, seconds=5):
        deadline=time.monotonic()+seconds
        while not condition() and time.monotonic()<deadline:
            APP.processEvents(); time.sleep(.005)
        self.assertTrue(condition())

    def test_hung_output_times_out_while_gui_remains_responsive_and_recovers(self):
        with tempfile.TemporaryDirectory(prefix='maat-audio-ipc-') as folder:
            helper=Path(folder)/'helper.py'
            helper.write_text('''import json, sys, time
def emit(**kw): print(json.dumps(kw), flush=True)
emit(event='devices', outputs=[['safe','Test speaker']])
emit(event='device_ready', available=True)
for line in sys.stdin:
    m=json.loads(line)
    if m['op']=='device':
        emit(event='device_changing')
        if m['identifier']=='stuck': time.sleep(60)
        emit(event='device_ready', available=True)
    emit(event='ack', id=m['id'])
''')
            audio=AudioProcess(command=[sys.executable,'-u',str(helper)],timeout_ms=450)
            errors=[];audio.error.connect(errors.append)
            ticks=[]; timer=QTimer(); timer.setInterval(10); timer.timeout.connect(lambda:ticks.append(True));timer.start()
            try:
                self.spin(lambda:bool(audio.devices) and not audio._pending)
                start=len(ticks)
                audio.select_output('stuck')
                self.spin(lambda:bool(errors))
                self.assertGreater(len(ticks)-start,15)
                self.assertIn('reagiert nicht',errors[-1])
                self.spin(lambda:not audio._retired)
                audio.select_output('safe')
                self.spin(lambda:audio.process is not None and not audio._pending)
                self.assertFalse(audio._failed)
                for n in range(20):
                    audio.select_output('safe')
                    audio.outputs['music'].setVolume(n/20)
                self.spin(lambda:not audio._pending)
                self.assertEqual(len(errors),1)
            finally:
                timer.stop();audio.close()
                self.spin(lambda:not audio._retired)
                audio.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)

    def test_late_end_event_cannot_finish_new_track(self):
        audio=AudioProcess(command=[sys.executable,'-c','import time; time.sleep(30)'])
        try:
            p=audio.players['music'];statuses=[];p.mediaStatusChanged.connect(statuses.append)
            p.setSource(QUrl.fromLocalFile('/tmp/old.mp3'));p.play();old=p._generation
            p.stop();p.setSource(QUrl.fromLocalFile('/tmp/new.mp3'));p.play()
            audio._buffer=(json.dumps(dict(event='status',channel='music',generation=old,value=QMediaPlayer.EndOfMedia.value))+'\n').encode()
            audio._read(audio.process)
            self.assertEqual(statuses,[])
        finally:
            audio.close();self.spin(lambda:not audio._retired)
            audio.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
