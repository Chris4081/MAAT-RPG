import unittest
from types import SimpleNamespace
from unittest.mock import patch
from test_desktop import APP
from PySide6.QtWidgets import QCheckBox
from shared.core.rpg_generation_context import is_llama_model
from shared.core.thinking_mode import prepare_generation_messages
from gui.live_window import LiveWindow


class LlamaContextTest(unittest.TestCase):
    def test_architecture_not_backend(self):
        for arch, expected in [('llama', True), ('gemma4', False), ('qwen3', False)]:
            self.assertEqual(is_llama_model({'backend':'llama', 'chat_state':{'architecture':arch}}), expected)
        self.assertTrue(is_llama_model(SimpleNamespace(metadata={'general.architecture':'llama'})))
        self.assertFalse(is_llama_model(architecture='gemma4', name='llama-misleading.gguf'))

    def test_memory_and_history_preserved_with_context_setting_on(self):
        original = [{'role':'system','content':'Erinnerung: Christof liebt Musik.'},
                    {'role':'user','content':'Was weißt du noch?'},
                    {'role':'assistant','content':'Du liebst Musik.'}]
        with patch('shared.core.thinking_mode.thinking_enabled', return_value=True), patch('shared.core.rpg_generation_context.rpg_context_enabled', return_value=True), patch('shared.core.rpg_generation_context._load_json', return_value={}):
            result = prepare_generation_messages(original, language='de', llm={'chat_state':{'architecture':'llama'}})
            self.assertEqual(result, original)
            self.assertIsNot(result[0], original[0])
            result = prepare_generation_messages(original, language='de', llm={'backend':'llama','chat_state':{'architecture':'gemma4'}})
            self.assertTrue(any('[MAAT-RPG-WELTZUSTAND]' in m['content'] for m in result))
            self.assertIn(original[0], result)

    def test_checkbox_switch_restores_other_model_preference(self):
        box = QCheckBox()
        window = SimpleNamespace(loaded_model_architecture='llama', saved_model='renamed.gguf', dialog_settings={'rpg_context_enabled':box}, game=SimpleNamespace(_profile_slot=lambda:1))
        with patch('gui.live_window.session_shared.load_profile_settings', return_value={'rpg_context_enabled':True}), patch('gui.live_window.session_shared.write_profile_settings') as save:
            LiveWindow.update_rpg_context_option(window)
            self.assertTrue(box.isChecked())
            self.assertFalse(box.isEnabled())
            self.assertIn('Erinnerungen', box.toolTip())
            window.loaded_model_architecture='gemma4'
            LiveWindow.update_rpg_context_option(window)
            self.assertFalse(box.isChecked())
            self.assertTrue(box.isEnabled())
            window.loaded_model_architecture='llama'
            window.loaded_model_family='mistral'
            LiveWindow.update_rpg_context_option(window)
            self.assertFalse(box.isChecked())
            self.assertTrue(box.isEnabled())
            save.assert_not_called()
        box.deleteLater()

    def test_bounded_context_and_no_dungeon_logs(self):
        from shared.core.rpg_generation_context import build_rpg_context_message, compact_player_context
        state = {'player': {'level': 50, 'hp': 100, 'max_hp': 120, 'inventory': 'SECRET' * 10000},
                 'stats': {'boss_wins': 3}, 'dungeon_plus': {'last_room': 'SECRET'},
                 'journal': [{'title': 'SECRET'}] * 1000, 'played': ['SECRET'] * 1000}
        runtime = {'battle_log': ['SECRET' * 10000], 'story_journal': state['journal'],
                   'combat_source': 'dungeon', 'story_choices': {'reflection_path': 'SECRET'}}
        with patch('shared.core.rpg_generation_context.rpg_context_enabled', return_value=True), patch('shared.core.rpg_generation_context._load_json', return_value=state):
            for language in ('de', 'en'):
                message = build_rpg_context_message(runtime, language, {'chat_state': {'architecture': 'gemma4'}})
                self.assertLess(len(message), 400)
                self.assertNotIn('SECRET', message)
                self.assertIn('Level=50', message)
        self.assertEqual(set(compact_player_context(state['player'])), {'level', 'hp', 'max_hp'})

    def test_disabled_removes_old_snapshot_preserves_memories_and_user_text(self):
        original = [{'role': 'system', 'content': 'Erinnerung: Wir waren im Dungeon.'},
                    {'role': 'system', 'content': '[MAAT-RPG-WELTZUSTAND]\nAlter Kampf'},
                    {'role': 'user', 'content': 'Erzähl mir vom Dungeon.'}]
        with patch('shared.core.thinking_mode.thinking_enabled', return_value=True), patch('shared.core.rpg_generation_context.rpg_context_enabled', return_value=False), patch('shared.core.rpg_generation_context._load_json') as load:
            result = prepare_generation_messages(original, language='de')
            self.assertEqual(result, [original[0], original[2]])
            load.assert_not_called()
        self.assertEqual(len(original), 3)

    def test_companion_routes_memories_through_shared_bounded_provider(self):
        from gui.game_worker import Runtime
        from unittest.mock import Mock
        runtime = SimpleNamespace(companion=SimpleNamespace(state={
            'dialogue': [], 'memories': ['Gemeinsame Erinnerung'], 'trust': 9}),
            core=SimpleNamespace(state=SimpleNamespace(state={'player': {'hp': 999, 'dungeon': 'SECRET'}})),
            llm={'chat_state': {'architecture': 'gemma4'}}, perf={}, stop_previous_speech=Mock())
        with patch('gui.game_worker.emit'), patch('shared.core.streaming.stream_chat_completion', side_effect=RuntimeError('test stop')) as stream:
            with self.assertRaisesRegex(RuntimeError, 'test stop'):
                Runtime.maatis_dialogue(runtime, 'Hallo')
            messages = stream.call_args.args[1]
            # Old campaign arrays bypassed the model-specific recall cap.
            # They must no longer be injected directly into Maatis' role prompt.
            self.assertNotIn('Gemeinsame Erinnerung', messages[0]['content'])
            self.assertNotIn('SECRET', messages[0]['content'])
            self.assertNotIn('999', messages[0]['content'])
            self.assertNotIn('"player"', messages[0]['content'])
            self.assertEqual(messages[-1], {'role': 'user', 'content': 'Hallo'})

    def test_llama_wiki_budget_and_model_switch(self):
        import json
        from shared.core.offline_wiki import context_block
        hit = {'title': 'Pyramide', 'text': 'Ein lokaler Artikel mit Fakten. ' * 100,
               'source': 'zim://Wikipedia.zim/Pyramide'}
        block = context_block(hit)
        original = [{'role': 'system', 'content': 'Erinnerung: Musik.'},
                    {'role': 'user', 'content': 'Was ist eine Pyramide?'}]
        ctx = {'offline_wiki_context': block}
        with patch('shared.core.thinking_mode.thinking_enabled', return_value=True), patch('shared.core.rpg_generation_context.rpg_context_enabled', return_value=False):
            for arch, limit in [('llama', 400), ('qwen3', 1000), ('gemma4', 1000), ('mistral3', 1000), ('llama', 400)]:
                messages = prepare_generation_messages(original, runtime_context=ctx,
                    llm={'backend': 'llama', 'chat_state': {'architecture': arch}})
                wiki = next(m['content'] for m in messages if m['content'].startswith('[MAAT-OFFLINE-WIKI]'))
                data = json.loads(wiki.rsplit('\n', 1)[-1])
                self.assertLessEqual(len(data['text']), limit)
                self.assertEqual(data['title'], 'Pyramide')
                self.assertIn(original[0], messages)
                self.assertIn(original[1], messages)
                if arch == 'llama':
                    self.assertLess(len(wiki), 700)
                    self.assertNotIn('zim://', wiki)
                else:
                    self.assertGreater(len(data['text']), 400)
            repeated = prepare_generation_messages(messages, runtime_context=ctx,
                llm={'chat_state': {'architecture': 'llama'}})
            self.assertEqual(sum(m['content'].startswith('[MAAT-OFFLINE-WIKI]') for m in repeated), 1)
        self.assertEqual(ctx['offline_wiki_context'], block)
