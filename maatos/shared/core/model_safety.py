"""Bounded GGUF inspection and conservative RAM checks, without loading an LLM.

The estimate reserves full model weights, FP16 KV for every layer, workspace
and a margin. Hybrid/SWA models may use less. This is a guard, not a guarantee
against native driver faults. Swap is deliberately not counted as capacity.
"""
import ctypes
from functools import lru_cache
import math
import os
from pathlib import Path
import platform
import struct

GIB = 1024**3
MEMORY_LIMIT_PERCENT = 99
MAX_METADATA = 256 * 1024**2
_SCALARS = {0:'B', 1:'b', 2:'H', 3:'h', 4:'I', 5:'i', 6:'f', 7:'?', 10:'Q', 11:'q', 12:'d'}


class ModelSafetyError(ValueError):
    def __init__(self, reason, report=None):
        super().__init__(reason)
        self.reason = reason
        self.report = report or {}


def gguf_metadata(path):
    """Read selected metadata only; never map or allocate tensor data."""
    path = Path(path)
    size = path.stat().st_size
    with path.open('rb') as stream:
        def read(count):
            if count < 0 or stream.tell()+count > min(size, MAX_METADATA):
                raise ModelSafetyError('metadata')
            value = stream.read(count)
            if len(value) != count:
                raise ModelSafetyError('metadata')
            return value

        def number(fmt):
            return struct.unpack('<'+fmt, read(struct.calcsize('<'+fmt)))[0]

        def skip(count):
            if count < 0 or stream.tell()+count > min(size, MAX_METADATA):
                raise ModelSafetyError('metadata')
            stream.seek(count, 1)

        def string(keep=False):
            count = number('Q')
            if keep:
                if count > 4096:
                    raise ModelSafetyError('metadata')
                return read(count).decode('utf-8', 'strict')
            skip(count)

        def value(kind, keep):
            if kind in _SCALARS:
                return number(_SCALARS[kind])
            if kind == 8:
                return string(keep)
            if kind == 9:
                item_kind, count = number('I'), number('Q')
                if count > 2_000_000 or item_kind == 9:
                    raise ModelSafetyError('metadata')
                if item_kind in _SCALARS:
                    if keep and count <= 1024:
                        return [number(_SCALARS[item_kind]) for _ in range(count)]
                    skip(count * struct.calcsize('<'+_SCALARS[item_kind]))
                    return None
                if item_kind == 8:
                    for _ in range(count):
                        string(False)
                    return None
            raise ModelSafetyError('metadata')

        try:
            if read(4) != b'GGUF' or number('I') not in (2, 3):
                raise ModelSafetyError('metadata')
            number('Q')  # tensor count; tensors themselves are not inspected
            count = number('Q')
            if count > 100_000:
                raise ModelSafetyError('metadata')
            result = {}
            suffixes = ('.block_count', '.embedding_length', '.attention.head_count',
                        '.attention.head_count_kv', '.attention.key_length', '.attention.value_length')
            for _ in range(count):
                key = string(True)
                keep = key in ('general.architecture', 'split.count') or key.endswith(suffixes)
                item = value(number('I'), keep)
                if keep:
                    result[key] = item
            return result
        except (UnicodeError, struct.error, OverflowError) as exc:
            raise ModelSafetyError('metadata') from exc


@lru_cache(maxsize=1)
def _mac_memory_api():
    lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib')
    lib.mach_host_self.restype = ctypes.c_uint32
    lib.host_statistics64.argtypes = [ctypes.c_uint32, ctypes.c_int,
                                     ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_uint32)]
    lib.sysctlbyname.argtypes = [ctypes.c_char_p, ctypes.c_void_p,
                                ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p, ctypes.c_size_t]
    total = ctypes.c_uint64()
    length = ctypes.c_size_t(ctypes.sizeof(total))
    if lib.sysctlbyname(b'hw.memsize', ctypes.byref(total), ctypes.byref(length), None, 0):
        raise OSError('hw.memsize unavailable')
    return lib, lib.mach_host_self(), total.value, os.sysconf('SC_PAGE_SIZE')


