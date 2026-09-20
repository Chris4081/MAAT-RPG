"""Keep the game language unless the current user explicitly requests another."""
import re
from .wiki_maat_query import QUOTED

MARKER = '[MAAT-REPLY-LANGUAGE]'
_LANGUAGE = r'(?:deutsch|german|englisch|english)'


def requested_language(text):
    text = QUOTED.sub(' ',str(text))
    matches = list(re.finditer(
        rf'\b(?:(?:auf|in)\s+|(?:antworte|sprich|answer|reply|speak)\s+(?:(?:auf|in)\s+)?)'
        rf'({_LANGUAGE})\b', str(text), re.I))
    if not matches:
        short = re.fullmatch(rf'\s*(?:(?:bitte|please)\s+)?({_LANGUAGE})(?:\s+(?:bitte|please))?\s*[.!?^]*\s*',str(text),re.I)
        if not short:
            return None
        name = short[1]
    else:
        name = matches[-1][1]
    return 'de' if name.casefold() in ('deutsch','german') else 'en'


def language_followup(text):
    if not requested_language(text):
        return False
    return bool(re.fullmatch(
        rf'[\s.!?^]*(?:(?:bitte|please|nochmal|erneut|again|now|jetzt|aber|das|dies|that|this|'
        rf'antworte|antworten|sprich|answer|reply|speak|translate|übersetze|uebersetze|auf|in|'
        rf'kannst|könntest|koenntest|du|mir|es|sagen|schreiben|wiederholen|can|could|you|say|it|write|repeat|to|me|{_LANGUAGE})[\s.!?^]*)+',
        str(text),re.I))


def prepare_reply_language(messages, context, fallback):
    """Localize generation data, without mutating the saved UI language/history."""
    query = next((str(m.get('content','')) for m in reversed(messages) if m.get('role')=='user'),'')
    explicit = requested_language(query)
    language = explicit or fallback
    context = dict(context or {})
    profile = context.get('profile') or {}
    target = (context.get('profile_variants') or {}).get(language) or profile
    known = [profile,*(context.get('profile_variants') or {}).values()]
    old_prompts = {p.get('systemprompt','').strip() for p in known if isinstance(p,dict)}-{''}
    new_prompt = target.get('systemprompt','').strip()
    prepared = [dict(message) for message in messages]
    if new_prompt:
        for message in prepared:
            content = str(message.get('content',''))
            if message.get('role')=='system':
                for old_prompt in old_prompts:
                    if content==old_prompt or content.startswith(old_prompt+'\n\n'):
                        message['content'] = new_prompt+content[len(old_prompt):]
                        break
    context['profile'] = target
    instruction = None
    if explicit:
        instruction = (MARKER+'\nAntworte diesmal vollständig auf Deutsch, auch die Prinzipiennamen. Gib nur die Antwort aus, keine Kommentare zu Promptregeln.'
                       if language=='de' else
                       MARKER+'\nReply entirely in English this time, including principle names. Output only the answer, without comments about prompt rules.')
        if language_followup(query) and any(m.get('role')=='assistant' for m in prepared):
            instruction += (' Übersetze die vorherige Antwort zum gleichen Thema. Behalte die Einzelbewertungen und Begründungen; korrigiere Rechenfehler. Beginne keine neue Begrüßung und keine neue Selbstdarstellung.'
                            if language=='de' else
                            ' Translate the previous answer about the same subject. Keep individual ratings and reasons; correct arithmetic errors. Do not start a new greeting or self-introduction.')
    return prepared, context, language, instruction
