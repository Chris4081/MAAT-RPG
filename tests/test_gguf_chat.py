import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_desktop import APP
from shared.core.gguf_chat import prepare_messages, normalize_channels, configure_template
from shared.core.thinking_mode import thinking_enabled, show_thinking_enabled, prepare_generation_messages, chat_completion_thinking_kwargs
from apps.maat_rpg import session_shared

class ChatCompatibilityTest(unittest.TestCase):
    def test_default_off_profile_switch_and_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = {slot: Path(folder) / f'profile{slot}.json' for slot in range(1, 5)}
            with patch.object(session_shared, 'profile_settings_path', side_effect=paths.get):
                for slot, path in paths.items():
                    with patch('shared.core.thinking_mode._settings_path', return_value=path):
                        self.assertFalse(session_shared.load_profile_settings(slot)['thinking_enabled'])
                        self.assertFalse(thinking_enabled())
                        self.assertFalse(show_thinking_enabled())
                        session_shared.write_profile_settings(slot, {'gui_volume': 35})
                        self.assertFalse(thinking_enabled())
                        session_shared.write_profile_settings(slot, {'thinking_enabled': True})
                        self.assertTrue(thinking_enabled())
                        self.assertTrue(session_shared.load_profile_settings(slot)['thinking_enabled'])
                        session_shared.write_profile_settings(slot, {'thinking_enabled': False})
                        self.assertFalse(thinking_enabled())
                        self.assertEqual(json.loads(path.read_text())['gui_volume'], 35)

    def test_default_off_reaches_all_embedded_model_templates(self):
        class Model:
            def token_eos(self): return 2
            def token_bos(self): return 1
            def detokenize(self, ids, special=False): return b'<s>'
        with patch('shared.core.thinking_mode._load_settings', return_value={}):
            for architecture in ('llama', 'qwen3', 'gemma3', 'gemma4'):
                model = Model()
                model.metadata = {'general.architecture': architecture, 'tokenizer.chat_template': '{% if enable_thinking %}<think>{% else %}DIRECT{% endif %}'}
                with patch('llama_cpp.llama_chat_format.chat_formatter_to_chat_completion_handler', side_effect=lambda f: f):
                    state = configure_template(model)
                self.assertEqual(model.chat_handler(messages=[{'role': 'user', 'content': 'Hallo'}]).prompt, 'DIRECT')
                self.assertFalse(state['thinking_prefix'])

    def test_default_off_generation_keeps_identity_and_maat_reflection(self):
        def backend(messages, chat_template_kwargs=None, reasoning_budget=None): pass
        original = [{'role': 'system', 'content': 'Du bist MAAT-KI. Zeige eine MAAT-Reflexion.'}, {'role': 'user', 'content': 'Hallo'}]
        with patch('shared.core.thinking_mode._load_settings', return_value={}), patch('shared.core.thinking_mode.build_rpg_context_message', return_value=None):
            for language in ('de', 'en'):
                prepared = prepare_generation_messages(original, language=language)
                self.assertEqual(prepared[0], original[0])
                self.assertEqual(prepared[-1], original[-1])
                self.assertIn('MAAT-Reflexion', prepared[0]['content'])
                self.assertIn('<think>', prepared[1]['content'])
                self.assertNotIn('MAAT', prepared[1]['content'])
                self.assertEqual(len(prepared), 3)
            self.assertEqual(chat_completion_thinking_kwargs(backend), {'chat_template_kwargs': {'enable_thinking': False}, 'reasoning_budget': 0})
        self.assertEqual(len(original), 2)

    def test_system_context_preserved_without_mutation(self):
        original = [{'role':'system','content':'MAAT'}, {'role':'system','content':'RPG'}, {'role':'user','content':'Hallo'}]
        self.assertEqual(prepare_messages(original, 'gemma3'), [{'role':'user','content':'MAAT\n\nRPG\n\nHallo'}])
        self.assertEqual(prepare_messages(original, 'gemma4')[0]['content'], 'MAAT\n\nRPG')
        self.assertEqual(prepare_messages(original, 'qwen3')[1], original[2])
        self.assertEqual(original[2]['content'], 'Hallo')

    def test_channel_markers_at_every_boundary(self):
        text = '<|channel>thought\nGedanken<channel|>Antwort!'
        for i in range(len(text)+1):
            self.assertEqual(''.join(normalize_channels([text[:i],text[i:]])), '<think>\nGedanken</think>Antwort!')
        self.assertEqual(''.join(normalize_channels(['Hallo < Welt'])), 'Hallo < Welt')

    def test_thinking_switch_reaches_embedded_template(self):
        class Model:
            metadata = {'general.architecture':'qwen3', 'tokenizer.chat_template': '{% for m in messages %}{{m.content}}{% endfor %}{% if enable_thinking %}<think>\n{% else %}<think>\n</think>\n{% endif %}'}
            def token_eos(self): return 2
            def token_bos(self): return 1
            def detokenize(self, ids, special=False): return b'<s>'
        model = Model()
        with patch('llama_cpp.llama_chat_format.chat_formatter_to_chat_completion_handler', side_effect=lambda f:f):
            state = configure_template(model)
        with patch('shared.core.gguf_chat.thinking_enabled', return_value=True):
            result = model.chat_handler(messages=[{'role':'user','content':'Hallo'}])
            self.assertTrue(result.prompt.endswith('<think>\n'))
            self.assertTrue(state['thinking_prefix'])
        with patch('shared.core.gguf_chat.thinking_enabled', return_value=False):
            self.assertTrue(model.chat_handler(messages=[]).prompt.endswith('</think>\n'))
            self.assertFalse(state['thinking_prefix'])

    def test_missing_qwen_template_fails_clearly(self):
        class Model: metadata = {'general.architecture':'qwen3'}
        for language, message in [('de', 'Chatvorlage'), ('en', 'no chat template')]:
            with self.subTest(language=language), patch('shared.core.gguf_chat.get_language', return_value=language):
                with self.assertRaisesRegex(ValueError, message):
                    configure_template(Model())
