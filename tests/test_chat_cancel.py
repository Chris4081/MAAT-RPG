import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from test_desktop import APP
from shared.core.chat_turn import ChatTurn, ChatCancelled


class CancellationTests(unittest.TestCase):
    def test_real_progression(self):
        for mode in ('adventure', 'companion'):
          with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix='maat-cancel-') as folder:
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('chat_cancel_probe.py')), folder, mode],
                                    capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout[-1000:] + result.stderr[-4000:])

    def test_native_prefill_abort_callback_is_cleared_and_model_can_be_reused(self):
        from shared.core import llama_backend
        from llama_cpp import llama_cpp as api
        from types import SimpleNamespace
        inst=SimpleNamespace(_ctx=SimpleNamespace(ctx=object()),reset=Mock())
        turn=ChatTurn('prefill'); callbacks=[]
        def generate(*args):
            self.assertFalse(callbacks[0](None))
            turn.cancel()
            self.assertTrue(callbacks[0](None))
            raise RuntimeError('llama_decode aborted')
            yield ''
        with patch.object(api,'llama_set_abort_callback',side_effect=lambda ctx,cb,data:callbacks.append(cb)), patch.object(llama_backend,'_stream_chat',side_effect=generate):
            with self.assertRaises(ChatCancelled):
                list(llama_backend.stream_chat({'instance':inst},[],{'_chat_turn':turn}))
        inst.reset.assert_called_once()
        self.assertFalse(bool(callbacks[-1]))  # Native null callback, no dangling Python closure.
        with patch.object(api,'llama_set_abort_callback'), patch.object(llama_backend,'_stream_chat',return_value=(text for text in ['Ready again'])):
            self.assertEqual(list(llama_backend.stream_chat({'instance':inst},[],{'_chat_turn':ChatTurn('next')})),['Ready again'])

    def test_reader_controls_never_consume_a_story_answer(self):
        import queue
        from gui import game_worker as worker
        commands = queue.Queue()
        source = io.StringIO('\n'.join([
            '{"op":"text","text":"Hallo","turn_id":"one"}',
            '{"op":"stop_speech"}',
            '{"op":"cancel_chat","turn_id":"stale"}',
            '{"op":"answer","id":"story","value":"2"}',
            '{"op":"cancel_chat","turn_id":"one"}',
        ]))
        with patch.object(worker,'INPUT',source), patch.object(worker,'COMMANDS',commands), patch.object(worker,'TURNS',{}), patch.object(worker,'SPEECH_CONTROL',Mock()) as speech:
            worker.read_controls()
            self.assertTrue(worker.TURNS['one'].cancelled.is_set())
            self.assertEqual(worker.receive()['op'],'text')
            self.assertEqual(worker.receive(),{'op':'answer','id':'story','value':'2'})
            self.assertEqual(speech.call_count,2)

    def test_no_memory_save_before_commit_or_after_cancel(self):
        from shared.core import streaming
        from shared.core.super_memory import SuperMemory
        folder = tempfile.TemporaryDirectory(prefix='maat-cancel-memory-')
        self.addCleanup(folder.cleanup)
        memory=SuperMemory(Path(folder.name), maintenance=False, migrate=False)
        memory.finish_turn=Mock()
        for cancelled in (True,False):
            turn=ChatTurn('memory')
            context={'super_memory':memory,'gui_chat_turn':turn,'super_memory_query':'hello'}
            with patch.object(streaming,'_stream_chat_completion_raw',return_value=iter(['A complete answer.'])):
                self.assertEqual(''.join(streaming.stream_chat_completion({},[],{},runtime_context=context)),'A complete answer.')
            memory.finish_turn.assert_not_called()
            if cancelled:
                turn.cancel()
                with self.assertRaises(ChatCancelled): turn.commit()
            else:
                turn.commit(); turn.commit()
                memory.finish_turn.assert_called_once()
