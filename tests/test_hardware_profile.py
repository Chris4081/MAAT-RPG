import unittest
from unittest.mock import patch, MagicMock
from test_desktop import APP
from shared.core.hardware_profile import automatic_settings
from shared.core.llama_backend import load

class HardwareTests(unittest.TestCase):
    def test_mtl_backend_enables_flash_attention_without_overriding_manual_choice(self):
        from shared.core.model_settings import resolve_settings
        hardware=dict(system='Darwin',machine='arm64',logical=10,physical=5,gpu=True,
            backend_info='MTL : EMBED_LIBRARY = 1 | CPU : NEON = 1 | ACCELERATE = 1 |')
        automatic=automatic_settings(hardware,'Qwen3.6-27B-UD-IQ2_XXS.gguf')
        self.assertEqual(automatic['acceleration'],'METAL')
        self.assertTrue(automatic['options']['flash_attn'])
        self.assertEqual(automatic['gpu_layers'],-1)
        self.assertTrue(automatic['options']['offload_kqv'])
        self.assertTrue(automatic['options']['op_offload'])
        manual_cpu=resolve_settings(automatic,{'mode':'manual','manual':{'gpu_layers':0}})
        self.assertFalse(manual_cpu['options']['offload_kqv'])
        self.assertFalse(manual_cpu['options']['op_offload'])
        self.assertTrue(resolve_settings(automatic,{'mode':'manual','manual':{'flash_attn':'auto'}})['options']['flash_attn'])
        self.assertFalse(resolve_settings(automatic,{'mode':'manual','manual':{'flash_attn':'off'}})['options']['flash_attn'])
        hardware['gpu']=False
        cpu=automatic_settings(hardware,'Qwen3.6-27B.gguf')
        self.assertEqual(cpu['acceleration'],'CPU')
        self.assertFalse(cpu['options']['flash_attn'])

    def test_platform_matrix(self):
        for system,machine,gpu,info in [('Darwin','arm64',True,'METAL = 1'),('Darwin','x86_64',False,''),('Linux','x86_64',True,'CUDA = 1'),('Linux','aarch64',False,''),('Windows','AMD64',True,'VULKAN = 1'),('Windows','AMD64',False,'')]:
            with self.subTest(system=system,machine=machine,gpu=gpu):
                s=automatic_settings(dict(system=system,machine=machine,logical=12,physical=6,gpu=gpu,backend_info=info),'llama.gguf')
                self.assertEqual(s['gpu_layers'],-1 if gpu else 0)
                self.assertEqual(s['threads'],9)
                self.assertEqual(s['options']['n_threads_batch'],12)
                self.assertTrue(s['options']['use_mmap'])
        s=automatic_settings(dict(system='Darwin',machine='arm64',logical=10,physical=4,gpu=True,backend_info='METAL = 1'),'gemma-4.gguf')
        self.assertEqual(s['options']['n_ubatch'],64)
        self.assertTrue(s['options']['flash_attn'])

    def test_generation_thread_budget(self):
        for logical,expected in [(1,1),(2,1),(4,3),(8,6),(10,8),(12,9),(16,12),(32,25)]:
            with self.subTest(logical=logical):
                settings=automatic_settings(dict(system='Darwin',machine='arm64',logical=logical,physical=4,gpu=True,backend_info='METAL = 1'),'llama.gguf')
                self.assertEqual(settings['threads'],expected)
                self.assertEqual(settings['threads_batch'],logical)
                self.assertEqual(settings['options']['n_threads_batch'],logical)

    def test_cpu_fallback_keeps_requested_context(self):
        instance=MagicMock()
        with patch('shared.core.llama_backend.Llama',side_effect=[ValueError('Failed to create llama_context'),instance]) as llama, patch('shared.core.llama_backend.configure_template',return_value={}):
            result=load('llama.gguf',n_ctx=20000,n_gpu_layers=-1,load_options={'use_mmap':True,'n_batch':512})
        self.assertEqual(llama.call_count,2)
        self.assertEqual(llama.call_args.kwargs['n_ctx'],20000)
        self.assertEqual(llama.call_args.kwargs['n_gpu_layers'],0)
        self.assertEqual(result['load_settings']['n_gpu_layers'],0)
        self.assertIsNotNone(result['hardware_fallback'])

    def test_invalid_model_does_not_retry(self):
        with patch('shared.core.llama_backend.Llama',side_effect=ValueError('Invalid model file')) as llama:
            with self.assertRaises(ValueError):load('bad.gguf',n_gpu_layers=-1,load_options={'use_mmap':True})
        self.assertEqual(llama.call_count,1)
