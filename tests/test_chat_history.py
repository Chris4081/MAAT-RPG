"""Archive isolation, bounded browsing, migration, deletion and real dialogue wiring."""
from pathlib import Path
import os
import sqlite3
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
from shared.core.chat_history import ChatHistory, PAGE_SIZE
from test_live_rpg import Worker


class ChatHistoryTests(unittest.TestCase):
    def assert_absent_from_archive_files(self, history, marker):
        for path in history.path.parent.glob('chat_history.db*'):
            self.assertNotIn(marker, path.read_bytes(), str(path))
        journal = Path(str(history.path)+'-journal')
        if journal.exists(): self.assertEqual(journal.stat().st_size,0)

    def test_secure_delete_overwrites_payload_and_overflow_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            history=ChatHistory(folder)
            marker=b'PRIVATE_ARCHIVE_ERASE_TEST_93be170d'
            secret=(marker.decode()+' Ägypten 🗝\n')*12000
            identifier=history.append('user',secret,'adventure','2026-09-09T12:00:00')
            survivor=history.append('assistant','Diese Nachricht bleibt erhalten.','adventure','2026-09-09T12:01:00')
            before=history.path.read_bytes()
            with history.connect() as db:
                page_size=db.execute('PRAGMA page_size').fetchone()[0]
            # SQLite reuses the front of a freed trunk page for freelist page
            # numbers. Check payload near the page's end, beyond that metadata.
            position=before.find(marker,10000)
            while position>=0 and not 3*page_size//4 < position%page_size < page_size-len(marker):
                position=before.find(marker,position+len(marker))
            self.assertGreater(position,10000)
            self.assertEqual(history.delete_message(identifier),1)
            after=history.path.read_bytes()
            self.assertEqual(after[position:position+len(marker)],b'\0'*len(marker))
            self.assert_absent_from_archive_files(history,marker)
            self.assertEqual(history.get(survivor)['content'],'Diese Nachricht bleibt erhalten.')
            with history.connect() as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertEqual(db.execute('PRAGMA secure_delete').fetchone()[0],1)
                self.assertEqual(db.execute('PRAGMA journal_mode').fetchone()[0],'truncate')
                self.assertEqual(db.execute('PRAGMA synchronous').fetchone()[0],3)
            if os.name=='posix': self.assertEqual(stat.S_IMODE(history.path.stat().st_mode),0o600)
            day_marker=b'DAY_ARCHIVE_ERASE_TEST_582af'
            history.append('user',day_marker.decode()*500,'companion','2026-09-08T12:00:00')
            history.append('assistant',day_marker.decode()*500,'companion','2026-09-08T12:01:00')
            row=next(r for r in history.days() if r['day']=='2026-09-08')
            new=history.append('user','Neu während der Bestätigung','companion','2026-09-08T12:02:00')
            self.assertEqual(history.delete_day(row['day'],row['last_id']),2)
            self.assert_absent_from_archive_files(history,day_marker)
            self.assertIsNotNone(history.get(new))

    def test_upgrade_cleans_records_deleted_by_old_release(self):
        with tempfile.TemporaryDirectory() as folder:
            history=ChatHistory(folder)
            marker=b'OLD_DELETION_REMNANT_42729dd'
            with sqlite3.connect(history.path) as db:
                db.execute('PRAGMA secure_delete=OFF')
                db.execute('INSERT INTO messages(timestamp,epoch,day,role,content,mode) VALUES (?,?,?,?,?,?)',
                           ('2026-09-09T12:00:00',0,'2026-09-09','user',marker.decode()*10000,'adventure'))
                db.commit()
                db.execute('DELETE FROM messages')
                db.execute("DELETE FROM metadata WHERE key='secure_storage_v1'")
            self.assertIn(marker,history.path.read_bytes())
            history=ChatHistory(folder)
            self.assert_absent_from_archive_files(history,marker)
            self.assertEqual(history.days(),[])

    def test_wal_is_checkpointed_before_deleting_and_locked_delete_is_not_successful(self):
        with tempfile.TemporaryDirectory() as folder:
            history=ChatHistory(folder)
            marker=b'WAL_PRIVATE_TEST_b30e88'
            identifier=history.append('user',marker.decode()*100,'adventure','2026-09-09T12:00:00')
            with sqlite3.connect(history.path) as other:
                other.execute('PRAGMA journal_mode=WAL')
                other.execute('PRAGMA wal_autocheckpoint=0')
                other.execute('UPDATE messages SET content=content || ? WHERE id=?',(marker.decode(),identifier))
                other.commit()
                self.assertIn(marker,Path(str(history.path)+'-wal').read_bytes())
                # An existing WAL reader prevents a mode change. Do not unlink
                # its journal, report success, or silently fall back to OFF.
                other.execute('BEGIN'); other.execute('SELECT * FROM messages').fetchall()
                with self.assertRaises(sqlite3.OperationalError): history.delete_message(identifier)
                self.assertEqual(other.execute('SELECT COUNT(*) FROM messages').fetchone()[0],1)
                other.rollback()
            other.close()
            self.assertEqual(history.delete_message(identifier),1)
            self.assert_absent_from_archive_files(history,marker)

    def test_filters_order_pagination_and_profile_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            history = ChatHistory(Path(folder)/'one')
            for day in ('2026-09-09','2026-08-07','2027-09-10'):
                history.append('user','Frage','adventure',day+'T12:00:00+02:00')
                history.append('assistant','Antwort','adventure',day+'T12:00:01+02:00')
            self.assertEqual(history.years(), ['2027','2026'])
            self.assertEqual([d['day'] for d in history.days('2026',9)], ['2026-09-09'])
            self.assertEqual(len(history.days(month=9)),2)
            self.assertEqual([d['day'] for d in history.days(newest=False)], ['2026-08-07','2026-09-09','2027-09-10'])
            self.assertEqual(ChatHistory(Path(folder)/'two').days(),[])
            self.assertIsNone(history.append('system','PRIVATE PROMPT'))
            self.assertIsNone(history.append('user','/fight'))
            for i in range(PAGE_SIZE): history.append('user',f'Frage {i}','adventure','2026-09-09T13:00:00+02:00')
            self.assertEqual(len(history.messages('2026-09-09')),PAGE_SIZE)
            self.assertEqual(len(history.messages('2026-09-09',1)),2)
            ids = [m['id'] for m in history.messages('2026-09-09')+history.messages('2026-09-09',1)]
            self.assertEqual(len(ids),len(set(ids)))

    def test_read_only_migration_and_deletion_stay_deleted_after_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            history = ChatHistory(folder)
            source = Path(folder)/'data/memory_v5.db'
            with sqlite3.connect(source) as old:
                old.execute('CREATE TABLE episodic(id INTEGER PRIMARY KEY, role TEXT, content TEXT, timestamp TEXT)')
                old.executemany('INSERT INTO episodic VALUES (?,?,?,?)',[
                    (1,'user','Hallo','2026-09-09T12:00:00'),(2,'assistant','Willkommen','2026-09-09T12:00:01'),
                    (3,'system','Kein Chat','2026-09-09T12:00:02'),(4,'user','Ohne Datum',None),
                    (5,'user','Ungültiges Datum','invalid')])
            before = source.read_bytes()
            history.import_legacy(); history.import_legacy()
            self.assertEqual(history.days()[0]['count'],2)
            self.assertEqual(source.read_bytes(), before)
            history.delete_message(history.messages('2026-09-09')[0]['id'])
            row = history.days()[0]
            new = history.append('user','Gerade angekommen','adventure','2026-09-09T12:01:00')
            history.delete_day(row['day'],row['last_id'])
            history = ChatHistory(folder); history.import_legacy()
            self.assertEqual([m['id'] for m in history.messages(row['day'])],[new])
            self.assertEqual(source.read_bytes(), before)

    def test_model_dialogue_archives_original_input_and_final_reply_only(self):
        from gui.game_worker import Runtime
        with tempfile.TemporaryDirectory() as folder:
            r=Runtime.__new__(Runtime); r.chat_history=ChatHistory(folder)
            r.context={'evo_engine':None}; r.llm=object(); r.perf={}
            r.boot=SimpleNamespace(conversation=[{'role':'system','content':'PRIVATE SYSTEM'}])
            r.select_story_campaign=Mock(); r.ensure_maatis_chat_opening=Mock(); r.restore_chat_prompt=Mock()
            r.pm=Mock(); r.pm.handle_before_chat.return_value=(False,'rewritten input')
            r.pm.has_before_final_response.return_value=True
            r.pm.handle_after_response.return_value='Die sichtbare Antwort.'
            r.pm.handle_before_final_response.return_value='reply before final plugin correction'
            with patch('gui.game_worker.emit'), patch('shared.core.streaming.stream_chat_completion',return_value=iter(['tokens'])), patch('shared.core.streaming.stream_to_console',return_value='raw reply'), patch('builtins.print'):
                r.text('Meine ursprüngliche Frage')
            day = r.chat_history.days()[0]['day']
            self.assertEqual([m['content'] for m in r.chat_history.messages(day)],['Meine ursprüngliche Frage','Die sichtbare Antwort.'])
            with patch.object(r.chat_history,'append',side_effect=sqlite3.OperationalError('locked')), patch('gui.game_worker.emit') as emitted:
                r.archive_chat('user','Geht trotzdem weiter')
                self.assertTrue(any(c.args[0]=='notice' for c in emitted.call_args_list))

    def test_real_companion_worker_counts_five_and_archives_both_sides(self):
        worker=Worker()
        try:
            worker.command('/ai-start')
            reply='Ich bin deine Begleiter KI und werde gemeinsam mit dir alle Hinweise sorgfältig prüfen, bevor wir einen sicheren nächsten Schritt wählen.'
            for i in range(5):
                worker.send(op='companion_answer',text=reply,choice=-1 if i==0 else 0)
                events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            profile=next(e['data'] for e in events if e['event']=='profile')
            self.assertEqual(profile['chat_messages'],5)
            history=ChatHistory(worker.temp.name)
            rows=history.messages(history.days()[0]['day'])
            self.assertEqual(sum(m['role']=='user' for m in rows),5)
            self.assertTrue(any('Wer bist du?' in m['content'] for m in rows))
            self.assertTrue(all(m['mode']=='companion' for m in rows))
            before=len(rows); worker.command('/help')
            self.assertEqual(len(history.messages(history.days()[0]['day'])),before)
        finally: worker.close()

    def test_generated_maatis_dialogue_keeps_prompts_out_of_archive(self):
        from gui.game_worker import Runtime
        with tempfile.TemporaryDirectory() as folder:
            r=Runtime.__new__(Runtime); r.chat_history=ChatHistory(folder)
            r.context={}; r.llm=object(); r.perf={}; r.stop_previous_speech=Mock()
            r.companion=SimpleNamespace(state={'dialogue':[],'memories':['PRIVATE MEMORY']},save=Mock())
            with patch('gui.game_worker.emit'), patch('shared.core.streaming.stream_chat_completion',return_value=iter(['reply'])), patch('shared.core.streaming.stream_to_console',return_value='Wie siehst du unseren Weg?'), patch('builtins.print'):
                r.maatis_dialogue()
            rows=r.chat_history.messages(r.chat_history.days()[0]['day'])
            self.assertEqual([(m['role'],m['mode'],m['content']) for m in rows],[('assistant','companion','Wie siehst du unseren Weg?')])
