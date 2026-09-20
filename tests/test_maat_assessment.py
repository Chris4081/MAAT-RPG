"""Reproduce the posted incorrect average while preserving the model's ratings."""
import unittest
from unittest.mock import Mock,patch
from contextlib import nullcontext,redirect_stdout
from types import SimpleNamespace
import io
from test_desktop import APP
from shared.core.maat_assessment import correct_average,context_messages
from shared.plugins.plugin_loader import PluginManager


def assessment(language='en',values=('7','6','8','7','8'),total=None,inline=False):
    names=('Harmony','Balance','Creative Power','Connection','Respect') if language=='en' else (
        'Harmonie','Balance','Schöpfungskraft','Verbundenheit','Respekt')
    unit='out of 10' if language=='en' else 'von 10'
    rows=[f'{name}: A reason → {value} {unit}.' for name,value in zip(names,values)]
    title='MAAT value: ' if language=='en' else 'MAAT-Wert: '
    rows.append(title+(total or f'(7+6+8+7+8)/5 = 7.6 → 8 {unit} (rounded to nearest whole number per standard MAAT reporting).'))
    return (' ' if inline else '\n').join(rows)


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.messages=[{'role':'user','content':'maat wert von licht'}]

    def test_posted_average_is_36_divided_by_5_without_invented_rounding(self):
        for language in ('de','en'):
            for inline in (False,True):
                text=assessment(language,inline=inline)+'\nAn unrelated final sentence.'
                reply=correct_average(text,self.messages)
                with self.subTest(language=language,inline=inline):
                    self.assertIn('(7+6+8+7+8)/5 = '+('7,2 von 10' if language=='de' else '7.2 out of 10'),reply)
                    self.assertNotIn('rounded',reply);self.assertNotIn('7.6',reply)
                    self.assertTrue(reply.endswith('\nAn unrelated final sentence.'))
                    self.assertEqual(reply.split('MAAT')[0],text.split('MAAT')[0])
                    self.assertEqual(correct_average(reply,self.messages),reply)

    def test_decimal_scores_and_markdown_preserve_each_individual_rating(self):
        original=assessment('de',('7,5','6,5','8','7','8'),total='7,9 von 10.')
        original=original.replace('MAAT-Wert:','**MAAT-Wert:**')
        result=correct_average(original,self.messages)
        self.assertIn('**MAAT-Wert:** (7,5+6,5+8+7+8)/5 = 7,4 von 10.',result)
        self.assertIn('Harmonie: A reason → 7,5 von 10.',result)

    def test_ambiguous_incomplete_or_advanced_responses_are_never_filled_in(self):
        original=assessment()
        alternatives=[original.replace('Respect:','Unknown:'),original.replace('Respect:','Harmony:'),
                      original.replace('7 out of 10','11 out of 10',1),original.replace('7 out of 10','−7 out of 10',1),
                      original+'\n'+original,'```\n'+original+'\n```',
                      original.replace('MAAT value:','PLP:')]
        for reply in alternatives:
            self.assertEqual(correct_average(reply,self.messages),reply)
        for query in ('Hallo','Calculate PLP','Berechne Stability'):
            self.assertEqual(correct_average(original,[{'role':'user','content':query}]),original)

    def test_translation_and_plugin_consumers_receive_the_correct_average(self):
        history=self.messages+[{'role':'assistant','content':assessment()},
                               {'role':'user','content':'bitte auf Deutsch'}]
        context={'conversation':history,'last_user_input':'bitte auf Deutsch'}
        self.assertEqual(context_messages(context),history)
        plugin=Mock();plugin.after_response.side_effect=lambda text,context:text
        manager=PluginManager.__new__(PluginManager);manager.plugins_chat=[plugin]
        result=manager.handle_after_response(assessment('de'),context)
        self.assertIn('7,2 von 10',result)
        self.assertIn('7,2 von 10',plugin.after_response.call_args.args[0])

    def test_gui_worker_replaces_the_average_once_and_archives_the_correction(self):
        from gui import game_worker as worker
        from shared.core import streaming
        for backend in ('llama','llama_intel'):
            runtime=worker.Runtime.__new__(worker.Runtime)
            runtime.boot=SimpleNamespace(conversation=[{'role':'system','content':'MAAT-RPG'}])
            runtime.llm={'backend':backend};runtime.perf={'gui_mode':True};runtime.context={};runtime.language='en'
            for name in ('archive_chat','select_story_campaign','ensure_maatis_chat_opening','restore_chat_prompt','complete_chat_turn'):
                setattr(runtime,name,Mock())
            runtime.game_event_output=nullcontext;runtime.pm=PluginManager([])
            with patch.object(streaming,'backend_stream_chat',return_value=iter([assessment()])) as native, \
                 patch.object(streaming,'key_pressed',return_value=False),patch.object(worker,'emit') as emit,redirect_stdout(io.StringIO()):
                runtime.text('maat wert von licht')
            native.assert_called_once()
            edits=[call.kwargs for call in emit.call_args_list if call.kwargs.get('action')=='replace']
            self.assertEqual(len(edits),1)
            self.assertIn('7.2 out of 10',edits[0]['text'])
            self.assertEqual(runtime.boot.conversation[-1]['content'],edits[0]['text'])
            runtime.archive_chat.assert_any_call('assistant',edits[0]['text'])

    def test_super_memory_receives_the_correct_average_without_an_extra_model_call(self):
        from shared.core import streaming
        memory=Mock()
        memory.engine._iter_save_spans.return_value=[]
        memory.code_spans.return_value=[]
        memory.extract_model_saves.side_effect=lambda raw:(raw,[])
        memory.generation_context.return_value=''
        context={'super_memory':memory,'super_memory_query':'maat wert von licht'}
        with patch.object(streaming,'backend_stream_chat',return_value=iter([assessment()])) as native, \
             patch.object(streaming,'key_pressed',return_value=False),redirect_stdout(io.StringIO()):
            list(streaming.stream_chat_completion({'backend':'llama'},self.messages,{'gui_mode':True},runtime_context=context))
        native.assert_called_once()
        memory.finish_turn.assert_called_once()
        self.assertIn('7.2 out of 10',memory.finish_turn.call_args.args[1])
        self.assertNotIn('7.6',memory.finish_turn.call_args.args[1])
