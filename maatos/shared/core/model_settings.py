"""Saved user preferences and validated llama.cpp overrides, independent of Qt."""
import os
from copy import deepcopy

DEFAULT_CONTEXT = 20000
MAX_CONTEXT = 100000
MIN_CONTEXT = 1024


def normalize_context(value):
    return max(MIN_CONTEXT, min(MAX_CONTEXT, int(value)))

INTEGER_LIMITS = {
    'threads': (1, 1024), 'threads_batch': (1, 1024),
    'gpu_layers': (-1, 999), 'n_batch': (1, 8192), 'n_ubatch': (1, 8192),
}


def manual_defaults():
    logical = max(1, min(1024, os.cpu_count() or 1))
    return dict(threads=max(1, logical * 4 // 5), threads_batch=logical,
                gpu_layers=-1, n_batch=256, n_ubatch=64,
                flash_attn='auto', use_mmap=True, use_mlock=False, repack_weights=False)


def normalize_tuning(value):
    """Old profiles stay automatic; malformed saved fields get safe defaults."""
    value = value if isinstance(value, dict) else {}
    source = value.get('manual', {})
    source = source if isinstance(source, dict) else {}
    manual = manual_defaults()
    for key, (low, high) in INTEGER_LIMITS.items():
        candidate = source.get(key)
        if isinstance(candidate, int) and not isinstance(candidate, bool):
            manual[key] = max(low, min(high, candidate))
    manual['n_ubatch'] = min(manual['n_ubatch'], manual['n_batch'])
    for key in ('use_mmap', 'use_mlock', 'repack_weights'):
        if isinstance(source.get(key), bool):
            manual[key] = source[key]
    if source.get('flash_attn') in ('auto', 'on', 'off'):
        manual['flash_attn'] = source['flash_attn']
    return dict(mode='manual' if value.get('mode') == 'manual' else 'auto', manual=manual)


def resolve_settings(automatic, tuning, n_ctx=20000):
    """Never let a dormant manual preset override automatic hardware detection."""
    selected = normalize_tuning(tuning)
    result = deepcopy(automatic)
    result['mode'] = selected['mode']
    result['adjustments'] = []
    if selected['mode'] == 'auto':
        return result
    manual = selected['manual']
    result['threads'] = manual['threads']
    result['threads_batch'] = manual['threads_batch']
    # CPU-only builds cannot offload, even if a profile came from another Mac.
    result['gpu_layers'] = manual['gpu_layers'] if automatic['gpu_layers'] != 0 else 0
    if result['gpu_layers'] == 0:
        result['acceleration'] = 'CPU'
    if automatic['gpu_layers'] == 0 and manual['gpu_layers'] != 0:
        result['adjustments'].append('gpu_unavailable')
    batch = min(manual['n_batch'], max(1, int(n_ctx)))
    ubatch = min(manual['n_ubatch'], batch)
    result['options'].update(n_threads_batch=manual['threads_batch'],
                             n_batch=batch, n_ubatch=ubatch,
                             use_mmap=manual['use_mmap'], use_mlock=manual['use_mlock'])
    if batch != manual['n_batch']:
        result['adjustments'].append('batch_capped')
    if manual['flash_attn'] != 'auto':
        result['options']['flash_attn'] = manual['flash_attn'] == 'on'
    if result['gpu_layers'] == 0:
        for key in ('offload_kqv', 'op_offload'):
            if key in result['options']:
                result['options'][key] = False
    if automatic.get('adapter') == 'llama_intel':
        result['options']['repack_weights'] = manual['repack_weights']
    return result
