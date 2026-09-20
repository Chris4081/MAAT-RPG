"""The real worker keeps load failures out of chat and writes useful local logs."""
from pathlib import Path
import unittest
from test_live_rpg import Worker


class WorkerDiagnosticsTests(unittest.TestCase):
    def test_load_failure_is_logged_and_worker_remains_usable(self):
        worker = Worker()
        self.addCleanup(worker.close)
        path = Path(worker.temp.name)/'broken.gguf'
        path.write_bytes(b'not a GGUF')
        worker.send(op='load_model', name=str(path), n_ctx=20000)
        events = worker.until(lambda e:e['event']=='busy' and not e['value'])
        self.assertTrue(any(e['event']=='model_error' for e in events))
        logs = list((Path(worker.temp.name)/'logs').glob('worker-*.log'))
        self.assertEqual(len(logs), 1)
        text = logs[0].read_text()
        self.assertIn("role='worker'", text)
        self.assertIn('machine=', text)
        self.assertIn('cpu_variant=', text)
        self.assertIn('model_load_requested', text)
        self.assertIn('model_load_failed', text)
        self.assertIn('worker_command_failed error_type=ValueError', text)
        self.assertIn('in load_model', text)
        self.assertIn('broken.gguf', text)
        self.assertFalse(any(e['event']=='output' and 'MAAT worker log:' in e.get('text','') for e in worker.boot))
        self.assertTrue(any(e['event']=='output' for e in worker.command('/quests')))
