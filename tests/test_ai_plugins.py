"""Profile switches, bilingual prompts and guarded output before TTS/memory."""
import contextlib
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP, ROOT
from shared.core.ai_plugin_settings import DEFAULTS, SNAPSHOT, begin_turn
from shared.core.thinking_mode import prepare_generation_messages
from shared.core import streaming
from shared.core.super_memory import SuperMemory
from shared.core.chat_turn import ChatTurn, ChatCancelled
from shared.plugins.plugin_loader import PluginManager
from shared.plugins.maat_emotion.plugin_main import Plugin as Emotion
from shared.plugins.maat_style.plugin_main import Plugin as Style
from shared.plugins.maat_identity.plugin_main import Plugin as Identity
from shared.plugins.maat_plp_anti_hallu.plugin_main import Plugin as Guard
from shared.plugins.maat_reality_layer.plugin_main import Plugin as Reality
from shared.plugins.maat_formatting.plugin_main import Plugin as Formatting
from shared.plugins.maat_reply_style.plugin_main import Plugin as ReplyStyle
from shared.core.maat_style import detect_intent
from shared.core.maat_plp_anti_hallu import question_type, evaluate_antihallu

GAME=ROOT/'maatos'


def manager():
    pm=PluginManager([])
    pm.plugins_chat=[Emotion(), Style(), Identity(), Guard(), Reality(), Formatting(), ReplyStyle()]
    return pm


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.settings=dict(DEFAULTS)
        self.load=patch('shared.core.ai_plugin_settings.load_settings',side_effect=lambda:dict(self.settings))
        self.load.start();self.addCleanup(self.load.stop)
        self.pm=manager()
        self.context={'pm':self.pm,'memory_perspective':'adventure'}

    def prepare(self, query='Hallo', language='de'):
        self.pm.handle_before_chat(query,self.context)
        original=[{'role':'system','content':'MAAT RPG on Terra'}, {'role':'user','content':query}]
        before=deepcopy(original)
        with patch('shared.core.thinking_mode.build_rpg_context_message',return_value=None):
            messages=prepare_generation_messages(original,language=language,runtime_context=self.context)
        self.assertEqual(original,before)
        return messages

    def test_defaults_and_no_additional_prompts_while_three_switches_off(self):
        messages=self.prepare('Ich bin traurig.')
        self.assertEqual(self.context['maat_fields']['emotion_raw'],'sadness')
        for marker in ('[MAAT_STYLE]','[MAAT_IDENTITY]','[MAAT_ANTI_HALLU]'):
            self.assertNotIn(marker,str(messages))
        self.assertEqual(self.pm.generation_output_guards(self.context),[])

    def test_emotion_switch_clears_old_signals_before_other_plugins_and_supports_english(self):
        self.prepare('I am angry and frustrated', 'en')
        self.assertEqual(self.context['maat_fields']['emotion_raw'],'anger')
        self.settings['emotion_enabled']=False
        self.prepare('I am happy', 'en')
        self.assertFalse(any(k.startswith('emotion') or k.endswith('from_emotion') for k in self.context['maat_fields']))
        self.assertIsNone(self.pm.plugins_chat[0].last_result)
        self.settings['emotion_enabled']=True
        with patch('shared.plugins.maat_emotion.plugin_main.get_language',return_value='en'):
            self.prepare('Thank you, I am grateful', 'en')
            text=self.pm.plugins_chat[0].command('/emotion')[1]
        self.assertIn('gratitude',text)
        self.assertNotIn('Ich ',text)
        self.assertLessEqual(self.context['maat_fields']['emotion_intensity'],1)

    def test_optional_prompts_language_role_and_no_accumulation_on_model_switch(self):
        self.settings.update(hallu_mode=True,maat_style_enabled=True,maat_identity_enabled=True)
        for language in ('de','en'):
            for perspective in ('adventure','companion'):
                self.context['memory_perspective']=perspective
                messages=self.prepare('Bitte auf Deutsch antworten' if language=='de' else 'Please answer in English',language)
                blocks={marker:[m['content'] for m in messages if m['content'].startswith(marker)]
                        for marker in ('[MAAT_STYLE]','[MAAT_IDENTITY]','[MAAT_ANTI_HALLU]')}
                self.assertTrue(all(len(v)==1 for v in blocks.values()))
                identity=blocks['[MAAT_IDENTITY]'][0]
                self.assertIn(('Play Maatis' if language=='en' else 'Spiele Maatis') if perspective=='companion'
                              else ('You are MAAT-AI' if language=='en' else 'Du bist MAAT-KI'),identity)
                self.assertIn('Do not invent' if language=='en' else 'Erfinde keine',blocks['[MAAT_ANTI_HALLU]'][0])
                for architecture in ('llama','qwen3','gpt-oss'):
                    repeated=prepare_generation_messages(messages,language=language,runtime_context=self.context,
                        llm={'chat_state':{'family':architecture}})
                    self.assertEqual(str(repeated).count('[MAAT_STYLE]'),1)
                    self.assertNotIn('Person Graph',str(repeated))
        self.settings.update(hallu_mode=False,maat_style_enabled=False,maat_identity_enabled=False)
        self.pm.handle_before_chat('Weiter',self.context)
        repeated=prepare_generation_messages(messages,language='de',runtime_context=self.context)
        for marker in blocks:self.assertNotIn(marker,str(repeated))

    def test_settings_snapshot_applies_changes_only_to_next_message(self):
        self.prepare()
        self.settings.update(hallu_mode=True,maat_style_enabled=True)
        self.assertEqual(self.pm.generation_output_guards(self.context),[])
        self.prepare()
        self.assertEqual(len(self.pm.generation_output_guards(self.context)),1)

    def test_bilingual_intents_and_questions(self):
        for text,intent in [('Hallo','greeting'),('Hello','greeting'),('Hello, please fix my Python code','technical'),
                            ('Ich bin traurig','emotional'),('I am sad','emotional'),('Write a story','creative'),
                            ('Was hältst du davon','analysis'),('What do you think about it','analysis')]:
            self.assertEqual(detect_intent(text),intent,text)
        for text,kind in [('Was habe ich gestern gesagt?','memory'),('What did I say yesterday?','memory'),
                          ('Wo liegt Berlin?','fact'),('Where is Berlin?','fact'),('What is 2+2?','calculation')]:
            self.assertEqual(question_type(text),kind,text)

    def stream(self, query, reply, memory=None, language='en', cancel=False, plugins=None):
        self.context.update(last_user_input=query,super_memory_query=query,super_memory_turn='one')
        if memory:self.context['super_memory']=memory
        self.pm.handle_before_chat(query,self.context)
        turn=ChatTurn('one')
        self.context['gui_chat_turn']=turn
        first=Mock();self.context['on_first_response_token']=first
        def chunks(*args,**kwargs):
            for pos in range(0,len(reply),7):
                if cancel and pos>=14:turn.cancel()
                yield reply[pos:pos+7]
        with patch.object(streaming,'backend_stream_chat',side_effect=chunks), \
             patch.object(streaming,'_stream_lang',return_value=language), \
             patch.object(streaming,'key_pressed',return_value=False),contextlib.redirect_stdout(io.StringIO()):
            result=''.join(streaming.stream_chat_completion({'backend':'llama'},
                [{'role':'system','content':'MAAT RPG'},{'role':'user','content':query}],
                {'gui_mode':True,'raise_errors':True},plugins or [],runtime_context=self.context))
        turn.commit()
        first.assert_called_once()
        return result

    def test_rejected_output_never_reaches_tts_or_super_memory(self):
        self.settings['hallu_mode']=True
        for language,query,reply in [
                ('en','What did I say yesterday?','Yesterday you said you live in Paris.'),
                ('de','Was habe ich gestern gesagt?','Gestern hast du gesagt, dass du in Paris wohnst.')]:
            with tempfile.TemporaryDirectory() as directory:
                memory=SuperMemory(Path(directory));plugin=Mock()
                raw=reply+' save: (memory="User lives in Paris.", type=fact)'
                result=self.stream(query,raw,memory,language,plugins=[plugin])
                self.assertNotIn('Paris',result)
                self.assertEqual(memory.entries(),[])
                self.assertEqual(''.join(call.args[0] for call in plugin.on_token.call_args_list),result)
                plugin.after_stream.assert_called_once_with(result)
                self.assertIn('cannot support' if language=='en' else 'nicht belegen',result)

    def test_supported_memories_and_calculations_survive_guard(self):
        self.settings['hallu_mode']=True
        with tempfile.TemporaryDirectory() as directory:
            memory=SuperMemory(Path(directory));memory.save('My project Lantern uses Python.',tags='project Lantern')
            result=self.stream('Do you remember my project Lantern?', 'Your project Lantern uses Python.',memory)
            self.assertEqual(result,'Your project Lantern uses Python.')
        self.context.pop('super_memory',None)
        result=self.stream('What is 2+2?', '2+2=4.')
        self.assertEqual(result,'2+2=4.')

    def test_cancelled_guarded_generation_does_not_emit_or_save(self):
        self.settings['hallu_mode']=True
        with tempfile.TemporaryDirectory() as directory:
            memory=SuperMemory(Path(directory));plugin=Mock()
            with self.assertRaises(ChatCancelled):
                self.stream('What did I say yesterday?','You definitely said you live in Berlin.',memory,cancel=True,plugins=[plugin])
            self.assertEqual(memory.entries(),[])
            plugin.on_token.assert_not_called()

    def test_guard_off_keeps_live_streaming(self):
        self.pm.handle_before_chat('Hello',self.context)
        emitted=[]
        def chunks(*args,**kwargs):
            yield 'One'
            self.assertEqual(emitted,['One'])
            yield ' two'
        with patch.object(streaming,'backend_stream_chat',side_effect=chunks),patch.object(streaming,'key_pressed',return_value=False),contextlib.redirect_stdout(io.StringIO()):
            for part in streaming.stream_chat_completion({'backend':'llama'},[],{'gui_mode':True},runtime_context=self.context):
                emitted.append(part)
        self.assertEqual(emitted,['One',' two'])

    def test_game_config_registers_one_guard_and_keeps_memory_wiki(self):
        config=json.loads((GAME/'apps/maat_rpg/plugin_config.json').read_text())['plugins']
        self.assertFalse(config['uncertainty_guard'])
        for name in ('maat_emotion','maat_style','maat_identity','maat_plp_anti_hallu','maat_reality_layer','maat_formatting','maat_reply_style','super_memory','offline_wiki'):
            self.assertTrue(config[name])
        pm=PluginManager([],config_path=str(GAME/'apps/maat_rpg/plugin_config.json'))
        with contextlib.redirect_stdout(io.StringIO()):
            for name in ('maat_emotion','maat_style','maat_identity','maat_plp_anti_hallu','maat_reality_layer','maat_formatting','maat_reply_style','uncertainty_guard'):
                pm._load_single(str(GAME/'shared/plugins'/name/'plugin_main.py'))
        self.assertEqual(len(pm.loaded_plugin_ids),7)
        self.assertIn('uncertainty_guard',pm.skipped_plugins)

    def test_only_supplied_evidence_can_ground_specifics(self):
        query='How many residents does Example Village have?'
        answer='Example Village has 250 residents.'
        options={'antihallu_enabled':True}
        ungrounded=evaluate_antihallu(query,answer+' According to a source.',{},options)
        self.assertTrue(ungrounded['unsupported_specifics'])
        grounded=evaluate_antihallu(query,answer,{'grounding_text':'Example Village has 250 residents.'},options)
        self.assertFalse(grounded['unsupported_specifics'])
        self.assertEqual(grounded['action'],'pass')
        unchanged=evaluate_antihallu('Is this scientifically proven?', 'This is not scientifically proven.', {},options)
        self.assertFalse(unchanged['unsupported_absolute_claim'])


