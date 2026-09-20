"""Local GPT-OSS Harmony chat; only final-channel text leaves this adapter.

Use the GGUF's embedded template and native token IDs, never a Llama prompt.
The bundled completion helper treats Harmony's message-end as end-of-generation
and hides some control tokens. Native generate() lets analysis continue into
final while retaining llama.cpp's sampling, batching and prefix-cache reuse.
"""
from __future__ import annotations

import codecs
import re
import time
import uuid

from .rpg_i18n import get_language
from .thinking_mode import thinking_enabled


MARKERS = {
    'start': ('<|start|>', '<|im_start|>'),
    'end': ('<|end|>', '<|im_end|>'),
    'message': ('<|message|>', '<|im_sep|>'),
    'channel': ('<|channel|>', '<|meta_sep|>'),
    'constrain': ('<|constrain|>', '<|meta_start|>'),
    'return': ('<|return|>', '<|fim_suffix|>'),
    'call': ('<|call|>', '<|ghissue|>'),
    'stop': ('<|endoftext|>',),
    'ignore': ('<|ghreview|>', '<|refusal|>', '<|disc_score|>',
               '<|fim_prefix|>', '<|fim_middle|>'),
}


def _error(de, en):
    return ValueError('GPT-OSS: ' + (en if get_language(('de', 'en')) == 'en' else de))


def _template_error():
    return _error('Die GGUF-Datei benötigt eine passende Harmony-Chatvorlage und Harmony-Tokenizer.',
                  'The GGUF file needs a compatible Harmony chat template and tokenizer.')


def _messages(messages):
    instructions, history = [], []
    for message in messages:
        role = message.get('role')
        content = str(message.get('content') or '')
        if role in ('system', 'developer'):
            instructions.append(content)
        elif role in ('user', 'assistant'):
            # Completed history contains public replies only, never old analysis.
            if role == 'assistant' and (message.get('channel') not in (None, 'final') or message.get('tool_calls')):
                continue
            history.append({'role': role, 'content': content})
        else:
            raise _error('Dieser Chat unterstützt keine Modell-Werkzeugaufrufe.',
                         'This chat does not support model tool calls.')
    return ([{'role': 'developer', 'content': '\n\n'.join(instructions)}] if instructions else []) + history


class HarmonyOutput:
    """Parse structural tokens before decoding text; works across UTF-8 pieces."""
    def __init__(self, prefix):
        self.header = ''
        self.body = False
        self.visible = False
        self.finished = False
        self.has_text = False
        self.decoder = codecs.getincrementaldecoder('utf-8')('replace')
        # Templates may prefill assistant, assistant/analysis or assistant/final.
        starts = [(prefix.rfind(marker), marker) for marker in MARKERS['start']]
        index, marker = max(starts)
        if index < 0:
            raise _template_error()
        tail = prefix[index + len(marker):]
        for value in MARKERS['channel']:
            tail = tail.replace(value, '\x1f')
        for value in MARKERS['constrain']:
            tail = tail.replace(value, '\x1e')
        separators = [value for value in MARKERS['message'] if value in tail]
        if separators:
            header, content = tail.split(separators[0], 1)
            if content.strip():
                raise _template_error()
            self.header = header
            self.control('message')
        else:
            self.header = tail
        if not self.header.strip().startswith('assistant'):
            raise _template_error()

    def control(self, kind):
        tail = ''
        if kind in ('start', 'end', 'return', 'call', 'stop'):
            if self.visible:
                tail = self.decoder.decode(b'', final=True)
                self.has_text = self.has_text or bool(tail.strip())
            self.decoder.reset()
            if kind in ('return', 'call', 'stop') or (kind == 'end' and self.visible):
                self.finished = True
            self.body = self.visible = False
            self.header = ''
        elif kind in ('channel', 'constrain'):
            if self.body:
                raise _error('Ungültige Antwortstruktur. Bitte erneut versuchen.',
                             'Invalid response structure. Please try again.')
            self.header += '\x1f' if kind == 'channel' else '\x1e'
        elif kind == 'message':
            header = self.header.strip()
            role = re.split(r'[\s\x1e\x1f]', header)[0]
            channel = header.split('\x1f', 1)[1] if '\x1f' in header else ''
            channel = re.split(r'[\s\x1e]', channel.strip())[0]
            self.body = True
            self.visible = role == 'assistant' and channel == 'final' and 'to=' not in header
        return tail

    def text(self, piece):
        if self.finished:
            return ''
        if not self.body:
            self.header += self.decoder.decode(piece)
            if len(self.header) > 512:
                raise _error('Ungültiger Antwortkopf. Bitte erneut versuchen.',
                             'Invalid response header. Please try again.')
            return ''
        if not self.visible:
            return ''
        text = self.decoder.decode(piece)
        self.has_text = self.has_text or bool(text.strip())
        return text

    def finish(self):
        tail = self.decoder.decode(b'', final=True) if self.visible else ''
        if not self.has_text and not tail.strip():
            raise _error('Keine fertige Antwort erzeugt. Bitte die Anfrage kürzen oder die niedrige Denkstufe verwenden.',
                         'No final answer generated. Please shorten the request or use low reasoning effort.')
        return tail


