"""Conservative automatic llama.cpp settings; no platform-specific dependency required."""
import os
import platform
import re
import subprocess
from .native_diagnostics import quiet_metal_startup


@quiet_metal_startup
def detect_hardware():
    system, machine = platform.system(), platform.machine().lower()
    logical = os.cpu_count() or 1
    physical = None
    if hasattr(os, 'sched_getaffinity'):
        logical = min(logical, len(os.sched_getaffinity(0)))
    try:
        import psutil
        physical = psutil.cpu_count(logical=False)
    except ImportError:
        pass
    if system == 'Darwin':
        key = 'hw.perflevel0.physicalcpu' if machine in ('arm64','aarch64') else 'hw.physicalcpu'
        try:
            physical = int(subprocess.check_output(['sysctl','-n',key], stderr=subprocess.DEVNULL, timeout=2).strip())
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    from llama_cpp import llama_cpp
    try:
        gpu = bool(llama_cpp.llama_supports_gpu_offload())
        info = llama_cpp.llama_print_system_info().decode('utf-8', 'replace')
    except (AttributeError, OSError):
        gpu, info = False, ''
    return dict(system=system, machine=machine, logical=logical,
                physical=max(1,min(logical,physical or max(1,logical//2))), gpu=gpu, backend_info=info,
                library_path=str(getattr(getattr(llama_cpp, '_lib', None), '_name', '')))


def automatic_settings(hardware, model_path):
    system, machine = hardware['system'], hardware['machine']
    arm = machine in ('arm64','aarch64')
    platform_name = ('Mac ARM' if arm else 'Mac Intel') if system == 'Darwin' else f'{system} {machine}'
    gpu = hardware['gpu']
    info = hardware.get('backend_info','').upper()
    # llama.cpp also reports Apple's backend as "MTL : ...". Recognize its
    # real name so Metal's automatic Flash Attention setting is applied.
    if re.search(r'\bMTL\s*:', info):
        info += ' METAL'
    acceleration = next((name for name in ('METAL','CUDA','VULKAN','SYCL','HIP','ROCM') if name in info), 'GPU-Backend') if gpu else 'CPU'
    gemma4 = 'gemma-4' in str(model_path).lower() or 'gemma4' in str(model_path).lower()
    result = dict(platform=platform_name, acceleration=acceleration,
                # Use 80% of available logical CPU threads for generation.
                threads=max(1, hardware['logical'] * 4 // 5), threads_batch=hardware['logical'],
                gpu_layers=-1 if gpu else 0,
                options=dict(use_mmap=True, use_mlock=False,
                             n_batch=128 if gemma4 else 512 if gpu else 256,
                             n_ubatch=64 if gemma4 else 128 if gpu else 64,
                             flash_attn=gemma4 or (gpu and acceleration in ('METAL','CUDA')),
                             n_threads_batch=hardware['logical']))
    if system == 'Darwin' and arm and acceleration == 'METAL':
        result['options'].update(offload_kqv=True, op_offload=True)
    return result
