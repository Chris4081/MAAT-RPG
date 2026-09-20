import builtins
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from test_desktop import APP
from shared.core.offline_wiki import OfflineWiki, WikiError, context_block, query_from_text
from shared.plugins.offline_wiki.plugin_main import Plugin
from shared.core.thinking_mode import prepare_generation_messages
from gui.wiki_settings import WikiSettings

ZIM = os.environ.get('MAAT_TEST_ZIM', '')

class OfflineWikiTests(unittest.TestCase):
    def test_no_file_bad_file_missing_reader(self):
        wiki = OfflineWiki()
        with self.assertRaisesRegex(WikiError, 'Keine ZIM'):wiki.lookup('Baum', '')
        with self.assertRaisesRegex(WikiError, 'nicht verfügbar'):wiki.lookup('Baum', '/missing.zim')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'broken.zim';path.write_text('invalid archive')
            with self.assertRaises(WikiError):wiki.lookup('Baum', str(path))
            real_import = builtins.__import__
            def no_lib(name,*args,**kwargs):
                if name.startswith('libzim'):raise ImportError('not installed')
                return real_import(name,*args,**kwargs)
            with patch('builtins.__import__',side_effect=no_lib):
                with self.assertRaisesRegex(WikiError,'benötigt libzim'):wiki.lookup('Baum',str(path))
        self.assertIsNone(wiki.archive)

    @unittest.skipUnless(Path(ZIM).is_file(), 'local ZIM not available')
    def test_real_zim_no_network_and_limited_excerpt(self):
        wiki = OfflineWiki()
        with patch('socket.create_connection',side_effect=AssertionError('network prohibited')):
            hit = wiki.lookup('Albert Einstein', ZIM)
            self.assertEqual(hit['title'], 'Albert Einstein')
            self.assertIn('1879',hit['text']);self.assertLessEqual(len(hit['text']),1400)
            self.assertTrue(hit['source'].startswith('zim://'))
            opened = wiki.archive
            self.assertEqual(wiki.lookup('Albert Einstein',ZIM),hit)
            self.assertIs(wiki.archive,opened)
            with self.assertRaises(WikiError):wiki.lookup('unbekannt_936328251',ZIM)
            with self.assertRaises(WikiError):wiki.lookup('Albert Einstein','/other-missing.zim')
            self.assertIsNone(wiki.archive);self.assertFalse(wiki.cache)

    def test_plugin_temporary_context_and_disabled(self):
        plugin = Plugin()
        hit = dict(title='Pyramide',source='zim://test.zim/Pyramide',text='Stein '*10000)
        original = 'Was ist Pyramide?';ctx = {'conversation': [{'role':'user','content':original}]}
        with patch('shared.plugins.offline_wiki.plugin_main.settings',return_value={'offline_wiki_zim_path':'test.zim'}), patch.object(plugin.wiki,'lookup',return_value=hit) as lookup:
            self.assertEqual(plugin.before_chat(original,ctx),(False,original))
            self.assertLess(len(ctx['offline_wiki_context']),1800)
            self.assertEqual(ctx['conversation'][0]['content'],original)
            self.assertEqual(lookup.call_args.args[0],'Pyramide')
            with patch('shared.core.thinking_mode.thinking_enabled',return_value=True), patch('shared.core.rpg_generation_context.rpg_context_enabled',return_value=False):
                messages = prepare_generation_messages(ctx['conversation'],runtime_context=ctx)
                self.assertEqual(len(messages),2)
                fresh = prepare_generation_messages(messages,runtime_context={})
                self.assertEqual(fresh,ctx['conversation'])
            plugin.before_chat('Hallo ^^',ctx)
            self.assertNotIn('offline_wiki_context',ctx)
        ctx['offline_wiki_context']='old'
        with patch('shared.plugins.offline_wiki.plugin_main.settings',return_value={'offline_wiki_auto':False,'offline_wiki_zim_path':'test.zim'}), patch.object(plugin.wiki,'lookup') as lookup:
            plugin.before_chat(original,ctx);lookup.assert_not_called()
            self.assertNotIn('offline_wiki_context',ctx)
        self.assertIsNone(query_from_text('Ich denke gerade nach.'))

    def test_picker_persistence_cancel_remove_profile(self):
        profiles = [{},{}];active = [0]
        view = WikiSettings(lambda:profiles[active[0]],lambda data:profiles[active[0]].update(data))
        try:
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'My Wiki.zim';path.write_bytes(b'test')
                with patch('gui.wiki_settings.QFileDialog.getOpenFileName',return_value=(str(path),'ZIM')):
                    view.choose()
                self.assertEqual(profiles[0]['offline_wiki_zim_path'],str(path))
                with patch('gui.wiki_settings.QFileDialog.getOpenFileName',return_value=('','')):view.choose()
                self.assertEqual(view.path.text(),str(path))
                view.auto.setChecked(False);self.assertFalse(profiles[0]['offline_wiki_auto'])
                active[0]=1;view.refresh();self.assertEqual(view.path.text(),'')
                self.assertTrue(view.auto.isChecked())
                active[0]=0;view.refresh();self.assertEqual(view.path.text(),str(path))
                view.select_path('');self.assertEqual(profiles[0]['offline_wiki_zim_path'],'')
        finally:view.close();view.deleteLater();APP.processEvents()

    def test_worker_returns_error_without_crash(self):
        from test_live_rpg import Worker
        worker=Worker()
        try:
            worker.send(op='wiki_lookup',term='Pyramide')
            events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            result=next(e for e in events if e['event']=='wiki_result')
            self.assertIn('Keine ZIM-Datei',result['text'])
            self.assertFalse(any(e['event']=='error' for e in events))
        finally:worker.close()

    def test_natural_questions_and_prefixes(self):
        examples = {
            'gut was weißt du über michael matzer': 'michael matzer',
            'wo ist wittighausen': 'wittighausen',
            'Hallo =) Wo liegt Wittighausen?': 'Wittighausen',
            'Was weisst du ueber Michael Matzer?': 'Michael Matzer',
            'Kannst du mir etwas über Albert Einstein erzählen?': 'Albert Einstein',
            'Erzähl mir etwas über Pyramiden bitte ^^': 'Pyramiden',
            'Kennst du den Michael Matzer?': 'Michael Matzer',
            'Wo befindet sich Wittighausen?': 'Wittighausen',
        }
        for question, expected in examples.items():
            with self.subTest(question=question):self.assertEqual(query_from_text(question),expected)
        self.assertIsNone(query_from_text('Hallo =)'))
        self.assertIsNone(query_from_text('Danke, mir geht es gut.'))

    @unittest.skipUnless(Path(ZIM).is_file(), 'local ZIM not available')
    def test_real_articles_reach_llama_completion_call(self):
        from shared.core.streaming import stream_chat_completion
        from unittest.mock import Mock
        import json
        plugin = Plugin()
        instance = SimpleNamespace(metadata={'general.architecture':'llama'},
            create_chat_completion=Mock(return_value=iter([])))
        llm = {'backend':'llama','chat_state':{'architecture':'llama'},'instance':instance}
        with patch('shared.plugins.offline_wiki.plugin_main.settings',return_value={'offline_wiki_zim_path':ZIM}), patch('shared.core.thinking_mode.thinking_enabled',return_value=True), patch('shared.core.rpg_generation_context.rpg_context_enabled',return_value=False), patch('shared.core.streaming._can_use_posix_cbreak',return_value=False):
            for question, title, evidence in [('gut was weißt du über michael matzer','Michael Matzer','Bürgermeister'),('wo ist wittighausen','Wittighausen','Main-Tauber-Kreis')]:
                ctx = {'last_user_input':question}
                # A previous plugin's memory prefix must not trigger the lookup.
                enriched = '[Erinnerung: Was ist Musik?]\n' + question
                self.assertEqual(plugin.before_chat(enriched,ctx),(False,enriched))
                history = [{'role':'system','content':'Erinnerungen bleiben.'},{'role':'user','content':question}]
                list(stream_chat_completion(llm,history,{'gui_mode':True},runtime_context=ctx))
                sent = instance.create_chat_completion.call_args.kwargs['messages']
                snippets = [m['content'] for m in sent if m['content'].startswith('[MAAT-OFFLINE-WIKI]')]
                self.assertEqual(len(snippets),1)
                data=json.loads(snippets[0].rsplit('\n',1)[-1])
                self.assertEqual(data['title'],title)
                self.assertIn(evidence,data['text'])
                self.assertLessEqual(len(data['text']),400)
                self.assertEqual(history[-1]['content'],question)
                self.assertIn(history[0],sent)

    def test_original_word_rule_categories(self):
        from shared.core.offline_wiki import queries_from_text
        cases = {
            'vergleiche Äpfel und Birnen': ['Apfel', 'Birne'],
            'was haben Äpfel und Birnen gemeinsam?': ['Apfel', 'Birne'],
            'ich fahre von Berlin nach Hamburg': ['Berlin', 'Hamburg'],
            'kennst du Materia den Rapper': ['Marteria'],
            'was weißt du über buckelwahl': ['Buckelwal'],
            'Leonrado da Vinci': ['Leonardo da Vinci'],
            'berechne den Maatwert von Pyramiden': ['Pyramiden'],
            'ich spiele gerne Minecraft': ['Minecraft'],
            'Suno erstellt Musik': ['Suno', 'Musik'],
            'schreibe ein Gedicht über Berlin': ['Gedicht'],
            'Was bedeutet Bewusstsein?': ['Bewusstsein'],
            'Was ist Qwen?': ['Alibaba Cloud'],
            'Wie viele Einwohner hat Berlin?': ['Berlin'],
            'Formel1': ['Formel 1'],
            '!wiki Albert Einstein': ['Albert Einstein'],
            '[MAAT_FILE_BUILDER_TEST_LOG]Was ist Musik?[/MAAT_FILE_BUILDER_TEST_LOG] Wo liegt Wittighausen?': ['Wittighausen'],
        }
        for question, expected in cases.items():
            with self.subTest(question=question):self.assertEqual(queries_from_text(question),expected)

    def test_comparisons_stay_bounded_and_llama_stops_after_one_hit(self):
        import json
        from shared.core.offline_wiki import generation_context
        def lookup(term, path):
            return {'title':term, 'source':'zim://test/'+term, 'text':'Fakten über diesen Artikel. '*100}
        for arch, count in [('llama',1),('qwen3',2)]:
            plugin=Plugin();ctx={'llm':{'chat_state':{'architecture':arch}}}
            with patch('shared.plugins.offline_wiki.plugin_main.settings',return_value={'offline_wiki_zim_path':'test.zim'}), patch.object(plugin.wiki,'lookup',side_effect=lookup) as search:
                plugin.before_chat('vergleiche Äpfel und Birnen',ctx)
                self.assertEqual(search.call_count,count)
                block=generation_context(ctx['offline_wiki_context'],ctx['llm'])
                data=json.loads(block.rsplit('\n',1)[-1])
                if arch=='llama':
                    self.assertEqual(data['title'],'Apfel')
                    self.assertLessEqual(len(data['text']),400)
                else:
                    self.assertEqual([a['title'] for a in data['articles']],['Apfel','Birne'])
                    self.assertLessEqual(sum(len(a['text']) for a in data['articles']),1000)
                    self.assertLessEqual(len(block),1800)
                    switched=generation_context(ctx['offline_wiki_context'],{'chat_state':{'architecture':'llama'}})
                    switched_data=json.loads(switched.rsplit('\n',1)[-1])
                    self.assertEqual(switched_data['title'],'Apfel')
                    self.assertLessEqual(len(switched_data['text']),400)

    def test_place_qualifiers_and_negative_questions(self):
        from shared.core.offline_wiki import queries_from_text
        for question in ('kennst du nicht reicholzheim?', 'kennst du etwa nicht Reicholzheim?',
                         'kennst du noch nicht Reicholzheim?', 'kennst du gar nicht Reicholzheim?',
                         'was weißt du über die Ortschaft Reicholzheim?', 'wo liegt der Ort Reicholzheim?',
                         'was weißt du über das Dorf Reicholzheim?'):
            with self.subTest(question=question):
                self.assertEqual([x.casefold() for x in queries_from_text(question)], ['reicholzheim'])
        self.assertEqual(queries_from_text('Was ist eine Ortschaft?'), ['Ortschaft'])

    @unittest.skipUnless(Path(ZIM).is_file(), 'local ZIM not available')
    def test_reicholzheim_lookup_and_visible_source_at_generation(self):
        import json
        from shared.core.offline_wiki import generation_context
        plugin=Plugin();llm={'chat_state':{'architecture':'llama'}}
        with patch('shared.plugins.offline_wiki.plugin_main.settings',return_value={'offline_wiki_zim_path':ZIM}), patch('shared.core.thinking_mode.thinking_enabled',return_value=True), patch('shared.core.rpg_generation_context.rpg_context_enabled',return_value=False), patch('shared.core.gui_bridge.emit') as notify:
            for question in ('was weißt du über reicholzheim', 'kennst du nicht reicholzheim?'):
                ctx={'llm':llm,'last_user_input':question}
                plugin.before_chat(question,ctx)
                messages=prepare_generation_messages([{'role':'user','content':question}],runtime_context=ctx,llm=llm)
                wiki=next(m['content'] for m in messages if m['content'].startswith('[MAAT-OFFLINE-WIKI]'))
                data=json.loads(wiki.rsplit('\n',1)[-1])
                self.assertEqual(data['title'],'Reicholzheim')
                self.assertIn('Ortschaft',data['text']);self.assertIn('Wertheim',data['text'])
                self.assertLessEqual(len(data['text']),400)
                self.assertEqual(notify.call_args.kwargs['titles'],['Reicholzheim'])
                self.assertEqual(notify.call_args.kwargs['excerpt'],data['text'])
            prepare_generation_messages([{'role':'user','content':'Hallo'}],runtime_context={},llm=llm)
            self.assertEqual(notify.call_args.kwargs['titles'],[])

    def test_chat_source_hint_and_reset(self):
        from PySide6.QtWidgets import QLabel
        from gui.live_window import LiveWindow
        window=SimpleNamespace(wiki_source=QLabel(),ui=lambda text,**values:text.format(**values))
        try:
            LiveWindow.update_wiki_source(window,{'titles':['Reicholzheim'],'excerpt':'Eine Ortschaft von Wertheim.'})
            self.assertIn('Reicholzheim',window.wiki_source.text())
            self.assertIn('Wertheim',window.wiki_source.toolTip())
            self.assertFalse(window.wiki_source.isHidden())
            LiveWindow.update_wiki_source(window,{'terms':['Testort'],'error':'Kein Treffer'})
            self.assertIn('Kein Offline-Auszug',window.wiki_source.text())
            self.assertEqual(window.wiki_source.toolTip(),'Kein Treffer')
            LiveWindow.update_wiki_source(window,{})
            self.assertTrue(window.wiki_source.isHidden())
            self.assertEqual(window.wiki_source.toolTip(),'')
        finally:window.wiki_source.deleteLater()

    def test_maat_assessment_word_variants(self):
        from shared.core.offline_wiki import queries_from_text
        variants = [
            'berechne den maat wert von "MOna Lisa"',
            'Wie hoch ist der MAAT-Wert von Mona Lisa?',
            'MAAT-Score: Mona Lisa', 'MAAT score Mona Lisa',
            'Berechne für Mona Lisa den MAAT-Wert',
            'Bewerte Mona Lisa nach MAAT',
            'Gib mir eine MAAT-Bewertung für die Mona Lisa',
            'Kannst du den MAAT‑Wert für „Mona Lisa“ berechnen?',
            'Calculate the MAAT value of Mona Lisa',
            'M.A.A.T.-Wert von Mona Lisa',
            'Ermittle den MAAT_Wert zu Mona Lisa bitte',
            'Maat-Analyse von Mona Lisa', 'Ma’at-Wert: Mona Lisa',
            'Schätze Mona Lisa anhand von MAAT ein',
            'Berechne den Wert von Mona Lisa nach MAAT',
            'Bewerte das Gemälde Mona Lisa nach MAAT',
            'Maatbewertung für Mona Lisa',
        ]
        for question in variants:
            with self.subTest(question=question):
                self.assertEqual([t.casefold() for t in queries_from_text(question)], ['mona lisa'])
        for question in ['MAAT Wert', 'MAAT-Wert bitte', 'Kannst du den MAAT-Wert berechnen?']:
            self.assertEqual(queries_from_text(question), [])
        self.assertEqual(queries_from_text('Was ist MAAT?'), ['MAAT'])
        self.assertEqual(queries_from_text('Berechne den MAAT-Wert von Reicholzheim'), ['Reicholzheim'])
        self.assertEqual(queries_from_text('Bewerte Michael Matzer nach MAAT'), ['Michael Matzer'])

    def test_maat_full_titles_and_comparisons(self):
        from shared.core.offline_wiki import queries_from_text
        for title in ['Krieg und Frieden', 'Das Leben ist schön', 'Der Herr der Ringe', 'Song of the South', 'Stadt der Engel']:
            self.assertEqual(queries_from_text(f'Berechne den MAAT-Wert von "{title}"'), [title])
        self.assertEqual(queries_from_text('MAAT-Bewertung von "Mona Lisa" und "Der Schrei"'), ['Mona Lisa','Der Schrei'])
        self.assertEqual(queries_from_text('berechne den maatwert von Apfel und Birne'), ['Apfel','Birne'])
        self.assertEqual(queries_from_text('Analysiere den MAAT-Wert von dem Lied Imagine'), ['Imagine'])

    @unittest.skipUnless(Path(ZIM).is_file(), 'local ZIM not available')
    def test_maat_mona_lisa_real_article_keeps_original_request(self):
        import json
        from shared.core.offline_wiki import generation_context
        question='berechne den maat wert von "MOna Lisa"'
        plugin=Plugin();llm={'chat_state':{'architecture':'llama'}}
        ctx={'llm':llm,'last_user_input':question}
        with patch('shared.plugins.offline_wiki.plugin_main.settings',return_value={'offline_wiki_zim_path':ZIM}), patch('shared.core.thinking_mode.thinking_enabled',return_value=True), patch('shared.core.rpg_generation_context.rpg_context_enabled',return_value=False):
            self.assertEqual(plugin.before_chat(question,ctx), (False,question))
            messages=prepare_generation_messages([{'role':'user','content':question}],runtime_context=ctx,llm=llm)
            wiki=next(m['content'] for m in messages if m['content'].startswith('[MAAT-OFFLINE-WIKI]'))
            article=json.loads(wiki.rsplit('\n',1)[-1])
            self.assertEqual(article['title'],'Mona Lisa')
            self.assertIn('Leonardo',article['text'])
            self.assertLessEqual(len(article['text']),400)
            self.assertEqual(messages[-1],{'role':'user','content':question})
