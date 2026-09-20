"""Hide known informational Metal startup lines, retaining unknown diagnostics."""
import re

_METAL_INFO = re.compile(
    r'^ggml_metal_(?:'
    r'device_init: (?:tensor API disabled for pre-M5 and pre-A19 devices|GPU name:.*|GPU family:.*|'
    r'(?:simdgroup reduction|simdgroup matrix mul\.|has unified memory|has bfloat|has tensor|use residency sets|use shared buffers)\s*=\s*(?:true|false)|'
    r'recommendedMaxWorkingSetSize\s*=\s*[0-9.]+ MB)|'
    r'library_init: (?:using embedded metal library|loaded in [0-9.]+ sec)|'
    r'rsets_init: creating a residency set collection \(keep_alive = [0-9]+ s\))$'
)


def visible_diagnostics(text):
    return ''.join(line for line in text.splitlines(keepends=True) if not _METAL_INFO.fullmatch(line.strip()))


def quiet_metal_startup(function):
    """Filter native stderr during short hardware discovery, including C writes."""
    from functools import wraps
    @wraps(function)
    def wrapped(*args, **kwargs):
        import os
        import tempfile
        with tempfile.TemporaryFile() as captured:
            previous = os.dup(2)
            try:
                os.dup2(captured.fileno(), 2)
                return function(*args, **kwargs)
            finally:
                os.dup2(previous, 2)
                os.close(previous)
                captured.seek(0)
                remaining = visible_diagnostics(captured.read().decode('utf-8', 'replace'))
                if remaining:
                    os.write(2, remaining.encode('utf-8'))
    return wrapped
