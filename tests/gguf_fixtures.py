"""Metadata-only GGUFs for mocked backends; never real model weights."""
from contextlib import contextmanager
from pathlib import Path
import struct
from unittest.mock import patch


def write_gguf(path, metadata=None):
    metadata = metadata if metadata is not None else {
        'general.architecture': 'llama', 'llama.block_count': 32,
        'llama.embedding_length': 4096, 'llama.attention.head_count': 32,
        'llama.attention.head_count_kv': 8,
        'tokenizer.ggml.tokens': ['hello', 'world', 'ä'],
    }
    def string(value):
        raw = value.encode('utf-8')
        return struct.pack('<Q', len(raw)) + raw
    def value(item):
        if isinstance(item, str): return struct.pack('<I', 8) + string(item)
        if isinstance(item, int): return struct.pack('<II', 4, item)
        if isinstance(item, list):
            kind = 8 if isinstance(item[0], str) else 4
            return struct.pack('<IIQ', 9, kind, len(item)) + b''.join(
                string(v) if kind == 8 else struct.pack('<I', v) for v in item)
        raise TypeError(item)
    Path(path).write_bytes(b'GGUF' + struct.pack('<IQQ', 3, 0, len(metadata)) +
                           b''.join(string(k) + value(v) for k,v in metadata.items()))
    return Path(path)


@contextmanager
def guarded_test_memory(folder):
    with patch('shared.core.model_safety.system_memory', return_value={'total':24*1024**3,'available':20*1024**3}), \
         patch('shared.core.model_safety.os.cpu_count', return_value=12), \
         patch('shared.core.model_safety._attempt_path', return_value=Path(folder)/'guard.json'):
        yield
