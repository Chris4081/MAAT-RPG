"""The selectable context window never limits or rewrites the durable archive."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from test_desktop import APP
import test_gui_language as ui_fixture
shared = ui_fixture.shared
from shared.core.conversation_history import message_limit, recent_messages, SETTING
from shared.core import streaming
from shared.core.super_memory import SuperMemory


def dialogue():
    result = [{'role':'system','content':'MAAT identity'}]
    for i in range(15):
        result.extend([{'role':'user','content':f'Question {i}'},
                       {'role':'assistant','content':f'Answer {i}'}])
    return result + [{'role':'user','content':'The current question'}]


class HistoryWindowTests(unittest.TestCase):
    def test_limits_and_invalid_settings(self):
        for value, expected in [(None,10),('bad',10),(True,10),(-30,2),(2,2),(7,7),(20,20),(999,20)]:
            self.assertEqual(message_limit({SETTING:value}),expected)
        self.assertEqual(message_limit({}),10)

    def test_recent_window_preserves_system_and_current_without_mutation(self):
        original = dialogue()
        before = json.dumps(original)
        for limit in (2,7,10,20):
            result = recent_messages(original,limit)
            self.assertEqual(result[0],original[0])
            self.assertEqual(result[1:],original[-(limit+1):])
            self.assertEqual(result[-1]['content'],'The current question')
        self.assertEqual(json.dumps(original),before)

    def test_both_adapters_and_roles_use_setting_before_generation_keep_memory(self):
        with TemporaryDirectory() as folder:
            root=Path(folder); settings=root/'settings.json'
            memory=SuperMemory(root)
            memory.save('The current question concerns our offline project.',tags='question')
            original=dialogue()
            for backend in ('llama','llama_intel'):
                for mode in ('adventure','companion'):
                    for limit in (2,20):
                        settings.write_text(json.dumps({SETTING:limit}))
                        ctx={'memory_perspective':mode,'super_memory':memory,'super_memory_query':'current question'}
                        model={'backend':backend,'chat_state':{'architecture':'mistral3','family':'mistral'}}
                        with patch('shared.core.conversation_history.state_file',return_value=str(settings)), \
                             patch.object(streaming,'backend_stream_chat',return_value=iter(['Reply.'])) as sent, \
                             patch.object(streaming,'key_pressed',return_value=False):
                            list(streaming.stream_chat_completion(model,original,{'gui_mode':True,'raise_errors':True},runtime_context=ctx))
                        received=sent.call_args.args[1]
                        self.assertEqual([m for m in received if m['role']!='system'],original[-(limit+1):])
                        self.assertTrue(any(m['content'].startswith('[MAAT-SUPER-MEMORY]') for m in received))
                        self.assertIn(original[0],received)
            self.assertEqual(len(original),32)


class HistorySettingsUITests(unittest.TestCase):
    setUp=ui_fixture.LanguageTests.setUp
    close_windows=ui_fixture.LanguageTests.close_windows
    window=ui_fixture.LanguageTests.window

    def test_profile_persistence_range_and_bilingual_render(self):
        from PySide6.QtWidgets import QLabel
        from test_settings_scroll import wheel
        shared.write_application_language('de')
        w=self.window(); w.apply_audio_settings()
        self.assertEqual((w.history_messages.minimum(),w.history_messages.maximum(),w.history_messages.value()),(2,20,10))
        w.history_messages.setValue(20)
        self.assertEqual(shared.load_profile_settings(1)[SETTING],20)
        with patch.object(w.game,'_profile_slot',return_value=2):
            w.apply_audio_settings()
            self.assertEqual(w.history_messages.value(),10)
            w.history_messages.setValue(2)
        w.apply_audio_settings(); self.assertEqual(w.history_messages.value(),20)
        wheel(w.history_messages)
        self.assertEqual(w.history_messages.value(),20)
        self.assertEqual(shared.load_profile_settings(2)[SETTING],2)
        card=w.history_messages.parentWidget()
        for language in ('en','de'):
            w.game.get_snapshot().language=language
            w.apply_menu_language()
            labels=' '.join(label.text() for label in card.findChildren(QLabel))
            self.assertIn('Messages in AI context' if language=='en' else 'Nachrichten im KI-Kontext',labels)
            self.assertIn('Chat archive' if language=='en' else 'Chatarchiv',labels)
            output=os.environ.get('MAAT_GUI_SCREENSHOTS')
            if output:
                Path(output).mkdir(parents=True,exist_ok=True)
                card.resize(720,card.sizeHint().height()); APP.processEvents()
                self.assertTrue(card.grab().save(str(Path(output)/f'dialogue-history-{language}.png')))