class PluginDialogTests(unittest.TestCase):
    def test_profile_persistence_translation_and_restore_without_saving(self):
        from PySide6.QtCore import QCoreApplication,QEvent
        from apps.maat_rpg import session_shared as shared
        from gui.plugin_settings import PluginSettingsPanel
        from gui.desktop import STYLE
        with tempfile.TemporaryDirectory() as directory:
            paths={i:Path(directory)/f'{i}.json' for i in (1,2)}
            slot=[1]
            with patch.object(shared,'profile_settings_path',side_effect=paths.get):
                save=Mock(side_effect=lambda update:shared.write_profile_settings(slot[0],update))
                dialog=PluginSettingsPanel(lambda:shared.load_profile_settings(slot[0]),save)
                dialog.setStyleSheet(STYLE)
                try:
                    dialog.show();APP.processEvents()
                    self.assertEqual({k:b.isChecked() for k,b in dialog.boxes.items()},DEFAULTS)
                    save.assert_not_called()
                    dialog.boxes['hallu_mode'].click();dialog.boxes['emotion_enabled'].click()
                    dialog.boxes['response_formatting_enabled'].click()
                    self.assertTrue(shared.load_profile_settings(1)['hallu_mode'])
                    self.assertFalse(shared.load_profile_settings(1)['emotion_enabled'])
                    self.assertFalse(shared.load_profile_settings(1)['response_formatting_enabled'])
                    before=save.call_count
                    dialog.set_language('en');dialog.refresh()
                    self.assertEqual(dialog.boxes['emotion_enabled'].text(),'Emotion detection')
                    self.assertEqual(save.call_count,before)
                    slot[0]=2;dialog.refresh()
                    self.assertEqual({k:b.isChecked() for k,b in dialog.boxes.items()},DEFAULTS)
                    slot[0]=1;dialog.refresh();self.assertTrue(dialog.boxes['hallu_mode'].isChecked())
                    if os.environ.get('MAAT_PLUGIN_SCREENSHOTS'):
                        slot[0]=2;dialog.refresh()
                        path=Path(os.environ['MAAT_PLUGIN_SCREENSHOTS']);path.mkdir(parents=True,exist_ok=True)
                        dialog.resize(660,760);dialog.show();APP.processEvents()
                        for language in ('de','en'):
                            dialog.set_language(language);APP.processEvents()
                            self.assertTrue(dialog.grab().save(str(path/f'plugins-{language}.png')))
                finally:
                    dialog.close();dialog.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)


