"""MAAT100 prompt delivery, language, settings and single-call streaming."""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from contextlib import redirect_stdout
from test_desktop import APP,ROOT
import test_gui_language as language_helpers
from apps.maat_rpg import session_shared as shared
from shared.core.thinking_mode import (prepare_generation_messages,thinking_enabled,
                                      chat_completion_thinking_kwargs)
from shared.core.gguf_chat import prepare_messages
from shared.plugins.plugin_loader import PluginManager
from shared.plugins.maat_thinking.prompt import normalize_level,level_status,build_prompt_block

GAME=ROOT/'maatos'
PLUGIN=GAME/'shared/plugins/maat_thinking/plugin_main.py'
MARKER='[MAAT_INTERNAL_QUALITY]'


class PromptTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory(prefix='maat-thinking-')
        self.addCleanup(folder.cleanup)
        self.root=Path(folder.name)
        environment=patch.dict(os.environ,{'MAAT_STATE_DIR':str(self.root)})
        environment.start();self.addCleanup(environment.stop)
        self.settings=self.root/'settings_state.json'
        self.configure()
        self.pm=PluginManager([],config_path=str(GAME/'apps/maat_rpg/plugin_config.json'))
        with redirect_stdout(io.StringIO()):self.pm._load_single(str(PLUGIN))
        self.history=[{'role':'system','content':'Keep the MAAT identity and requested memory format.'},
                      {'role':'user','content':'A previous question'},
                      {'role':'assistant','content':'A previous answer'},
                      {'role':'user','content':'Hello!'}]

    def configure(self, **settings):
        self.settings.write_text(json.dumps(dict(language='de',rpg_context_enabled=False,**settings)))

    def prepare(self, messages=None, language='de', architecture='llama', **context):
        return prepare_generation_messages(messages if messages is not None else self.history,
            language=language,runtime_context=dict(pm=self.pm,**context),
            llm={'backend':'llama','chat_state':{'architecture':architecture}})

    def block(self,messages):
        blocks=[m['content'] for m in messages if m['role']=='system' and m['content'].startswith(MARKER)]
        self.assertEqual(len(blocks),1)
        return blocks[0]

    def test_user_template_level_100_and_invalid_levels(self):
        for value,expected in [('MAAT100%',100),('aus',0),('off',0),(-5,0),(200,100),
                               (None,0),(float('inf'),0),(float('nan'),0),('oops',0)]:
            self.assertEqual(normalize_level(value),expected)
        status=level_status(100)
        self.assertEqual((status['level'],status['target'],status['repairs'],status['depth']),
                         (100,9.5,3,'deep'))
        for language in ('de','en'):
            block=build_prompt_block(100,language)
            self.assertIn('MAAT100 (100%)',block)
            self.assertIn('9.5/10',block)
            self.assertLess(len(block),3000)
            self.assertEqual(build_prompt_block(0,language),'')
        self.assertIn('Maximale Reparaturrunden: 3.',build_prompt_block(100,'de'))
        self.assertIn('Maximum revision rounds: 3.',build_prompt_block(100,'en'))

    def test_enabled_by_default_registered_plugin_without_native_thinking(self):
        self.assertIn('maat_thinking',self.pm.loaded_plugin_ids)
        for architecture in ('llama','qwen3','gemma4'):
            original=deepcopy(self.history)
            messages=self.prepare(architecture=architecture)
            self.block(messages)
            self.assertEqual([m for m in messages if m['role']!='system'],self.history[1:])
            self.assertEqual(messages[0],self.history[0])
            self.assertEqual(self.history,original)
            self.assertFalse(thinking_enabled())
            self.assertNotIn('MAAT-RPG-WELTZUSTAND',str(messages))
        def backend(messages,chat_template_kwargs=None,reasoning_budget=None):pass
        self.assertEqual(chat_completion_thinking_kwargs(backend),
                         {'chat_template_kwargs':{'enable_thinking':False},'reasoning_budget':0})

    def test_toggle_and_language_switch_replace_stale_blocks_and_preserve_user_content(self):
        history=self.history+[{'role':'user','content':MARKER+' Explain this marker.'}]
        messages=self.prepare(history)
        self.assertIn('Erstelle einen Entwurf',self.block(messages))
        for _ in range(3):messages=self.prepare(messages,language='en')
        block=self.block(messages)
        self.assertIn('Prepare a draft',block);self.assertNotIn('Erstelle einen Entwurf',block)
        self.assertEqual(sum(m['content'].startswith('[THINKING MODE OFF]') for m in messages),1)
        self.assertNotIn('[THINKING-MODUS AUS]',str(messages))
        self.configure(maat_thinking_enabled=False)
        messages=self.prepare(messages)
        self.assertFalse(any(m['role']=='system' and MARKER in m['content'] for m in messages))
        self.assertIn(history[-1],messages)
        self.configure(maat_thinking_enabled=True,thinking_enabled=True)
        messages=self.prepare(messages)
        self.block(messages)
        self.assertNotIn('[THINKING-MODUS AUS]',str(messages))
        self.assertNotIn('[THINKING MODE OFF]',str(messages))

    def test_plugin_configuration_can_disable_injection(self):
        config=self.root/'plugins.json'
        config.write_text(json.dumps({'plugins':{'maat_thinking':False}}))
        disabled=PluginManager([],config_path=str(config))
        with redirect_stdout(io.StringIO()):disabled._load_single(str(PLUGIN))
        self.assertEqual(disabled.generation_system_messages(),[])
        self.assertIn('maat_thinking',disabled.skipped_plugins)

    def test_offline_wiki_and_recall_remain_separate_with_llama_limits(self):
        from shared.core.offline_wiki import context_block
        wiki=context_block({'title':'Mona Lisa','text':'Known local facts. '*100,'source':'zim://local/Mona Lisa'})
        memory=Mock()
        memory.generation_context.return_value='[MAAT-SUPER-MEMORY]\nA remembered conversation.'
        messages=self.prepare(offline_wiki_context=wiki,super_memory=memory)
        self.block(messages)
        self.assertTrue(any(m['content'].startswith('[MAAT-SUPER-MEMORY]') for m in messages))
        snippet=next(m['content'] for m in messages if m['content'].startswith('[MAAT-OFFLINE-WIKI]'))
        self.assertLessEqual(len(json.loads(snippet.rsplit('\n',1)[-1])['text']),400)
        self.assertIn('Mona Lisa',snippet)
        memory.generation_context.assert_called_once()

    def test_prompt_survives_each_backend_role_format_once(self):
        for architecture in ('llama','qwen3','gemma3','gemma4'):
            messages=prepare_messages(self.prepare(language='en',architecture=architecture),architecture)
            self.assertEqual(sum(m['content'].count(MARKER) for m in messages),1)
            self.assertIn('Hello!',messages[-1]['content'])
            self.assertIn('Keep the MAAT identity',str(messages))

    def test_single_stream_call_final_text_and_cancellation(self):
        from shared.core import streaming
        from shared.core.chat_turn import ChatTurn,ChatCancelled
        llm={'backend':'llama','chat_state':{'architecture':'llama'}}
        context={'pm':self.pm}
        before=self.settings.read_bytes()
        with patch.object(streaming,'backend_stream_chat',return_value=iter(['Hello',' there!'])) as backend, \
             patch.object(streaming,'key_pressed',return_value=False),redirect_stdout(io.StringIO()):
            response=''.join(streaming.stream_chat_completion(llm,self.history,{'gui_mode':True},runtime_context=context))
        backend.assert_called_once()
        self.assertEqual(response,'Hello there!')
        self.block(backend.call_args.args[1])
        self.assertNotIn(MARKER,response)
        self.assertEqual(self.settings.read_bytes(),before)
        turn=ChatTurn('cancelled');turn.cancel()
        with patch.object(streaming,'backend_stream_chat') as backend:
            with self.assertRaises(ChatCancelled):
                list(streaming.stream_chat_completion(llm,self.history,{'gui_mode':True},runtime_context=dict(context,gui_chat_turn=turn)))
            backend.assert_not_called()

    def test_companion_route_uses_same_plugin_and_keeps_role(self):
        from gui.game_worker import Runtime
        from shared.core import streaming
        runtime=SimpleNamespace(context={'pm':self.pm},
            companion=SimpleNamespace(state={'dialogue':[]},save=Mock()),
            llm={'backend':'llama','chat_state':{'architecture':'llama'}},perf={},
            stop_previous_speech=Mock(),complete_chat_turn=Mock(),archive_chat=Mock())
        with patch.object(streaming,'backend_stream_chat',return_value=iter(['Wer bist du?'])) as backend, \
             patch.object(streaming,'key_pressed',return_value=False),patch('gui.game_worker.emit'),redirect_stdout(io.StringIO()):
            reply=Runtime.maatis_dialogue(runtime,'Hallo')
        backend.assert_called_once()
        self.block(backend.call_args.args[1])
        self.assertIn('Du bist Maatis',backend.call_args.args[1][0]['content'])
        self.assertEqual(reply,'Wer bist du?')
        self.assertNotIn(MARKER,str(runtime.companion.state['dialogue']))


