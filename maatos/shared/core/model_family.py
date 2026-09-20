"""Distinguish model families from shared GGUF tensor architectures."""
from pathlib import Path
import re


def identify_family(metadata=None, *, architecture='', name=''):
    metadata = metadata or {}
    architecture = str(metadata.get('general.architecture') or architecture).lower()
    # Most Mistral 7B / older Ministral GGUFs use the llama tensor architecture.
    names = ' '.join(str(metadata.get(key) or '') for key in
                     ('general.name', 'general.basename', 'general.finetune'))
    names += ' ' + Path(str(name)).name
    if architecture in ('gpt-oss', 'gpt_oss') or (not architecture and re.search(r'(?<![a-z0-9])gpt[-_ ]?oss(?![a-z])', names.lower())):
        return 'gpt-oss'
    if architecture.startswith(('mistral', 'ministral', 'mixtral')):
        return 'mistral'
    if architecture in ('', 'llama') and re.search(r'(?<![a-z])tiny[-_ ]?llama(?![a-z])', names.lower()):
        return 'tinyllama'
    if architecture in ('', 'llama') and re.search(r'(?:^|[^a-z])(?:mistral|ministral|mixtral)(?:[^a-z]|$)', names.lower()):
        return 'mistral'
    if architecture:
        return architecture
    if 'llama' in names.lower():
        return 'llama'
    return ''


def model_family(llm=None, *, architecture='', name='', family=''):
    if isinstance(llm, dict):
        chat_state = llm.get('chat_state') or {}
        if chat_state.get('family'):
            return chat_state['family']
        architecture = chat_state.get('architecture') or architecture
        name = llm.get('model_path') or name
        llm = llm.get('instance')
    if family:
        return family
    metadata = getattr(llm, 'metadata', None)
    return identify_family(metadata if isinstance(metadata, dict) else {},
                           architecture=architecture, name=getattr(llm, 'model_path', None) or name)
