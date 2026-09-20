"""Choose a bundled Intel CPU library before anything imports llama_cpp."""
import os
import platform
from pathlib import Path
import subprocess


def supports_avx2(features):
    tokens = set(features.upper().split())
    return {'AVX2', 'FMA', 'F16C', 'BMI2'}.issubset(tokens) and bool(tokens & {'AVX1.0', 'AVX'})


def select_library():
    if platform.machine().lower() != 'x86_64' or os.environ.get('LLAMA_CPP_LIB_PATH'):
        return
    root = Path(__file__).resolve().parent.parent / 'x86_64/lib/python3.11/site-packages/llama_cpp/lib'
    os.environ['MAAT_CPU_VARIANT'] = 'portable'
    if not (root / 'avx2/libllama.dylib').is_file():
        return
    try:
        features = subprocess.check_output(
            ['/usr/sbin/sysctl', '-n', 'machdep.cpu.features', 'machdep.cpu.leaf7_features'],
            text=True, stderr=subprocess.DEVNULL, timeout=2)
        if supports_avx2(features):
            os.environ['LLAMA_CPP_LIB_PATH'] = str(root / 'avx2')
            os.environ['MAAT_CPU_VARIANT'] = 'avx2'
    except (OSError, subprocess.SubprocessError):
        pass  # Older CPUs and restricted hosts retain the compatible library.


select_library()
