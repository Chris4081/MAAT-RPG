"""Compatibility for TinyLlama Chat v1.0 exports without embedded templates.

Template source (Apache-2.0), checked 2026-09-17:
https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0/blob/main/tokenizer_config.json
CHAT_V1_TEMPLATE is extracted from that repository's chat_template value and
embedded here as a Python constant. The surrounding RPG integration is separate.
License and attribution: ../../../packaging/licenses/Apache-2.0.txt and
../../../packaging/licenses/TINYLLAMA-NOTICE.md (relative to this file).
Always prefer the GGUF's own template, including other TinyLlama fine-tunes.
"""
from pathlib import Path
import re


CHAT_V1_TEMPLATE = """{% for message in messages %}
{% if message['role'] == 'user' %}
{{ '<|user|>\n' + message['content'] + eos_token }}
{% elif message['role'] == 'system' %}
{{ '<|system|>\n' + message['content'] + eos_token }}
{% elif message['role'] == 'assistant' %}
{{ '<|assistant|>\n' + message['content'] + eos_token }}
{% endif %}
{% if loop.last and add_generation_prompt %}
{{ '<|assistant|>' }}
{% endif %}
{% endfor %}"""
ROLE_STOPS = ('<|user|>', '<|system|>', '<|assistant|>')


def chat_v1_fallback(metadata, name=''):
    """Do not guess Zephyr for base checkpoints or unknown chat fine-tunes."""
    names = ' '.join(str(metadata.get(key) or '') for key in
                     ('general.name', 'general.basename', 'general.finetune'))
    names += ' ' + Path(str(name)).name
    return bool(re.search(r'(?<![a-z])chat[-_ .]*v?1[._]0(?![0-9]|[._][0-9])', names.lower()))
