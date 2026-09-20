"""English intent extraction, without translating archive titles or user text.

None means the existing German/bare-title rules should try next; [] means an
English request has no concrete encyclopedia subject (e.g. a memory question).
"""
import re
from .wiki_maat_query import QUOTED

STOPWORDS = set('''i me my mine myself you your yours yourself we us our ourselves
they them their it its this that these those someone somebody something anyone
anything everything nothing where when do does did dont didnt can could would
should will shall have has had was were be been being know knows knew tell told
heard hear say said think thought feel feeling thanks thank hello fine well good
yes no not really still already also more much many of for from to with at on
by as than then today yesterday tomorrow ago months years days remember recall
calculate compute assess evaluate rate score value rating analysis assessment
estimate please explain about what who how why is are the a an and or'''.split())


def _clean(subject):
    subject = subject.strip().strip(' .!?;:')
    while True:
        cleaned = re.sub(r'\s*[,;]?\s+(?:please|briefly|in detail|in simple (?:words|terms)|for me|to me|thanks)\s*[,.!?]*$', '', subject, flags=re.I)
        if cleaned == subject:break
        subject = cleaned
    quoted = QUOTED.fullmatch(subject)
    if quoted:
        return next(value for value in quoted.groups() if value is not None).strip()
    subject = re.sub(r'^(?:the\s+|a\s+|an\s+)?(?:village|town|city|municipality|district|place|painting|artwork|book|novel|film|movie|song|musician|singer|rapper)\s+(?:(?:of|called|named)\s+)?', '', subject, flags=re.I)
    subject = re.sub(r'\s*[,–—]\s*(?:the\s+)?(?:musician|singer|rapper|village|town|city)\s*$', '', subject, flags=re.I)
    subject = re.sub(r'\s+the\s+(?:musician|singer|rapper)\s*$', '', subject, flags=re.I)
    quoted = QUOTED.fullmatch(subject)
    if quoted:return next(value for value in quoted.groups() if value is not None).strip()
    return subject.strip(' .!?;:')


def clean_terms(subjects, raw='', limit=2):
    terms=[]
    # Only spelling/brand aliases from the original plugin, never a factual
    # assertion that an entity is identical to an organisation or a concept.
    aliases={'openai':'OpenAI','suno ai':'Suno','suno.com':'Suno',
             'leonrado da vinci':'Leonardo da Vinci','leonardo da vinci':'Leonardo da Vinci'}
    quoted={next(v for v in m.groups() if v is not None).strip().casefold() for m in QUOTED.finditer(raw)}
    for subject in subjects:
        subject=_clean(subject)
        if subject.casefold()=='materia' and re.search(r'\b(?:musician|singer|rapper)\b',raw,re.I):subject='Marteria'
        term=aliases.get(subject.casefold(),subject)
        words=re.findall(r"[\w'-]+",term.casefold())
        if not 2 <= len(term) <= 100 or len(words)>10:continue
        if term.casefold() not in quoted and not any(w not in STOPWORDS for w in words):continue
        if term.casefold() not in {t.casefold() for t in terms}:terms.append(term)
        if len(terms)>=limit:break
    return terms


def split_pair(subject):
    """Split two explicitly compared subjects; keep conjunctions inside quotes."""
    ranges=[m.span() for m in QUOTED.finditer(subject)]
    for separator in re.finditer(r'\s+(?:and|with|versus|vs\.?|or)\s+|\s*\+\s*',subject,re.I):
        if not any(start<=separator.start()<end for start,end in ranges):
            return [subject[:separator.start()],subject[separator.end():]]
    return [subject]


