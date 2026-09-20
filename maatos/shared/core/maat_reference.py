"""Give small models the formula reference only for relevant user requests."""
import re
import unicodedata
from .wiki_maat_query import MAAT, SEPARATOR, assessment_topics

MARKER = '[MAAT-FORMULA-REFERENCE]'


def _text(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(text)).casefold() if not unicodedata.combining(c))


def _explicit(text):
    # Share the wiki's assessment vocabulary so e.g. "MAAT-Wert von Mona
    # Lisa" selects both the article and the same formula as "MAAT score".
    if assessment_topics(text) is not None:
        return True
    text = _text(text)
    if _ratings(text):
        return True
    sep = SEPARATOR
    return bool(re.search(
        rf'\b{MAAT}{sep}(?:welt{sep}formel\w*|world(?:{sep}formula\w*)?|master|formel\w*|formula\w*)\b|'
        rf'\b(?:plp|welt{sep}formel\w*|agi{sep}proximity|ai{sep}consciousness|b{sep}universe|'
        rf'world{sep}formula\w*|local{sep}coherence|lokale{sep}koharenz|ki{sep}bewusstsein|'
        rf'agi{sep}nahe|universums{sep}formel\w*|universe{sep}formula\w*|'
        rf'problem{sep}solving{sep}potential|problem{sep}losungs{sep}poten[zt]ial)\b|'
        r'\b(?:stability|stabilitat)\s*(?:=|\()|'
        r'\bc\s*\(\s*x\s*\)|'
        rf'\b{MAAT}\b.{{0,40}}\b(?:formel\w*|formula\w*|berechn\w*|calculat\w*|bewert\w*|assess\w*|stability|stabilitat)\b|'
        rf'\b(?:formel\w*|formula\w*|berechn\w*|calculat\w*|bewert\w*|assess\w*|stability|stabilitat)\b.{{0,40}}\b{MAAT}\b|'
        r'\b(?:berechn\w*|calculat\w*|compute|erklare|explain)\b.{0,25}\b(?:stability|stabilitat)\b|'
        r'\b[hbsvr]\s*=\s*\d+(?:[.,]\d+)?\s*[,; ]+\s*[hbsvr]\s*=',text))


def _ratings(text):
    """Recognize explicit named ratings without treating small talk as maths."""
    names = r'harmonie|harmony|balance|schopfungskraft|creative\s+power|creativity|verbundenheit|connection|connectedness|respekt|respect|[hbsvr]'
    return bool(re.search(rf'\b(?:{names})\s*[:=]?\s*\d+(?:[.,]\d+)?\s*(?:von|out\s+of|/)\s*10\b',text))


def _formula_keys(text):
    text = _text(text)
    sep = SEPARATOR
    patterns = {
        'stability': r'\b(?:stability|stabilitat)\b',
        'world': rf'\b(?:(?:{MAAT}{sep})?welt{sep}formel\w*|{MAAT}{sep}world(?:{sep}formula\w*)?|world{sep}formula\w*)\b',
        'plp': rf'\b(?:plp|problem{sep}solving{sep}potential|problem{sep}losungs{sep}poten[zt]ial)\b',
        'coherence': rf'\bc\s*\(\s*x\s*\)|\b(?:local{sep}coherence|lokale{sep}koharenz)\b',
        'agi': rf'\bagi{sep}(?:proximity|nahe)\b',
        'consciousness': rf'\b(?:ai{sep}consciousness|ki{sep}bewusstsein)\b',
        'master': rf'\b{MAAT}{sep}master\b',
        'universe': rf'\b(?:b{sep}universe|universums{sep}formel\w*|universe{sep}formula\w*)\b',
    }
    keys = [key for key,pattern in patterns.items() if re.search(pattern,text)]
    if not keys and re.search(rf'\b{MAAT}{sep}(?:formeln|formulas)\b',text):
        return list(patterns)
    return keys


def _request(messages):
    queries=[str(m.get('content','')) for m in messages if m.get('role')=='user']
    if not queries:
        return None
    from .reply_language import language_followup
    while len(queries)>1 and language_followup(queries[-1]):
        queries.pop()
    current=queries[-1]
    if _explicit(current):
        # Supplied ratings can be the direct answer to a preceding formula
        # question. A new named assessment always starts its own request.
        if (len(queries)>1 and _ratings(_text(current)) and
                assessment_topics(current) is None and not _formula_keys(current) and
                _explicit(queries[-2]) and _formula_keys(queries[-2])):
            return queries[-2]+'\n'+current
        return current
    # A direct follow-up may omit the formula's name. Greetings and ordinary
    # conversation must not inherit formula instructions from earlier turns.
    followup=bool(re.search(r'\b(?:beispiel\w*|example\w*|nochmal|again|werte\w*|values?|einsetzen|substitut\w*)\b',_text(current)))
    return queries[-2] if followup and len(queries)>1 and _explicit(queries[-2]) else None


def needs_reference(messages):
    return _request(messages) is not None


def assessment_requested(messages):
    request = _request(messages)
    return request is not None and not _formula_keys(request)


def generation_reference(messages, context):
    request = _request(messages)
    if request is None:
        return None
    profile=(context or {}).get('profile') or {}
    reference=profile.get('maat_reference','')
    formulas = profile.get('maat_formulas') or {}
    keys = _formula_keys(request)
    parts = []
    if isinstance(formulas,dict) and keys:
        # Only the requested advanced formulas get normalized inputs; a normal
        # MAAT value receives the full-name, out-of-ten guide alone.
        parts = [formulas.get(key,'') for key in ['scale',*keys]]
        parts = [part.strip() for part in parts if isinstance(part,str) and part.strip()]
    if not parts or assessment_topics(request) is not None:
        if isinstance(reference,str) and reference.strip():
            parts.insert(0,reference.strip())
    if parts:
        return MARKER+'\n'+'\n'.join(parts)
    return None
