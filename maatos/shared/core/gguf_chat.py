"""Text-chat adapters for embedded GGUF templates."""
from .thinking_mode import thinking_enabled
from .model_family import identify_family
from .rpg_i18n import get_language


def prepare_messages(messages, architecture, *, mistral=False, fold_system=False):
    copied = [dict(m) for m in messages]
    systems = [str(m.get('content') or '') for m in copied if m.get('role') == 'system']
    other = [m for m in copied if m.get('role') != 'system']
    if mistral:
        # Legacy templates require user/assistant alternation. Merge adjacent
        # turns without deleting content; a greeting may precede the first user.
        merged = []
        for message in other:
            if merged and message.get('role') == merged[-1].get('role') and message.get('role') in ('user', 'assistant'):
                merged[-1]['content'] = str(merged[-1].get('content') or '') + '\n\n' + str(message.get('content') or '')
            else:
                merged.append(message)
        other = merged
        if other and other[0].get('role') == 'assistant':
            other.insert(0, {'role': 'user', 'content': ''})
    if not systems:
        return other
    context = '\n\n'.join(systems)
    if fold_system or architecture in {'gemma', 'gemma2', 'gemma3', 'gemma3n'}:
        if other and other[0]['role'] == 'user':
            other[0]['content'] = context + '\n\n' + str(other[0].get('content') or '')
        else:
            other.insert(0, {'role': 'user', 'content': context})
        return other
    return [{'role': 'system', 'content': context}] + other


def configure_template(inst):
    from llama_cpp.llama_chat_format import Jinja2ChatFormatter, chat_formatter_to_chat_completion_handler
    template = inst.metadata.get('tokenizer.chat_template')
    architecture = inst.metadata.get('general.architecture', '')
    family = identify_family(inst.metadata, name=getattr(inst, 'model_path', ''))
    state = {'architecture': architecture, 'family': family, 'thinking_prefix': False}
    if family == 'gpt-oss':
        from .gpt_oss import configure
        return configure(inst, state)
    if not template and family == 'tinyllama':
        from .tinyllama import CHAT_V1_TEMPLATE, chat_v1_fallback
        if chat_v1_fallback(inst.metadata, getattr(inst, 'model_path', '')):
            template = CHAT_V1_TEMPLATE
            state['template_source'] = 'tinyllama-chat-v1.0-fallback'
        else:
            raise ValueError('TinyLlama: The GGUF file has no chat template. Use TinyLlama Chat v1.0 or a Chat GGUF with an embedded template.'
                             if get_language(('de', 'en')) == 'en' else
                             'TinyLlama: Der GGUF-Datei fehlt die Chatvorlage. Nutze TinyLlama Chat v1.0 oder ein Chat-GGUF mit eingebetteter Vorlage.')
    if not template:
        if family == 'mistral' or architecture.startswith(('qwen', 'gemma')):
            raise ValueError('The GGUF file has no chat template. Please use an Instruct/Chat GGUF with an embedded template.'
                             if get_language(('de','en')) == 'en' else
                             'Der GGUF-Datei fehlt die Chatvorlage. Bitte ein Instruct-/Chat-GGUF mit eingebetteter Vorlage verwenden.')
        return state
    def token_text(token_id):
        return inst.detokenize([token_id], special=True).decode('utf-8', 'replace') if token_id >= 0 else ''
    formatter = Jinja2ChatFormatter(template=template, eos_token=token_text(inst.token_eos()),
                                   bos_token=token_text(inst.token_bos()), stop_token_ids=[inst.token_eos()])
    from .tinyllama import ROLE_STOPS
    tinyllama_roles = family == 'tinyllama' and all(marker in template for marker in ROLE_STOPS)
    fold_system = False
    if family == 'mistral':
        # Use the GGUF's own whitespace, control tokens and system placement.
        # Old official v1 templates reject system roles; some conversions omit
        # them silently. Probe formatting only, without allocating model tokens.
        probe = [{'role': 'system', 'content': 'MAAT_SYSTEM_TEMPLATE_PROBE'},
                 {'role': 'user', 'content': 'MAAT_USER_TEMPLATE_PROBE'}]
        try:
            fold_system = 'MAAT_SYSTEM_TEMPLATE_PROBE' not in formatter(messages=probe, enable_thinking=False).prompt
        except (ValueError, TypeError):
            fold_system = True
        checked = formatter(messages=prepare_messages(probe, architecture, mistral=True,
                                                       fold_system=fold_system), enable_thinking=False).prompt
        if any(message['content'] not in checked for message in probe):
            raise ValueError('Mistral GGUF: The chat template does not preserve the system prompt or user message.'
                             if get_language(('de','en')) == 'en' else
                             'Mistral GGUF: Die Chatvorlage übernimmt Systemprompt oder Nachricht nicht vollständig.')
    state['fold_system'] = fold_system
    def format_chat(**kwargs):
        kwargs['messages'] = prepare_messages(kwargs['messages'], architecture,
                                               mistral=family == 'mistral', fold_system=fold_system)
        kwargs['enable_thinking'] = thinking_enabled()
        result = formatter(**kwargs)
        if tinyllama_roles:
            # Stop in the native sampler before a second simulated speaker;
            # no delayed postprocessing or duplicated answer is needed.
            result.stop = list(dict.fromkeys([*result.stop, *ROLE_STOPS]))
        state['thinking_prefix'] = result.prompt.rstrip().endswith(('<think>', '[THINK]'))
        return result
    inst.chat_handler = chat_formatter_to_chat_completion_handler(format_chat)
    return state


def normalize_channels(chunks, *, mistral=False):
    """Convert model reasoning markers across arbitrary stream boundaries."""
    markers = ({'[THINK]': '<think>', '[/THINK]': '</think>'} if mistral else
               {'<|channel>thought': '<think>', '<|channel>final': '', '<channel|>': '</think>'})
    pending = ''
    for chunk in chunks:
        pending += chunk
        output = []
        while pending:
            match = next((key for key in markers if pending.startswith(key)), None)
            if match:
                output.append(markers[match])
                pending = pending[len(match):]
            elif any(key.startswith(pending) for key in markers):
                break
            else:
                output.append(pending[0])
                pending = pending[1:]
        if output:
            yield ''.join(output)
    if pending:
        yield pending
