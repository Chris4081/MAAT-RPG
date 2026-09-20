"""GPT-OSS protocol tests with a project-written serializer and controlled tokens.

The minimal synthetic template is not an upstream model template. It exercises
the RPG adapter's protocol handling, not a particular model's full prompt format.
"""
from copy import deepcopy
from unittest import TestCase, main
from unittest.mock import Mock, patch

from test_desktop import APP
from shared.core.gpt_oss import MARKERS, HarmonyOutput
from shared.core.gguf_chat import configure_template
from shared.core.model_family import identify_family
from shared.core.backend_router import stream_chat
from shared.core.thinking_mode import prepare_generation_messages

TEMPLATE = (
    "<|start|>system<|message|>Reasoning: {{ reasoning_effort }}<|end|>"
    "{% for turn in messages %}<|start|>{{ turn.role }}<|message|>"
    "{{ turn.content }}<|end|>{% endfor %}<|start|>assistant"
)


class Model:
    def __init__(self, legacy=False, prefix=None):
        self.markers = {kind: values[min(int(legacy), len(values)-1)] for kind, values in MARKERS.items()}
        self.ids = {value: 1000+i for i, value in enumerate(self.markers.values())}
        self.pieces = {value: key.encode() for key, value in self.ids.items()}
        template = TEMPLATE
        if legacy:
            for values in MARKERS.values():
                if len(values) == 2:
                    template = template.replace(values[0], values[1])
        if prefix:
            template += self.markers['channel'] + prefix + self.markers['message']
        self.metadata = {'general.architecture': 'gpt-oss', 'general.name': 'gpt-oss-20b',
                         'tokenizer.chat_template': template}
        self.model_path = 'gpt-oss-20b.gguf'
        self.output = []
        self.generated = 0
        self.closed = False
        self.capacity = 20000
        self.close = Mock()
        self.intel_repacking = False

    def token_eos(self): return self.ids[self.markers['end']]
    def token_bos(self): return -1
    def n_ctx(self): return self.capacity
    def tokenize(self, text, add_bos=False, special=False):
        string = text.decode()
        if special and string in self.ids:
            return [self.ids[string]]
        self.last_prompt = string
        return [10, 11, 12]
    def detokenize(self, tokens, special=False):
        self.last_special = special
        return b''.join(self.pieces.get(token, b'') for token in tokens)
    def generate(self, tokens, **kwargs):
        self.sampling = kwargs
        try:
            for token in self.output:
                self.generated += 1
                yield token
        finally:
            self.closed = True
    def script(self, *parts):
        for part in parts:
            if isinstance(part, tuple):
                self.output.append(self.ids[self.markers[part[0]]])
            else:
                # Every UTF-8 byte is a separate token, including multibyte emoji.
                for value in part.encode():
                    token = len(self.pieces) + 10000
                    self.pieces[token] = bytes([value])
                    self.output.append(token)
        return self


def final_script(model):
    return model.script(('channel',), 'analysis', ('message',), 'PRIVATE DRAFT', ('end',),
                        ('start',), 'assistant', ('channel',), 'final', ('message',),
                        'Grüße, Maatis! 🜂 5 < 10. Ha ha.', ('return',), 'DUPLICATE')


def configured(model, backend='llama'):
    state = configure_template(model)
    return dict(instance=model, backend=backend, chat_state=state, temperature=.6)


