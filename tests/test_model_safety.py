"""Exercise dangerous configurations without loading models or allocating RAM."""
import copy
import os
from pathlib import Path
import struct
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
from PySide6.QtCore import QProcess
from gguf_fixtures import write_gguf, guarded_test_memory
from shared.core import model_safety as safety
from shared.core.model_safety import GIB, ModelSafetyError
from gui.live_session import LiveSession
import test_model_switch_prompt as model_helpers
import test_gui_language as language_helpers
from apps.maat_rpg import session_shared as shared


class SafetyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='maat-safety-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.model = write_gguf(self.root/'test.gguf')
        self.settings = dict(threads=4, threads_batch=8, options=dict(
            use_mmap=True, use_mlock=False, n_batch=512, n_ubatch=128, flash_attn=True))
        self.memory = dict(total=16*GIB, available=12*GIB)

    def check(self, **kwargs):
        return safety.check_model_safety(self.model, kwargs.pop('context',20000), self.settings,
            memory=kwargs.pop('memory',self.memory), logical=8, **kwargs)

    def test_header_tokenizer_and_array_dimensions(self):
        metadata = safety.gguf_metadata(self.model)
        self.assertEqual(metadata['general.architecture'], 'llama')
        self.assertNotIn('tokenizer.ggml.tokens', metadata)
        report = self.check()
        self.assertEqual(report['kv_cache'], 32*8*(128+128)*2*20000)
        self.assertEqual(report['budget'], 16*GIB*99//100)
        self.assertEqual(report['limit_percent'], 99)
        self.assertEqual(report['context'],20000)
        metadata['llama.attention.head_count_kv'] = [4,8]
        write_gguf(self.model,metadata)
        self.assertEqual(self.check()['kv_cache'], report['kv_cache'])

    def test_corrupt_headers_are_rejected_before_tensor_reads(self):
        good = self.model.read_bytes()
        for data in (b'GGUF', b'GGUF'+struct.pack('<IQQ',3,0,100001),
                     b'GGUF'+struct.pack('<IQQQ',3,0,1,2**63),good[:-1]):
            self.model.write_bytes(data)
            with self.assertRaises(ModelSafetyError): safety.gguf_metadata(self.model)

    def test_unknown_dimensions_and_split_models_fail_closed(self):
        metadata = safety.gguf_metadata(self.model)
        for change in ({'llama.block_count':0},{'split.count':2},{'general.architecture':'new_unknown'}):
            with self.assertRaises(ModelSafetyError):self.check(metadata=dict(metadata,**change))

    def test_zero_and_one_split_count_are_single_file_models(self):
        metadata=safety.gguf_metadata(self.model)
        original=self.check(metadata=metadata)
        for count in (0,1):
            report=self.check(metadata=dict(metadata,**{'split.count':count}))
            self.assertEqual(report['estimated'],original['estimated'])
        for count in (-1,2,True,'0'):
            with self.assertRaises(ModelSafetyError):
                self.check(metadata=dict(metadata,**{'split.count':count}))

    def test_llama_8b_on_16gb_intel_with_default_context_and_existing_apps(self):
        # Sparse 5 GiB file: filesystem length represents weights, no RAM allocation.
        with self.model.open('r+b') as f: f.truncate(5*GIB)
        from shared.core.hardware_profile import automatic_settings
        for gpu in (False,True):
            self.settings=automatic_settings(dict(system='Darwin',machine='x86_64',logical=8,
                physical=4,gpu=gpu,backend_info='METAL' if gpu else ''),self.model)
            report=self.check(memory=dict(total=16*GIB,available=6*GIB))
            self.assertLess(report['estimated'],report['budget'])
            self.assertIn('available',report['warnings'])
            self.assertEqual(report['context'],20000)
            self.assertTrue(self.settings['options']['use_mmap'])
            self.assertFalse(self.settings['options']['use_mlock'])
            self.assertIn('Achtung',safety.safety_warning(report))
            self.assertIn('Warning',safety.safety_warning(report,'en'))
            self.assertLess(self.check(context=2048)['estimated'],report['estimated'])

    def test_qwen_small_context_and_q2_quantizations_are_allowed(self):
        # Matches inspected Qwen35 27B architecture, weights rounded upward.
        meta={'general.architecture':'qwen35','qwen35.block_count':64,
              'qwen35.embedding_length':5120,'qwen35.attention.head_count':24,
              'qwen35.attention.head_count_kv':4,'qwen35.attention.key_length':256,
              'qwen35.attention.value_length':256}
        write_gguf(self.model,meta)
        self.settings['options'].update(use_mmap=False,flash_attn=False)
        for weights in (9,12): # IQ2 and Q2_K sized files
            with self.model.open('r+b') as f:f.truncate(weights*GIB)
            report=self.check(context=2048,memory=dict(total=24*GIB,available=5*GIB))
            self.assertLess(report['estimated'],report['budget'])
            self.assertEqual(report['kv_cache'],GIB//2)
            self.assertIn('mmap',report['warnings'])
            report=self.check(context=20000,memory=dict(total=24*GIB,available=5*GIB))
            self.assertLess(report['estimated'],report['budget'])
        with self.model.open('r+b') as f:f.truncate(9*GIB)
        self.assertLess(self.check(context=2048)['estimated'],16*GIB*99//100)

    def test_99_percent_is_the_only_memory_capacity_threshold(self):
        memory=dict(total=16*GIB,available=2*GIB)
        estimate=safety.estimate_model_memory(self.model,20000,self.settings['options'])
        budget=memory['total']*99//100
        with patch.object(safety,'estimate_model_memory',return_value=dict(estimate,estimated=budget)):
            self.assertEqual(self.check(memory=memory)['budget'],budget)
        with patch.object(safety,'estimate_model_memory',return_value=dict(estimate,estimated=budget+1)):
            with self.assertRaises(ModelSafetyError) as caught:self.check(memory=memory)
        self.assertEqual(caught.exception.reason,'capacity')
        for language,expected in [('de','99 %'),('en','99%')]:
            text=safety.safety_message(caught.exception,language)
            self.assertIn(expected,text)
            self.assertNotIn('Mindestreserve',text)
        self.assertIn('No automatic retry',safety.safety_message(caught.exception,'en'))

    def test_large_manual_attention_workspace_is_counted(self):
        before=self.check()['estimated']
        self.settings['options'].update(flash_attn=False,n_batch=8192,n_ubatch=8192)
        with self.assertRaises(ModelSafetyError) as caught:self.check()
        self.assertGreater(caught.exception.report['estimated'],before)

    def test_risky_options_warn_without_changing_or_blocking_them(self):
        for key,value,reason in [('use_mmap',False,'mmap'),('use_mlock',True,'mlock')]:
            original=self.settings['options'][key]
            self.settings['options'][key]=value
            before=copy.deepcopy(self.settings)
            report=self.check()
            self.assertIn(reason,report['warnings'])
            self.assertEqual(self.settings,before)
            self.settings['options'][key]=original
        self.settings['threads']=9
        self.assertIn('threads',self.check()['warnings'])
        self.assertEqual(self.settings['threads'],9)
        self.settings['threads']=4
        with patch.object(safety,'system_memory',return_value=None):
            report=self.check(memory=None)
        self.assertIn('memory_unknown',report['warnings'])
        self.assertIn('unavailable',safety.safety_warning(report,'en'))

    def test_critical_threshold_ignores_transient_and_absent_measurements(self):
        self.assertTrue(safety.critical_memory(dict(total=24*GIB,available=128*1024**2)))
        self.assertFalse(safety.critical_memory(dict(total=24*GIB,available=GIB)))
        self.assertFalse(safety.critical_memory(dict(total=24*GIB,available=3*GIB)))
        self.assertFalse(safety.critical_memory(dict(total=100*GIB,available=GIB)))
        self.assertTrue(safety.critical_memory(dict(total=100*GIB,available=GIB-1)))
        self.assertFalse(safety.critical_memory(None))

    def test_already_over_99_percent_stops_before_loading(self):
        with self.assertRaises(ModelSafetyError) as caught:
            self.check(memory=dict(total=16*GIB,available=0))
        self.assertEqual(caught.exception.reason,'memory_full')
        self.assertIn('already in use',safety.safety_message(caught.exception,'en'))

    def test_marker_persists_unconfirmed_attempt_and_is_cleared_on_success(self):
        with guarded_test_memory(self.root):
            self.assertIsNone(safety.previous_load_attempt())
            safety.mark_load_attempt('selected.gguf',20000)
            self.assertEqual(safety.previous_load_attempt()['model'],'selected.gguf')
            self.assertEqual(list(self.root.glob('.model-guard-*')),[])
            (self.root/'guard.json').write_text('{broken')
            self.assertIsNotNone(safety.previous_load_attempt())
            safety.clear_load_attempt();safety.clear_load_attempt()
            self.assertIsNone(safety.previous_load_attempt())

    def test_worker_gate_prevents_backend_and_never_saves_failed_selection(self):
        runtime=model_helpers.ModelSwitchPromptTests().runtime()
        runtime.shared.load_profile_settings.return_value={}
        hardware=dict(self.settings,platform='test',acceleration='CPU',gpu_layers=0)
        with guarded_test_memory(self.root), \
             patch('shared.core.hardware_profile.detect_hardware',return_value={}), \
             patch('shared.core.hardware_profile.automatic_settings',return_value=hardware), \
             patch('shared.core.backend_router.load_backend') as backend, \
             patch('shared.core.llm_loader.save_last_model_choice') as save, \
             patch('shared.core.llm_loader.save_perf'), patch('gui.game_worker.emit') as emit:
            with self.model.open('r+b') as f:f.truncate(24*GIB)
            with self.assertRaises(ModelSafetyError):runtime.load_model(str(self.model))
            backend.assert_not_called();save.assert_not_called()
            self.assertIsNone(safety.previous_load_attempt())
            write_gguf(self.model)
            hardware['options'].update(use_mmap=False,use_mlock=True)
            backend.side_effect=RuntimeError('Metal allocation failed')
            with self.assertRaises(RuntimeError):runtime.load_model(str(self.model))
            self.assertEqual(backend.call_count,1)
            self.assertFalse(backend.call_args.kwargs['allow_cpu_fallback'])
            save.assert_not_called()
            self.assertIsNotNone(safety.previous_load_attempt())
            backend.side_effect=None;backend.return_value={'chat_state':{'architecture':'llama'}}
            runtime.load_model(str(self.model))
            self.assertIsNone(safety.previous_load_attempt())
            save.assert_called_once()
            self.assertFalse(backend.call_args.kwargs['load_options']['use_mmap'])
            self.assertTrue(backend.call_args.kwargs['load_options']['use_mlock'])
            reports=[call.kwargs['data'] for call in emit.call_args_list if call.args==('model_safety',)]
            self.assertEqual(len(reports),2)
            self.assertIn('mmap',reports[-1]['warnings'])
            self.assertIn('mlock',reports[-1]['warnings'])

    def test_gui_backend_failure_has_no_automatic_cpu_allocation(self):
        from shared.core.llama_backend import load
        with patch('shared.core.llama_backend.Llama',side_effect=RuntimeError('Metal out of memory')) as backend:
            with self.assertRaises(RuntimeError):load('test.gguf',n_gpu_layers=-1,load_options={},allow_cpu_fallback=False)
            backend.assert_called_once()

    def test_generic_and_native_load_errors_are_english(self):
        from gui.model_errors import load_error,process_exit_error
        for error in (MemoryError(),PermissionError(),FileNotFoundError(),
                      ValueError('invalid magic'),RuntimeError('unknown model architecture'),RuntimeError('Metal failed')):
            message,_=load_error(error,'en')
            self.assertIn('The model cannot be loaded',message)
            self.assertNotIn('Wähle',message)
        self.assertIn('restored without a model',process_exit_error('en'))


class MemoryAPITests(unittest.TestCase):
    def test_linux_available_and_container_limit_exclude_swap(self):
        files={'/proc/meminfo':'MemTotal: 16777216 kB\nMemAvailable: 12582912 kB\nSwapFree: 99999999 kB',
               '/sys/fs/cgroup/memory.max':str(8*GIB),'/sys/fs/cgroup/memory.current':str(6*GIB)}
        with patch.object(safety.platform,'system',return_value='Linux'), \
             patch.object(Path,'read_text',lambda path:files[str(path)]), \
             patch.object(Path,'exists',return_value=True):
            self.assertEqual(safety.system_memory(),dict(total=8*GIB,available=2*GIB))

    def test_windows_native_memory_status(self):
        def memory_status(pointer):
            pointer._obj.total=16*GIB;pointer._obj.available=7*GIB
            return 1
        kernel=SimpleNamespace(GlobalMemoryStatusEx=memory_status)
        with patch.object(safety.platform,'system',return_value='Windows'), \
             patch.object(safety.ctypes,'windll',SimpleNamespace(kernel32=kernel),create=True):
            self.assertEqual(safety.system_memory(),dict(total=16*GIB,available=7*GIB))

    def test_mac_native_page_counts_and_unavailable_api(self):
        def statistics(host,flavor,words,count):
            self.assertEqual(flavor,4)
            words[0]=65536;words[1]=999999;words[2]=131072;words[3]=999999
            return 0
        lib=SimpleNamespace(host_statistics64=statistics)
        with patch.object(safety.platform,'system',return_value='Darwin'), \
             patch.object(safety,'_mac_memory_api',return_value=(lib,1,24*GIB,16384)):
            self.assertEqual(safety.system_memory(),dict(total=24*GIB,available=3*GIB))
        with patch.object(safety.platform,'system',return_value='Darwin'), \
             patch.object(safety,'_mac_memory_api',side_effect=OSError('unavailable')):
            self.assertIsNone(safety.system_memory())


class WatchdogTests(unittest.TestCase):
    def test_sustained_pressure_kills_only_owned_worker_and_is_idempotent(self):
        session=LiveSession();self.addCleanup(session.shutdown)
        owned=Mock();owned.state.return_value=QProcess.Running
        session.process=owned;session._loading_model='test.gguf'
        low=dict(total=24*GIB,available=128*1024**2);normal=dict(total=24*GIB,available=GIB)
        with patch.object(safety,'system_memory',side_effect=[low,normal,low,low]):
            for _ in range(3):session._check_model_memory()
            owned.kill.assert_not_called()
            session._check_model_memory()
            session._check_model_memory()
            owned.kill.assert_called_once()
        owned.state.return_value=QProcess.NotRunning
        self.assertFalse(session._memory_timer.isActive())

    def test_expected_shutdown_and_unloaded_session_do_not_kill(self):
        session=LiveSession();self.addCleanup(session.shutdown)
        owned=Mock();owned.state.return_value=QProcess.Running;session.process=owned
        with patch.object(safety,'system_memory',return_value=dict(total=24*GIB,available=0)):
            session._check_model_memory()
            session._loading_model='test.gguf';session._closing=True
            session._check_model_memory();session._check_model_memory()
        owned.kill.assert_not_called();owned.state.return_value=QProcess.NotRunning

    def test_memory_stop_recovers_real_empty_worker_without_reload(self):
        # Real process recovery, simulated pressure; no LLM is loaded.
        with tempfile.TemporaryDirectory(prefix='maat-memory-worker-') as folder, \
             patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':folder}):
            session=LiveSession();events=[];session.on_transport(events.append)
            def spin(condition):
                end=time.monotonic()+12
                while not condition() and time.monotonic()<end:APP.processEvents();time.sleep(.01)
                self.assertTrue(condition())
            try:
                session.start();spin(lambda:session.ready)
                original=session.process;session._active_model='fake.gguf'
                with patch.object(safety,'system_memory',return_value=dict(total=24*GIB,available=128*1024**2)):
                    session._check_model_memory();session._check_model_memory()
                spin(lambda:session.process is not original and session.ready)
                errors=[e for e in events if e['event']=='model_error']
                self.assertEqual(len(errors),1);self.assertIn('99 %',errors[0]['text'])
                self.assertIsNone(session._active_model);self.assertIsNone(session._loading_model)
                self.assertFalse(session._memory_timer.isActive())
                self.assertEqual(sum(e['event']=='ready' for e in events),2)
                session.send_command('/quests');spin(lambda:not session.busy)
            finally:session.shutdown()


class SafetyUITests(unittest.TestCase):
    setUp=language_helpers.LanguageTests.setUp
    close_windows=language_helpers.LanguageTests.close_windows
    window=language_helpers.LanguageTests.window
    ready=language_helpers.LanguageTests.ready

    def test_warnings_are_bilingual_and_allow_manual_loading(self):
        shared.write_application_language('de');shared.set_profile_name(1,'Warning test')
        window=self.window();self.ready(window)
        window.enter_menu();window.open_models()
        path=write_gguf(self.root/'warning.gguf')
        settings=dict(threads=9,threads_batch=9,options=dict(use_mmap=False,use_mlock=True))
        report=safety.check_model_safety(path,20000,settings,
            memory=dict(total=16*GIB,available=2*GIB),logical=8)
        window.model_combo.addItem(str(path));window.model_combo.setCurrentText(str(path))
        window.model_tuning.restore(dict(mode='manual',manual=dict(threads=9,threads_batch=9,
            use_mmap=False,use_mlock=True)))
        window.text_stream.finish()
        window.update_controls()
        self.assertTrue(window.load_button.isEnabled())
        for language,word in [('de','Achtung'),('en','Warning'),('de','Achtung')]:
            window.game.get_snapshot().language=language
            window.apply_menu_language()
            window.receive({'event':'model_safety','data':report})
            APP.processEvents()
            self.assertIn(word,window.memory_warning.text())
            self.assertIn(word,window.model_memory_status.text())
            self.assertTrue(window.model_memory_status.isVisible())
            self.assertFalse(window._model_error_pending)
            self.assertFalse(window._startup_model_failed)
            self.assertFalse(window.model_error.text())
            self.assertTrue(window.model_tuning.mmap.isEnabled())
            self.assertTrue(window.model_tuning.mlock.isEnabled())
            self.assertNotIn('must',window.model_tuning.mmap.toolTip())
            with patch.object(window.game,'load_model') as load:
                window.load_button.click();load.assert_called_once()
                manual=load.call_args.args[4]['manual']
                self.assertFalse(manual['use_mmap']);self.assertTrue(manual['use_mlock'])
                self.assertEqual(manual['threads'],9)
            target=os.environ.get('MAAT_SAFETY_PREVIEW')
            if target:
                window.model_scroll.verticalScrollBar().setValue(0)
                APP.processEvents()
                window.ki_dialog.grab().save(str(Path(target)/f'model-safety-99-{language}-20260912.png'))
        # Dynamic report also follows a language switch without a new load.
        window.game.get_snapshot().language='en';window.apply_menu_language()
        self.assertIn('Warning',window.model_memory_status.text())

    def test_crash_marker_blocks_startup_until_explicit_load_in_both_languages(self):
        for language in ('de','en'):
            shared.write_application_language(language);shared.set_profile_name(1,'Safe test')
            window=self.window();self.ready(window)
            window.phase='title';window._startup_model_attempted=False
            with patch.object(window.game,'load_model') as load:
                window.receive({'event':'models','items':['test.gguf'],'selected':'test.gguf',
                    'performance':{},'previous_load_attempt':{'model':'test.gguf'}})
                window.prepare_startup_model();window.prepare_startup_model()
                load.assert_not_called()
                self.assertIn('Automatisches Laden' if language=='de' else 'Automatic loading',window.model_error.text())
                window.phase='playing';window._auto_model_pending=True
                window.stream_drained();load.assert_not_called()
                window.load_model();load.assert_called_once()
            window.game.shutdown();window.close()