class ThinkingUITests(unittest.TestCase):
    setUp=language_helpers.LanguageTests.setUp
    close_windows=language_helpers.LanguageTests.close_windows
    window=language_helpers.LanguageTests.window
    ready=language_helpers.LanguageTests.ready

    def test_default_toggle_restart_and_profiles_do_not_reload_model(self):
        shared.write_application_language('de');shared.set_profile_name(1,'Thinking test')
        window=self.window();self.ready(window);window.enter_menu();window.navigate(4)
        box=window.dialog_settings['maat_thinking_enabled']
        self.assertTrue(box.isChecked());self.assertEqual(box.text(),'MAAT Thinking aktivieren')
        self.assertFalse(window.dialog_settings['thinking_enabled'].isChecked())
        with patch.object(window.game,'load_model') as load,patch.object(window.game,'shutdown') as shutdown:
            box.click()
            self.assertFalse(shared.load_profile_settings(1)['maat_thinking_enabled'])
            load.assert_not_called();shutdown.assert_not_called()
        self.assertTrue(shared.load_profile_settings(2)['maat_thinking_enabled'])
        window.change_profile(1);self.ready(window)
        self.assertTrue(box.isChecked())
        window.change_profile(0);self.ready(window)
        self.assertFalse(box.isChecked())
        window.game.shutdown();window.close()
        restarted=self.window();self.ready(restarted)
        self.assertFalse(restarted.dialog_settings['maat_thinking_enabled'].isChecked())

    def test_english_label_explanation_and_runtime_prompt_language(self):
        from PySide6.QtWidgets import QLabel
        shared.write_application_language('en');shared.set_profile_name(1,'Thinking test')
        window=self.window();self.ready(window);window.enter_menu();window.navigate(4)
        box=window.dialog_settings['maat_thinking_enabled']
        self.assertEqual(box.text(),'Enable MAAT Thinking')
        self.assertIn('up to three',box.toolTip())
        labels=[label.text() for label in window.stack.widget(4).findChildren(QLabel)]
        self.assertIn('MAAT Thinking improves the internal thinking process before the model responds.',labels)
        settings_path=shared.profile_settings_path(1)
        with patch('shared.core.rpg_i18n.state_file',return_value=str(settings_path)):
            from shared.plugins.maat_thinking.plugin_main import Plugin
            plugin=Plugin()
            self.assertIn('Prepare a draft',plugin.generation_prompt())
            box.click();self.assertEqual(plugin.generation_prompt(),'')
            box.click();self.assertIn('Maximum revision rounds: 3',plugin.generation_prompt())
