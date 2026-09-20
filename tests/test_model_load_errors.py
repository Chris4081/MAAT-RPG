import os,unittest,tempfile,time
from pathlib import Path
from unittest.mock import patch
from test_desktop import APP
from test_live_rpg import Worker
from gui.model_errors import load_error,MODEL_LOAD_MESSAGE
from gui.live_session import LiveSession

class ModelErrorTests(unittest.TestCase):
    def spin(self,condition):
        end=time.monotonic()+12
        while not condition() and time.monotonic()<end:APP.processEvents();time.sleep(.01)
        self.assertTrue(condition())
    def test_actionable_error_categories(self):
        for exc,word in [(MemoryError(),'Arbeitsspeicher'),(PermissionError(),'gelesen'),(FileNotFoundError(),'gefunden'),(ValueError('invalid magic'),'ungültig'),(RuntimeError('unknown model architecture'),'unterstützt'),(RuntimeError('backend broke'),'erneut')]:
            message,detail=load_error(exc);self.assertTrue(message.startswith(MODEL_LOAD_MESSAGE));self.assertIn(word,message);self.assertTrue(detail)
    def test_invalid_file_keeps_worker_usable_and_can_retry(self):
        worker=Worker()
        try:
            bad=Path(worker.temp.name)/'bad.gguf';bad.write_bytes(b'broken')
            for name in (str(bad.with_name('missing.gguf')),str(bad)):
                worker.send(op='load_model',name=name)
                events=worker.until(lambda e:e['event']=='busy' and not e['value'])
                self.assertTrue(any(e['event']=='model_error' and e['text'] for e in events))
                self.assertIsNone(worker.p.poll())
            self.assertTrue(worker.command('/quests'))
        finally:worker.close()
    def test_native_load_crash_restarts_once_without_loading_again(self):
        with tempfile.TemporaryDirectory(prefix='maat-model-crash-') as folder,patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':folder}):
            session=LiveSession();events=[];session.on_transport(events.append)
            try:
                session.start();self.spin(lambda:session.ready)
                original=session.process
                # Simulate a native library exit while an explicitly started load is pending.
                session._loading_model='test-model.gguf';session.busy=True
                original.kill()
                self.spin(lambda:session.process is not original and session.ready)
                self.assertTrue(any(e['event']=='model_error' and e['text'].startswith(MODEL_LOAD_MESSAGE) for e in events))
                self.assertTrue(any(e['event']=='stopped' and e['model_load_failed'] for e in events))
                self.assertIsNone(session._loading_model)
                self.assertFalse(session.busy)
                self.assertEqual(sum(e['event']=='ready' for e in events),2)
                session.send_command('/quests');self.spin(lambda:not session.busy)
            finally:session.shutdown()
