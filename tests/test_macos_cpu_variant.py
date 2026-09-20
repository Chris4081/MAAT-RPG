import importlib.util
import unittest
import os
from pathlib import Path
from unittest.mock import patch

path=Path(__file__).resolve().parents[1]/'packaging/macos/sitecustomize.py'
spec=importlib.util.spec_from_file_location('maat_cpu_selection',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class CpuVariantTests(unittest.TestCase):
    def test_requires_every_instruction_used_by_optimized_binary(self):
        features='SSE SSE2 SSE4.1 AVX1.0 F16C FMA BMI1 BMI2 AVX2'
        self.assertTrue(module.supports_avx2(features))
        for required in ('AVX1.0','F16C','FMA','BMI2','AVX2'):
            self.assertFalse(module.supports_avx2(features.replace(required,'')),required)
        self.assertFalse(module.supports_avx2(''))

    def test_supported_intel_selects_optimized_library_before_model_import(self):
        expected = path.parent.parent/'x86_64/lib/python3.11/site-packages/llama_cpp/lib/avx2'
        with patch.dict(os.environ, {}, clear=True), patch.object(module.platform, 'machine', return_value='x86_64'), \
             patch.object(module.Path, 'is_file', return_value=True), \
             patch.object(module.subprocess, 'check_output', return_value='AVX1.0 AVX2 FMA F16C BMI2'):
            module.select_library()
            self.assertEqual(os.environ['MAAT_CPU_VARIANT'], 'avx2')
            self.assertEqual(Path(os.environ['LLAMA_CPP_LIB_PATH']), expected)
            # A child inherits both fields and must keep the selected library.
            with patch.object(module.subprocess, 'check_output', side_effect=AssertionError('must preserve inherited library')):
                module.select_library()
            self.assertEqual(os.environ['MAAT_CPU_VARIANT'], 'avx2')

    def test_older_cpu_and_failed_detection_keep_portable_library(self):
        for answer in ('SSE3 SSSE3 SSE4.1 AVX1.0', OSError('sysctl unavailable')):
            with self.subTest(answer=answer), patch.dict(os.environ, {}, clear=True), \
                 patch.object(module.platform, 'machine', return_value='x86_64'), \
                 patch.object(module.Path, 'is_file', return_value=True), \
                 patch.object(module.subprocess, 'check_output') as query:
                if isinstance(answer, Exception): query.side_effect=answer
                else: query.return_value=answer
                module.select_library()
                self.assertEqual(os.environ['MAAT_CPU_VARIANT'], 'portable')
                self.assertNotIn('LLAMA_CPP_LIB_PATH', os.environ)

    def test_arm_and_explicit_library_override_are_preserved(self):
        for machine, initial in [('arm64', {}), ('x86_64', {'LLAMA_CPP_LIB_PATH':'/custom/llama'})]:
            with self.subTest(machine=machine), patch.dict(os.environ, initial, clear=True), \
                 patch.object(module.platform, 'machine', return_value=machine), \
                 patch.object(module.subprocess, 'check_output', side_effect=AssertionError('no CPU probe needed')):
                module.select_library()
                self.assertEqual(dict(os.environ), initial)
