from __future__ import annotations

import re
from typing import Any


LAST_EVAL: dict[str, Any] | None = None


FACT_QUESTION_PATTERNS = [
    "wie viele",
    "wieviel",
    "wann",
    "wo",
    "wer ist",
    "wer war",
    "was ist",
    "how many",
    "when",
    "where",
    "who is",
    "what is",
]

MEMORY_QUESTION_PATTERNS = [
    "was habe ich",
    "was hab ich",
    "was haben wir",
    "was war gestern",
    "was war vorgestern",
    "was war vor",
    "was haben wir vor",
    "woran haben wir",
    "wann haben wir",
    "woran erinnerst du dich",
    "was hast du gespeichert",
    "wer ist mein",
    "wer ist meine",
    "wer war mein",
    "wer war meine",
]

OPINION_PATTERNS = [
    "was hältst du",
    "was haeltst du",
    "was denkst du",
    "deine sicht",
    "deine meinung",
    "wie siehst du",
    "was würdest du",
    "was wuerdest du",
]

PHILOSOPHY_PATTERNS = [
    "bewusstsein",
    "existenz",
    "selbst",
    "wahrheit",
    "harmonie",
    "sinn",
    "freiheit",
    "seele",
    "wirklichkeit",
    "identität",
    "identitaet",
]

SYMBOLIC_PATTERNS = [
    "symbol",
    "symbole",
    "symbolik",
    "symbolisch",
    "zahlen",
    "zahlencode",
    "zahlenmuster",
    "numerologie",
    "gematria",
    "gematrie",
    "vesica",
    "maat",
    "ma'at",
    "da vinci code",
    "codierung",
    "codiert",
    "dimensionen",
    "mona lisa",
    "christus-code",
    "666",
    "777",
    "299792458",
    "lichtgeschwindigkeit",
    "sacred geometry",
    "heilige geometrie",
    "matrix",
    "deutung",
    "interpretation",
]

UNCERTAINTY_MARKERS = [
    "ich weiß nicht",
    "ich weiss nicht",
    "ich bin mir nicht sicher",
    "nicht sicher",
    "kann ich nicht sicher sagen",
    "möglicherweise",
    "moeglicherweise",
    "vielleicht",
    "vermutlich",
    "vorsichtig formuliert",
    "i don't know",
    "not sure",
    "not certain",
]

OVERCONFIDENT_MARKERS = [
    "definitiv",
    "garantiert",
    "ohne zweifel",
    "zweifellos",
    "100% sicher",
    "bewiesen",
    "endgültig",
    "endgueltig",
    "definitely",
    "guaranteed",
    "without doubt",
]

ABSOLUTE_CLAIM_MARKERS = [
    "wissenschaftlich bewiesen",
    "empirisch bewiesen",
    "endgültig bewiesen",
    "endgueltig bewiesen",
    "ist bewiesen",
    "definitiv bewiesen",
    "garantiert wahr",
    "steht fest",
    "ist fakt",
    "proven fact",
    "scientifically proven",
]

EVIDENCE_MARKERS = [
    "quelle",
    "source",
    "beleg",
    "laut",
    "nach",
    "gespeichert",
    "memory",
    "erinnerung",
    "im person graph",
    "im super memory",
]

DRIFT_MARKERS = [
    "eigentlich geht es darum",
    "die wahre frage",
    "nicht die frage ist",
    "the real question",
    "what really matters",
]

PLACE_PATTERNS = [
    r"\b(in|liegt in|befindet sich in|region|bezirk|stadt|dorf|ort)\b",
    r"\b(oberfranken|bayern|deutschland|germany|austria|schweiz)\b",
    r"\b(straße|strasse|platz|allee|gasse|weg)\b",
]


# Bilingual RPG adaptation. These lexical scores are heuristics, not fact checks.
FACT_QUESTION_PATTERNS += ['who was', 'how much', 'what do you know about', 'tell me about',
                          'was weißt du über', 'was weisst du ueber', 'kennst du', 'wie viel']
