"""Intel library selection must require every compiled instruction set."""
import os
from pathlib import Path
import runpy
import subprocess
import unittest
from unittest.mock import patch

SELECTOR = Path(__file__).resolve().parents[1] / 'packaging/macos/sitecustomize.py'


class IntelBackendSelectionTests(unittest.TestCase):
    def setUp(self):
        with patch('platform.machine', return_value='arm64'):
            self.module = runpy.run_path(str(SELECTOR))

    def test_requires_all_compiled_instructions(self):
        features = ['SSE4.2', 'AVX1.0', 'AVX2', 'FMA', 'F16C', 'BMI2']
        supports = self.module['supports_avx2']
        self.assertTrue(supports(' '.join(features).lower()))
        for required in features[1:]:
            with self.subTest(missing=required):
                self.assertFalse(supports(' '.join(f for f in features if f != required)))

    def test_supported_intel_selects_optimized_library(self):
        with patch.dict(os.environ, {}, clear=True), patch('platform.machine', return_value='x86_64'), \
                patch('pathlib.Path.is_file', return_value=True), \
                patch('subprocess.check_output', return_value='AVX1.0 FMA F16C\nAVX2 BMI2'):
            self.module['select_library']()
            self.assertEqual(os.environ['MAAT_CPU_VARIANT'], 'avx2')
            self.assertTrue(os.environ['LLAMA_CPP_LIB_PATH'].endswith('/llama_cpp/lib/avx2'))

    def test_older_cpu_or_probe_failure_keeps_portable(self):
        for result in ['SSE4.2', subprocess.CalledProcessError(1, 'sysctl'), OSError('unavailable')]:
            with self.subTest(result=result), patch.dict(os.environ, {}, clear=True), \
                    patch('platform.machine', return_value='x86_64'), \
                    patch('pathlib.Path.is_file', return_value=True), \
                    patch('subprocess.check_output') as probe:
                if isinstance(result, Exception):
                    probe.side_effect = result
                else:
                    probe.return_value = result
                self.module['select_library']()
                self.assertEqual(os.environ['MAAT_CPU_VARIANT'], 'portable')
                self.assertNotIn('LLAMA_CPP_LIB_PATH', os.environ)

    def test_arm_and_explicit_library_are_preserved(self):
        for arch, settings in [('arm64', {}), ('x86_64', {'LLAMA_CPP_LIB_PATH': '/custom/lib'})]:
            with patch.dict(os.environ, settings, clear=True), \
                    patch('platform.machine', return_value=arch), patch('subprocess.check_output') as probe:
                self.module['select_library']()
                probe.assert_not_called()
                self.assertEqual(dict(os.environ), settings)


if __name__ == '__main__':
    unittest.main()
