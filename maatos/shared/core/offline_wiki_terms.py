"""Term rules copied from the user's MAAT Textgen offline wiki (2026-09-09).

Only the pure word/intent extraction is shared, with no runtime dependency on
Textgen, Gradio, its archive path, or its prompt injection. Additional place
questions retain the RPG fixes. Original aliases are search heuristics, not facts.
"""
import re
from typing import List, Optional

STOPWORDS = {
    "ich", "du", "wir", "ihr", "sie", "er", "es", "der", "die", "das",
    "ein", "eine", "einen", "einem", "einer", "und", "oder", "aber",
    "bin", "bist", "seid", "ist", "sind", "war", "waren", "wird", "wurde",
    "habe", "hast", "hat", "haben", "muss", "musst", "müssen", "muessen",
    "was", "wer", "wie", "wo", "wann",
    "warum", "wieso", "weshalb", "bitte", "kurz", "mir", "mich", "dir",
    "dich", "zu", "zur", "zum", "von", "über", "ueber", "mit", "für", "fuer", "im",
    "im", "in", "am", "an", "auf", "nach", "den", "dem", "des",
    "the", "a", "an", "and", "or", "what", "who", "how", "why", "is",
    "are", "please", "about", "tell", "explain",
    "hallo", "servus", "hi", "hey", "moin", "grüß", "gruess",
    "mmh", "mhm", "ähm", "aehm", "ehm", "hm", "hmm",
    "ja", "nein", "ok", "okay", "richtig", "super", "gut", "danke", "jetzt",
    "kenne", "kennst", "kennt", "auch",
    "mein", "meine", "meiner", "meinem", "meinen", "meines", "meinst",
    "dein", "deine", "deiner", "deinem", "deinen", "deines",
    "meinung", "dazu", "darüber", "darueber",
    "kann", "kannst", "können", "koennen", "könntest", "koenntest",
    "sage", "sagen", "erzähl", "erzaehl", "erzähle", "erzaehle", "erzählen", "erzaehlen",
    "mach", "mache", "machen", "bau", "baue", "bauen", "erstelle", "erstellen",
    "erstellt", "generiere", "generieren", "generiert",
    "berechne", "berechnen", "bestimme", "ermittle", "maß", "mass",
    "maatwert", "wert",
    "viele", "einwohner", "bewohner", "menschen", "population",
    "weiß", "weis", "nicht", "macht", "sich", "sowas", "gedanken", "denke",
    "doch", "stimmt", "trainiert", "worden", "möchte", "moechte", "will",
    "fahren", "fahre", "fährst", "faehrst", "fahrt", "auto", "route", "reise",
    "spiele", "spiel", "spielst", "spielen", "gespielt", "zocke", "zockst", "zocken",
    "gerne", "gern", "liebe", "mag",
    "vergleich", "vergleiche", "vergleichen", "unterschied", "unterschiede",
    "gemeinsam", "besser", "schlechter", "ähnlich", "aehnlich",
    "tagebuch", "eintrag", "einträge", "eintraege", "leben", "hinein",
    "korrigiere", "korrigieren", "korrigiert", "korrektur",
    "ehren", "geschrieben", "schrieb", "schreiben", "verfasst",
    "suche", "suchst", "suchen", "gesucht", "finde", "finden",
    "musiker", "musikerin", "rapper", "sänger", "saenger",
    "strophe", "strophen", "strofe", "strofen", "refrain", "refree", "refrains",
}


NON_WIKI_CONTEXT_BLOCKS = [
    re.compile(
        r"\[MAAT_FILE_BUILDER_TEST_LOG\].*?\[/MAAT_FILE_BUILDER_TEST_LOG\]",
        flags=re.I | re.S,
    ),
]


