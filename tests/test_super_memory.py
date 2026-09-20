"""Native Super Memory: real storage, prompt limits, deletion and GUI bindings."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch
from test_desktop import APP
from shared.core.super_memory import SuperMemory, SaveStreamFilter, MARKER
from shared.core.thinking_mode import prepare_generation_messages
from shared.core import streaming
from gui.memories import Memories
from PySide6.QtWidgets import QMessageBox

ROOT=Path(__file__).resolve().parents[1]/'maatos'


class SuperMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.s=SuperMemory(self.root)

    def dated(self,text,day):
        self.s.save(text)
        fp=self.s.engine._fingerprint(text); ts=datetime.fromisoformat(day+'T12:00:00').timestamp()
        with self.s.operation() as db:
            for table in ('native_saves','episodic','semantic'):db.execute(f'UPDATE {table} SET ts=? WHERE fp=?',(ts,fp))
            items=self.s._load_keywords()
            for item in items:
                if item['fp']==fp:item['created_at']=day+'T12:00:00'
            self.s._save_keywords(items)

    def test_person_store_absent_and_old_plugins_disabled(self):
        with self.s.connection() as db:
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn('person_graph',tables)
        self.assertFalse(any('person' in k or 'current_user' in k or 'known_user' in k for k in self.s.settings))
        self.s.finish_turn('Ich heiße Erika. Mein Freund heißt Jonas.','Hallo.','a')
        self.assertEqual(self.s.engine._extract_person_names('Erika und Jonas',{}),[])
        cfg=json.loads((ROOT/'apps/maat_rpg/plugin_config.json').read_text())['plugins']
        for key in ('memory_v5','memory_v6','memory_orchestrator','chat_memory','maat_time_kernel','maat_usercontext_memory'):
            self.assertIs(cfg[key],False)
        self.assertIs(cfg['super_memory'],True)

    def test_manual_model_and_automatic_saves_deduplicate(self):
        self.s.begin_turn('Merke dir: Mein Projekt Resonanz verwendet Python.')
        self.s.finish_turn('Merke dir: Mein Projekt Resonanz verwendet Python.','Das merke ich mir.','manual')
        self.assertEqual(len(self.s.entries()),1)
        out='Ein Plan. save: (memory="Wir testen das Projekt (offline).", type=project, tags="tests, offline", priority=high) Fertig.'
        self.assertEqual(self.s.finish_turn('Plan?',out,'model'),'Ein Plan.  Fertig.')
        self.s.finish_turn('Plan?',out,'model')
        self.assertEqual(len(self.s.entries()),2)
        self.assertEqual(self.s.stats()['keyword_memory'],2)
        self.s.finish_turn('hallo =)','Hallo!','smalltalk')
        self.assertEqual(len(self.s.entries()),2)
        self.s.finish_turn('Ich bevorzuge ausführliche Antworten über mein Projekt Resonanz mit konkreten Beispielen.','Alles klar.','auto')
        self.assertGreater(len(self.s.entries()),2)
        self.assertTrue(all(r['role'] in ('user','assistant') for r in self.s.entries()))

    def test_english_and_german_short_preferences_are_saved_without_model_directives(self):
        for i, text in enumerate(('I prefer concise answers.', 'I work in IT.', 'Ich mag Tee.',
                                  'My project uses local files only.')):
            self.s.begin_turn(text)
            self.s.finish_turn(text, 'Understood.', f'preference-{i}')
            self.assertIn(text, [r['content'] for r in self.s.entries()])
        before=len(self.s.entries())
        for i,text in enumerate(('hallo', 'Hello', 'Thanks!', 'What is a pyramid?')):
            self.s.finish_turn(text,'A response.',f'casual-{i}')
        self.assertEqual(len(self.s.entries()),before)

    def test_vague_or_repeated_model_saves_do_not_suppress_useful_user_notes(self):
        for i,text in enumerate(('Ich bevorzuge kurze Antworten mit konkreten Beispielen.',
                                 'Mein Projekt verwendet Python und bleibt offline.')):
            raw='Gut. save: (memory="das", type=fact)'
            self.assertEqual(self.s.finish_turn(text,raw,f'vague-{i}'),'Gut. ')
        contents=[r['content'] for r in self.s.entries()]
        self.assertEqual(len(contents),2)
        self.assertNotIn('das',contents)
        raw='Understood. save: (memory="Our project works offline.", type=project)'
        for i,text in enumerate(('I prefer concise answers.', 'I work in IT.')):
            self.s.finish_turn(text,raw,f'repeated-{i}')
        contents=[r['content'] for r in self.s.entries()]
        self.assertIn('I prefer concise answers.',contents)
        self.assertIn('I work in IT.',contents)
        self.assertEqual(contents.count('Our project works offline.'),1)

    def test_memory_save_guidance_follows_game_language(self):
        en=self.s.generation_context('',language='en')
        de=self.s.generation_context('',language='de')
        self.assertIn('short complete sentence',en)
        self.assertNotIn('Speichere',en)
        self.assertIn('kurzen vollständigen Satz',de)

    def test_failed_commit_can_retry_same_turn_without_phantom_memories(self):
        from contextlib import contextmanager
        from shared.core import super_memory as module
        connect=module.connect
        @contextmanager
        def failed_commit(path):
            with connect(path) as db:
                yield db
                raise sqlite3.OperationalError('simulated commit failure')
        with patch.object(module,'connect',failed_commit):
            with self.assertRaises(sqlite3.OperationalError):
                self.s.finish_turn('I prefer concise answers.','Understood.','retry')
        self.assertEqual(self.s.entries(),[])
        self.assertNotIn('retry',self.s.finished_turns)
        self.assertEqual(self.s.engine._WORKING_MEMORY,[])
        self.s.finish_turn('I prefer concise answers.','Understood.','retry')
        self.assertEqual([r['content'] for r in self.s.entries()],['I prefer concise answers.'])

    def test_stream_filter_chunk_boundaries_and_code_examples(self):
        examples=[
            ('Hallo! save: (memory="Das Projekt bleibt offline.", tags="Projekt") Ende.','Hallo!  Ende.',1),
            ('Nutze `save: (memory="Nur ein Beispiel")` im Code.','Nutze `save: (memory="Nur ein Beispiel")` im Code.',0),
            ('```python\nsave: (memory="Nur Code")\n```','```python\nsave: (memory="Nur Code")\n```',0),
            ('<think>save: (memory="Nicht speichern")</think>Hallo.','<think></think>Hallo.',0),
            ('Hallo save: {"memory":"Das Projekt ist lokal.","type":"project"}','Hallo ',1),
            ('Fertig. save: (memory="Unvollständig"','Fertig. ',0),
            ('Fertig. save: {"memory":"Unvollständig"','Fertig. ',0),
        ]
        for raw,expected,count in examples:
            self.assertEqual(self.s.extract_model_saves(raw)[0],expected)
            self.assertEqual(len(self.s.extract_model_saves(raw)[1]),count)
            for width in (1,2,5,13,1000):
                f=SaveStreamFilter(self.s); parts=[f.feed(raw[i:i+width]) for i in range(0,len(raw),width)]
                parts.append(f.finish())
                self.assertEqual(''.join(parts),expected,(width,raw))

    def test_strict_total_caps_switching_and_ephemeral_context(self):
        for i in range(10):self.s.save(f'Projekt Resonanz: Aufgabe {i} verwendet eine eigene Offline-Testdatei mit Beispielwert {i+30}.',tags='Projekt Resonanz')
        messages=[{'role':'system','content':'Du bist MAAT.'},{'role':'user','content':'Welche Aufgaben hat Projekt Resonanz?'}]
        ctx={'super_memory':self.s,'super_memory_query':messages[-1]['content'],'dungeon_secret':'DO NOT INJECT'}
        for architecture,limit in [('llama',3),('qwen3',5),('gemma4',5),('mistral3',5),('llama',3)]:
            llm={'backend':'llama','chat_state':{'architecture':architecture}}
            with patch('shared.core.thinking_mode.thinking_enabled',return_value=True),patch('shared.core.thinking_mode.build_rpg_context_message',return_value=None):
                result=prepare_generation_messages(messages,runtime_context=ctx,llm=llm)
            blocks=[m['content'] for m in result if m['content'].startswith(MARKER)]
            self.assertEqual(len(blocks),1)
            self.assertEqual(len(self.s.last_recall),limit)
            self.assertNotIn('DO NOT INJECT',str(result))
            self.assertLess(len(blocks[0]),3000 if limit==5 else 1300)
            self.assertEqual(messages[0]['content'],'Du bist MAAT.')
            self.assertEqual(len(messages),2)
        self.s.configure(supermem_autorecall=False)
        self.s.generation_context('Projekt Resonanz',llm)
        self.assertEqual(self.s.last_recall,[])
        self.s.configure(supermem_enabled=False)
        self.assertEqual(self.s.generation_context('Projekt Resonanz',llm),'')

    def test_successful_stream_stores_and_does_not_show_directives(self):
        ctx={'super_memory':self.s,'super_memory_query':'Unser Projekt bleibt offline.','super_memory_turn':'stream'}
        raw=['Das ','passt. sa','ve: (memory="Das Projekt bleibt lokal.", type=project)']
        with patch.object(streaming,'_stream_chat_completion_raw',return_value=iter(raw)):
            visible=''.join(streaming.stream_chat_completion(None,[],{},runtime_context=ctx))
        self.assertEqual(visible,'Das passt. ')
        self.assertEqual(len(self.s.entries()),1)
        self.s.finish_turn(ctx['super_memory_query'],visible,'stream')
        self.assertEqual(len(self.s.entries()),1)
        def broken():
            yield 'save: (memory="Nicht speichern'
            raise RuntimeError('backend failed')
        ctx['super_memory_turn']='broken'
        with patch.object(streaming,'_stream_chat_completion_raw',return_value=broken()),self.assertRaises(RuntimeError):
            list(streaming.stream_chat_completion(None,[],{},runtime_context=ctx))
        self.assertEqual(len(self.s.entries()),1)

    def test_disabled_model_saves_still_strip_and_do_not_store(self):
        self.s.configure(supermem_allow_model_saves=False,supermem_autostore=False)
        self.assertEqual(self.s.finish_turn('Hallo','Hallo save: (memory="Keine Speicherung.")','off'),'Hallo ')
        self.assertEqual(self.s.entries(),[])

    def test_output_plugins_only_receive_visible_prose_and_cancel_on_first_raw_token(self):
        events=[]
        class Voice:
            def before_stream(self,text):events.append(('before',text))
            def on_token(self,text):events.append(('token',text))
            def after_stream(self,text):events.append(('after',text))
        ctx={'super_memory':self.s,'super_memory_query':'Unser Projekt nutzt Python.','super_memory_turn':'tts',
             'on_first_response_token':lambda:events.append(('cancel',''))}
        raw=['sa','ve: (memory="Das Projekt nutzt Python.", type=project) ', 'Eine sichtbare Antwort.']
        llm={'backend':'llama','chat_state':{'architecture':'llama'}}
        with patch.object(streaming,'backend_stream_chat',return_value=iter(raw)), patch.object(streaming,'key_pressed',return_value=False):
            out=''.join(streaming.stream_chat_completion(llm,[],{'gui_mode':True,'raise_errors':True},[Voice()],ctx))
        self.assertEqual(out,' Eine sichtbare Antwort.')
        self.assertEqual(events[1],('cancel',''))
        self.assertEqual(sum(e[0]=='cancel' for e in events),1)
        self.assertNotIn('save:',''.join(v for _,v in events))
        self.assertEqual(events[-1],('after',out))
        self.assertEqual(len(self.s.entries()),1)

    def test_dates_summaries_and_deletion_remove_every_copy(self):
        marker='PRIVATMARKER_Äöß_934768'
        text=marker+' Mein Projekt nutzt besondere Daten. '+('Inhalt '+marker+' ')*150
        self.dated(text,'2026-07-15')
        self.dated('Mein anderes Projekt bleibt erhalten.','2026-08-20')
        self.s.report('archive')
        self.s.report('timeline','2026-07'); self.s.report('milestones')
        with self.s.operation():self.s.engine._run_dreaming(10000)
        self.assertGreater(self.s.stats()['monthly_archive'],0)
        other=SuperMemory(self.root)
        other.generation_context('Projekt')
        ids=[r['id'] for r in self.s.entries(period='2026-07')]
        self.assertEqual(self.s.delete(ids),1)
        self.assertEqual(self.s.stats()['monthly_archive'],0)
        for p in self.root.joinpath('data').iterdir():
            self.assertNotIn(marker.encode(),p.read_bytes(),p.name)
        with self.s.connection() as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        self.assertEqual(self.s.path.stat().st_mode&0o777,0o600)
        self.assertEqual(Path(str(self.s.path)+'-journal').stat().st_size,0)
        context={'conversation':[{'role':'system','content':'MAAT'},{'role':'user','content':text}]}
        # Even a intervening read must not consume the pending dialogue reset.
        other.generation_context('Projekt')
        other.begin_turn('Und nun?',context)
        self.assertEqual(context['conversation'],[{'role':'system','content':'MAAT'}])
        self.assertTrue(context['super_memory_reset_dialogue'])
        restarted=SuperMemory(self.root,maintenance=True,migrate=True)
        self.assertEqual(len(restarted.entries()),1)
        self.assertNotIn(marker,restarted.generation_context('Projekt'))

    def test_migration_dates_readonly_and_no_resurrection(self):
        p=self.root/'data'/'memory_v5.db'
        with sqlite3.connect(p) as db:
            db.execute('CREATE TABLE episodic(id INTEGER PRIMARY KEY,role TEXT,content TEXT,timestamp TEXT)')
            db.executemany('INSERT INTO episodic(role,content,timestamp) VALUES(?,?,?)',[
                ('user','Mein Projekt Altbestand bleibt lokal.','2026-02-03T10:00:00'),
                ('assistant','Eine Antwort ohne Datum.',None)])
        before=p.read_bytes()
        self.s.import_legacy()
        self.assertEqual(p.read_bytes(),before)
        self.assertEqual(len(self.s.entries(period='2026-02-03')),1)
        self.s.delete([r['id'] for r in self.s.entries()])
        restarted=SuperMemory(self.root,migrate=True)
        self.assertEqual(restarted.entries(),[])
        self.assertEqual(p.read_bytes(),before)

    def test_busy_database_rolls_back_all_layers(self):
        self.s.save('Diese Erinnerung bleibt bei einem Fehler erhalten.')
        ids=[r['id'] for r in self.s.entries()]
        blocker=sqlite3.connect(self.s.path); blocker.execute('BEGIN EXCLUSIVE')
        try:
            with self.assertRaises(sqlite3.OperationalError):self.s.delete(ids)
        finally:blocker.rollback(); blocker.close()
        self.assertEqual(len(self.s.entries()),1)
        with patch.object(self.s.engine,'_add_semantic',side_effect=RuntimeError('test')):
            with self.assertRaises(RuntimeError):self.s.save('Diese neue Erinnerung darf nicht teilweise gespeichert werden.')
        self.assertEqual(len(self.s.entries()),1)

    def test_native_filters_confirmation_cutoff_profile_and_unlock(self):
        self.dated('Erinnerung am ersten Tag.','2026-07-01')
        self.dated('Erinnerung am zweiten Tag.','2026-07-02')
        self.dated('Erinnerung aus August.','2026-08-01')
        w=Memories(); w.set_profile(self.root); w.set_count(4)
        try:
            self.assertFalse(w.body.isVisible())
            w.set_count(5); panel=w.saves
            self.assertEqual(panel.list.count(),3)
            panel.year.setCurrentIndex(panel.year.findData('2026'))
            panel.month.setCurrentIndex(panel.month.findData('07'))
            self.assertEqual(panel.list.count(),2)
            with patch.object(QMessageBox,'question',return_value=QMessageBox.No):panel.confirm_delete('month')
            self.assertEqual(len(panel.store.entries()),3)
            def confirm(*a,**k):
                self.dated('Neu während der Bestätigung.','2026-07-03')
                return QMessageBox.Yes
            with patch.object(QMessageBox,'question',side_effect=confirm):panel.confirm_delete('month')
            self.assertEqual(len(panel.store.entries()),2)
            self.assertEqual(panel.list.count(),1)
            self.assertIn('überschrieben',panel.status.text())
            self.assertIn('Neu während',panel.detail.toPlainText())
            panel.set_editable(False); self.assertFalse(panel.delete_buttons['entry'].isEnabled())
            w.set_profile(self.root/'other'); w.set_count(5)
            self.assertEqual(panel.store.entries(),[])
            self.assertNotIn('Neu während',panel.detail.toPlainText())
        finally:w.deleteLater(); APP.processEvents()

    def test_real_worker_commands_use_only_new_memory(self):
        from test_live_rpg import Worker
        w=Worker()
        try:
            result=w.command('/mem save Mein Projekt arbeitet nur mit lokalen Dateien.')
            text=''.join(e.get('text','') for e in result)
            self.assertIn('Erinnerung gespeichert',text)
            result=w.command('/mem search Projekt')
            self.assertIn('lokalen Dateien',''.join(e.get('text','') for e in result))
            root=Path(w.temp.name)
            self.assertTrue(list(root.rglob('super_memory.db')))
            self.assertFalse(list(root.rglob('memory_v5.db')))
            self.assertFalse(list(root.rglob('mem6.db')))
            self.assertFalse(list(root.rglob('*identity.json')))
        finally:w.close()


if __name__=='__main__':unittest.main()
