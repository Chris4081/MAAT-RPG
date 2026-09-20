"""Mistral adapter contracts using project-written synthetic templates.

These small serializers cover the RPG's role handling and generation boundaries;
they are not copies of upstream templates or tests of a particular model release.
"""
from copy import deepcopy
import io
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
from shared.core.gguf_chat import configure_template, normalize_channels
from shared.core.rpg_generation_context import is_llama_model
from shared.core.model_family import identify_family
from shared.core.thinking_mode import prepare_generation_messages

NATIVE_TEST_TEMPLATE = (
    "{{ bos_token }}{% for turn in messages %}"
    "{% if turn.role == 'system' %}[SYSTEM_PROMPT]{{ turn.content }}[/SYSTEM_PROMPT]"
    "{% elif turn.role == 'user' %}[INST]{{ turn.content }}[/INST]"
    "{% elif turn.role == 'assistant' %}{{ turn.content }}{{ eos_token }}"
    "{% else %}{{ raise_exception('Unsupported test role') }}{% endif %}{% endfor %}"
)
LEGACY_TEST_TEMPLATE = (
    "{{ bos_token }}{% for turn in messages %}"
    "{% if turn.role == 'user' %}[INST]{{ turn.content }}[/INST]"
    "{% elif turn.role == 'assistant' %}{{ turn.content }}{{ eos_token }}"
    "{% else %}{{ raise_exception('Unsupported test role') }}{% endif %}{% endfor %}"
)


class Model:
    def __init__(self, template, architecture='mistral3', name='Ministral-3-3B-Instruct-2512'):
        self.metadata={'general.architecture':architecture,'general.name':name,'tokenizer.chat_template':template}
    def token_eos(self):return 2
    def token_bos(self):return 1
    def detokenize(self, tokens, special=False):return b'<s>' if tokens==[1] else b'</s>'


def configured(template, **kwargs):
    model=Model(template,**kwargs)
    with patch('llama_cpp.llama_chat_format.chat_formatter_to_chat_completion_handler',side_effect=lambda f:f):
        state=configure_template(model)
    return model,state