PATTERNS = [
    r"^(?:!wiki|!wikipedia)\s+(.+)$",
    r"^/maat\s+wiki\s+(?!on$|off$|status$|test\b)(.+)$",
    r"\b(?:berechne|berechnen|bestimme|ermittle)\s+(?:den|die|das)?\s*(?:maat[-_\s]*wert|maatwert)\s+(?:von|für|fuer|zu)\s+(.+)$",
    r"\b(?:was\s+ist|wie\s+ist|zeige|gib\s+mir)?\s*(?:der|den|die|das)?\s*(?:maat[-_\s]*wert|maatwert)\s+(?:von|für|fuer|zu)\s+(.+)$",
    r"\b(?:was\s+ist\s+)?(?:deine|dein|eure|ihre)?\s*(meinung)\s+(?:dazu|darüber|darueber)\??$",
    r"\b(?:was\s+ist\s+)?(?:deine|dein|eure|ihre)?\s*meinung\s+(?:zu|zur|zum|über|ueber|von)\s+(.+)$",
    r"\bwas\s+sagst\s+du\s+(?:zu|zur|zum|über|ueber|von)\s+(.+?)(?:[?.!]|$)",
    r"\bwas\s+hältst\s+du\s+(?:von|über|ueber|zur|zum)\s+(.+)$",
    r"\b(?:was\s+)?(?:weißt|weisst|weist|weis)\s+du\s+(?:über|ueber|zu|von)\s+(.+?)(?:[?.!]|$)",
    r"\bwie\s+viele\s+(?:einwohner|bewohner|menschen)\s+(?:hat|haben)\s+(.+)$",
    r"\bwie\s+viele\s+(?:einwohner|bewohner|menschen)\s+(?:leben|wohnen)\s+(?:in|auf)\s+(.+)$",
    r"\b(?:einwohnerzahl|bevölkerung|bevoelkerung|population)\s+(?:von|in|für|fuer)\s+(.+)$",
    r"\b(?:ich\s+)?(?:spiele|spiel|zocke|zocken)\s+(?:gerne|gern)?\s*(.+)$",
    r"\b(?:ich\s+)?(?:liebe|mag)\s+(?:das\s+spiel\s+)?(.+)$",
    r"\b(?:ich\s+)?(?:bin|bist|seid|sind)\s+(?:ein|eine|einen|einem|einer)?\s*(.+)$",
    r"\bzu\s+ehren\s+(?:von\s+)?(.+?)(?:\s+(?:geschrieben|verfasst|gemacht|erstellt).*)?$",
    r"\bwie\s+(.+?)\s+(?:es\s+)?(?:sehen|gesehen|denken|machen)\s+(?:würde|wuerde|würdest|wuerdest)\b.*$",
    r"\bkannst\s+du(?:\s+mir)?(?:\s+(?:was|etwas|mehr|kurz))?\s+(?:über|ueber|zu|von)\s+(.+)$",
    r"\bkönntest\s+du(?:\s+mir)?(?:\s+(?:was|etwas|mehr|kurz))?\s+(?:über|ueber|zu|von)\s+(.+)$",
    r"\bkoenntest\s+du(?:\s+mir)?(?:\s+(?:was|etwas|mehr|kurz))?\s+(?:über|ueber|zu|von)\s+(.+)$",
    r"\bkannst\s+du(?:\s+mir)?\s+(.+?)\s+(?:erklären|erklaeren|beschreiben)\??$",
    r"\bkönntest\s+du(?:\s+mir)?\s+(.+?)\s+(?:erklären|erklaeren|beschreiben)\??$",
    r"\bkoenntest\s+du(?:\s+mir)?\s+(.+?)\s+(?:erklären|erklaeren|beschreiben)\??$",
    r"\b(?:ich\s+suche|suche|finde)\s+(?:nach\s+)?(.+)$",
    r"\bkennst\s+du(?:\s+auch)?\s+(?:den|die|das|einen|eine|einem|einer)?\s*(.+)$",
    r"\b(?:was ist|wer ist|was bedeutet|bedeutung von|definition von)\s+(.+)$",
    r"\b(?:erkläre|erklaere|definiere|beschreibe)\s+(?:mir\s+)?(.+)$",
    r"\b(?:infos?|informationen|wissen)\s+(?:zu|über|ueber|von)\s+(.+)$",
    r"\b(?:über|ueber|zu|von)\s+(.+)$",
    r"\b(?:what is|who is|define|explain|information about)\s+(.+)$",
]


def strip_non_wiki_context(text: str) -> str:
    cleaned = text or ""
    for pattern in NON_WIKI_CONTEXT_BLOCKS:
        cleaned = pattern.sub(" ", cleaned)
    return cleaned.strip()


def _norm_spaces(text: str) -> str:
    text = re.sub(r"(?<!\s)(?:\^\^|[xX][dD]+)\s*", " ", text or "")
    return re.sub(r"\s+", " ", text.strip())