MEMORY_QUESTION_PATTERNS += ['what did i', 'what have i', 'what did we', 'what have we', 'do you remember', 'what did you save', 'who is my', 'who was my']
OPINION_PATTERNS += ['what do you think', 'your opinion', 'your view', 'how do you see', 'what would you']
PHILOSOPHY_PATTERNS += ['consciousness', 'existence', 'truth', 'meaning', 'freedom', 'soul', 'reality', 'identity']
SYMBOLIC_PATTERNS += ['symbolic', 'numerology', 'number pattern', 'symbolism', 'interpretation', 'speed of light']
UNCERTAINTY_MARKERS += ["i do not know", "i don't have", "i have no", "i cannot verify", "i can't verify", "uncertain", "possibly", "perhaps", "i'm not sure", "i am not sure", "keine erinnerung", "nicht gespeichert", "keinen eintrag"]
UNCERTAINTY_MARKERS += ['not proven', 'not scientifically proven', 'not established', 'not a proven fact', 'nicht bewiesen', 'nicht belegt']
OVERCONFIDENT_MARKERS += ['certainly', 'undoubtedly', 'proven', '100% sure']
ABSOLUTE_CLAIM_MARKERS += ['definitely proven', 'empirically proven', 'guaranteed true', 'proven beyond doubt']
EVIDENCE_MARKERS += ['according to', 'record', 'saved', 'evidence', 'citation']
PLACE_PATTERNS += [r'\b(city|village|town|district|region|located in|street|avenue|square)\b']


def _settings(settings: Any) -> dict[str, Any]:
    if isinstance(settings, dict):
        return settings
    try:
        return vars(settings)
    except Exception:
        return {}


def _get(settings: Any, key: str, default: Any) -> Any:
    return _settings(settings).get(key, default)


def _clamp(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, value))


def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9äöüÄÖÜß_+\-]+", _norm(text))


def _count_hits(text: str, patterns: list[str]) -> int:
    return sum(1 for pattern in patterns if pattern in text)


def _overlap_score(a: str, b: str) -> float:
    ta = set(_tokenize(a))
    tb = set(_tokenize(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta | tb), 1)


def _is_symbolic_question(text: str) -> bool:
    t = _norm(text)
    if any(pattern in t for pattern in SYMBOLIC_PATTERNS):
        return True
    return bool(re.search(r"\b\d{2,}\b", t) and any(marker in t for marker in ["code", "bedeut", "deut", "muster", "pattern"]))


def _is_person_relation_question(text: str) -> bool:
    t = _norm(text)
    if not re.search(r"\bwer\s+(?:ist|sind|war|waren)\s+(?:mein|meine|meiner|meinen)\b", t):
        return False
    relation_terms = [
        "bruder",
        "brueder",
        "brüder",
        "schwester",
        "mutter",
        "mama",
        "vater",
        "papa",
        "oma",
        "grossmutter",
        "großmutter",
        "opa",
        "grossvater",
        "großvater",
        "freund",
        "freundin",
        "patentante",
        "pate",
        "patin",
        "tante",
        "onkel",
        "partner",
        "partnerin",
    ]
    return any(re.search(rf"\b{re.escape(term)}\b", t) for term in relation_terms)


def _is_memory_question(text: str) -> bool:
    t = _norm(text)
    return any(pattern in t for pattern in MEMORY_QUESTION_PATTERNS) or _is_person_relation_question(t)


def _is_opinion_question(text: str) -> bool:
    t = _norm(text)
    return any(pattern in t for pattern in OPINION_PATTERNS)


def _is_fact_question(text: str) -> bool:
    t = _norm(text)
    if _is_memory_question(t) or _is_opinion_question(t) or _is_symbolic_question(t):
        return False
    if any(re.search(r'\b'+re.escape(pattern)+r'\b', t) for pattern in FACT_QUESTION_PATTERNS):
        return True
    return bool(re.search(r"\bwo\s+(ist|war|liegt|lag|befindet|kommt|kam|steht|stand)\b", t))