class MistralCompatibilityTests(unittest.TestCase):
    def test_family_separates_shared_llama_architecture_and_renamed_gguf(self):
        for name,arch,family in [('Ministral-3-3B-Q4_K_M','mistral3','mistral'),
                ('Mistral-7B-Instruct-v0.1','llama','mistral'),('Ministral-8B-2410','llama','mistral'),
                ('Mixtral-8x7B-Instruct','llama','mistral'),('Meta-Llama-3.1-8B','llama','llama'),
                ('llama-filename-but-qwen','qwen3','qwen3')]:
            with self.subTest(name=name):
                model=SimpleNamespace(metadata={'general.architecture':arch,'general.name':name})
                self.assertEqual(identify_family(model.metadata),family)
                self.assertEqual(is_llama_model({'backend':'llama_intel','instance':model}),family=='llama')
        self.assertFalse(is_llama_model(architecture='llama',name='Ministral-8B.gguf'))
        self.assertFalse(is_llama_model(architecture='llama',name='renamed.gguf',family='mistral'))

    def test_template_contracts_keep_maat_system_memory_and_chat_roles(self):
        for name, template in (('native', NATIVE_TEST_TEMPLATE), ('legacy', LEGACY_TEST_TEMPLATE)):
            for language in ('de','en'):
                with self.subTest(template=name,language=language):
                    original=[{'role':'system','content':'You are MAAT-AI in the MAAT-RPG on Terra.'},
                        {'role':'system','content':'[MAAT-SUPER-MEMORY]\nA saved memory of the oasis.'},
                        {'role':'assistant','content':'Welcome, Maatis.'},
                        {'role':'user','content':'First fragment.'}, {'role':'user','content':'Second fragment.'},
                        {'role':'assistant','content':'Previous answer.'},
                        {'role':'user','content':'How do we continue?' if language=='en' else 'Wie geht es weiter?'}]
                    before=deepcopy(original)
                    # Real preparation keeps the existing profile and language instruction.
                    with patch('shared.core.thinking_mode.thinking_enabled',return_value=False):
                        messages=prepare_generation_messages(original,language=language)
                    # Memory is ephemeral; supplied by the memory provider in production.
                    messages.insert(1,original[1])
                    model,state=configured(template,architecture='llama',name='Ministral test')
                    prompt=model.chat_handler(messages=messages).prompt
                    for message in before:
                        self.assertEqual(prompt.count(message['content']),1)
                    self.assertNotIn('Le Chat',prompt)
                    self.assertTrue(prompt.startswith('<s>'))
                    self.assertTrue(prompt.endswith('[/INST]') or prompt.endswith('[/INST] '))
                    self.assertIn('THINKING MODE OFF' if language=='en' else 'THINKING-MODUS AUS',prompt)
                    self.assertEqual(state['family'],'mistral')
                    self.assertEqual(original,before)
                    self.assertFalse(state['thinking_prefix'])

    def test_legacy_system_rejection_or_silent_omission_keeps_identity(self):
        for strict in (True,False):
            template="{{bos_token}}{% for m in messages %}{% if m.role=='user' %}[INST]{{m.content}}[/INST]{% elif m.role=='assistant' %}{{m.content}}{{eos_token}}"
            if strict:template+="{% else %}{{raise_exception('Only user and assistant roles supported')}}"
            template+="{% endif %}{% endfor %}"
            model,state=configured(template,architecture='llama',name='Mistral-7B-Instruct')
            result=model.chat_handler(messages=[{'role':'system','content':'MAAT identity'},
                {'role':'user','content':'Hello'}])
            self.assertTrue(state['fold_system'])
            self.assertEqual(result.prompt,'<s>[INST]MAAT identity\n\nHello[/INST]')

    def test_ministral_3_preserves_native_system_delimiters(self):
        model,state=configured(NATIVE_TEST_TEMPLATE)
        prompt=model.chat_handler(messages=[{'role':'system','content':'MAAT'},
            {'role':'user','content':'Bonjour'}]).prompt
        self.assertEqual(prompt,'<s>[SYSTEM_PROMPT]MAAT[/SYSTEM_PROMPT][INST]Bonjour[/INST]')
        self.assertFalse(state['fold_system'])

    def test_missing_template_does_not_silently_fall_back_to_llama_2(self):
        for architecture,name in [('mistral3','renamed'),('llama','Mistral-7B'),('llama','Ministral-8B')]:
            with self.subTest(architecture=architecture,name=name), patch('shared.core.gguf_chat.get_language', return_value='de'):
                with self.assertRaisesRegex(ValueError,'Chatvorlage'):
                    configure_template(Model('',architecture,name))
        with patch('shared.core.gguf_chat.get_language',return_value='en'):
            with self.assertRaisesRegex(ValueError,'no chat template'):
                configure_template(Model(''))

    def test_prefilled_mistral_reasoning_prefix_is_recognized(self):
        model,state=configured('{{bos_token}}{% for m in messages %}{{m.content}}{% endfor %}[THINK]')
        model.chat_handler(messages=[{'role':'user','content':'Hello'}])
        self.assertTrue(state['thinking_prefix'])

    def test_normalized_mistral_reasoning_stays_out_of_visible_reply(self):
        from shared.core import streaming
        from contextlib import redirect_stdout
        raw='[THINK]Private draft[/THINK]Hello, Maatis!'
        with patch.object(streaming,'_show_thinking_enabled',return_value=False), \
             patch.object(streaming,'key_pressed',return_value=False), redirect_stdout(io.StringIO()):
            result=streaming.stream_to_console(normalize_channels(iter(raw),mistral=True),echo=False,raise_errors=True)
        self.assertEqual(result,'Hello, Maatis!')

    def test_mistral_thinking_markers_at_every_stream_boundary(self):
        raw='[THINK]Draft[/THINK]Hello, Maatis!'
        for index in range(len(raw)+1):
            self.assertEqual(''.join(normalize_channels([raw[:index],raw[index:]],mistral=True)),
                             '<think>Draft</think>Hello, Maatis!')
        self.assertEqual(''.join(normalize_channels(['A [T','est]'],mistral=True)),'A [Test]')

    def test_both_adapters_stream_once_and_keep_stops_and_sampling(self):
        from shared.core.backend_router import stream_chat
        for backend in ('llama','llama_intel'):
            for thinking_prefix in (False,True):
                with self.subTest(backend=backend,thinking_prefix=thinking_prefix):
                    inst=Mock()
                    inst.metadata={'general.architecture':'mistral3'}
                    native=iter([{'choices':[{'delta':{'role':'assistant'}}]}]+[
                        {'choices':[{'delta':{'content':part}}]} for part in
                        (['draft','[/TH','INK]','Hello','!'] if thinking_prefix else ['Hello','!'])])
                    inst.create_chat_completion.return_value=native
                    llm=dict(backend=backend,instance=inst,temperature=.2,
                             chat_state=dict(architecture='mistral3',family='mistral',thinking_prefix=thinking_prefix))
                    messages=[{'role':'system','content':'MAAT'},{'role':'user','content':'Hello'}]
                    out=''.join(stream_chat(llm,messages,{'max_tokens':20,'top_p':.9}))
                    self.assertEqual(out,'<think>draft</think>Hello!' if thinking_prefix else 'Hello!')
                    inst.create_chat_completion.assert_called_once()
                    args=inst.create_chat_completion.call_args.kwargs
                    self.assertEqual((args['max_tokens'],args['temperature'],args['top_p']),(20,.2,.9))
                    self.assertTrue(args['stream'])
                    self.assertEqual(args['messages'],messages)

    def test_both_adapter_loaders_configure_ministral_and_close_invalid_models(self):
        from shared.core import llama_backend,intel_gguf_backend
        template=NATIVE_TEST_TEMPLATE
        for loader,target in [(llama_backend.load,'shared.core.llama_backend.Llama'),
                              (intel_gguf_backend.load,'shared.core.intel_binding.IntelLlama')]:
            model=Model(template);model.intel_repacking=False;model.close=Mock()
            with patch(target,return_value=model),patch('shared.core.intel_gguf_backend.intel_architecture',return_value=True):
                loaded=loader('Ministral-3-3B-Q4_K_M.gguf',n_ctx=20000)
                self.assertEqual(loaded['chat_state']['family'],'mistral')
                self.assertEqual(loaded['n_ctx'],20000)
                model.close.assert_not_called()
                model.metadata.pop('tokenizer.chat_template')
                with self.assertRaises(ValueError):loader('Ministral-3-3B-Q4_K_M.gguf')
                model.close.assert_called_once()


if __name__=='__main__':unittest.main()