def _clean_term(term: str) -> str:
    term = _norm_spaces(term)
    term = re.split(r"[?!]\s+", term, maxsplit=1)[0]
    term = re.sub(r"\s+[:;=xX]-?[dDpP)(]+$", "", term)
    term = re.sub(r"^[\"'`´“”„‚\s]+|[\"'`´“”„‚\s?.!,;:]+$", "", term)
    term = re.sub(r"[\s\^~_*#=+\\/|<>()[\]{}]+$", "", term)
    term = re.sub(r"[\"'`´“”„‚\s?.!,;:]+$", "", term)
    term = re.sub(
        r"^(?:ein|eine|einen|einem|einer|der|die|das|"
        r"von|aus|nach|in|zu|zur|zum|über|ueber|"
        r"mein|meine|meiner|meinem|meinen|meines|"
        r"dein|deine|deiner|deinem|deinen|deines)\s+",
        "",
        term,
        flags=re.I,
    )
    while True:
        cleaned = re.sub(
            r"^(?:aber|doch|auch|ja|nein|ok|okay|mmh|mhm|ähm|aehm|ehm|hm|hmm|halt|eigentlich)\s+",
            "",
            term,
            flags=re.I,
        )
        if cleaned == term:
            break
        term = cleaned
    term = re.sub(r"\bformel\s*1\b", "Formel 1", term, flags=re.I)
    term = re.sub(r"\bbuckelwahl\b", "Buckelwal", term, flags=re.I)
    term = re.sub(r"\bleonrado\b", "Leonardo", term, flags=re.I)
    term = re.sub(
        r"\s+(?:den|die|das|der|einen|eine|einem|einer)\s+"
        r"(?:musiker|musikerin|rapper|sänger|saenger|band|person|ort|stadt|dorf|film|lied|song|album)\b.*$",
        "",
        term,
        flags=re.I,
    )
    term = re.sub(
        r"^(.+?)\s+(?:den|die|das|der|einen|eine|einem|einer)\s+(.+)$",
        r"\1 \2",
        term,
        flags=re.I,
    )
    term = re.sub(r"\b(?:bitte|kurz|einfach|genau|eigentlich)\b", " ", term, flags=re.I)
    term = re.sub(r"\b(?:meine|mein)\s+ich\b.*$", "", term, flags=re.I)
    term = re.sub(r"\b(?:geschrieben|verfasst|gemacht|erstellt|gedacht)\b.*$", "", term, flags=re.I)
    term = re.sub(r"\b(?:sagen|erzählen|erzaehlen|erklären|erklaeren|beschreiben|geben)\b.*$", "", term, flags=re.I)
    term = re.sub(r"\b(?:ist|sind|war|waren|heißt|heisst)\b.*$", "", term, flags=re.I)
    term = re.sub(r"\s+(?:nicht|noch\s+nicht|gar\s+nicht|auch\s+nicht)$", "", term, flags=re.I)
    term = re.sub(
        r"\s+(?:gemeinsam|im\s+vergleich|verglichen|vergleichen|unterschiede?|"
        r"besser|schlechter|ähnlich|aehnlich|vs\.?|versus)$",
        "",
        term,
        flags=re.I,
    )
    return _norm_spaces(term)


def _apply_role_hint(term: str, raw: str) -> str:
    raw_low = (raw or "").lower()
    term_low = (term or "").strip().lower()
    music_hint = any(k in raw_low for k in ["musiker", "musikerin", "rapper", "sänger", "saenger"])

    # Common ambiguity/typo: "Materia" is a disambiguation page; the musician is "Marteria".
    if term_low == "marteria":
        return "Marteria"
    if term_low == "materia" and (music_hint or re.search(r"\b(?:korrigier|korrektur|geschrieben|schreiben)\b", raw_low)):
        return "Marteria"
    if term_low == "openai":
        return "OpenAI"
    if term_low in {"qwen", "qianwen", "tongyi qianwen"}:
        return "Alibaba Cloud"
    if term_low in {"suno", "suno ai", "suno.com"}:
        return "Suno"
    if term_low in {"musik", "music"}:
        return "Musik"
    if term_low in {"äpfel", "aepfel"}:
        return "Apfel"
    if term_low == "birnen":
        return "Birne"
    if term_low == "leonardo da vinci":
        return "Leonardo da Vinci"
    if term_low in {"formel1", "formel 1"}:
        return "Formel 1"

    return term


