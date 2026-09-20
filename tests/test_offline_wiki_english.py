"""English wiki intents and real local article delivery, with no GGUF load."""
import builtins
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
from test_offline_wiki import ZIM
from test_live_rpg import Worker
from shared.core.offline_wiki import OfflineWiki, WikiError, queries_from_text, generation_context
from shared.plugins.offline_wiki.plugin_main import Plugin
from shared.core.thinking_mode import prepare_generation_messages


class EnglishWikiTests(unittest.TestCase):
    def test_people_places_questions_comparisons_titles_and_small_talk(self):
        cases={
            'What do you know about Michael Matzer?':['Michael Matzer'],
            'Hi ^^ Can you tell me something about Albert Einstein?':['Albert Einstein'],
            'Could you tell me more about the village of Reicholzheim?':['Reicholzheim'],
            "Don't you know Reicholzheim?":['Reicholzheim'],
            'Do you not know Reicholzheim?':['Reicholzheim'],
            'Where is Wittighausen located?':['Wittighausen'],
            'Where is the town of Wertheim situated?':['Wertheim'],
            'How many people live in Berlin?':['Berlin'],
            'How many inhabitants does Berlin have?':['Berlin'],
            "What's the population of Berlin?":['Berlin'],
            'Who was Michael Matzer?':['Michael Matzer'],
            'What does photosynthesis mean?':['photosynthesis'],
            'Explain photosynthesis to me, please.':['photosynthesis'],
            'What do you think of Mona Lisa?':['Mona Lisa'],
            "What's your opinion on Mona Lisa?":['Mona Lisa'],
            'Compare Berlin and Hamburg.':['Berlin','Hamburg'],
            'What is the difference between Berlin and Hamburg?':['Berlin','Hamburg'],
            'What do Berlin and Hamburg have in common?':['Berlin','Hamburg'],
            'I am travelling from Berlin to Hamburg.':['Berlin','Hamburg'],
            'What is the distance between Berlin and Hamburg?':['Berlin','Hamburg'],
            'Compare "War and Peace" with "The Lord of the Rings"':['War and Peace','The Lord of the Rings'],
            'Tell me about the book "War and Peace"':['War and Peace'],
            'What is "The Who"?':['The Who'],
            'What did I say yesterday?':[],
            'Do you remember what I said last month?':[],
            'Thank you!':[],
            'How are you doing?':[],
            'Can you explain it?':[],
            'Tell me about the musician Peter Fox':['Peter Fox'],
            'Have you heard of Materia the rapper?':['Marteria'],
            'I enjoy playing Minecraft':['Minecraft'],
            'Write a poem about Berlin':['Poem'],
            'Suno creates music':['Suno','Music'],
        }
        for question,expected in cases.items():
            with self.subTest(question=question):self.assertEqual(queries_from_text(question),expected)
        self.assertEqual(queries_from_text('Compare Berlin and Hamburg',max_terms=1),['Berlin'])

    def test_english_maat_variations_preserve_exact_subjects(self):
        for question in (
            'Calculate the MAAT value of "MOna Lisa"',
            'Can you estimate the MAAT score of the painting Mona Lisa?',
            'Please assess Mona Lisa using MAAT.',
            "What would Mona Lisa's MAAT score be?",
            'What is Mona Lisa’s MAAT rating?',
            "Can you calculate Mona Lisa's MAAT value?",
            'Determine the MAAT rating for Mona Lisa in detail.',
            'Give me a MAAT assessment of Mona Lisa please.',
            'Analyze Mona Lisa according to MAAT',
            'MAAT analysis: Mona Lisa',
            'Evaluate the MAAT value for Mona Lisa using Wikipedia',
            'Calculate the MAAT value for Mona Lisa on a scale of 0 to 1',
        ):
            with self.subTest(question=question):
                self.assertEqual([t.casefold() for t in queries_from_text(question)],['mona lisa'])
        self.assertEqual(queries_from_text('Compare the MAAT values of Berlin and Hamburg'),['Berlin','Hamburg'])
        self.assertEqual(queries_from_text('MAAT assessment of "War and Peace" and "The Who"'),['War and Peace','The Who'])
        for question in ('What is the MAAT value?', 'Can you calculate the MAAT score?', 'MAAT analysis please'):
            self.assertEqual(queries_from_text(question),[])

    def test_one_llama_excerpt_and_two_other_model_excerpts_never_replace_memory(self):
        for arch,count in (('llama',1),('qwen3',2),('gemma4',2)):
            plugin=Plugin();llm={'chat_state':{'architecture':arch}}
            question='Compare Berlin and Hamburg'
            context={'llm':llm,'last_user_input':question}
            history=[{'role':'system','content':'Keep this memory: we discussed music.'},
                     {'role':'user','content':question}]
            def hit(term,path):return dict(title=term,source='zim://test/'+term,text='Archive evidence. '*200)
            with patch('shared.plugins.offline_wiki.plugin_main.settings',return_value={'language':'en','offline_wiki_zim_path':'test.zim'}),patch.object(plugin.wiki,'lookup',side_effect=hit) as lookup,patch('shared.core.rpg_generation_context.rpg_context_enabled',return_value=False):
                enriched='[Memory: What is Music?]\n'+question
                self.assertEqual(plugin.before_chat(enriched,context),(False,enriched))
                self.assertEqual(lookup.call_count,count)
                self.assertEqual([c.args[0] for c in lookup.call_args_list],['Berlin','Hamburg'][:count])
                messages=prepare_generation_messages(history,llm=llm,runtime_context=context)
                blocks=[m['content'] for m in messages if m['content'].startswith('[MAAT-OFFLINE-WIKI]')]
                self.assertEqual(len(blocks),1)
                self.assertIn('Answer in English',blocks[0])
                data=json.loads(blocks[0].rsplit('\n',1)[-1])
                if count==1:self.assertLessEqual(len(data['text']),400)
                else:
                    self.assertEqual(len(data['articles']),2)
                    self.assertLessEqual(sum(len(a['text']) for a in data['articles']),1000)
                    self.assertLessEqual(len(blocks[0]),1800)
                    switched=generation_context(blocks[0],{'chat_state':{'architecture':'llama'}},'en')
                    self.assertLessEqual(len(json.loads(switched.rsplit('\n',1)[-1])['text']),400)
                self.assertIn(history[0],messages)
                self.assertEqual(messages[-1],history[-1])
                context['last_user_input']='What did I say yesterday?'
                plugin.before_chat(context['last_user_input'],context)
                self.assertNotIn('offline_wiki_context',context)
                fresh=prepare_generation_messages(messages,llm=llm,runtime_context=context)
                self.assertFalse(any(m['content'].startswith('[MAAT-OFFLINE-WIKI]') for m in fresh))
                lookup.reset_mock()
                with patch('shared.plugins.offline_wiki.plugin_main.settings',return_value={'language':'en','offline_wiki_zim_path':'test.zim','offline_wiki_auto':False}):
                    plugin.before_chat(question,context)
                lookup.assert_not_called()

    @unittest.skipUnless(Path(ZIM).is_file(),'local ZIM not available')
    def test_english_questions_read_real_german_zim_and_reach_llama_call(self):
        from shared.core.streaming import stream_chat_completion
        plugin=Plugin()
        instance=SimpleNamespace(metadata={'general.architecture':'llama'},create_chat_completion=Mock(return_value=iter([])))
        llm={'backend':'llama','chat_state':{'architecture':'llama'},'instance':instance}
        with patch('socket.create_connection',side_effect=AssertionError('network prohibited')),patch('shared.plugins.offline_wiki.plugin_main.settings',return_value={'language':'en','offline_wiki_zim_path':ZIM}),patch('shared.core.streaming._stream_lang',return_value='en'),patch('shared.core.thinking_mode.thinking_enabled',return_value=True),patch('shared.core.rpg_generation_context.rpg_context_enabled',return_value=False),patch('shared.core.streaming._can_use_posix_cbreak',return_value=False):
            for question,title,evidence in (
                ('What do you know about Michael Matzer?','Michael Matzer','Bürgermeister'),
                ('Where is Wittighausen located?','Wittighausen','Main-Tauber-Kreis'),
                ("Don't you know the village of Reicholzheim?",'Reicholzheim','Wertheim'),
                ("What would Mona Lisa's MAAT score be?",'Mona Lisa','Leonardo'),
            ):
                ctx={'llm':llm,'last_user_input':question}
                plugin.before_chat(question,ctx)
                history=[{'role':'system','content':'Preserve our memories.'},{'role':'user','content':question}]
                list(stream_chat_completion(llm,history,{'gui_mode':True},runtime_context=ctx))
                sent=instance.create_chat_completion.call_args.kwargs['messages']
                block=next(m['content'] for m in sent if m['content'].startswith('[MAAT-OFFLINE-WIKI]'))
                article=json.loads(block.rsplit('\n',1)[-1])
                self.assertEqual(article['title'],title)
                self.assertIn(evidence,article['text'])
                self.assertLessEqual(len(article['text']),400)
                self.assertIn('Answer in English',block)
                self.assertEqual(sent[-1],history[-1])
                self.assertIn(history[0],sent)

    def test_english_errors_commands_and_chat_source_hint(self):
        from gui.live_window import LiveWindow
        from PySide6.QtWidgets import QLabel
        from shared.core.wiki_i18n import tr
        wiki=OfflineWiki('en')
        with self.assertRaisesRegex(WikiError,'No ZIM file selected'):wiki.lookup('Berlin','')
        with self.assertRaisesRegex(WikiError,'ZIM file unavailable'):wiki.lookup('Berlin','/missing.zim')
        plugin=Plugin()
        with patch('shared.plugins.offline_wiki.plugin_main.settings',return_value={'language':'en'}):
            self.assertIn('Automatic: on',plugin.command('/wiki status'))
            self.assertIn('No ZIM file selected',plugin.command('/wiki Berlin'))
        view=SimpleNamespace(wiki_source=QLabel(),ui=lambda text,**values:tr(text,'en',**values))
        try:
            LiveWindow.update_wiki_source(view,dict(titles=['Mona Lisa'],excerpt='Article text.'))
            self.assertEqual(view.wiki_source.text(),'📚 Offline source for this answer: Mona Lisa')
            self.assertEqual(view.wiki_source.toolTip(),'Article text.')
            LiveWindow.update_wiki_source(view,dict(terms=['Unknown'],error='No result'))
            self.assertIn('No offline excerpt',view.wiki_source.text())
        finally:view.wiki_source.deleteLater();APP.processEvents()

    def test_english_fulltext_skips_disambiguation_without_changing_article(self):
        wiki=OfflineWiki('en');wiki.identity=('/tmp/fixture.zim',0,0)
        text=b'<p>An English archive article.</p>'
        entry=SimpleNamespace(title='Mercury (planet)',path='Mercury_(planet)',get_item=lambda:SimpleNamespace(mimetype='text/html',size=len(text),content=text))
        archive=Mock();archive.get_entry_by_title.side_effect=KeyError()
        def path(value):
            if value=='ambiguous':return SimpleNamespace(title='Mercury (disambiguation)')
            if value=='planet':return entry
            raise KeyError(value)
        archive.get_entry_by_path.side_effect=path
        searcher=Mock();searcher.search.return_value.getResults.return_value=['ambiguous','planet']
        with patch.object(wiki,'open',return_value=archive),patch('libzim.search.Searcher',return_value=searcher):
            hit=wiki.lookup('nonexistent exact title','/tmp/fixture.zim')
        self.assertEqual(hit['title'],'Mercury (planet)')
        self.assertEqual(hit['text'],'An English archive article.')

    def test_real_english_worker_reports_optional_archive_error_without_crash(self):
        worker=Worker(seed={'settings_state.json':{'language':'en'}})
        try:
            worker.send(op='wiki_lookup',term='Berlin')
            events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            self.assertIn('No ZIM file selected',next(e['text'] for e in events if e['event']=='wiki_result'))
            events=worker.command('/wiki status')
            self.assertIn('No online requests',''.join(e.get('text','') for e in events))
        finally:worker.close()


if __name__=='__main__':unittest.main()
