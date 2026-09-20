"""Hardware visibility, dedicated allocation, native defaults and streaming."""
import contextlib
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
from shared.core.gguf_adapters import available_adapters, selected_adapter
from shared.core.intel_gguf_backend import automatic_settings, load
from shared.core.intel_binding import IntelLlama, _ModelDefaults
from shared.core.model_settings import resolve_settings


class IntelAdapterTests(unittest.TestCase):
    def test_only_matching_adapter_visible(self):
        for machine, expected in [('x86_64','llama_intel'),('AMD64','llama_intel'),
                                  ('arm64','llama'),('aarch64','llama')]:
            with self.subTest(machine=machine):
                self.assertEqual(len(available_adapters(machine)), 1)
                self.assertEqual(selected_adapter(machine), expected)

    def test_intel_defaults_and_manual_repacking(self):
        for system in ('Darwin', 'Linux'):
            hardware=dict(system=system,machine='x86_64',logical=8,physical=4,gpu=True,
                          backend_info='CPU : AVX = 1 | AVX2 = 1 | ACCELERATE = 1')
            with patch('shared.core.intel_gguf_backend.physical_threads',return_value=4):
                auto=automatic_settings(hardware, 'Llama-8B.gguf')
            self.assertEqual(auto['threads'],4)
            self.assertEqual(auto['threads_batch'],8)
            self.assertEqual(auto['gpu_layers'],0)
            self.assertEqual(auto['options']['n_ubatch'],128)
            self.assertFalse(auto['options']['repack_weights'])
            self.assertFalse(auto['options']['offload_kqv'])
            self.assertFalse(auto['options']['op_offload'])
            self.assertIn('AVX2',auto['acceleration'])
            selected=resolve_settings(auto,{'mode':'auto','manual':{'use_mmap':False,'repack_weights':True}})
            self.assertTrue(selected['options']['use_mmap'])
            self.assertFalse(selected['options']['repack_weights'])
            selected=resolve_settings(auto,{'mode':'manual','manual':{'threads':2,'gpu_layers':-1,'repack_weights':True}})
            self.assertEqual(selected['threads'],2)
            self.assertEqual(selected['gpu_layers'],0)
            self.assertTrue(selected['options']['repack_weights'])

    def test_constructor_proxy_is_per_instance_and_preserves_original_api(self):
        from llama_cpp import Llama
        api=SimpleNamespace(llama_model_default_params=lambda:SimpleNamespace(use_extra_bufts=True), marker=42)
        scope={'llama_cpp':api,'contextlib':contextlib}
        exec("def init(self, *, option='kept'):\n self.model_params=llama_cpp.llama_model_default_params()\n self.marker=llama_cpp.marker\n self.option=option\n self._stack=contextlib.ExitStack()\n",scope)
        original=scope['init']
        with patch.object(Llama,'__init__',original):
            first=IntelLlama(repack_weights=False)
            second=IntelLlama(repack_weights=True,option='manual')
        self.assertFalse(first.intel_repacking)
        self.assertTrue(second.intel_repacking)
        self.assertEqual((first.option,second.option),('kept','manual'))
        self.assertEqual(first.marker,42)
        self.assertIs(original.__globals__['llama_cpp'],api)
        self.assertTrue(api.llama_model_default_params().use_extra_bufts)
        first.close();second.close()

    def test_native_defaults_not_modified_globally(self):
        from llama_cpp import llama_cpp
        original=llama_cpp.llama_model_default_params
        before=original()
        proxy=_ModelDefaults(llama_cpp,False)
        changed=proxy.llama_model_default_params()
        if hasattr(before,'use_extra_bufts'):
            self.assertFalse(changed.use_extra_bufts)
            self.assertEqual(original().use_extra_bufts,before.use_extra_bufts)
        self.assertIs(llama_cpp.llama_model_default_params,original)
        self.assertIs(proxy.llama_context_default_params,llama_cpp.llama_context_default_params)

    def test_native_load_is_cpu_only_and_closes_on_template_error(self):
        instance=Mock(intel_repacking=False)
        with patch('shared.core.intel_gguf_backend.intel_architecture',return_value=True), \
             patch('shared.core.intel_binding.IntelLlama',return_value=instance) as native, \
             patch('shared.core.gguf_chat.configure_template',return_value={'architecture':'llama'}):
            model=load('test.gguf',n_ctx=20000,n_gpu_layers=-1,load_options={'op_offload':True})
        self.assertEqual(model['backend'],'llama_intel')
        self.assertEqual(native.call_args.kwargs['n_ctx'],20000)
        self.assertEqual(native.call_args.kwargs['n_gpu_layers'],0)
        self.assertFalse(native.call_args.kwargs['op_offload'])
        with patch('shared.core.intel_gguf_backend.intel_architecture',return_value=True), \
             patch('shared.core.intel_binding.IntelLlama',return_value=instance), \
             patch('shared.core.gguf_chat.configure_template',side_effect=ValueError('bad template')):
            with self.assertRaises(ValueError):load('test.gguf')
        instance.close.assert_called_once()

    def test_ui_exposes_intel_controls_and_translates(self):
        from gui.model_tuning import ModelTuningPanel
        with patch('shared.core.gguf_adapters.platform.machine',return_value='x86_64'):
            panel=ModelTuningPanel()
        panel.show();panel.mode.setCurrentIndex(1)
        try:
            self.assertFalse(panel.repack.isHidden())
            self.assertFalse(panel.fields['gpu_layers'].isEnabled())
            self.assertFalse(panel.settings()['manual']['repack_weights'])
            panel.repack.setChecked(True)
            self.assertTrue(panel.settings()['manual']['repack_weights'])
            panel.set_language('en')
            self.assertIn('rearrange model weights',panel.repack.text())
            self.assertIn('extra time',panel.repack.toolTip())
        finally:
            panel.close();panel.deleteLater();APP.processEvents()

    def test_stream_keeps_router_and_chat_contract(self):
        from shared.core.backend_router import stream_chat
        model={'backend':'llama_intel','instance':object()}
        messages=[{'role':'system','content':'MAAT identity and memories'},{'role':'user','content':'Hello'}]
        perf={'max_tokens':30}
        with patch('shared.core.llama_backend.stream_chat',return_value=iter(['Hello','!'])) as stream:
            self.assertEqual(list(stream_chat(model,messages,perf)),['Hello','!'])
        stream.assert_called_once_with(model,messages,perf)

    def test_linux_library_selection_and_affinity(self):
        from shared.core import intel_runtime as runtime
        with patch.dict(os.environ,{},clear=True), patch.object(runtime,'intel_architecture',return_value=True), \
             patch.dict(runtime.sys.modules,{'llama_cpp':None}):
            # Already-imported native code is never switched in a live process.
            runtime.prepare_library()
            self.assertNotIn('LLAMA_CPP_LIB_PATH',os.environ)
        with patch.object(runtime.platform,'system',return_value='Linux'), \
             patch.object(runtime.os,'sched_getaffinity',return_value={2,3},create=True), \
             patch.object(Path,'read_text',return_value='1'):
            self.assertEqual(runtime.physical_threads(8),1)

    def test_linux_selects_only_a_supported_installed_avx2_library(self):
        from shared.core import intel_runtime as runtime
        for flags, expected in [({'AVX','AVX2','FMA','F16C','BMI2'}, True), ({'AVX'}, False)]:
            with self.subTest(flags=flags), patch.dict(os.environ,{},clear=True), \
                 patch.object(runtime,'intel_architecture',return_value=True), \
                 patch.object(runtime.sys,'modules',{}), \
                 patch.object(runtime.platform,'system',return_value='Linux'), \
                 patch.object(runtime.importlib.util,'find_spec',return_value=SimpleNamespace(origin='/venv/llama_cpp/__init__.py')), \
                 patch.object(Path,'is_file',return_value=True), \
                 patch.object(runtime,'cpu_features',return_value=flags):
                runtime.prepare_library()
                self.assertEqual('LLAMA_CPP_LIB_PATH' in os.environ,expected)
                if expected:self.assertEqual(os.environ['LLAMA_CPP_LIB_PATH'],'/venv/llama_cpp/lib/avx2')
