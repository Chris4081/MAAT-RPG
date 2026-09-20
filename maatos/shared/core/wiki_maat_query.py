"""Extract the subject of a MAAT assessment, not the assessment instruction."""
import re

MAAT = r"(?:maat|ma['’]at|m\.a\.a\.t\.?)"
SEPARATOR = r"[\s_\-‐‑‒–—]*"
VALUE = rf"\b{MAAT}{SEPARATOR}(?:wert(?:e|es|en)?|scores?|values?|ratings?|assessment|analysis|bewertung|beurteilung|analyse|einschätzung|einschaetzung)\b"
ACTION = r"(?:berechne(?:n)?|bestimme(?:n)?|ermittle(?:n)?|bewerte(?:n)?|analysiere(?:n)?|schätze|schaetze|calculate|compute|assess|evaluate|rate|estimate|determine|analyse|analyze)"
ARTICLE = r"(?:den|die|das|der|dem|des|ein|eine|einen|einem|einer|the)"
CONNECTOR = r"(?:von|für|fuer|zu|über|ueber|of|for)"
QUOTED = re.compile(r'''"([^"\n]+)"|„([^“”\n]+)[“”]|“([^”\n]+)”|'([^'\n]+)'|‘([^’\n]+)’|«([^»\n]+)»''')


def _strip_tail(text):
    text = text.strip()
    text = re.sub(rf'\s+{ACTION}(?:\s+(?:bitte|please))?[.!? ]*$', '', text, flags=re.I)
    return re.sub(r"\s+(?:bitte|kurz|ausführlich|ausfuehrlich|please|for\s+me|in\s+detail|using\s+wikipedia|based\s+on\s+wikipedia|on\s+a\s+scale|anhand\s+von\s+wikipedia|auf\s+(?:einer|der)\s+skala)\b.*$", '', text, flags=re.I).strip(' \t\n.!?;:')


def assessment_topics(raw):
    """Return None for other intents, [] for a MAAT request without a subject.

    Quoted titles are returned intact and flagged, so conjunctions and words such
    as 'ist' inside a title are not interpreted as chat grammar.
    """
    marker = re.search(VALUE, raw, re.I)
    subject = None
    if marker:
        # Topic before the label: 'für Mona Lisa den MAAT-Wert berechnen'.
        before = re.search(rf"\b{CONNECTOR}\s+(.+?)\s+(?:{ARTICLE}\s+)?{VALUE}", raw, re.I)
        possessive = re.search(rf"(.+?)['’]s\s+{VALUE}", raw, re.I)
        after = raw[marker.end():].strip()
        after = re.sub(rf"^(?:{ACTION}\s*)?(?:{CONNECTOR}\b\s*|[:=]\s*)", '', after, flags=re.I)
        after = _strip_tail(after)
        if re.fullmatch(rf"(?:{ACTION}|bitte|please|be|is|was|high|low|hoch|aus|ist|beträgt|betraegt|werden|kann|können|koennen|\s)*", after, re.I):
            after = ''
        if after:
            subject = after
        elif before:
            subject = before.group(1)
        elif possessive:
            subject = re.sub(rf'^.*?\b{ACTION}\s+', '', possessive.group(1),flags=re.I)
            subject = re.sub(r"^(?:what\s+(?:is|was|would|could)|what['’]s)\s+", '',subject,flags=re.I)
        else:
            # '"Mona Lisa": MAAT-Wert' also has an explicit bounded subject.
            quotes = list(QUOTED.finditer(raw[:marker.start()]))
            if quotes:
                subject = quotes[-1].group(0)
            else:
                return []
    else:
        # MAAT assessment without the noun 'Wert'. Ordinary MAAT questions stay
        # with the usual wiki rules ('Was ist MAAT?' is not an assessment).
        pattern = rf"\b{ACTION}\s+(.+?)\s+(?:nach|mit|anhand\s+von|gemäß|gemaess|using|with|according\s+to)\s+(?:{ARTICLE}\s+)?{MAAT}\b"
        match = re.search(pattern, raw, re.I)
        if match:
            subject = match.group(1)
        else:
            return None
    subject = _strip_tail(subject)
    # Common object descriptions are not part of the encyclopedia title.
    subject = re.sub(rf"^{ARTICLE}\s+", '', subject, flags=re.I)
    subject = re.sub(rf'^(?:Wert|Score|Bewertung|value|rating)\s+{CONNECTOR}\s+', '', subject, flags=re.I)
    subject = re.sub(r"^(?:Gemälde|Gemaelde|Bild|Kunstwerk|Werk|Buch|Roman|Film|Lied|Song|Person|Musiker|Stadt|Ort|Dorf|Ortschaft)\s+(?:namens\s+)?", '', subject, flags=re.I)
    quotes = list(QUOTED.finditer(subject))
    if quotes:
        # Only treat quotes as the subject when they form the subject list.
        remainder = QUOTED.sub('', subject)
        if re.fullmatch(r"[\s,;:+&.!?]*(?:(?:und|oder|mit|vs\.?|versus|and|or)[\s,;:+&.!?]*)*", remainder, re.I):
            return [(next(value for value in match.groups() if value is not None).strip(), True) for match in quotes]
    return [(subject, False)] if subject else []
