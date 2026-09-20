"""Hardware-based GUI adapter selection without importing a native AI library."""
import platform


def intel_architecture(machine=None):
    return (machine if machine is not None else platform.machine()).lower() in {'x86_64', 'amd64'}


def available_adapters(machine=None):
    if intel_architecture(machine):
        return [('llama_intel', 'GGUF (Intel)')]
    if (machine if machine is not None else platform.machine()).lower() in {'arm64','aarch64'}:
        return [('llama', 'GGUF (ARM · Metal)' if platform.system() == 'Darwin' else 'GGUF (ARM)')]
    return [('llama', 'llama.cpp · GGUF')]


def selected_adapter(machine=None):
    return available_adapters(machine)[0][0]
