"""Prompt reuse across live clock/recall updates, without caching stale facts."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import os
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
from test_ai_plugins import manager
from shared.core.ai_plugin_settings import DEFAULTS, SNAPSHOT
from shared.core.thinking_mode import prepare_generation_messages
from shared.core.gguf_chat import prepare_messages, configure_template
from shared.plugins.maat_thinking.plugin_main import Plugin as Quality


def common_prefix(first, second):
    return os.path.commonprefix([first, second])


class PromptPrefixTests(unittest.TestCase):
    def test_clock_changes_leave_complete_static_instructions_reusable(self):
        now = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
        for language in ('de', 'en'):
            with self.subTest(language=language):
                pm = manager()
                pm.plugins_chat.append(Quality())
                memory = Mock(last_recall=[])
                memory.generation_context.side_effect = [
                    '[MAAT-SUPER-MEMORY]\nEarlier retained fact.',
                    '[MAAT-SUPER-MEMORY]\nUpdated retained fact.']
                context = {'pm': pm, SNAPSHOT: dict(DEFAULTS), 'super_memory': memory}
                original = [{'role': 'system', 'content': 'You are Maatis in Terra.'},
                            {'role': 'user', 'content': 'Hello!'}]
                before = deepcopy(original)
                results = []
                for minute in (0, 3):
                    with patch('shared.core.maat_reality_layer.now_local', return_value=now + timedelta(minutes=minute)), \
                         patch('shared.core.thinking_mode._load_settings', return_value={}), \
                         patch('shared.plugins.maat_thinking.plugin_main.load_settings', return_value={}), \
                         patch('shared.core.thinking_mode.build_rpg_context_message', return_value=None):
                        results.append(prepare_generation_messages(original, language, context))
                systems = [prepare_messages(result, 'llama')[0]['content'] for result in results]
                prefix = common_prefix(*systems)
                for marker in ('[MAAT_INTERNAL_QUALITY]', '[MAAT_REPLY_STYLE]', '[MAAT_FORMATTING]'):
                    block = next(m['content'] for m in results[0] if m['content'].startswith(marker))
                    self.assertIn(block, prefix)
                    self.assertEqual(systems[1].count(marker), 1)
                self.assertIn('12:03', systems[1])
                self.assertNotIn('12:00', systems[1])
                self.assertIn('Updated retained fact.', systems[1])
                self.assertNotIn('Earlier retained fact.', systems[1])
                self.assertEqual(original, before)
                self.assertEqual(results[1][-1], original[-1])
                # Compare the same instructions in the previous (clock-first)
                # order: this is prefix coverage, not a hardware speed claim.
                previous = []
                for result in results:
                    blocks = [m['content'] for m in result if m['role'] == 'system']
                    clock = next(b for b in blocks if b.startswith('[MAAT_REALITY]'))
                    previous.append('\n\n'.join([blocks[0], clock, *[b for b in blocks[1:] if b != clock]]))
                self.assertGreater(len(prefix), len(common_prefix(*previous)) + 1000)

    def test_switches_apply_immediately_and_old_blocks_are_not_retained(self):
        pm = manager()
        context = {'pm': pm, SNAPSHOT: dict(DEFAULTS)}
        original = [{'role': 'system', 'content': 'MAAT identity'}, {'role': 'user', 'content': 'Hallo'}]
        with patch('shared.core.thinking_mode._load_settings', return_value={}), \
             patch('shared.core.thinking_mode.build_rpg_context_message', return_value=None):
            first = prepare_generation_messages(original, 'de', context)
            context[SNAPSHOT].update(reality_enabled=False, reply_style_enabled=False, response_formatting_enabled=False)
            second = prepare_generation_messages(first, 'de', context)
        for marker in ('[MAAT_REALITY]', '[MAAT_REPLY_STYLE]', '[MAAT_FORMATTING]'):
            self.assertIn(marker, str(first))
            self.assertNotIn(marker, str(second))
        self.assertEqual(second[0], original[0])
        self.assertEqual(second[-1], original[-1])

    def test_smollm3_thinking_flag_reaches_embedded_template(self):
        # Minimal reproduction of the official SmolLM3 mode selection:
        # https://huggingface.co/HuggingFaceTB/SmolLM3-3B/blob/main/chat_template.jinja
        class Model:
            metadata = {'general.architecture': 'llama', 'general.name': 'SmolLM3-3B',
                        'tokenizer.chat_template':
                            "{% if enable_thinking is not defined %}{% set enable_thinking = true %}{% endif %}"
                            "Reasoning Mode: {{ '/think' if enable_thinking else '/no_think' }}\n"
                            "{% for m in messages %}{{ m.content }}\n{% endfor %}"
                            "{% if add_generation_prompt %}<|im_start|>assistant\n"
                            "{% if not enable_thinking %}<think>\n\n</think>\n{% endif %}{% endif %}"}
            def token_eos(self): return 2
            def token_bos(self): return 1
            def detokenize(self, ids, special=False): return b'<|im_end|>'
        model = Model()
        with patch('llama_cpp.llama_chat_format.chat_formatter_to_chat_completion_handler', side_effect=lambda formatter: formatter):
            state = configure_template(model)
        messages = [{'role': 'system', 'content': 'MAAT identity'}, {'role': 'user', 'content': 'Hallo'}]
        with patch('shared.core.thinking_mode._load_settings', return_value={}):
            prompt = model.chat_handler(messages=messages).prompt
        self.assertIn('Reasoning Mode: /no_think', prompt)
        self.assertTrue(prompt.rstrip().endswith('</think>'))
        self.assertFalse(state['thinking_prefix'])
        self.assertIn('MAAT identity', prompt)
        with patch('shared.core.thinking_mode._load_settings', return_value={'thinking_enabled': True}):
            prompt = model.chat_handler(messages=messages).prompt
        self.assertIn('Reasoning Mode: /think\n', prompt)
        self.assertNotIn('</think>', prompt)
