"""Select optional x86 libraries on macOS/Linux, before importing llama_cpp."""
import importlib.util
import os
from pathlib import Path
import platform
import subprocess
import sys
from .gguf_adapters import intel_architecture


def cpu_features():
    try:
        if platform.system() == 'Darwin':
            text = subprocess.check_output(
                ['/usr/sbin/sysctl', '-n', 'machdep.cpu.features', 'machdep.cpu.leaf7_features'],
                text=True, stderr=subprocess.DEVNULL, timeout=2)
            return set(text.upper().replace('AVX1.0', 'AVX').split())
        if platform.system() == 'Linux':
            sets = [set(line.split(':', 1)[1].upper().split())
                    for line in Path('/proc/cpuinfo').read_text().splitlines()
                    if line.split(':', 1)[0].strip() == 'flags']
            return set.intersection(*sets) if sets else set()
    except (OSError, subprocess.SubprocessError):
        pass
    return set()


def prepare_library():
    if not intel_architecture() or 'llama_cpp' in sys.modules or os.environ.get('LLAMA_CPP_LIB_PATH'):
        return
    spec = importlib.util.find_spec('llama_cpp')
    if spec is None or not spec.origin:
        return
    root = Path(spec.origin).parent/'lib'
    suffix = '.dylib' if platform.system() == 'Darwin' else '.so'
    optimized = root/'avx2'
    if (optimized/('libllama'+suffix)).is_file() and {'AVX', 'AVX2', 'FMA', 'F16C', 'BMI2'} <= cpu_features():
        os.environ['LLAMA_CPP_LIB_PATH'] = str(optimized)
        os.environ['MAAT_CPU_VARIANT'] = 'avx2'


def physical_threads(fallback):
    """Respect Linux CPU affinity and physical topology, including containers."""
    if platform.system() == 'Linux':
        try:
            allowed = os.sched_getaffinity(0)
            cores = set()
            for cpu in allowed:
                root = Path('/sys/devices/system/cpu')/f'cpu{cpu}'/'topology'
                cores.add(((root/'physical_package_id').read_text().strip(),
                           (root/'core_id').read_text().strip()))
            if cores:
                return len(cores)
        except (OSError, AttributeError):
            pass
    return max(1, int(fallback))
