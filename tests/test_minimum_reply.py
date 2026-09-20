"""Saved hard minima must never block a natural end; loops must not be rewarded."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from test_desktop import APP
from shared.core import streaming
from shared.core.ai_plugin_settings import begin_turn
from shared.core.reply_style import generation_length_options, build_reply_style_prompt
from shared.core.chat_turn import ChatTurn, ChatCancelled
from shared.core.repetition_guard import RepetitionStopped, RepetitionGuard, guard_chunks
from test_gpt_oss import Model as HarmonyModel, configured
from shared.core.backend_router import stream_chat
import test_ai_plugins as helpers

SETTINGS = {'reply_style_enabled':True, 'reply_style_force_length':True,
            'reply_style_min_tokens':300, 'reply_style_max_tokens':600}

class Model:
    metadata = {}
    def __init__(self, output=('Hello! ', 'How are you?')):
        self.output, self.calls, self.closed = output, [], False
        self.reset = Mock()
    def create_chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        self.closed = False
        try:
            for text in self.output:
                yield {'choices':[{'delta':{'content':text}}]}
        finally:self.closed = True

class MinimumReplyTests(unittest.TestCase):
    def stream(self, model, backend='llama', context=None, plugins=None):
        llm = model if backend=='classic' else {'backend':backend, 'instance':model}
        context = context if context is not None else {'pm':helpers.manager()}
        with patch('shared.core.ai_plugin_settings.load_settings', return_value=SETTINGS), \
             patch.object(streaming, '_stream_lang', return_value='en'), \
             patch.object(streaming, 'key_pressed', return_value=False), contextlib.redirect_stdout(io.StringIO()):
            begin_turn(context, 'Hello')
            yield from streaming.stream_chat_completion(llm, [{'role':'user','content':'Hello'}],
                {'max_tokens':100, '_reply_min_tokens':300, 'gui_mode':True, 'raise_errors':True},
                plugins=plugins, runtime_context=context)

    def test_legacy_preferences_are_soft_and_caps_unchanged(self):
        for maximum in (None, 0, 1, 100, 1000):
            perf = {'max_tokens':maximum, 'n_ctx':2048, '_reply_min_tokens':300}
            self.assertEqual(generation_length_options(perf, SETTINGS), {'max_tokens':maximum, 'n_ctx':2048})
            self.assertEqual(perf['_reply_min_tokens'], 300)
        self.assertEqual(generation_length_options({}, SETTINGS), {})
        for language in ('de','en'):
            prompt = build_reply_style_prompt(SETTINGS, language)
            for part in (('300–600', 'soft lower target', 'Greetings', 'never invent') if language=='en'
                         else ('300–600', 'weiche Untergrenze', 'Begrüßungen', 'erfinde keine')):
                self.assertIn(part, prompt)
            self.assertNotIn('enforced', prompt)
        self.assertEqual(build_reply_style_prompt(dict(SETTINGS, reply_style_enabled=False)), '')

    def test_arm_intel_classic_stream_short_reply_once_without_eos_filter(self):
        for backend in ('llama','llama_intel','classic'):
            model = Model()
            source = self.stream(model, backend)
            self.assertEqual(next(source), 'Hello! ')
            self.assertFalse(model.closed)
            self.assertEqual(''.join(source), 'How are you?')
            self.assertTrue(model.closed)
            self.assertEqual(len(model.calls), 1)
            self.assertEqual(model.calls[0]['max_tokens'], 100)
            self.assertNotIn('logits_processor', model.calls[0])
            self.assertNotIn('min_tokens', model.calls[0])

    def test_gpt_oss_allows_analysis_end_and_short_final_with_stale_minimum(self):
        for backend in ('llama','llama_intel'):
            model = HarmonyModel().script(('channel',), 'analysis', ('message',), 'Private reasoning.',
                ('end',), ('start',), 'assistant', ('channel',), 'final', ('message',), 'Hello!', ('return',))
            llm = configured(model, backend)
            self.assertEqual(''.join(stream_chat(llm, [{'role':'user','content':'Hello'}],
                {'max_tokens':300, '_reply_min_tokens':300})), 'Hello!')
            self.assertTrue(model.closed)
            self.assertNotIn('logits_processor', model.sampling)

    def test_loop_stops_speech_without_memory_after_hooks_or_commit(self):
        from shared.core.super_memory import SuperMemory
        folder = tempfile.TemporaryDirectory(prefix='maat-repeat-memory-')
        self.addCleanup(folder.cleanup)
        for backend in ('llama','llama_intel','classic'):
          for memory_enabled in (False, True):
            model = Model(['Hello! '] + ['🚀 :) 🚀 '] * 100)
            turn, speech = ChatTurn('loop'), Mock()
            memory = SuperMemory(Path(folder.name), maintenance=False, migrate=False)
            memory.finish_turn = Mock()
            context = {'pm':helpers.manager(), 'gui_chat_turn':turn}
            if memory_enabled: context['super_memory'] = memory
            shown = []
            with self.assertRaises(RepetitionStopped):
                for text in self.stream(model, backend, context, [speech]): shown.append(text)
            self.assertIn('Hello!', ''.join(shown))
            self.assertLess(len(''.join(shown)), 150)
            self.assertEqual(''.join(c.args[0] for c in speech.on_token.call_args_list), ''.join(shown))
            self.assertTrue(model.closed)
            self.assertTrue(turn.cancelled.is_set())
            speech.begin_response_speech.assert_called()
            speech.after_stream.assert_not_called()
            memory.finish_turn.assert_not_called()
            with self.assertRaises(ChatCancelled):turn.commit()
            if backend != 'classic':model.reset.assert_called_once()

    def test_escape_and_next_turn(self):
        model, turn = Model(), ChatTurn('escape')
        source = self.stream(model, context={'gui_chat_turn':turn})
        self.assertEqual(next(source), 'Hello! ')
        turn.cancel()
        with self.assertRaises(ChatCancelled):next(source)
        self.assertTrue(model.closed)
        self.assertEqual(''.join(self.stream(model)), 'Hello! How are you?')

class RepetitionGuardTests(unittest.TestCase):
    def collect(self, text, size=1, query=''):
        return ''.join(guard_chunks((text[i:i+size] for i in range(0,len(text),size)),query=query))

    def test_detects_emoji_smiley_words_sentences_across_chunks(self):
        for unit in ('🚀 :) 🚀 ', '🙂', ':) ', 'again ', 'Das ist wirklich interessant. '):
            for size in (1,2,7,31,10000):
                with self.subTest(unit=unit, size=size), self.assertRaises(RepetitionStopped):
                    self.collect('A complete answer. '+unit*100, size)

    def test_allows_short_examples_markdown_numbers_code_quotes_varied_text(self):
        examples = ['Hallo! Schön, dass du wieder da bist. Was liegt dir auf dem Herzen? 😊',
            'Testfall: 🚀 :) 🚀 🚀 :) 🚀 🚀 :)',
            '100000000000000000000000\n' + '|---'*80,
            '\n'.join(f'| {i} | pending |' for i in range(50)),
            '```python\n' + 'print("again")\n'*30 + '```\nReady.',
            '~~~text\n' + 'again '*100 + '\n~~~\nReady.',
            '> ' + 'again '*100 + '\nReady.',
            '`' + 'again '*100 + '` done.',
            ' '.join(f'The item {i} has another property.' for i in range(100))]
        for text in examples:
            for size in (1,7,10000):self.assertEqual(self.collect(text,size), text)
        for query in ('Please repeat hello 30 times.', 'Wiederhole Hallo bitte 30 mal.'):
            self.assertEqual(self.collect('hello '*100, query=query), 'hello '*100)

    def test_resumes_after_code_bilingual_notice_and_bounded_window(self):
        with self.assertRaises(RepetitionStopped):
            self.collect('```text\n'+ 'again '*100+'\n```\n'+ '🚀 :) '*100)
        self.assertIn('Wiederholung erkannt', RepetitionStopped().notice('de'))
        self.assertIn('Repetition detected', RepetitionStopped().notice('en'))
        guard = RepetitionGuard()
        guard.feed(' '.join(str(i) for i in range(10000)))
        self.assertLessEqual(len(guard.window), guard.WINDOW)

if __name__=='__main__':unittest.main()