def question_type(text: str) -> str:
    t = _norm(text)
    if _is_memory_question(t):
        return "memory"
    if re.search(r"\d\s*[+*/×÷−-]\s*\d", t):
        return "calculation"
    if _is_symbolic_question(t):
        return "symbolic"
    if _is_opinion_question(t):
        return "opinion"
    if _is_fact_question(t):
        return "fact"
    if any(pattern in t for pattern in PHILOSOPHY_PATTERNS):
        return "philosophical"
    return "general"


def _memory_recall_info(context: dict[str, Any], user_input: str, output: str = "") -> dict[str, Any]:
    memory = context.get("super_memory") if isinstance(context, dict) else {}
    if not isinstance(memory, dict):
        return {"count": 0, "matched": False, "memory_question": _is_memory_question(user_input)}

    memories = memory.get("memories") or []
    count = len(memories) if isinstance(memories, list) else 0
    memory_question = _is_memory_question(user_input)
    if count <= 0:
        return {"count": 0, "matched": False, "memory_question": memory_question}

    if memory_question:
        return {"count": count, "matched": True, "memory_question": True}

    out = _norm(output)
    if any(marker in out for marker in ["erinnere", "gespeichert", "memory", "super memory", "person graph"]):
        return {"count": count, "matched": True, "memory_question": True}

    return {"count": count, "matched": False, "memory_question": False}


def _has_grounded_memory_recall(context: dict[str, Any], user_input: str, output: str = "") -> bool:
    info = _memory_recall_info(context, user_input, output)
    return bool(info.get("memory_question") and info.get("matched") and int(info.get("count", 0) or 0) > 0)


def _has_evidence_marker(output: str) -> bool:
    out = _norm(output)
    return _count_hits(out, EVIDENCE_MARKERS) > 0 or _count_hits(out, UNCERTAINTY_MARKERS) > 0


def _has_unsupported_specifics(user_input: str, output: str) -> bool:
    if _is_symbolic_question(user_input) or question_type(user_input) == "calculation":
        return False
    if not _is_fact_question(user_input):
        return False
    out = _norm(output)
    has_number = bool(re.search(r"\b\d+\b", output or ""))
    has_place = any(bool(re.search(pattern, out)) for pattern in PLACE_PATTERNS)
    return (has_number or has_place) and _count_hits(out, UNCERTAINTY_MARKERS) == 0


def _has_unsupported_absolute_claim(user_input: str, output: str) -> bool:
    combined = _norm(output)
    out = _norm(output)
    if not any(marker in combined for marker in ABSOLUTE_CLAIM_MARKERS):
        return False
    return _count_hits(out, UNCERTAINTY_MARKERS) == 0


def _has_unsupported_memory_claim(user_input: str, output: str, context: dict[str, Any]) -> bool:
    if not _is_memory_question(user_input):
        return False
    if _has_grounded_memory_recall(context, user_input, output):
        return False
    out = _norm(output)
    if _count_hits(out, UNCERTAINTY_MARKERS) > 0:
        return False
    if any(marker in out for marker in ["weiß ich nicht", "weiss ich nicht", "keine erinnerung", "kein memory", "nicht gespeichert"]):
        return False
    return len(_tokenize(output)) >= 4


def _truth_priority_factor(user_input: str, output: str) -> float:
    if _has_unsupported_absolute_claim(user_input, output):
        return 0.35
    if _has_unsupported_specifics(user_input, output):
        return 0.15
    qtype = question_type(user_input)
    out = _norm(output)
    if qtype == "fact" and _count_hits(out, OVERCONFIDENT_MARKERS) > 0:
        return 0.45
    if qtype == "fact" and re.search(r"\b\d+\b", output or "") and not _has_evidence_marker(output):
        return 0.6
    if qtype == "symbolic":
        return 0.95
    if qtype == "opinion":
        return 0.9
    return 1.0