def _valid_term(term: str, state: dict) -> bool:
    return bool(
        term
        and len(term) >= int(state.get("offline_wiki_min_term_len", 3))
        and term.lower() not in STOPWORDS
    )


def _append_term(out: List[str], term: str, raw: str, state: dict) -> None:
    term = _apply_role_hint(_clean_term(term), raw)
    if not _valid_term(term, state):
        return
    key = term.lower()
    if key in {t.lower() for t in out}:
        return
    out.append(term)


def _route_terms(raw: str, state: dict) -> List[str]:
    terms: List[str] = []
    route_patterns = [
        r"\b(?:von|aus)\s+(.+?)\s+(?:nach|in|zur|zum|zu|bis)\s+(.+?)(?:[?.!;:]|$)",
        r"\bzwischen\s+(.+?)\s+und\s+(.+?)(?:[?.!;:]|$)",
    ]
    for pattern in route_patterns:
        m = re.search(pattern, raw, flags=re.I)
        if not m:
            continue
        _append_term(terms, m.group(1), raw, state)
        _append_term(terms, m.group(2), raw, state)
        if len(terms) >= 2:
            break
    return terms


def _paired_terms(raw: str, state: dict) -> List[str]:
    terms: List[str] = []
    if _creative_request_term(raw) or _music_creation_terms(raw):
        return terms
    pair_patterns = [
        r"\b(?:vergleiche|vergleich|unterschiede?)\s+(.+?)\s+"
        r"(?:mit|zu|gegen|gegenüber|gegenueber)\s+(.+?)(?:[?.!;:]|$)",
        r"\b(?:vergleiche|vergleich\s+(?:von|zwischen)?|unterschiede?\s+(?:zwischen|von)?|"
        r"was\s+haben)\s+(.+?)\s+und\s+(.+?)(?:\s+gemeinsam)?(?:[?.!;:]|$)",
        r"\b(.+?)\s+(?:vs\.?|versus|oder)\s+(.+?)(?:[?.!;:]|$)",
        r"\b(.+?)\s+im\s+vergleich\s+(?:zu|mit)\s+(.+?)(?:[?.!;:]|$)",
        r"\b(?:zwischen)\s+(.+?)\s+und\s+(.+?)(?:[?.!;:]|$)",
        r"\b(?:von|über|ueber|zu|zur|zum)\s+(.+?)\s+und\s+"
        r"(?:(?:von|über|ueber|zu|zur|zum)\s+)?(.+?)(?:[?.!;:]|$)",
        r"^(.+?)\s+und\s+(.+?)(?:[?.!;:]|$)",
        r"^(.+?)\s*,\s*(.+?)(?:[?.!;:]|$)",
        r"^(.+?)\s*\+\s*(.+?)(?:[?.!;:]|$)",
    ]
    for pattern in pair_patterns:
        m = re.search(pattern, raw, flags=re.I)
        if not m:
            continue
        _append_term(terms, m.group(1), raw, state)
        _append_term(terms, m.group(2), raw, state)
        if len(terms) >= 2:
            break
    return terms


def _creative_request_term(raw: str) -> Optional[str]:
    lowered = (raw or "").lower()
    creative_intent = re.search(
        r"\b(?:schreib(?:e|en|st)?|mach(?:e|en|st)?|bau(?:e|en|st)?|"
        r"erstelle(?:n|st)?|dichte|dichtest|komponiere|komponierst)\b",
        lowered,
    ) or re.search(
        r"\b(?:möchte|moechte|will)\b.*\b(?:du|dass|das)\b",
        lowered,
    )
    if not creative_intent:
        return None

    if re.search(r"\b(?:song|lied|songs|lieder)\b", lowered):
        return "Song"
    if re.search(r"\b(?:gedicht|poem|poesie)\b", lowered):
        return "Gedicht"
    if re.search(r"\b(?:rap|rappertext|raptext)\b", lowered):
        return "Rap"

    return None