class GptOssTests(TestCase):
    def test_family_metadata_and_filenames_do_not_override_other_architectures(self):
        for architecture, name, expected in [('gpt-oss','renamed.gguf','gpt-oss'),
                ('','gpt-oss-20b-MXFP4.gguf','gpt-oss'), ('','GPT_OSS_20B.gguf','gpt-oss'),
                ('qwen3','gpt-oss-name.gguf','qwen3'), ('llama','Llama 8B','llama')]:
            self.assertEqual(identify_family(architecture=architecture, name=name), expected)

    def test_template_contract_preserves_maat_roles_language_and_memory_once(self):
        for legacy in (False, True):
            for language in ('de', 'en'):
                for thinking, effort in [(False,'low'), (True,'medium')]:
                    with self.subTest(legacy=legacy, language=language, thinking=thinking):
                        model = final_script(Model(legacy))
                        llm = configured(model)
                        memory = Mock()
                        memory.generation_context.return_value = '[MAAT-SUPER-MEMORY] OASIS_MEMORY'
                        original = [{'role':'system','content':'MAAT RPG on Terra. ROLE_IDENTITY'},
                                    {'role':'assistant','content':'PREVIOUS_REPLY', 'thinking':'OLD_PRIVATE'},
                                    {'role':'user','content':'Hello, reply in English' if language=='en' else 'Hallo, antworte auf Deutsch'}]
                        before = deepcopy(original)
                        with patch('shared.core.gpt_oss.thinking_enabled',return_value=thinking), \
                             patch('shared.core.thinking_mode.thinking_enabled',return_value=thinking), \
                             patch('shared.core.thinking_mode.build_rpg_context_message',return_value=None):
                            messages = prepare_generation_messages(original,language=language,llm=llm,
                                runtime_context={'super_memory':memory})
                            out = ''.join(stream_chat(llm, messages))
                        self.assertEqual(out,'Grüße, Maatis! 🜂 5 < 10. Ha ha.')
                        prompt = model.last_prompt
                        for text in ('ROLE_IDENTITY','PREVIOUS_REPLY','OASIS_MEMORY'):
                            self.assertEqual(prompt.count(text),1)
                        self.assertIn('Reasoning: '+effort,prompt)
                        self.assertIn('developer'+model.markers['message'],prompt)
                        self.assertNotIn('OLD_PRIVATE',prompt)
                        self.assertNotIn('THINKING MODE OFF',prompt)
                        self.assertNotIn('THINKING-MODUS AUS',prompt)
                        self.assertNotIn(model.markers['return'],prompt)
                        self.assertIn('[MAAT-REPLY-LANGUAGE]',prompt)
                        self.assertEqual(original,before)
                        self.assertTrue(model.closed)

    def test_both_routes_stream_final_once_and_keep_sampling(self):
        for backend in ('llama','llama_intel'):
            model=final_script(Model())
            out=''.join(stream_chat(configured(model,backend),[{'role':'user','content':'Hi'}],
                                   {'temperature':.3,'top_p':.88,'max_tokens':1000}))
            self.assertEqual(out,'Grüße, Maatis! 🜂 5 < 10. Ha ha.')
            self.assertEqual(model.sampling['temp'],.3)
            self.assertEqual(model.sampling['top_p'],.88)
            self.assertTrue(model.last_special)
            self.assertLess(model.generated,len(model.output))

    def test_prefilled_analysis_and_final_and_open_assistant(self):
        for prefix in ('analysis','final',None):
            model=Model(prefix=prefix)
            if prefix=='analysis':
                model.script('DRAFT',('end',),('start',),'assistant',('channel',),'final',('message',))
            elif prefix is None:
                model.script(('channel',),'final',('message',))
            model.script('Answer',('return',))
            self.assertEqual(''.join(stream_chat(configured(model),[{'role':'user','content':'Hi'}])), 'Answer')

    def test_handoff_commentary_and_unknown_channel_are_never_public(self):
        for header in ('assistant to=browser'+Model().markers['channel']+'commentary',
                       'assistant'+Model().markers['channel']+'analysis',
                       'assistant'+Model().markers['channel']+'unknown'):
            model=Model()
            # Tokens are structural; ordinary words like "analysis" inside final remain intact.
            model.script(('start',))
            parts=header.split(model.markers['channel'])
            model.script(parts[0],('channel',),parts[1],('message',),'SECRET',('call',))
            with self.assertRaises(ValueError):
                list(stream_chat(configured(model),[{'role':'user','content':'Hi'}]))
            self.assertTrue(model.closed)

    def test_limits_do_not_overflow_context_or_disclose_truncated_analysis(self):
        for language, expected in [('de','Keine fertige Antwort'),('en','No final answer')]:
            model=final_script(Model())
            with patch('shared.core.gpt_oss.get_language',return_value=language):
                with self.assertRaisesRegex(ValueError,expected):
                    list(stream_chat(configured(model),[{'role':'user','content':'Hi'}],{'max_tokens':8}))
            self.assertEqual(model.generated,8)
            self.assertTrue(model.closed)
        model=Model(prefix='final').script('0123456789',('return',))
        model.capacity=8  # three prompt tokens plus five generated tokens
        self.assertEqual(''.join(stream_chat(configured(model),[{'role':'user','content':'Hi'}])), '01234')
        self.assertEqual(model.generated,5)
        model=Model(); model.capacity=3
        with self.assertRaises(ValueError):list(stream_chat(configured(model),[{'role':'user','content':'Hi'}]))
        self.assertEqual(model.generated,0)

    def test_nonstream_has_same_answer_and_accurate_usage_no_analysis(self):
        model=final_script(Model()); configured(model)
        result=model.chat_handler(llama=model,messages=[{'role':'user','content':'Hi'}])
        self.assertEqual(result['choices'][0]['message']['content'],'Grüße, Maatis! 🜂 5 < 10. Ha ha.')
        self.assertEqual(result['choices'][0]['finish_reason'],'stop')
        self.assertEqual(result['usage']['completion_tokens'],model.generated)

    def test_only_public_reply_reaches_tts_and_plugin_history(self):
        import contextlib
        import io
        from shared.core import streaming
        for backend in ('llama','llama_intel'):
            model=final_script(Model())
            llm=configured(model,backend)
            plugin=Mock()
            first=Mock()
            api=streaming.StreamingPluginInterface([plugin],on_first_token=first)
            with patch.object(streaming,'key_pressed',return_value=False), contextlib.redirect_stdout(io.StringIO()):
                result=''.join(streaming._router_stream(llm,[{'role':'user','content':'Hi'}],
                              {'gui_mode':True,'raise_errors':True},api))
            self.assertEqual(result,'Grüße, Maatis! 🜂 5 < 10. Ha ha.')
            self.assertEqual(''.join(call.args[0] for call in plugin.on_token.call_args_list),result)
            plugin.after_stream.assert_called_once_with(result)
            first.assert_called_once()

    def test_early_consumer_close_stops_native_iterator(self):
        model=final_script(Model())
        stream=stream_chat(configured(model),[{'role':'user','content':'Hi'}])
        self.assertEqual(next(stream),'G')
        stream.close()
        self.assertTrue(model.closed)
        self.assertLess(model.generated,len(model.output))

    def test_unlabelled_or_empty_or_unfinished_reply_cannot_leak_analysis(self):
        for parts in [(('message',),'PRIVATE',('return',)),
                      (('channel',),'anal'),
                      (('channel',),'final',('message',),('return',))]:
            model=Model().script(*parts)
            with self.assertRaises(ValueError):
                list(stream_chat(configured(model),[{'role':'user','content':'Hi'}]))

    def test_gpt_oss_settings_caption_roundtrips_both_languages(self):
        from gui.ui_i18n import tr
        caption='GPT-OSS: aus = niedrige Denkstufe, an = mittlere Denkstufe. Der Chat zeigt nur die fertige Antwort.'
        translated=tr(caption,'en')
        self.assertIn('low reasoning effort',translated)
        self.assertEqual(tr(translated,'de'),caption)

    def test_cancel_during_analysis_closes_generator_without_emitting_draft(self):
        from shared.core.chat_turn import ChatTurn, ChatCancelled
        model=final_script(Model()); llm=configured(model)
        turn=ChatTurn('gpt-oss-cancel')
        original=model.generate
        def generate(*args,**kwargs):
            for token in original(*args,**kwargs):
                if model.generated==12:turn.cancel()
                yield token
        model.generate=generate
        model.reset=Mock()
        with self.assertRaises(ChatCancelled):
            list(stream_chat(llm,[{'role':'user','content':'Hi'}],{'_chat_turn':turn}))
        self.assertTrue(model.closed)
        model.reset.assert_called_once()

    def test_both_loaders_reject_invalid_templates_and_close_model(self):
        from shared.core import llama_backend,intel_gguf_backend
        for loader,target in [(llama_backend.load,'shared.core.llama_backend.Llama'),
                              (intel_gguf_backend.load,'shared.core.intel_binding.IntelLlama')]:
            model=Model()
            with patch(target,return_value=model),patch('shared.core.intel_gguf_backend.intel_architecture',return_value=True):
                loaded=loader('gpt-oss-20b.gguf',n_ctx=20000)
                self.assertEqual(loaded['chat_state']['family'],'gpt-oss')
                model.close.assert_not_called()
                model.metadata['tokenizer.chat_template']='{{messages[0].content}}'
                with self.assertRaises(ValueError):loader('gpt-oss-20b.gguf')
                model.close.assert_called_once()


if __name__ == '__main__': main()
