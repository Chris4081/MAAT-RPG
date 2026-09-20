"""Exercise the GUI-to-router-to-llama boundary without allocating a real model."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from gguf_fixtures import write_gguf, guarded_test_memory
import test_model_switch_prompt as helpers


class BackendRouteTests(unittest.TestCase):
    def test_gui_router_preserves_effective_settings_and_ignores_dormant_options(self):
        cases = [
            # Dormant settings from an Apple profile must not leak into Intel Auto.
            ('x86_64', False, 'auto', False, True, 'on', 0, 256, 128, False, True, False),
            ('arm64', True, 'auto', False, True, 'off', -1, 512, 128, True, True, False),
            # Explicit manual choices are honored; a CPU-only build still uses zero GPU layers.
            ('x86_64', False, 'manual', False, True, 'on', 0, 128, 32, True, False, True),
        ]
        for machine, gpu, mode, mmap, mlock, flash, layers, batch, ubatch, expected_fa, expected_mmap, expected_mlock in cases:
            with self.subTest(machine=machine, mode=mode), tempfile.TemporaryDirectory() as folder:
                runtime = helpers.ModelSwitchPromptTests().runtime()
                tuning = dict(mode=mode, manual=dict(
                    threads=3, threads_batch=5, gpu_layers=-1, n_batch=128, n_ubatch=32,
                    use_mmap=mmap, use_mlock=mlock, flash_attn=flash))
                runtime.shared.load_profile_settings.return_value = {'gui_model_tuning': tuning}
                hardware = dict(system='Darwin', machine=machine, logical=8, physical=4,
                                gpu=gpu, backend_info='MTL : EMBED_LIBRARY = 1' if gpu else 'CPU : ACCELERATE = 1')
                model = Path(folder)/'llama.gguf'
                write_gguf(model)
                intel = machine == 'x86_64'
                target = 'shared.core.intel_binding.IntelLlama' if intel else 'shared.core.llama_backend.Llama'
                with guarded_test_memory(folder), \
                     patch('shared.core.gguf_adapters.platform.machine', return_value=machine), \
                     patch('shared.core.hardware_profile.detect_hardware', return_value=hardware), \
                     patch(target, return_value=Mock(intel_repacking=False)) as native, \
                     patch('shared.core.gguf_chat.configure_template' if intel else 'shared.core.llama_backend.configure_template', return_value={}), \
                     patch('shared.core.llm_loader.save_last_model_choice'), \
                     patch('shared.core.llm_loader.save_perf'), \
                     patch('gui.game_worker.emit'), patch('gui.game_worker.diagnostic') as log:
                    # GUI only accepts GGUF, so even a stale MLX preference uses llama.cpp.
                    runtime.load_model(str(model), backend='mlx', n_ctx=100000)
                native.assert_called_once()
                options = native.call_args.kwargs
                self.assertEqual(options['n_ctx'], 100000)
                self.assertEqual(runtime.perf['n_ctx'],100000)
                self.assertEqual(options['n_gpu_layers'], layers)
                self.assertEqual(options['n_threads'], 3 if mode == 'manual' else 4 if intel else 6)
                self.assertEqual(options['n_threads_batch'], 5 if mode == 'manual' else 8)
                self.assertEqual((options['n_batch'], options['n_ubatch']), (batch, ubatch))
                self.assertEqual(options['flash_attn'], expected_fa)
                self.assertEqual(options['use_mmap'], expected_mmap)
                self.assertEqual(options['use_mlock'], expected_mlock)
                self.assertFalse(options['logits_all'])
                self.assertFalse(options['embedding'])
                self.assertEqual(runtime.llm['backend'], 'llama_intel' if intel else 'llama')
                loaded = next(c.kwargs for c in log.call_args_list if c.args == ('model_backend_loaded',))
                self.assertEqual(loaded['settings']['n_ubatch'], ubatch)
                self.assertIsNone(loaded['fallback'])

    def test_gui_allocation_error_does_not_retry_with_another_backend(self):
        from shared.core.backend_router import load_backend
        with patch('shared.core.llama_backend.Llama', side_effect=RuntimeError('context allocation failed')) as native, \
             patch('shared.core.backend_router.mlx_supported', return_value=True):
            with self.assertRaisesRegex(RuntimeError, 'context allocation failed'):
                load_backend('llama.gguf', backend='llama', max_ctx=20000,
                             n_gpu_layers=-1, load_options={'use_mmap': True}, allow_cpu_fallback=False)
        native.assert_called_once()
