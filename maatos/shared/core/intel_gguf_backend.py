"""Dedicated CPU GGUF adapter for x86-64 macOS and Linux."""
import re
from .gguf_adapters import intel_architecture
from .intel_runtime import prepare_library, physical_threads


def automatic_settings(hardware, model_path):
    logical = max(1, int(hardware['logical']))
    physical = min(logical, physical_threads(hardware.get('physical', logical)))
    # Generation is usually memory-bandwidth bound; avoid automatically
    # oversubscribing physical cores with Hyper-Threading workers.
    threads = min(physical, max(1, logical * 4 // 5))
    info = hardware.get('backend_info', '').upper()
    features = [name for name in ('AVX2', 'AVX', 'ACCELERATE', 'BLAS')
                if re.search(r'\b' + name + r'\s*(?:=\s*1|:)', info)]
    gemma4 = 'gemma-4' in str(model_path).lower() or 'gemma4' in str(model_path).lower()
    return dict(platform='Mac Intel' if hardware['system'] == 'Darwin' else f"{hardware['system']} Intel",
                adapter='llama_intel', acceleration='CPU' + (' · ' + ' · '.join(features) if features else ''),
                threads=threads, threads_batch=logical, gpu_layers=0,
                options=dict(use_mmap=True, use_mlock=False, n_batch=256,
                             n_ubatch=64 if gemma4 else 128, n_threads_batch=logical,
                             flash_attn=gemma4, offload_kqv=False, op_offload=False,
                             repack_weights=False))


def load(model_path, n_ctx=20000, temperature=.7, n_threads=4,
         n_gpu_layers=0, load_options=None, allow_cpu_fallback=False):
    if not intel_architecture():
        raise ValueError('GGUF (Intel) requires an x86-64 processor.')
    prepare_library()
    from .intel_binding import IntelLlama
    from .gguf_chat import configure_template
    options = dict(use_mmap=True, use_mlock=False, n_batch=256, n_ubatch=128,
                   flash_attn=False, repack_weights=False)
    options.update(load_options or {})
    # This adapter is explicitly CPU-based, even with a CUDA/Metal-capable
    # Python installation or a manual preset copied from another computer.
    options.update(offload_kqv=False, op_offload=False)
    kwargs = dict(model_path=str(model_path), n_ctx=n_ctx, n_threads=n_threads,
                  n_gpu_layers=0, logits_all=False, embedding=False, verbose=False, **options)
    inst = IntelLlama(**kwargs)
    try:
        chat_state = configure_template(inst)
    except Exception:
        inst.close()
        raise
    settings = {k:v for k,v in kwargs.items() if k != 'model_path'}
    settings['repack_weights'] = inst.intel_repacking
    return dict(backend='llama_intel', instance=inst, n_ctx=n_ctx, temperature=temperature,
                chat_state=chat_state, load_settings=settings, hardware_fallback=None)


def stream_chat(llm, messages, perf=None):
    # Share the established template, cancellation and token-normalization
    # contract, while model allocation belongs exclusively to this adapter.
    from .llama_backend import stream_chat as stream
    yield from stream(llm, messages, perf)
