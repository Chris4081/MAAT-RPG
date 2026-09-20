"""TinyLlama roles and real llama.cpp format/stream conversion, without weights."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP, ROOT
from shared.core.gguf_chat import configure_template
from shared.core.model_family import identify_family
from shared.core.rpg_generation_context import is_llama_model, build_rpg_context_message
from shared.core.tinyllama import CHAT_V1_TEMPLATE, ROLE_STOPS, chat_v1_fallback
from shared.core.backend_router import stream_chat
from shared.core.offline_wiki import generation_context as wiki_context
from shared.core.thinking_mode import prepare_generation_messages
from shared.core.ai_plugin_settings import DEFAULTS, begin_turn
import test_ai_plugins as helpers


class Model:
    def __init__(self, name='TinyLlama-1.1B-Chat-v1.0', template=None):
        self.metadata = {'general.architecture': 'llama', 'general.name': name}
        if template is not None: self.metadata['tokenizer.chat_template'] = template
        self.model_path = 'renamed.gguf'
        self.intel_repacking = False
        self.close = Mock()
        self.completions = []

    def token_eos(self): return 2
    def token_bos(self): return 1
    def detokenize(self, ids, special=False): return b'<s>' if ids == [1] else b'</s>'
    def tokenize(self, prompt, **options):
        self.prompt = prompt.decode()
        self.token_options = options
        return [7, 8, 9]
    def create_chat_completion(self, **kwargs): return self.chat_handler(llama=self, **kwargs)
    def create_completion(self, **kwargs):
        self.completions.append(kwargs)
        for part in ('Hello', ', Maatis', '!'):
            yield {'id': 'cmpl-test', 'object': 'text_completion', 'created': 1, 'model': self.model_path,
                   'choices': [{'text': part, 'index': 0, 'logprobs': None, 'finish_reason': None}]}


class TinyLlamaTests(unittest.TestCase):
    def test_metadata_and_filename_recognition_preserves_other_families(self):
        for name in ('TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf', 'tiny-llama-chat', 'tiny_llama'):
            self.assertEqual(identify_family(name=name), 'tinyllama')
            self.assertEqual(identify_family({'general.architecture': 'llama', 'general.name': name}, name='renamed.gguf'), 'tinyllama')
            self.assertTrue(is_llama_model(architecture='llama', name=name))
        self.assertEqual(identify_family({'general.architecture': 'qwen3'}, name='TinyLlama.gguf'), 'qwen3')
        self.assertEqual(identify_family({'general.architecture': 'llama'}, name='Ministral-3B.gguf'), 'mistral')
        self.assertEqual(identify_family({'general.architecture': 'llama'}, name='Llama-3.1.gguf'), 'llama')

    def test_official_v1_prompt_bytes_roles_and_fallback_stop_markers(self):
        messages = [{'role': 'system', 'content': 'MAAT RPG'},
                    {'role': 'system', 'content': 'A saved memory.'},
                    {'role': 'user', 'content': 'Hello'},
                    {'role': 'assistant', 'content': 'Welcome'},
                    {'role': 'user', 'content': 'Continue'}]
        original = deepcopy(messages)
        # Explicit expected wire format from the upstream tokenizer config.
        expected = ('<|system|>\nMAAT RPG\n\nA saved memory.</s>\n'
                    '<|user|>\nHello</s>\n<|assistant|>\nWelcome</s>\n'
                    '<|user|>\nContinue</s>\n<|assistant|>\n')
        for template in (None, CHAT_V1_TEMPLATE):
            model = Model(template=template)
            with patch('llama_cpp.llama_chat_format.chat_formatter_to_chat_completion_handler', side_effect=lambda f: f):
                state = configure_template(model)
            response = model.chat_handler(messages=messages)
            self.assertEqual(response.prompt, expected)
            self.assertEqual(state['family'], 'tinyllama')
            self.assertEqual(response.stop, ['</s>', *ROLE_STOPS])
            self.assertTrue(response.stopping_criteria([1, 2], None))
            self.assertFalse(response.stopping_criteria([1, 3], None))
            self.assertEqual(messages, original)

    def test_embedded_custom_templates_win_and_unknown_checkpoints_fail_clearly(self):
        model = Model('TinyLlama-custom-finetune', '{{bos_token}}CUSTOM{% for m in messages %}{{m.content}}{{eos_token}}{% endfor %}')
        with patch('llama_cpp.llama_chat_format.chat_formatter_to_chat_completion_handler', side_effect=lambda f: f):
            state = configure_template(model)
        response = model.chat_handler(messages=[{'role': 'user', 'content': 'Hi'}])
        self.assertEqual(response.prompt, '<s>CUSTOMHi</s>')
        self.assertEqual(response.stop, ['</s>'])
        self.assertNotIn('template_source', state)
        for name in ('TinyLlama-1.1B', 'TinyLlama-Chat-v0.1', 'TinyLlama-Chat-v1.01', 'TinyLlama-Chat-v1.0.1'):
            for language in ('de', 'en'):
                with patch('shared.core.gguf_chat.get_language', return_value=language):
                    with self.assertRaisesRegex(ValueError, 'Chatvorlage' if language == 'de' else 'chat template'):
                        configure_template(Model(name))
        self.assertTrue(chat_v1_fallback({'general.finetune': 'Chat-v1.0'}))

    def test_both_loaders_and_real_chat_formatter_stream_once_with_native_stops(self):
        from shared.core import llama_backend, intel_gguf_backend
        for loader, target, backend in ((llama_backend.load, 'shared.core.llama_backend.Llama', 'llama'),
                (intel_gguf_backend.load, 'shared.core.intel_binding.IntelLlama', 'llama_intel')):
            model = Model()
            with patch(target, return_value=model), patch('shared.core.intel_gguf_backend.intel_architecture', return_value=True):
                loaded = loader('tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf', n_ctx=2048)
                self.assertEqual((loaded['backend'], loaded['n_ctx']), (backend, 2048))
                self.assertEqual(loaded['chat_state']['template_source'], 'tinyllama-chat-v1.0-fallback')
                context = {'pm': helpers.manager(), 'llm': loaded}
                with patch('shared.core.ai_plugin_settings.load_settings', return_value=dict(DEFAULTS)):
                    begin_turn(context, 'Hello')
                    messages = prepare_generation_messages([{'role': 'system', 'content': 'MAAT RPG on Terra.'},
                                {'role': 'user', 'content': 'Hello'}], language='en', runtime_context=context, llm=loaded)
                before = deepcopy(messages)
                self.assertEqual(list(stream_chat(loaded, messages, {'max_tokens': 128, 'temperature': .4})), ['Hello', ', Maatis', '!'])
                self.assertEqual(len(model.completions), 1)
                call = model.completions[0]
                self.assertEqual(call['max_tokens'], 128); self.assertEqual(call['temperature'], .4)
                self.assertTrue(call['stream'])
                self.assertEqual(call['stop'], ['</s>', *ROLE_STOPS])
                self.assertEqual(model.token_options, {'add_bos': False, 'special': True})
                self.assertIn('MAAT RPG on Terra.', model.prompt)
                self.assertIn('[MAAT_REPLY_STYLE]', model.prompt)
                self.assertEqual(messages, before)
                model.close.assert_not_called()
                model.metadata['general.name'] = 'TinyLlama-Base'
                with self.assertRaises(ValueError): loader('tinyllama-base.gguf', n_ctx=2048)
                model.close.assert_called_once()

    def test_tinyllama_keeps_sparse_wiki_and_no_battle_context(self):
        model = {'chat_state': {'family': 'tinyllama', 'architecture': 'llama'}}
        self.assertTrue(is_llama_model(model))
        with patch('shared.core.rpg_generation_context.rpg_context_enabled', return_value=True):
            self.assertIsNone(build_rpg_context_message({'battle_log': 'PRIVATE'}, llm=model))
        block = '[MAAT-OFFLINE-WIKI]\n' + json.dumps({'title': 'Oasis', 'text': 'Water and sand. ' * 300})
        data = json.loads(wiki_context(block, model, 'en').splitlines()[-1])
        self.assertLessEqual(len(data['text']), 400)
        self.assertEqual(data['title'], 'Oasis')

    def test_model_menu_mentions_tinyllama_in_both_languages(self):
        from gui.ui_i18n import EN
        self.assertTrue(any('TinyLlama' in key and 'TinyLlama' in value for key, value in EN.items()))


if __name__ == '__main__': unittest.main()