def system_memory():
    """Physical/available bytes via OS APIs; no subprocess or model library."""
    try:
        system = platform.system()
        if system == 'Darwin':
            lib, host, total, page_size = _mac_memory_api()
            # Oversized, 64-bit-aligned buffer for vm_statistics64. Its first
            # four natural_t fields are free, active, inactive and wired pages.
            buffer = (ctypes.c_uint64 * 128)()
            count = ctypes.c_uint32(ctypes.sizeof(buffer)//4)
            words = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_int32))
            if lib.host_statistics64(host, 4, words, ctypes.byref(count)) or count.value < 4:
                return None
            pages = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_uint32))
            available = (pages[0]+pages[2]) * page_size
        elif system == 'Linux':
            fields = {}
            for line in Path('/proc/meminfo').read_text().splitlines():
                key, val = line.split(':', 1)
                fields[key] = int(val.split()[0])*1024
            total = fields['MemTotal']
            available = fields.get('MemAvailable', fields.get('MemFree',0)+fields.get('Cached',0)+fields.get('Buffers',0)-fields.get('Shmem',0))
            # Honor a v2 container limit when present.
            limit = Path('/sys/fs/cgroup/memory.max')
            if limit.exists() and limit.read_text().strip().isdigit():
                total = min(total, int(limit.read_text()))
                available = min(available, total-int(Path('/sys/fs/cgroup/memory.current').read_text()))
        elif system == 'Windows':
            class Status(ctypes.Structure):
                _fields_ = [('length',ctypes.c_uint32),('load',ctypes.c_uint32)]+[
                    (name,ctypes.c_uint64) for name in ('total','available','page_total','page_available','virtual_total','virtual_available','extended')]
            status = Status(); status.length = ctypes.sizeof(status)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return None
            total, available = status.total, status.available
        else:
            import psutil
            memory = psutil.virtual_memory()
            total, available = memory.total, memory.available
        if total <= 0:
            return None
        return dict(total=int(total), available=max(0,min(int(total),int(available))))
    except (ImportError, OSError, ValueError, KeyError, AttributeError):
        return None


def estimate_model_memory(path, n_ctx, options, metadata=None):
    metadata = gguf_metadata(path) if metadata is None else metadata
    arch = metadata.get('general.architecture')
    if not isinstance(arch, str) or not arch:
        raise ModelSafetyError('metadata')
    # llama.cpp treats both absent/zero and one as a single GGUF.
    # Some Qwen exports explicitly write zero.
    split_count = metadata.get('split.count', 0)
    if type(split_count) is not int or split_count not in (0, 1):
        raise ModelSafetyError('split')

    def dimension(key, fallback=None):
        value = metadata.get(arch+'.'+key, fallback)
        values = value if isinstance(value,list) else [value]
        if not values or any(type(v) is not int or v <= 0 or v > 1_000_000 for v in values):
            raise ModelSafetyError('dimensions')
        return max(values)

    layers = dimension('block_count')
    embedding = dimension('embedding_length')
    heads = dimension('attention.head_count')
    kv_heads = dimension('attention.head_count_kv', heads)
    key = dimension('attention.key_length', math.ceil(embedding/heads))
    val = dimension('attention.value_length', key)
    # Full context for every layer is intentionally conservative for SWA and
    # hybrid recurrent models; do not assume a small cache from the filename.
    kv = 2 * layers * kv_heads * (key+val) * n_ctx
    batch = int(options.get('n_batch',512))
    ubatch = int(options.get('n_ubatch',batch))
    workspace = 512*1024**2 + embedding*batch*4*8
    if not options.get('flash_attn'):
        workspace += n_ctx*ubatch*heads*4
    weights = Path(path).stat().st_size
    if options.get('repack_weights'):
        # A CPU repack can temporarily coexist with the mapped source weights.
        workspace += weights
    estimate = math.ceil((weights+kv+workspace)*1.20)
    return dict(architecture=arch, weights=weights, kv_cache=kv,
                workspace=workspace, estimated=estimate, context=n_ctx)


def check_model_safety(path, n_ctx, settings, *, memory=None, metadata=None, logical=None):
    options = settings['options']
    warnings = []
    if not options.get('use_mmap',True):
        warnings.append('mmap')
    if options.get('use_mlock',False):
        warnings.append('mlock')
    logical = logical or os.cpu_count() or 1
    if any(not 1 <= int(settings[key]) <= logical for key in ('threads','threads_batch')):
        warnings.append('threads')
    report = estimate_model_memory(path,n_ctx,options,metadata)
    report.update(warnings=warnings, limit_percent=MEMORY_LIMIT_PERCENT, logical=logical)
    memory = system_memory() if memory is None else memory
    if memory is None:
        warnings.append('memory_unknown')
        return report
    # User-selected permissive policy: 99% of physical RAM, not 99% of the
    # currently free RAM. Existing apps/cache must not impose a hidden lower cap.
    budget = memory['total'] * MEMORY_LIMIT_PERCENT // 100
    report.update(memory, budget=budget)
    if report['estimated'] > budget:
        raise ModelSafetyError('capacity', report)
    if critical_memory(memory):
        raise ModelSafetyError('memory_full', report)
    if report['estimated'] > memory['available']:
        warnings.append('available')
    return report


def critical_memory(memory):
    return memory is not None and memory['available'] * 100 < memory['total'] * (100 - MEMORY_LIMIT_PERCENT)