def _music_creation_terms(raw: str) -> List[str]:
    lowered = (raw or "").lower()
    has_music = re.search(r"\b(?:musik|music|song|songs|lied|lieder|track|tracks)\b", lowered)
    has_creation = re.search(
        r"\b(?:erstellt|gemacht|gebaut|generiert|komponiert|produziert|"
        r"erstelle|machen|baue|generiere|komponiere|produziere)\b",
        lowered,
    )
    if not has_music:
        return []

    terms: List[str] = []
    if re.search(r"\b(?:suno|suno\s+ai|suno\.com)\b", lowered):
        terms.append("Suno")

    if has_creation or terms:
        terms.append("Musik")

    return terms


def _titlecase_name_candidates(raw: str) -> List[str]:
    names: List[str] = []
    tokens = re.findall(r"\b[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß'-]{1,}\b", raw or "")
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.lower() in STOPWORDS:
            i += 1
            continue

        run = [token]
        j = i + 1
        while j < len(tokens) and tokens[j].lower() not in STOPWORDS:
            # In lowercase chat input, two adjacent non-stopword words often mark a name.
            if len(run) >= 4:
                break
            run.append(tokens[j])
            j += 1

        if len(run) >= 2:
            candidate = " ".join(w[:1].upper() + w[1:] for w in run)
            if candidate not in names:
                names.append(candidate)
        i += 1

    return names


def _maat_value_terms(raw, state, max_terms):
    from .wiki_maat_query import assessment_topics
    subjects = assessment_topics(raw)
    if subjects is None:
        return None
    terms = []
    english = bool(re.search(r'\b(?:values?|scores?|ratings?|assessment|analysis|evaluate|calculate|compute|assess|rate|estimate|analyze|analyse)\b',raw,re.I))
    for subject, quoted in subjects:
        if quoted:
            # Preserve full artwork/book/song titles, including 'und' and 'ist'.
            if _valid_term(subject, state) and subject.casefold() not in {t.casefold() for t in terms}:
                terms.append(subject)
        elif english:
            from .offline_wiki_english import clean_terms, split_pair
            for term in clean_terms(split_pair(subject),raw,max_terms):
                if term.casefold() not in {t.casefold() for t in terms}:terms.append(term)
        else:
            paired = _paired_terms(subject, state)
            if paired:
                for term in paired:
                    _append_term(terms, term, subject, state)
            else:
                _append_term(terms, subject, subject, state)
        if len(terms) >= max_terms:
            break
    return terms[:max_terms]


def extract_main_term(text: str, state: dict = None) -> Optional[str]:
    state = state or {}
    raw = _norm_spaces(text)
    if not raw:
        return None

    maat_terms = _maat_value_terms(raw, state, 1)
    if maat_terms is not None:
        return maat_terms[0] if maat_terms else None

    from .offline_wiki_english import english_terms
    english = english_terms(raw,1)
    if english is not None:return english[0] if english else None

    lowered = raw.lower()
    music_terms = _music_creation_terms(raw)
    if music_terms:
        return music_terms[0]

    creative_term = _creative_request_term(raw)
    if creative_term:
        return creative_term

    pair_terms = _paired_terms(raw, state)
    if pair_terms:
        return pair_terms[0]

    route_terms = _route_terms(raw, state)
    if route_terms:
        return route_terms[0]

    if re.search(r"\bbewusstsein\b", lowered):
        return "Bewusstsein"
    if re.search(r"\bconsciousness\b", lowered):
        return "Consciousness"
    if re.search(r"\bchina\b", lowered) and re.search(r"\btaiwan\b", lowered):
        if re.search(r"\b(?:angreif|angreifen|angriff|krieg|invasion|attack|militär|militaer)", lowered):
            return "Taiwan-Konflikt"
        return "Chinesisch-taiwanische Beziehungen"
    if re.search(r"\b(?:qwen|qianwen|tongyi\s+qianwen)\b", lowered):
        return "Alibaba Cloud"

    correction_patterns = [
        r"\b(?:korrigiere|korrigieren|korrigiert|korrektur)\b.*?"
        r"\b([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9_-]{2,})\s+"
        r"(?:wird|wurde|ist|heißt|heisst)\b",
        r"\b([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9_-]{2,})\s+"
        r"(?:wird|wurde|ist|heißt|heisst)\s+(?:mit|ohne)\b.*?"
        r"\b(?:geschrieben|schreiben)\b",
    ]
    for pattern in correction_patterns:
        m = re.search(pattern, raw, flags=re.I)
        if m:
            term = _apply_role_hint(_clean_term(m.group(1)), raw)
            if _valid_term(term, state):
                return term

    m = re.search(
        r"^(.+?)\s+(?:kennst|kennste)\s+du\s+"
        r"(?:nicht|noch\s+nicht|gar\s+nicht|auch\s+nicht)\b",
        raw,
        flags=re.I,
    )
    if m:
        term = _apply_role_hint(_clean_term(m.group(1)), raw)
        if _valid_term(term, state):
            return term

    for candidate in _titlecase_name_candidates(raw):
        probe = candidate.lower()
        # Prefer names/entities that appear as the grammatical subject before a verb phrase.
        if re.search(rf"\b{re.escape(probe)}\b\s+(?:macht|denkt|sagt|ist|war|hat|spricht)\b", lowered):
            return _apply_role_hint(_clean_term(candidate), raw)

    for pattern in PATTERNS:
        m = re.search(pattern, raw, flags=re.I)
        if m:
            term = _apply_role_hint(_clean_term(m.group(1)), raw)
            if _valid_term(term, state):
                return term

    candidates: List[str] = []

    # Prefer adjacent title/name words before falling back to a single noun.
    for candidate in _titlecase_name_candidates(raw):
        term = _apply_role_hint(_clean_term(candidate), raw)
        if _valid_term(term, state):
            return term

    # German nouns and proper names are often capitalized. Prefer them.
    for m in re.finditer(r"\b[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9_-]{2,}\b", raw):
        token = m.group(0)
        if token.lower() not in STOPWORDS:
            candidates.append(token)

    if not candidates:
        for token in re.findall(r"\b[A-Za-zÄÖÜäöüß0-9_-]{5,}\b", raw):
            if token.lower() not in STOPWORDS:
                candidates.append(token)

    if not candidates:
        return None

    return _apply_role_hint(_clean_term(candidates[0]), raw)


