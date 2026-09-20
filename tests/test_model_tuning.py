from gguf_fixtures import write_gguf, guarded_test_memory
"""Manual settings reach the backend and survive reloads without affecting Auto."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication, QEvent
from test_desktop import APP
import test_gui_language as language_helpers
import test_model_switch_prompt as model_helpers
from gui.model_tuning import ModelTuningPanel
from gui.live_session import LiveSession
from shared.core.model_settings import normalize_tuning, resolve_settings
from shared.core.hardware_profile import automatic_settings
from apps.maat_rpg import session_shared as shared


def preset():
    return {'mode':'manual','manual':dict(threads=3,threads_batch=5,gpu_layers=0,
        n_batch=128,n_ubatch=32,flash_attn='off',use_mmap=True,use_mlock=False,repack_weights=False)}


class ModelSettingsTests(unittest.TestCase):
    def test_context_default_and_extended_limit(self):
        from shared.core.model_settings import DEFAULT_CONTEXT, MAX_CONTEXT, normalize_context
        self.assertEqual(DEFAULT_CONTEXT,20000)
        self.assertEqual(MAX_CONTEXT,100000)
        for value,expected in [(20000,20000),(40000,40000),(100000,100000),(120000,100000),(1,1024)]:
            self.assertEqual(normalize_context(value),expected)

    def automatic(self, gpu=True):
        return automatic_settings(dict(system='Darwin',machine='arm64' if gpu else 'x86_64',
            logical=10,physical=4,gpu=gpu,backend_info='METAL = 1' if gpu else ''), 'llama.gguf')

    def test_auto_ignores_manual_preset_and_old_profiles_stay_auto(self):
        for saved in (None, {}, {'threads':2}, dict(preset(), mode='auto')):
            auto=self.automatic()
            result=resolve_settings(auto, saved)
            self.assertEqual(result['mode'],'auto')
            for key,value in auto.items(): self.assertEqual(result[key],value)
            result['options']['n_batch']=1
            self.assertEqual(auto['options']['n_batch'],512)

    def test_manual_options_cpu_fallback_and_context_limits(self):
        saved=preset();saved['manual'].update(gpu_layers=7,n_batch=8192,n_ubatch=4000,flash_attn='on',use_mmap=False,use_mlock=True)
        for gpu in (False,True):
            result=resolve_settings(self.automatic(gpu),saved,2048)
            self.assertEqual(result['threads'],3)
            self.assertEqual(result['threads_batch'],5)
            self.assertEqual(result['gpu_layers'],7 if gpu else 0)
            expected=dict(n_threads_batch=5,n_batch=2048,n_ubatch=2048,
                          flash_attn=True,use_mmap=False,use_mlock=True)
            if gpu:expected.update(offload_kqv=True,op_offload=True)
            self.assertEqual(result['options'],expected)
            self.assertIn('batch_capped',result['adjustments'])
            self.assertEqual('gpu_unavailable' in result['adjustments'],not gpu)
        self.assertEqual(normalize_tuning({'mode':'manual','manual':{'threads':-5,'n_batch':2,'n_ubatch':99}})['manual']['n_ubatch'],2)
        self.assertEqual(normalize_tuning({'manual':{'use_mmap':'false'}})['manual']['use_mmap'],True)

    def test_worker_applies_and_saves_requested_parameters_then_restores_auto(self):
        runtime=model_helpers.ModelSwitchPromptTests().runtime()
        runtime.shared.load_profile_settings.return_value={'gui_model_tuning':preset()}
        with tempfile.TemporaryDirectory(prefix='maat-tuning-backend-') as folder:
            model=Path(folder)/'test.gguf';write_gguf(model)
            with guarded_test_memory(folder), patch('shared.core.hardware_profile.detect_hardware',return_value={}), patch('shared.core.hardware_profile.automatic_settings',side_effect=lambda *a:self.automatic()), patch('shared.core.backend_router.load_backend',side_effect=lambda *a,**kw:{'chat_state':{'architecture':'llama'}}) as backend, patch('shared.core.llm_loader.save_perf') as save, patch('shared.core.llm_loader.save_last_model_choice'), patch('gui.game_worker.emit'):
                runtime.load_model(str(model))
                args=backend.call_args.kwargs
                self.assertEqual(args['n_threads'],3)
                self.assertEqual(args['n_gpu_layers'],0)
                self.assertEqual(args['max_ctx'],20000)
                self.assertEqual(args['load_options']['n_threads_batch'],5)
                self.assertEqual(args['load_options']['n_ubatch'],32)
                self.assertFalse(args['load_options']['flash_attn'])
                self.assertEqual(save.call_args.args[0]['model_tuning'],preset())
                runtime.shared.write_profile_settings.assert_called_with(1,{'gui_model_tuning':preset()})
                runtime.load_model(str(model), tuning=dict(preset(),mode='auto'))
                self.assertEqual(backend.call_args.kwargs['n_threads'],8)
                self.assertEqual(backend.call_args.kwargs['n_gpu_layers'],-1)
                self.assertTrue(backend.call_args.kwargs['load_options']['flash_attn'])

    def test_transport_carries_manual_settings_to_worker(self):
        session=LiveSession();session.ready=True;session.busy=False
        with patch.object(session,'write') as write:
            session.load_model('test.gguf',tuning=preset())
        self.assertEqual(write.call_args.args[0]['tuning'],preset())


class ModelTuningUITests(unittest.TestCase):
    setUp=language_helpers.LanguageTests.setUp
    close_windows=language_helpers.LanguageTests.close_windows
    window=language_helpers.LanguageTests.window
    ready=language_helpers.LanguageTests.ready

    def test_mode_expands_keeps_manual_values_and_translates_without_editing(self):
        panel=ModelTuningPanel();panel.show();APP.processEvents()
        changes=[];panel.changed.connect(changes.append)
        try:
            self.assertTrue(panel.manual_panel.isHidden())
            panel.restore(preset());self.assertEqual(changes,[])
            self.assertFalse(panel.manual_panel.isHidden())
            panel.mode.setCurrentIndex(0)
            self.assertTrue(panel.manual_panel.isHidden())
            panel.mode.setCurrentIndex(1)
            self.assertEqual(panel.settings(),preset())
            panel.fields['n_batch'].setValue(16)
            self.assertEqual(panel.fields['n_ubatch'].value(),16)
            before=panel.settings();count=len(changes)
            panel.set_language('en')
            self.assertEqual(panel.mode.itemText(0),'Auto · Default')
            self.assertIn('Number of CPU',panel.fields['threads'].toolTip())
            self.assertEqual(panel.settings(),before)
            self.assertEqual(len(changes),count)
            panel.set_language('de')
            self.assertEqual(panel.mode.itemText(1),'Manuell')
        finally:
            panel.close();panel.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)

    def test_profile_save_restart_and_both_model_load_buttons(self):
        shared.write_application_language('de')
        shared.write_profile_settings(1,{'language':'de'})
        window=self.window();self.ready(window)
        window.enter_menu();window.open_models()
        window.model_tuning.mode.setCurrentIndex(1)
        window.model_tuning.fields['threads'].setValue(3)
        window.model_tuning.fields['threads_batch'].setValue(5)
        selected=window.model_tuning.settings()
        self.assertEqual(shared.load_profile_settings(1)['gui_model_tuning'],selected)
        self.assertNotIn('gui_model_tuning',shared.load_profile_settings(2))
        window.receive({'event':'models','items':['selected.gguf'],'selected':'selected.gguf','performance':{}})
        self.assertEqual(window.model_tuning.settings(),selected)
        with patch.object(window.game,'load_model') as load:
            window.load_model();window.load_chat_model()
            self.assertEqual(load.call_count,2)
            self.assertEqual(load.call_args.args[-1],selected)
        # Auto also persists; the manual values stay available when expanded again.
        window.model_tuning.mode.setCurrentIndex(0)
        expected=window.model_tuning.settings()
        window.game.shutdown();window.close()
        reopened=self.window();self.ready(reopened)
        self.assertEqual(reopened.model_tuning.settings(),expected)
        self.assertTrue(reopened.model_tuning.manual_panel.isHidden())
        reopened.model_tuning.mode.setCurrentIndex(1)
        self.assertEqual(reopened.model_tuning.fields['threads'].value(),3)
        reopened.open_models();APP.processEvents()
        self.assertFalse(reopened.model_scroll.horizontalScrollBar().isVisible())
        self.assertTrue(reopened.load_button.isVisible())

    def test_manual_mode_restored_before_startup_load(self):
        shared.write_application_language('en')
        shared.write_profile_settings(1,{'language':'en','gui_model_tuning':preset()})
        window=self.window();self.ready(window)
        window.phase='title';window.model_combo.addItem('saved.gguf');window.saved_model='saved.gguf'
        window._startup_model_attempted=False
        with patch.object(window.game,'load_model') as load:
            window.prepare_startup_model()
        self.assertEqual(load.call_args.args[-1],preset())
        self.assertEqual(window.model_tuning.mode.currentText(),'Manual')


if __name__=='__main__': unittest.main()