def _estimate_RB_from_engine(context: dict[str, Any]) -> tuple[float, float]:
    try:
        engine_eval = context.get("maat_engine") or {}
        if isinstance(engine_eval, dict):
            if "last_eval" in engine_eval and isinstance(engine_eval["last_eval"], dict):
                engine_eval = engine_eval["last_eval"]
            return _clamp(float(engine_eval.get("R", 7.0))), _clamp(float(engine_eval.get("B", 6.5)))
    except Exception:
        pass
    return 7.0, 6.5


def _estimate_context_coherence(user_input: str, output: str) -> float:
    overlap = _overlap_score(user_input, output)
    score = 3.5 + overlap * 7.0
    if "deine frage" in _norm(output):
        score += 0.7
    return _clamp(score)


def _estimate_evidence_proximity(user_input: str, output: str, context: dict[str, Any]) -> float:
    score = 3.0
    out = _norm(output)
    if _has_grounded_memory_recall(context, user_input, output):
        score += 3.0
    if _count_hits(out, UNCERTAINTY_MARKERS) > 0:
        score += 1.5
    if any(marker in out for marker in ["gespeichert", "erinnere", "memory", "person graph"]):
        score += 1.2
    if any(marker in out for marker in ["quelle", "source", "beleg", "aufzeichnung"]):
        score += 1.0
    if _is_symbolic_question(user_input):
        score += 1.2
    return _clamp(score)


def _estimate_uncertainty(user_input: str, output: str) -> float:
    qtype = question_type(user_input)
    score = 2.5
    if qtype == "fact":
        score += 2.5
    if qtype == "memory":
        score += 1.5
    if _count_hits(_norm(output), UNCERTAINTY_MARKERS) > 0:
        score += 0.8
    if qtype != "symbolic" and re.search(r"\b\d+\b", output or "") and not _has_evidence_marker(output):
        score += 1.5
    return _clamp(score)


def _estimate_drift(user_input: str, output: str) -> float:
    score = 1.5
    overlap = _overlap_score(user_input, output)
    if overlap < 0.08:
        score += 3.0
    elif overlap < 0.15:
        score += 1.8
    score += min(_count_hits(_norm(output), DRIFT_MARKERS) * 1.2, 3.0)
    return _clamp(score)


def _estimate_speculation_pressure(user_input: str, output: str) -> float:
    score = 1.5
    out = _norm(output)
    score += min(_count_hits(out, OVERCONFIDENT_MARKERS) * 1.5, 4.0)
    if question_type(user_input) == "fact" and re.search(r"\b\d+\b", output or "") and not _has_evidence_marker(output):
        score += 2.0
    return _clamp(score)


