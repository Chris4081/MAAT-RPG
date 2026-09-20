"""Game speakers are distinct from the unchanged model transport roles."""
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from test_desktop import APP
from test_live_rpg import Worker
from shared.core.super_memory import SuperMemory, MARKER
from shared.core.thinking_mode import prepare_generation_messages
from shared.core import streaming
from gui.super_memory_panel import SuperMemoryPanel

COMPANION = {'memory_perspective': 'companion'}
ADVENTURE = {'memory_perspective': 'adventure'}


class MemoryPerspectiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = SuperMemory(self.root)
        self.clock = patch('shared.core.super_memory.time.time', return_value=datetime(2026, 9, 10, 12).timestamp())
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def test_manual_and_streamed_saves_have_the_correct_companion_sources(self):
        query = 'Merke dir: Ich bin die Begleiter-KI und bewahre den blauen Kristall.'
        ctx = dict(COMPANION, super_memory=self.store, super_memory_query=query, super_memory_turn='companion')
        self.store.begin_turn(query, ctx)
        raw = ['Ich frage dich um Rat. ', 'save: (memory="Maatis sucht den Weg zur Bibliothek.", type=project)']
        llm = {'backend': 'llama', 'chat_state': {'architecture': 'llama'}}
        with patch.object(streaming, 'backend_stream_chat', return_value=iter(raw)), patch.object(streaming, 'key_pressed', return_value=False):
            reply = ''.join(streaming.stream_chat_completion(llm, [{'role':'user','content':query}], {'gui_mode':True,'raise_errors':True}, [], ctx))
        self.assertNotIn('save:', reply)
        # after_response sees the same turn and must not write it twice.
        self.store.finish_turn(query, reply, 'companion', runtime_context=ctx)
        rows = self.store.entries()
        self.assertEqual(len(rows), 2)
        by_role = {r['role']: r for r in rows}
        self.assertEqual({r['perspective'] for r in rows}, {'companion'})
        self.assertIn('Begleiter-KI (Spieler)', self.store.source_label(by_role['user']))
        self.assertIn('Maatis', self.store.source_label(by_role['assistant']))
        self.assertEqual({m['perspective'] for m in self.store.engine._WORKING_MEMORY}, {'companion'})

    def test_dated_i_and_you_queries_in_german_and_english_keep_transport_roles(self):
        with patch('shared.core.super_memory.time.time', return_value=datetime(2026,9,9,12).timestamp()):
            for i in range(6):
                self.store.save(f'KI_{i}: Ich bewahre Kristall Nummer {i}.', runtime_context=COMPANION)
                self.store.save(f'MAATIS_{i}: Ich reise zum Tempel Nummer {i}.', role='assistant', runtime_context=COMPANION)
        for language, own_query, other_query in (
            ('de','Was habe ich gestern gesagt?','Was hast du gestern gesagt?'),
            ('en','What did I say yesterday?','What did you say yesterday?'),
        ):
            for arch, cap in (('llama',3),('qwen3',5),('gemma4',5)):
                model = {'chat_state': {'architecture': arch}}
                own = self.store.generation_context(own_query, model, runtime_context=COMPANION)
                self.assertEqual(len(self.store.last_recall), cap)
                self.assertTrue(all(r['role']=='user' for r in self.store.last_recall))
                self.assertNotIn('MAATIS_', own)
                self.assertIn('Begleiter-KI (Spieler)' if language=='de' else 'companion AI (player)', own)
                other = self.store.generation_context(other_query, model, runtime_context=COMPANION)
                self.assertTrue(all(r['role']=='assistant' for r in self.store.last_recall))
                self.assertNotIn('KI_', other)
                self.assertIn('Maatis (Modellnotiz)' if language=='de' else 'Maatis (model note)', other)
                self.assertLess(len(own), 2200 if cap==3 else 3200)

    def test_topic_recall_sources_survive_hidden_dates_restart_and_mode_switch(self):
        self.store.save('Ich bewahre den Kristall in meinem Gedächtnis.', runtime_context=COMPANION)
        self.store.save('Maatis sucht den Kristall in der Bibliothek.', role='assistant', runtime_context=COMPANION)
        self.store.configure(supermem_show_source=False)
        self.store.engine._add_working('user','Nur kurzfristig: Kristall aus der KI-Perspektive')
        self.store.save('Mein Projekt über den Kristall bleibt ein lokales Projekt.', runtime_context=ADVENTURE)
        self.assertFalse(self.store.engine._WORKING_MEMORY)
        restarted = SuperMemory(self.root)
        for context in (COMPANION, ADVENTURE, COMPANION):
            messages = [{'role':'system','content':'Aktuelle Identität'}, {'role':'user','content':'Was weißt du über den Kristall?'}]
            ctx = dict(context, super_memory=restarted, super_memory_query=messages[-1]['content'])
            with patch('shared.core.thinking_mode.build_rpg_context_message', return_value=None):
                prepared = prepare_generation_messages(messages, runtime_context=ctx)
            block = next(m['content'] for m in prepared if m['content'].startswith(MARKER))
            self.assertIn('Begleiter-KI (Spieler)', block)
            self.assertIn('Maatis (Modellnotiz)', block)
            self.assertIn('Nutzernotiz', block)
            self.assertEqual(messages[0]['content'], 'Aktuelle Identität')
            self.assertEqual(len(messages), 2)

    def test_profile_setting_and_panel_show_player_ai_and_maatis(self):
        settings = self.root/'state/settings_state.json'
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({'gui_perspective':'companion'}))
        self.store.save('Ein manuell angelegter Save der Begleiter-KI.')
        self.store.save('Eine Antwort von Maatis.', role='assistant')
        panel = SuperMemoryPanel()
        try:
            panel.set_profile(self.root)
            panel.refresh()
            for i in range(panel.list.count()):
                panel.list.setCurrentRow(i)
                text = panel.detail.toPlainText()
                if 'manuell' in text:self.assertIn('Quelle: Begleiter-KI (Spieler)',text)
                else:self.assertIn('Quelle: Maatis (Modellnotiz)',text)
        finally:
            panel.deleteLater(); APP.processEvents()

    def test_old_schema_migrates_without_guessing_a_game_role_and_deletes_cleanly(self):
        # Reproduce the pre-change ledger shape, including a dated save.
        old_root = self.root/'old'
        path = old_root/'data/super_memory.db'; path.parent.mkdir(parents=True)
        marker = 'ALT_PRIVAT_836491'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE native_saves(id INTEGER PRIMARY KEY AUTOINCREMENT, fp TEXT NOT NULL UNIQUE, ts REAL NOT NULL, content TEXT NOT NULL, role TEXT, memory_type TEXT, category TEXT, tags TEXT, maat_field TEXT, priority REAL, status TEXT DEFAULT "active")')
            db.execute('INSERT INTO native_saves(fp,ts,content,role,memory_type,priority) VALUES(?,?,?,?,?,?)',
                       (self.store.engine._fingerprint(marker), datetime(2026,9,9,12).timestamp(),marker,'user','fact',.65))
        migrated = SuperMemory(old_root)
        row = migrated.entries()[0]
        self.assertEqual(row['id'],1); self.assertEqual(row['content'],marker)
        self.assertEqual(row['perspective'],'')
        self.assertIn('Spielrolle unbekannt',migrated.source_label(row))
        block = migrated.generation_context('Was habe ich gestern gesagt?',runtime_context=COMPANION)
        self.assertIn('Spielrolle unbekannt',block)
        self.assertNotIn('[09.09.2026 12:00; Begleiter-KI',block)
        self.assertEqual(migrated.delete([row['id']]),1)
        for file in path.parent.iterdir():self.assertNotIn(marker.encode(),file.read_bytes())
        self.assertEqual(SuperMemory(old_root).entries(),[])

    def test_identical_text_in_different_roles_is_not_given_a_false_single_author(self):
        text='Wir suchen den Kristall in der Bibliothek.'
        self.store.save(text,runtime_context=COMPANION)
        self.store.save(text,role='assistant',runtime_context=COMPANION)
        self.store.save(text,runtime_context=ADVENTURE)
        rows=self.store.entries()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['perspective'],'mixed')
        self.assertIn('Mehrere Rollen',self.store.source_label(rows[0]))

    def test_corrections_only_supersede_the_same_speaker_in_the_same_mode(self):
        self.store.save('Für das Kristallprojekt nutze ich Qwen 3.',memory_type='technical',runtime_context=COMPANION)
        self.store.save('Für das Kristallprojekt nutze ich nun Qwen 4.',memory_type='technical',role='assistant',runtime_context=COMPANION)
        self.store.save('Für das Kristallprojekt nutze ich nun Qwen 5.',memory_type='technical',runtime_context=ADVENTURE)
        self.assertTrue(all(r['status']=='active' for r in self.store.entries()))
        self.store.save('Für das Kristallprojekt nutze ich jetzt Qwen 6.',memory_type='technical',runtime_context=COMPANION)
        rows={r['content']:r for r in self.store.entries()}
        self.assertEqual(rows['Für das Kristallprojekt nutze ich Qwen 3.']['status'],'superseded')
        self.assertEqual(rows['Für das Kristallprojekt nutze ich nun Qwen 4.']['status'],'active')
        self.assertEqual(rows['Für das Kristallprojekt nutze ich nun Qwen 5.']['status'],'active')

    def test_real_worker_companion_first_message_stores_player_as_companion_ai(self):
        w=Worker()
        try:
            w.command('/ai-start')
            w.send(op='companion_answer',choice=0,text='Merke dir: Ich bin deine Begleiter-KI und möchte den blauen Kristall behutsam mit dir erforschen, Maatis. Gemeinsam prüfen wir unsere Beobachtungen und achten die Grenzen aller Reisenden.')
            w.until(lambda e:e['event']=='busy' and not e['value'])
            store=SuperMemory(Path(w.temp.name))
            row=next(r for r in store.entries() if 'blauen Kristall' in r['content'])
            self.assertEqual(row['role'],'user')
            self.assertEqual(row['perspective'],'companion')
            self.assertEqual(store.source_label(row),'Begleiter-KI (Spieler)')
        finally:w.close()