def extract_main_terms(text: str, state: dict = None, max_terms: int = None) -> List[str]:
    state = state or {}
    raw = _norm_spaces(text)
    if not raw:
        return []

    if max_terms is None:
        max_terms = int(state.get("offline_wiki_max_terms", 2))
    max_terms = max(1, min(int(max_terms), 4))
    maat_terms = _maat_value_terms(raw, state, max_terms)
    if maat_terms is not None:
        return maat_terms

    from .offline_wiki_english import english_terms
    english = english_terms(raw,max_terms)
    if english is not None:return english

    terms: List[str] = []

    for term in _music_creation_terms(raw):
        _append_term(terms, term, raw, state)
        if len(terms) >= max_terms:
            return terms
    if terms:
        return terms[:max_terms]

    creative_term = _creative_request_term(raw)
    if creative_term:
        _append_term(terms, creative_term, raw, state)
        return terms[:max_terms]

    for term in _paired_terms(raw, state):
        _append_term(terms, term, raw, state)
        if len(terms) >= max_terms:
            return terms

    for term in _route_terms(raw, state):
        _append_term(terms, term, raw, state)
        if len(terms) >= max_terms:
            return terms

    primary = extract_main_term(raw, state)
    if primary:
        _append_term(terms, primary, raw, state)

    return terms[:max_terms]


# Preserve natural place questions supported by the RPG before this import.
PATTERNS[:0] = [
    r"\b(?:kennst|kennste)\s+du\s+(?:(?:etwa|denn|wirklich|auch|noch|gar)\s+)*nicht\s+(.+?)(?:[?!;]|$)",
    r"\bwo\s+(?:ist|liegt|befindet\s+sich)\s+(.+?)(?:[?!;]|$)",
    r"\bwhere\s+is\s+(.+?)(?:[?!;]|$)",
    r"\b(?:erzähl|erzähle|erzaehl|erzaehle)\s+(?:mir\s+)?(?:etwas\s+)?(?:über|ueber|von)\s+(.+)$",
]
# Keep everyday acknowledgements from becoming an accidental noun lookup.
STOPWORDS.update({'geht', 'gerade', 'heute', 'gestern', 'morgen', 'dabei', 'etwas'})
from .offline_wiki_english import STOPWORDS as ENGLISH_STOPWORDS
STOPWORDS.update(ENGLISH_STOPWORDS)