def configure(inst, state):
    from llama_cpp.llama_chat_format import Jinja2ChatFormatter
    template = inst.metadata.get('tokenizer.chat_template')
    if not template:
        raise _template_error()
    controls = {}
    for kind, markers in MARKERS.items():
        for marker in markers:
            ids = inst.tokenize(marker.encode(), add_bos=False, special=True)
            if len(ids) == 1 and inst.detokenize(ids, special=True).decode('utf-8', 'replace') == marker:
                controls[ids[0]] = kind
    if not {'start', 'end', 'message', 'channel', 'return', 'call'} <= set(controls.values()):
        raise _template_error()
    # EOS may be message-end in converted GGUFs. Never use it as a turn stop.
    eos = inst.token_eos()
    if eos >= 0 and eos not in controls:
        controls[eos] = 'stop'
    def token_text(token_id):
        return inst.detokenize([token_id], special=True).decode('utf-8', 'replace') if token_id >= 0 else ''
    formatter = Jinja2ChatFormatter(template=template, eos_token=token_text(eos),
                                   bos_token=token_text(inst.token_bos()))

    def format_prompt(messages):
        effort = 'medium' if thinking_enabled() else 'low'
        prompt = formatter(messages=_messages(messages), reasoning_effort=effort,
                           builtin_tools=[], tools=None).prompt
        HarmonyOutput(prompt)  # Refuse malformed/incompatible generation prefixes.
        return prompt

    probe = [{'role': 'system', 'content': 'MAAT_SYSTEM_TEMPLATE_PROBE'},
             {'role': 'system', 'content': 'MAAT_MEMORY_TEMPLATE_PROBE'},
             {'role': 'user', 'content': 'MAAT_USER_TEMPLATE_PROBE'}]
    checked = format_prompt(probe)
    if any(checked.count(m['content']) != 1 for m in probe):
        raise _template_error()
    state['reasoning_mode'] = 'low/medium'

    def handler(*, llama, messages, stream=False, **kwargs):
        check = kwargs.get('cancel_check')
        if check:
            check()
        prompt = format_prompt(messages)
        tokens = llama.tokenize(prompt.encode(), add_bos=False, special=True)
        available = int(llama.n_ctx()) - len(tokens)
        if available <= 0:
            raise _error('Der Kontext ist voll. Bitte weniger Nachrichten im KI-Kontext verwenden.',
                         'The context is full. Please include fewer messages in the AI context.')
        requested = kwargs.get('max_tokens')
        limit = min(available, int(requested)) if requested and int(requested) > 0 else available
        usage = {'prompt_tokens': len(tokens), 'completion_tokens': 0, 'total_tokens': len(tokens)}
        finish_reason = 'length'
        identity = dict(id='chatcmpl-' + uuid.uuid4().hex, created=int(time.time()),
                        model=str(kwargs.get('model') or getattr(llama, 'model_path', 'gpt-oss')))

        def responses():
            nonlocal finish_reason
            parsed = HarmonyOutput(prompt)
            if kwargs.get('seed') is not None:
                llama.set_seed(int(kwargs['seed']))
            sampling = {key: kwargs[key] for key in ('top_p', 'top_k', 'min_p', 'typical_p',
                        'repeat_penalty', 'presence_penalty', 'frequency_penalty', 'tfs_z',
                        'mirostat_mode', 'mirostat_tau', 'mirostat_eta', 'logits_processor', 'grammar')
                        if key in kwargs}
            sampling['temp'] = float(kwargs.get('temperature', .7))
            source = llama.generate(tokens, **sampling)
            try:
                for token in source:
                    if check:
                        check()
                    usage['completion_tokens'] += 1
                    usage['total_tokens'] += 1
                    kind = controls.get(int(token))
                    text = parsed.control(kind) if kind else parsed.text(llama.detokenize([token], special=True))
                    if text:
                        yield dict(identity, object='chat.completion.chunk', choices=[
                            dict(index=0, delta={'content': text}, finish_reason=None)])
                    if parsed.finished:
                        finish_reason = 'stop'
                        break
                    if usage['completion_tokens'] >= limit:
                        break
                tail = parsed.finish()
                if tail:
                    yield dict(identity, object='chat.completion.chunk', choices=[
                        dict(index=0, delta={'content': tail}, finish_reason=None)])
                yield dict(identity, object='chat.completion.chunk', choices=[
                    dict(index=0, delta={}, finish_reason=finish_reason)])
            finally:
                close = getattr(source, 'close', None)
                if close:
                    close()

        if stream:
            return responses()
        content = ''.join(chunk['choices'][0]['delta'].get('content', '') for chunk in responses())
        return dict(identity, object='chat.completion', usage=usage, choices=[
            dict(index=0, message={'role': 'assistant', 'content': content}, finish_reason=finish_reason)])

    inst.chat_handler = handler
    return state
