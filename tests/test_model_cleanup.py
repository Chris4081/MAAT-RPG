"""Native model ownership must end before Python/Metal process teardown."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from test_desktop import APP
from gui import game_worker as worker
from gguf_fixtures import guarded_test_memory, write_gguf

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'maatos'


class ModelCleanupTests(unittest.TestCase):
    def runtime(self, backend='llama'):
        runtime = worker.Runtime.__new__(worker.Runtime)
        native = Mock()
        runtime.llm = {'backend': backend, 'instance': native}
        runtime.context = {'llm': runtime.llm, 'conversation': ['keep history'],
                           'memories': ['keep memory'], 'callback': lambda: runtime}
        runtime.stop_previous_speech = Mock()
        return runtime, native

    def test_retained_model_closed_once_without_clearing_history_for_both_adapters(self):
        for backend in ('llama', 'llama_intel'):
            with self.subTest(backend=backend):
                runtime, native = self.runtime(backend)
                retained = runtime.llm
                runtime.unload_model()
                runtime.unload_model()
                native.close.assert_called_once_with()
                self.assertIs(retained['instance'], native)
                self.assertIsNone(runtime.llm)
                self.assertNotIn('llm', runtime.context)
                self.assertEqual(runtime.context['conversation'], ['keep history'])
                self.assertEqual(runtime.context['memories'], ['keep memory'])

    def test_old_native_model_closed_before_replacement_safety_check(self):
        runtime, native = self.runtime()
        runtime.slot = 1
        runtime.shared = Mock()
        hardware = dict(platform='test', threads=2, gpu_layers=0, options={})
        def check(*args):
            native.close.assert_called_once_with()
            self.assertIsNone(runtime.llm)
            raise ValueError('blocked test allocation')
        with tempfile.TemporaryDirectory() as folder:
            path = write_gguf(Path(folder) / 'test.gguf')
            with guarded_test_memory(folder), \
                 patch('shared.core.hardware_profile.detect_hardware', return_value={'machine': 'arm64'}), \
                 patch('shared.core.hardware_profile.automatic_settings', return_value=hardware), \
                 patch('shared.core.model_safety.check_model_safety', side_effect=check), \
                 patch('shared.core.backend_router.load_backend') as allocate, patch.object(worker, 'emit'):
                with self.assertRaisesRegex(ValueError, 'blocked test allocation'):
                    runtime.load_model(str(path), tuning={'mode': 'auto'})
                allocate.assert_not_called()

    def test_failed_close_keeps_ownership_but_cannot_be_used_for_chat(self):
        runtime, native = self.runtime()
        retained = runtime.llm
        native.close.side_effect = RuntimeError('native close failed')
        with self.assertRaisesRegex(RuntimeError, 'native close failed'):
            runtime.unload_model()
        self.assertIsNone(runtime.llm)
        self.assertNotIn('llm', runtime.context)
        self.assertIs(runtime._unreleased_model, retained)
        native.close.side_effect = None
        runtime.unload_model()
        self.assertEqual(native.close.call_count, 2)
        self.assertIsNone(runtime._unreleased_model)

    def run_main(self, runtime, receive):
        # Restore legacy I/O redirection after the worker's real finally block.
        with patch.object(worker, 'Runtime', return_value=runtime), \
             patch.object(worker, 'receive', side_effect=receive), \
             patch.object(worker, 'emit'), \
             patch('gui.runtime_diagnostics.configure', return_value=None), \
             patch.object(worker.threading, 'Thread'), \
             patch.object(sys, 'argv', ['game_worker.py', '1']), \
             patch.object(sys, 'stdout', sys.stdout), patch.object(sys, 'stderr', sys.stderr), \
             patch('builtins.input'):
            return worker.main()

    def test_shutdown_and_control_eof_both_release_native_model(self):
        for receive in ([{'op': 'shutdown'}], worker.WorkerStopped):
            runtime, native = self.runtime()
            self.assertEqual(self.run_main(runtime, receive), 0)
            native.close.assert_called_once_with()

    def test_speech_shutdown_error_still_releases_model(self):
        runtime, native = self.runtime()
        runtime.stop_previous_speech.side_effect = RuntimeError('speech stop failed')
        with self.assertRaisesRegex(RuntimeError, 'speech stop failed'):
            self.run_main(runtime, [{'op': 'shutdown'}])
        native.close.assert_called_once_with()


class DiagnosticHooksTests(unittest.TestCase):
    def test_thread_and_cleanup_errors_logged_without_private_exception_text(self):
        code = '''
import gc, sys, threading
from gui.runtime_diagnostics import configure
threading.excepthook = lambda args: print('previous thread hook called')
sys.unraisablehook = lambda args: print('previous cleanup hook called')
configure(announce=False)
def fail_thread():
    raise ValueError('PRIVATE_CHAT_SENTINEL')
t = threading.Thread(target=fail_thread)
t.start(); t.join()
class BrokenCleanup:
    def __del__(self):
        raise RuntimeError('PRIVATE_MEMORY_SENTINEL')
obj = BrokenCleanup()
del obj
gc.collect()
'''
        with tempfile.TemporaryDirectory() as folder:
            env = dict(os.environ, PYTHONPATH=str(GAME), MAAT_GUI_DATA_ROOT=folder)
            result = subprocess.run([sys.executable, '-c', code], env=env, text=True,
                                    capture_output=True, timeout=12)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('previous thread hook called', result.stdout)
            self.assertIn('previous cleanup hook called', result.stdout)
            log = next((Path(folder) / 'logs').glob('gui-*.log')).read_text()
            self.assertIn('thread_failed error_type=ValueError', log)
            self.assertIn('in fail_thread', log)
            self.assertIn('cleanup_callback_failed error_type=RuntimeError', log)
            self.assertIn('in __del__', log)
            self.assertNotIn('PRIVATE_', log)