def english_terms(raw, max_terms=2):
    text=re.sub(r'\s+', ' ', str(raw or '')).strip()
    if not text:return None
    normal=text.replace('’',"'")
    # Dates/history requests belong to memory; do not search for "yesterday".
    if re.search(r"\b(?:what|when)\s+(?:did|have)\s+(?:i|we)\b|\b(?:do you remember|can you recall)\s+(?:what|when|my|our)\b",normal,re.I):return []
    if re.fullmatch(r"(?:hello|hi|hey|thanks|thank you|i(?:'m| am) (?:fine|good|well)|how are you(?:\s+doing|\s+today)?)[\s.!?,]*(?:thanks|thank you|too)?[\s.!?]*",normal,re.I):return []
    # Same creative categories as the original German plugin.
    if re.search(r'\b(?:write|compose|create|make)\s+(?:me\s+)?(?:a|an|some|the)\s+(?:poem|poetry|song|rap)\b',normal,re.I):
        kind=re.search(r'\b(poem|poetry|song|rap)\b',normal,re.I).group(1).lower()
        return [{'poem':'Poem','poetry':'Poetry','song':'Song','rap':'Rap'}[kind]]
    if re.search(r'\bSuno\b',normal,re.I) and re.search(r'\b(?:creates?|makes?|generates?|composes?|produces?)\b.*\b(?:music|songs?|tracks?)\b',normal,re.I):return ['Suno','Music'][:max_terms]
    patterns=[
        r'\b(?:compare|contrast)\s+(.+)$',
        r'\b(?:difference|differences|similarities)\s+between\s+(.+)$',
        r'\bwhat\s+do\s+(.+?)\s+have\s+in\s+common[?.!]*$',
    ]
    for pattern in patterns:
        match=re.search(pattern,text,re.I)
        if match:return clean_terms(split_pair(match.group(1)),text,max_terms)
    for pattern in (
        r'\b(?:travel(?:ling|ing)?|drive|driving|go|going|route|trip|journey|distance)\b.*?\bfrom\s+(.+?)\s+to\s+(.+?)[.!?]*$',
        r'\b(?:route|distance|trip)\s+between\s+(.+?)\s+and\s+(.+?)[.!?]*$',
    ):
        match=re.search(pattern,text,re.I)
        if match:return clean_terms(match.groups(),text,max_terms)
    patterns=[
        r"\bwhat\s+(?:do|can|did)\s+you\s+(?:know|tell me)\s+about\s+(.+)$",
        r"\b(?:tell\s+me|can\s+you\s+tell\s+me|could\s+you\s+tell\s+me)\s+(?:(?:something|anything|more|a little|a bit)\s+)?about\s+(.+)$",
        r"\b(?:do(?:n't| not)?\s+you\s+know|don't\s+you\s+know|have(?:n't)?\s+you\s+heard\s+(?:of|about)|are\s+you\s+familiar\s+with)\s+(.+)$",
        r"\b(?:where\s+(?:is|was|are)|where's)\s+(.+?)(?:\s+(?:located|situated))?[?.!]*$",
        r'\bhow\s+many\s+(?:people|inhabitants|residents)\s+(?:live|reside)\s+in\s+(.+)$',
        r'\bhow\s+many\s+(?:people|inhabitants|residents)\s+does\s+(.+?)\s+have[?.!]*$',
        r"\b(?:what\s+(?:is|was)\s+the\s+)?population\s+of\s+(.+)$",
        r'\b(?:what\s+do\s+you\s+think\s+(?:of|about)|what(?:\s+is|\x27s)\s+your\s+opinion\s+(?:of|on|about))\s+(.+)$',
        r'\bwhat\s+does\s+(.+?)\s+mean[?.!]*$',
        r'\b(?:meaning|definition)\s+of\s+(.+)$',
        r"\b(?:what\s+(?:is|are|was|were)|who\s+(?:is|was|are|were)|what's|who's|define|explain|describe|information\s+(?:on|about)|facts\s+about|look\s+up)\s+(.+)$",
        r"\bi\s+(?:like|love|enjoy|play|am playing)\s+(?:playing\s+)?(.+)$",
    ]
    for pattern in patterns:
        match=re.search(pattern,normal,re.I)
        if match:return clean_terms([match.group(1)],normal,max_terms)
    return None