def evaluate_antihallu(user_input: str, output: str, context: dict[str, Any] | None = None, settings: Any | None = None) -> dict[str, Any]:
    context = context or {}
    qtype = question_type(user_input)
    symbolic_lenient = bool(_get(settings, "antihallu_symbolic_lenient", True))

    r_value, b_value = _estimate_RB_from_engine(context)
    c_value = _estimate_context_coherence(user_input, output)
    e_value = _estimate_evidence_proximity(user_input, output, context)
    u_value = _estimate_uncertainty(user_input, output)
    d_value = _estimate_drift(user_input, output)
    sh_value = _estimate_speculation_pressure(user_input, output)

    memory_grounded = _has_grounded_memory_recall(context, user_input, output)
    unsupported_specifics = _has_unsupported_specifics(user_input, output)
    unsupported_claim = _has_unsupported_absolute_claim(user_input, output)
    unsupported_memory = _has_unsupported_memory_claim(user_input, output, context)
    numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", output or ''))
    # Check the actual clock fact independently: unrelated retrieved articles
    # must not drown out a short, supported date/time answer's lexical overlap.
    for evidence in (str(context.get('grounding_text') or ''), str(context.get('clock_context') or '')):
        grounded_numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", evidence))
        if evidence and (not numbers or numbers <= grounded_numbers) and _overlap_score(output, evidence) >= .08:
            unsupported_specifics = False
            e_value = _clamp(e_value + 3.0)
            break
    unsupported = unsupported_specifics or unsupported_claim or unsupported_memory
    truth_factor = _truth_priority_factor(user_input, output)

    if memory_grounded:
        qtype = "memory"
        e_value = _clamp(e_value + 1.5)
        u_value = _clamp(u_value * 0.45)
        d_value = _clamp(d_value * 0.55)
        sh_value = _clamp(sh_value * 0.5)
        truth_factor = max(truth_factor, 1.0)
        unsupported_specifics = False
        unsupported_memory = False
        unsupported = unsupported_claim

    if unsupported_specifics:
        u_value = _clamp(u_value + 2.0)
        sh_value = _clamp(sh_value + 3.5)
    if unsupported_claim:
        u_value = _clamp(u_value + 1.6)
        sh_value = _clamp(sh_value + 2.4)
    if unsupported_memory:
        u_value = _clamp(u_value + 2.2)
        sh_value = _clamp(sh_value + 2.0)

    if qtype == "philosophical":
        d_value = _clamp(d_value * 0.6)

    if qtype == "symbolic" and symbolic_lenient:
        unsupported_specifics = False
        unsupported_memory = False
        unsupported = unsupported_claim
        e_value = _clamp(e_value + 1.0)
        u_value = _clamp(u_value * 0.55)
        d_value = _clamp(d_value * 0.75)
        sh_value = _clamp(sh_value * 0.65)
        if not unsupported_claim:
            truth_factor = max(truth_factor, 0.95)

    eps = 0.01
    ahf_raw = (r_value * b_value * c_value * e_value) / (u_value + d_value + sh_value + eps)
    ahf = _clamp(ahf_raw / 10.0)
    hrs = round(float((u_value + d_value + sh_value) / (r_value + b_value + c_value + e_value + eps)), 3)

    mode = normalize_mode(_get(settings, "antihallu_mode", "soften"))
    soften_thr = float(_get(settings, "antihallu_soften_threshold", 0.55) or 0.55)
    strict_thr = float(_get(settings, "antihallu_strict_threshold", 0.85) or 0.85)
    action = "pass"
    if unsupported:
        action = "strict" if mode == "strict" else "soften"
    elif hrs >= strict_thr:
        action = "strict" if mode == "strict" else "soften"
    elif hrs >= soften_thr:
        action = "soften" if mode in {"soften", "strict"} else "warn"

    if qtype in {"general", "opinion", "philosophical", "calculation"} and not unsupported:
        action = "pass"
    if memory_grounded and not unsupported:
        action = "pass"
    if qtype == "symbolic" and symbolic_lenient and not unsupported:
        action = "pass"

    result = {
        "R": round(r_value, 2),
        "B": round(b_value, 2),
        "C": round(c_value, 2),
        "E": round(e_value, 2),
        "U": round(u_value, 2),
        "D": round(d_value, 2),
        "S_h": round(sh_value, 2),
        "AHF": round(ahf, 2),
        "AHF_raw": round(ahf_raw, 2),
        "HRS": hrs,
        "qtype": qtype,
        "truth_factor": round(truth_factor, 2),
        "unsupported_specifics": bool(unsupported_specifics),
        "unsupported_absolute_claim": bool(unsupported_claim),
        "unsupported_memory_claim": bool(unsupported_memory),
        "memory_grounded": bool(memory_grounded),
        "symbolic_lenient": bool(symbolic_lenient),
        "action": action,
    }
    result["text"] = (
        f"AHF={result['AHF']:.2f} HRS={result['HRS']:.3f} T={result['truth_factor']:.2f} "
        f"qtype={qtype} action={action} | R={r_value:.1f} B={b_value:.1f} C={c_value:.1f} "
        f"E={e_value:.1f} U={u_value:.1f} D={d_value:.1f} S_h={sh_value:.1f}"
        + (" UNSUPPORTED_SPECIFICS" if unsupported_specifics else "")
        + (" UNSUPPORTED_CLAIM" if unsupported_claim else "")
        + (" UNSUPPORTED_MEMORY" if unsupported_memory else "")
    )
    return result


