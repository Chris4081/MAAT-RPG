"""Archive recovery after a failed startup/open or a transient SQLite lock."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import sqlite3
import unittest
from unittest.mock import patch
from test_desktop import APP
from gui.game_worker import Runtime
from shared.core.chat_history import ChatHistory
from shared.core.chat_turn import ChatTurn, ChatCancelled


class ArchiveRecoveryTests(unittest.TestCase):
    def runtime(self,root):
        r=Runtime.__new__(Runtime)
        r.chat_history=None; r.slot=1; r.language='en'; r.context={}
        r.shared=SimpleNamespace(profile_slot_root=lambda slot:Path(root))
        return r

    def test_failed_startup_reopens_and_saves_each_role_exactly_once(self):
        for mode in ('adventure','companion'):
            with TemporaryDirectory() as folder:
                r=self.runtime(folder)
                with patch('shared.core.chat_history.ChatHistory',side_effect=sqlite3.OperationalError('locked')), \
                     patch('gui.game_worker.emit') as emitted:
                    r.archive_chat('user','Original input',mode)
                self.assertTrue(any(c.args[0]=='notice' for c in emitted.call_args_list))
                with patch('gui.game_worker.emit'):
                    r.archive_chat('assistant','Complete reply',mode)
                    r.archive_chat('user','Next input',mode)
                rows=r.chat_history.messages(r.chat_history.days()[0]['day'])
                self.assertEqual([m['content'] for m in rows],['Original input','Complete reply','Next input'])
                self.assertTrue(all(m['mode']==mode for m in rows))
                self.assertEqual(r._pending_chat_archive,[])

    def test_write_failure_retains_order_date_and_committed_rows(self):
        with TemporaryDirectory() as folder,patch('gui.game_worker.emit'):
            r=self.runtime(folder)
            r.archive_chat('user','Already saved')
            with patch.object(r.chat_history,'append',side_effect=sqlite3.OperationalError('locked')):
                r.archive_chat('assistant','Queued reply')
            stamp=r._pending_chat_archive[0]['timestamp']
            r.archive_chat('user','Another input')
            rows=r.chat_history.messages(r.chat_history.days()[0]['day'])
            self.assertEqual([m['content'] for m in rows],['Already saved','Queued reply','Another input'])
            self.assertEqual(rows[1]['timestamp'],stamp)

    def test_cancelled_chat_and_demo_do_not_enter_retry_queue(self):
        with TemporaryDirectory() as folder,patch('gui.game_worker.emit'):
            r=self.runtime(folder); turn=ChatTurn('cancel')
            r.context['gui_chat_turn']=turn
            r.archive_chat('user','Cancelled input')
            turn.cancel()
            with self.assertRaises(ChatCancelled):turn.commit()
            self.assertIsNone(r.chat_history)
            self.assertFalse(getattr(r,'_pending_chat_archive',[]))
            r.context={'title_demo_mode':True}
            r.archive_chat('assistant','Demo text')
            self.assertIsNone(r.chat_history)

    def test_deferred_memory_failure_does_not_interrupt_chat_archiving(self):
        from unittest.mock import Mock
        from shared.core import streaming
        with TemporaryDirectory() as folder,patch('gui.game_worker.emit'):
            r=self.runtime(folder); turn=ChatTurn('memory-fails')
            memory=Mock(); memory.finish_turn.side_effect=sqlite3.OperationalError('locked')
            # Use the real streaming filter so model directives remain hidden.
            from shared.core.super_memory import SuperMemory
            store=SuperMemory(Path(folder)/'memory')
            store.finish_turn=memory.finish_turn
            r.context={'gui_chat_turn':turn,'super_memory':store,'super_memory_query':'Original input'}
            r.archive_chat('user','Original input')
            with patch.object(streaming,'_stream_chat_completion_raw',return_value=iter(['Complete reply.'])):
                reply=''.join(streaming.stream_chat_completion({},[],{},runtime_context=r.context))
            turn.commit()
            r.archive_chat('assistant',reply)
            self.assertIn('super_memory_error',r.context)
            self.assertEqual([m['content'] for m in r.chat_history.messages(r.chat_history.days()[0]['day'])],
                             ['Original input','Complete reply.'])
            self.assertFalse(getattr(r,'_pending_chat_archive',[]))