def safety_warning(report, language='de'):
    """Inform without rejecting or changing the user's manual load options."""
    en = language == 'en'
    reasons = {
        'mmap': ('mmap ist aus: Das Laden kann mehr RAM benötigen.', 'mmap is off: loading may require more RAM.'),
        'mlock': ('mlock ist an: Gesperrte Modellgewichte lassen sich nicht auslagern.', 'mlock is on: locked model weights cannot be swapped out.'),
        'threads': ('Mehr Threads als logische CPU-Threads gewählt: Das kann langsamer sein.', 'More threads than logical CPU threads selected: this may be slower.'),
        'memory_unknown': ('RAM konnte nicht ermittelt werden; die 99-%-Prüfung ist derzeit nicht verfügbar.', 'RAM could not be measured; the 99% check is currently unavailable.'),
        'available': ('Der geschätzte Bedarf übersteigt den aktuell verfügbaren RAM. Auslagerung kann Laden und Antworten stark verlangsamen.', 'Estimated requirements exceed currently available RAM. Swapping may greatly slow loading and responses.'),
    }
    text = ('Geschätzter Modellbedarf: {need:.1f} GiB' if not en else 'Estimated model requirements: {need:.1f} GiB').format(need=report['estimated']/GIB)
    if 'budget' in report:
        text += (' · Grenze: {budget:.1f} GiB (99 % RAM)\nAktuell verfügbar: {available:.1f} GiB' if not en else
                 ' · Limit: {budget:.1f} GiB (99% RAM)\nCurrently available: {available:.1f} GiB').format(budget=report['budget']/GIB, available=report['available']/GIB)
    notes = [reasons[key][int(en)] for key in report.get('warnings', []) if key in reasons]
    if notes:
        text += '\n\n' + ('Warning: These settings may slow down or crash your computer.' if en else
                            'Achtung: Diese Einstellungen können den Computer verlangsamen oder zum Absturz bringen.')
        text += '\n' + '\n'.join(notes)
    return text


def _attempt_path():
    from .maat_paths import state_file
    return Path(state_file('model_load_guard.json'))


def previous_load_attempt():
    import json
    path = _attempt_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data,dict) else {'model':'unknown'}
    except (OSError, ValueError):
        # A torn/unreadable marker also means the previous load is unconfirmed.
        return {'model':'unknown'}


def mark_load_attempt(name, context):
    import json
    import tempfile
    path = _attempt_path(); path.parent.mkdir(parents=True,exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,
                                         prefix='.model-guard-',delete=False) as handle:
            temporary=handle.name
            json.dump({'model':str(name),'context':int(context),'status':'loading'},handle)
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary,path)
    finally:
        if temporary and os.path.exists(temporary):os.unlink(temporary)


def clear_load_attempt():
    _attempt_path().unlink(missing_ok=True)


def safety_message(error, language='de'):
    en = language == 'en'
    reasons = {
        'capacity': ('Der geschätzte Bedarf für Modell, Kontext und Ladepuffer überschreitet 99 % des physischen RAM.', 'Estimated model, context and loading buffer requirements exceed 99% of physical RAM.'),
        'metadata': ('Die GGUF-Metadaten sind unvollständig oder können nicht sicher gelesen werden.', 'The GGUF metadata is incomplete or cannot be read safely.'),
        'dimensions': ('Für dieses Modell lässt sich der Speicherbedarf noch nicht zuverlässig abschätzen.', 'The memory requirements of this model cannot yet be estimated reliably.'),
        'split': ('Geteilte GGUF-Modelle werden von der Speicherprüfung noch nicht unterstützt. Wähle eine einzelne vollständige GGUF-Datei.', 'Split GGUF models are not yet supported by the memory check. Choose a single complete GGUF file.'),
        'memory_full': ('Mehr als 99 % des RAM sind bereits belegt. Gib Speicher frei und starte das Laden erneut.', 'More than 99% of RAM is already in use. Free memory and try loading again.'),
        'pressure': ('Mehr als 99 % des RAM waren in zwei aufeinanderfolgenden Messungen belegt. Der KI-Prozess wurde beendet, um Speicher freizugeben.', 'More than 99% of RAM was in use in two consecutive measurements. The AI process was stopped to free memory.'),
    }
    title = 'Model loading stopped by the safety check.' if en else 'Modellladen durch Sicherheitsprüfung gestoppt.'
    if error.reason == 'pressure':
        title = 'AI process stopped by memory protection.' if en else 'KI-Prozess durch Speicherschutz gestoppt.'
    text = title+'\n\n'+reasons[error.reason][int(en)]
    r=error.report
    if 'budget' in r:
        text += ('\n\nEstimated: {need:.1f} GiB · Available: {available:.1f} GiB\nModel limit (99% RAM): {budget:.1f} GiB'
                 if en else '\n\nGeschätzt: {need:.1f} GiB · Verfügbar: {available:.1f} GiB\nModellgrenze (99 % RAM): {budget:.1f} GiB').format(
                     need=r['estimated']/GIB,available=r['available']/GIB,budget=r['budget']/GIB)
    if error.reason in ('capacity','pressure','memory_full'):
        text += ('\n\nUse a smaller GGUF model or a shorter context and close other memory-intensive programs. No automatic retry.'
                 if en else '\n\nWähle ein kleineres GGUF-Modell oder einen kürzeren Kontext und schließe andere speicherintensive Programme. Kein automatischer Neuversuch.')
    return text