import test_gui_language as language_helpers


class PluginMenuIntegrationTests(unittest.TestCase):
    setUp=language_helpers.LanguageTests.setUp
    close_windows=language_helpers.LanguageTests.close_windows
    window=language_helpers.LanguageTests.window
    ready=language_helpers.LanguageTests.ready

    def test_settings_tab_opens_without_dialog_model_restart_or_music_change(self):
        from apps.maat_rpg import session_shared as shared
        from PySide6.QtWidgets import QApplication, QDialog, QPushButton
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        shared.write_application_language('en')
        window=self.window();self.ready(window)
        window.enter_menu()
        self.assertFalse(hasattr(window,'plugins_button'))
        for root in (window.stack.widget(0),window.stack.widget(4)):
            self.assertFalse(any(button.text()=='Plugins' for button in root.findChildren(QPushButton)))
        window.options_button.click();APP.processEvents()
        self.assertEqual(window.stack.currentIndex(),4)
        self.assertEqual(window.settings_tabs.tabText(0),'General')
        audio_before=list(window.audio.starts)
        process=window.game.process
        tabs=window.settings_tabs.tabBar()
        QTest.mouseClick(tabs,Qt.LeftButton,pos=tabs.tabRect(1).center());APP.processEvents()
        self.assertTrue(window.plugin_panel.isVisible())
        self.assertIs(window.settings_tabs.currentWidget(),window.plugin_panel)
        self.assertFalse(window.plugin_panel.isWindow())
        self.assertNotIsInstance(window.plugin_panel,QDialog)
        self.assertIsNone(QApplication.activeModalWidget())
        self.assertEqual(window.plugin_panel.boxes['emotion_enabled'].text(),'Emotion detection')
        window.plugin_panel.boxes['maat_identity_enabled'].click()
        self.assertTrue(shared.load_profile_settings(window.game._profile_slot())['maat_identity_enabled'])
        window.settings_tabs.setCurrentIndex(0);APP.processEvents()
        self.assertFalse(window.plugin_panel.isVisible())
        window.settings_tabs.setCurrentIndex(1);APP.processEvents()
        self.assertTrue(window.plugin_panel.boxes['maat_identity_enabled'].isChecked())
        self.assertIs(window.game.process,process)
        self.assertEqual(window.audio.starts,audio_before)
        if os.environ.get('MAAT_PLUGIN_SCREENSHOTS'):
            target=Path(os.environ['MAAT_PLUGIN_SCREENSHOTS']);target.mkdir(parents=True,exist_ok=True)
            window.resize(1200,850);APP.processEvents()
            self.assertTrue(window.grab().save(str(target/'settings-plugins-en.png')))


if __name__=='__main__':unittest.main()
