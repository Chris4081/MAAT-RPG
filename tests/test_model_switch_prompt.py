from gguf_fixtures import write_gguf, guarded_test_memory
import unittest,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
from test_desktop import APP
from gui.game_worker import Runtime

class ModelSwitchPromptTests(unittest.TestCase):
    def runtime(self):
        r=Runtime.__new__(Runtime)
        r.boot=SimpleNamespace(system_prompt='Du bist MAAT-KI. Harmonie, Balance, Schöpfungskraft, Verbundenheit, Respekt.',conversation=[{'role':'user','content':'Unsere gemeinsame Erinnerung'},{'role':'assistant','content':'Ich erinnere mich.'}])
        r.context={};r.llm={'instance':object()};r.slot=1;r.shared=Mock();r.companion_active=False
        return r
    def test_prompt_restored_once_and_history_preserved(self):
        r=self.runtime();history=list(r.boot.conversation)
        r.restore_chat_prompt();r.restore_chat_prompt()
        self.assertEqual(r.boot.conversation,[{'role':'system','content':r.boot.system_prompt}]+history)
        self.assertIs(r.context['conversation'],r.boot.conversation)
    def test_model_switch_rebinds_identity_and_keeps_memory_without_new_companion_turn(self):
        r=self.runtime();r.companion_active=True;r.free_companion=False
        r.shared.load_profile_settings.return_value={'gui_perspective':'companion'}
        r.companion_view=Mock(return_value={'memories':['Erinnerung']});r.companion_start=Mock()
        hardware={'platform':'test','acceleration':'CPU','threads':2,'threads_batch':2,'gpu_layers':0,'options':{}}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.gguf';write_gguf(path)
            with guarded_test_memory(folder), patch('shared.core.hardware_profile.detect_hardware',return_value={}),patch('shared.core.hardware_profile.automatic_settings',return_value=hardware),patch('shared.core.backend_router.load_backend',return_value={'chat_state':{'architecture':'llama'}}),patch('shared.core.llm_loader.save_last_model_choice'),patch('shared.core.llm_loader.save_perf'),patch('gui.game_worker.emit'):
                for _ in range(2):r.load_model(str(path))
        self.assertEqual(r.boot.conversation[0]['content'],r.boot.system_prompt)
        self.assertEqual(len(r.boot.conversation),3)
        self.assertIs(r.context['llm'],r.llm)
        self.assertTrue(r.free_companion);r.companion_start.assert_not_called()

    def test_story_decision_hint_repeats_on_invalid_input_and_keeps_choice(self):
        import io
        from contextlib import redirect_stdout
        from apps.maat_rpg.plugins.story_loader.plugin_main import Plugin
        story=Plugin.__new__(Plugin);story.state={};story._language=lambda:'de'
        story._append_journal_entry=Mock();story._refresh_path_profile=Mock();story._save_state=Mock()
        with patch('builtins.input',side_effect=['falsch','2']) as ask,redirect_stdout(io.StringIO()):
            story._handle_story_choice({'id':'combat_vow','prompt':'Welches Versprechen gibst du?',
                'options':[{'label':'Schutz','value':'protect'},{'label':'Wahrheit','value':'truth'}]})
        self.assertEqual(story.state['choices']['combat_vow'],'truth')
        self.assertEqual(ask.call_count,2)
        for call in ask.call_args_list:self.assertIn('Wähle eine Entscheidung – sie prägt deinen Spielverlauf!',call.args[0])
        story._save_state.assert_called_once()