def normalize_mode(value: str) -> str:
    raw = str(value or '').lower().strip()
    return raw if raw in {'warn', 'soften', 'strict'} else 'soften'


def _en(settings):
    return _get(settings, 'language', 'de') == 'en'


def build_antihallu_prompt(settings: Any, user_input: str = '') -> str:
    if not _get(settings, 'antihallu_enabled', False):
        return ''
    if _en(settings):
        body = ('Do not invent facts, memories, citations or sources. Mark uncertainty and say specifically what evidence is missing. '
                'Use the actual conversation, retrieved memories and supplied offline Wiki excerpts; a source label alone proves nothing. '
                'For symbols and number patterns, distinguish the user premise, calculation, interpretation and historical evidence. '
                'Treat the RPG world as fiction; distinguish it from real-world facts. Do not replace a factual answer with poetic evasion.')
    else:
        body = ('Erfinde keine Fakten, Erinnerungen, Zitate oder Quellen. Benenne Unsicherheit und konkret fehlende Belege. '
                'Nutze den tatsächlichen Gesprächskontext, abgerufene Erinnerungen und vorhandene Offline-Wiki-Auszüge; eine Quellenbehauptung allein ist kein Beleg. '
                'Bei Symbolik und Zahlenmustern trenne Nutzervorgabe, Rechnung, Deutung und historische Belege. '
                'Trenne die fiktive RPG-Welt von realen Tatsachen. Weiche bei Faktfragen nicht poetisch aus.')
    return '[MAAT_ANTI_HALLU]\n'+body+'\n[/MAAT_ANTI_HALLU]'


def apply_antihallu_guard(settings: Any, user_input: str, output: str, context=None):
    global LAST_EVAL
    if not _get(settings, 'antihallu_enabled', False):
        return output, None
    # Visible H/B/S/V/R ratings are response diagnostics, not factual quantities.
    prose = re.sub(r'^\s*(?:H\s*=.*|[HBSVR]\s*:.*|Stability\s*[≈=:].*)$', '', output, flags=re.M)
    result = evaluate_antihallu(user_input, prose, context or {}, settings)
    result['heuristic'] = True
    LAST_EVAL = result
    action, qtype, en = result['action'], result['qtype'], _en(settings)
    if action in ('pass','warn'):
        return output, result
    unsupported = any(result[key] for key in ('unsupported_specifics','unsupported_absolute_claim','unsupported_memory_claim'))
    if unsupported or action == 'strict':
        if qtype == 'memory':
            guarded = ('I cannot support that from the retrieved memories. I do not want to attribute something to you that you may not have said. '
                       'A keyword or approximate date would help.' if en else
                       'Das kann ich aus den abgerufenen Erinnerungen nicht belegen. Ich möchte dir nichts zuschreiben, was du möglicherweise nicht gesagt hast. '
                       'Ein Stichwort oder ungefähres Datum würde helfen.')
        else:
            guarded = ('I do not have enough supporting evidence to present that as a definite fact. '
                       'A reliable source or more specific context would help.' if en else
                       'Mir fehlen ausreichende Belege, um das als feste Tatsache darzustellen. '
                       'Eine verlässliche Quelle oder ein genauerer Kontext würde helfen.')
    else:
        guarded = ('I am not fully certain about this, so treat the following as a cautious assessment:\n\n' if en else
                   'Dabei bin ich nicht vollständig sicher; verstehe das Folgende als vorsichtige Einordnung:\n\n')+output
    return guarded, result


def get_last_antihallu():
    return LAST_EVAL


def remember_antihallu(result):
    global LAST_EVAL
    LAST_EVAL = result


def report_lines(result=None, language='de'):
    result = result or LAST_EVAL
    if not result:
        return ['PLP Anti-Hallu: no answer analysed yet.' if language=='en' else 'PLP Anti-Hallu: noch keine Antwort analysiert.']
    return [result['text'], 'Heuristic estimate, not a fact check or truth probability.' if language=='en' else
            'Heuristische Einschätzung, keine Faktenprüfung oder Wahrheitswahrscheinlichkeit.']
