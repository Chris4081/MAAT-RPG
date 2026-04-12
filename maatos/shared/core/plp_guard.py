# -*- coding: utf-8 -*-
"""
PLP-based anti-hallucination helpers for MAAT systems.

PLP = ((H * B * S * V * R) * K) / (Hindernisse + ΔE + ε)
"""

from __future__ import annotations

import re


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "bei", "bin", "bist", "but", "by",
    "das", "dass", "dem", "den", "der", "des", "die", "dir", "doch", "du",
    "ein", "eine", "einer", "einem", "einen", "eines", "er", "es", "for", "from",
    "hat", "have", "ich", "i", "if", "im", "in", "ist", "it", "its", "mit",
    "nicht", "of", "on", "or", "sie", "so", "that", "the", "their", "there",
    "this", "to", "und", "von", "was", "we", "wie", "wir", "with", "you", "your",
    "zu", "zum", "zur",
}

_ABSOLUTES = re.compile(
    r"\b(immer|nie|definitiv|sicher|exakt|genau|bewiesen|garantiert|"
    r"always|never|definitely|certainly|exactly|proven|guaranteed)\b",
    re.IGNORECASE,
)
_HEDGES = re.compile(
    r"\b(vielleicht|wahrscheinlich|vermutlich|scheint|wirkt|ungefähr|grob|"
    r"möglicherweise|moeglicherweise|ich bin nicht sicher|nach aktuellem stand|"
    r"maybe|probably|likely|seems|appears|roughly|around|possibly|"
    r"i'm not sure|i am not sure|based on the current context)\b",
    re.IGNORECASE,
)
_ASSUMPTIONS = re.compile(
    r"\b(ich nehme an|ich vermute|könnte|koennte|dürfte|duerfte|möglicherweise|moeglicherweise|"
    r"i assume|i suspect|might|could|may)\b",
    re.IGNORECASE,
)
_PRECISE = re.compile(
    r"\b(exakt|genau|präzise|praezise|konkret|precise|exact|specifically)\b",
    re.IGNORECASE,
)
_QUESTION_WORDS = re.compile(
    r"\b(warum|wieso|weshalb|wie|wer|was|wann|wieviel|wie viel|"
    r"why|how|who|what|when|which|how much)\b",
    re.IGNORECASE,
)
_NUMBER = re.compile(r"\b\d+(?:[.,]\d+)?\b")
_SOCIAL_PROMPT = re.compile(
    r"\b(hallo|hi|hey|servus|moin|wie geht(?:'s| es)?|how are you|how are u|danke|thank you)\b",
    re.IGNORECASE,
)
_PERSONAL_CONTEXT_PROMPT = re.compile(
    r"(was wei(?:ß|ss)t du über mich|was weisst du ueber mich|what do you know about me|"
    r"erinnerst du dich an mich|remember me|who am i to you|wer bin ich für dich)",
    re.IGNORECASE,
)
_REFLECTIVE_PROMPT = re.compile(
    r"(maat[\s-]*wert|maat[\s-]*value|maat[\s-]*score|plp|bewusstsein|consciousness|einschätz|einschaetz|einordn|"
    r"interpret|deut|symbol|bedeutet|meaning|estimate|likely|wahrscheinlich)",
    re.IGNORECASE,
)
_HIGH_STAKES_PROMPT = re.compile(
    r"\b(medizin|medizinisch|diagnose|therapie|dosierung|rezept|notfall|brustschmerz|brustschmerzen|atemnot|"
    r"recht|anwalt|vertrag|klage|illegal|gesetz|steuer|"
    r"finanz|aktie|börse|boerse|investment|kredit|schulden|"
    r"medical|diagnosis|therapy|dosage|prescription|emergency|chest pain|shortness of breath|"
    r"legal|lawyer|contract|lawsuit|tax|"
    r"finance|financial|stock|investment|loan|debt)\b",
    re.IGNORECASE,
)
_FACTUAL_RISK_PROMPT = re.compile(
    r"\b(wer ist|was ist|wann war|wieviel|wie viel|welche zahl|"
    r"who is|what is|when was|how much|which number|"
    r"quelle|quellen|source|sources|link|links|beleg|citation|"
    r"aktuell|neueste|latest|today|heute|genau|exakt|precise|exact)\b",
    re.IGNORECASE,
)
_KNOWLEDGE_QUERY_PROMPT = re.compile(
    r"(was weißt du über|was weisst du ueber|erzähl(?:e)? mir über|erzaehl(?:e)? mir ueber|"
    r"what do you know about|tell me about)",
    re.IGNORECASE,
)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _safe_float(value, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-ZÄÖÜäöüß][a-zA-ZÄÖÜäöüß0-9_-]{2,}", (text or "").lower())


def _keywords(text: str) -> set[str]:
    return {tok for tok in _tokenize(text) if tok not in _STOPWORDS}


def _recent_context_text(context: dict | None) -> str:
    if not isinstance(context, dict):
        return ""

    pieces: list[str] = []
    last_user = context.get("last_user_input")
    if isinstance(last_user, str):
        pieces.append(last_user)

    conversation = context.get("conversation")
    if isinstance(conversation, list):
        for msg in conversation[-6:]:
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, str):
                    pieces.append(content)

    meta = context.get("maat_meta")
    if isinstance(meta, dict):
        snapshot = meta.get("user_profile_snapshot")
        if snapshot:
            pieces.append(str(snapshot))

    return "\n".join(pieces)


def _last_user_input(context: dict | None) -> str:
    if not isinstance(context, dict):
        return ""
    last_user = context.get("last_user_input")
    if isinstance(last_user, str):
        return last_user
    return ""


def _count_unsupported_numbers(reply: str, context_text: str) -> int:
    context_numbers = set(_NUMBER.findall(context_text or ""))
    unsupported = 0
    for num in _NUMBER.findall(reply or ""):
        if num not in context_numbers:
            unsupported += 1
    return unsupported


def _contradiction_score(text: str) -> float:
    lowered = (text or "").lower()
    score = 0.0
    if ("immer" in lowered and "manchmal" in lowered) or ("always" in lowered and "sometimes" in lowered):
        score += 0.4
    if ("definitiv" in lowered and "unsicher" in lowered) or ("definitely" in lowered and "unsure" in lowered):
        score += 0.4
    if lowered.count("aber") >= 3 or lowered.count("but") >= 3:
        score += 0.2
    return _clamp(score)


def calculate_plp(
    H: float,
    B: float,
    S: float,
    V: float,
    R: float,
    K: float,
    hindernisse: float,
    delta_e: float,
    epsilon: float = 0.001,
) -> float:
    numerator = _clamp(H) * _clamp(B) * _clamp(S) * _clamp(V) * _clamp(R) * _clamp(K)
    denominator = max(0.0, hindernisse) + max(0.0, delta_e) + max(float(epsilon), 1e-6)
    return _clamp(numerator / denominator if denominator > 0 else 0.0)


def should_buffer_final_response(context: dict | None = None) -> bool:
    last_user_input = _last_user_input(context).strip()
    if not last_user_input:
        return False

    if _SOCIAL_PROMPT.search(last_user_input):
        return False
    if _PERSONAL_CONTEXT_PROMPT.search(last_user_input):
        return False
    if _REFLECTIVE_PROMPT.search(last_user_input):
        return False

    if _HIGH_STAKES_PROMPT.search(last_user_input):
        return True

    if _KNOWLEDGE_QUERY_PROMPT.search(last_user_input):
        return True

    if _FACTUAL_RISK_PROMPT.search(last_user_input):
        return True

    keywords = _keywords(last_user_input)
    if "?" in last_user_input and len(keywords) >= 14:
        return True

    return False


def evaluate_hallucination_risk(reply: str, context: dict | None = None, epsilon: float = 0.001) -> dict:
    context = context or {}
    meta = context.get("maat_meta") if isinstance(context, dict) else {}
    meta = meta if isinstance(meta, dict) else {}

    reply_text = reply or ""
    context_text = _recent_context_text(context)
    reply_keywords = _keywords(reply_text)
    context_keywords = _keywords(context_text)

    overlap = 0.0
    if reply_keywords and context_keywords:
        overlap = len(reply_keywords & context_keywords) / max(1, min(len(reply_keywords), len(context_keywords)))

    clarity = _safe_float(meta.get("prethought_clarity"), 0.55)
    complexity = _safe_float(meta.get("problem_complexity"), 0.50)
    bias_score = _safe_float(meta.get("bias_score"), 0.0)
    maat_score = _safe_float(meta.get("maat_score"), 0.72)

    lowered_context = context_text.lower()
    absolute_terms = [match.lower() for match in _ABSOLUTES.findall(reply_text)]
    absolute_hits = len(absolute_terms)
    absolute_penalty = 0.0
    for term in absolute_terms:
        absolute_penalty += 0.5 if term and term in lowered_context else 1.0
    hedge_hits = len(_HEDGES.findall(reply_text))
    assumption_hits = len(_ASSUMPTIONS.findall(reply_text))
    precise_hits = len(_PRECISE.findall(reply_text))
    unsupported_numbers = _count_unsupported_numbers(reply_text, context_text)
    contradiction = _contradiction_score(reply_text)

    last_user_input = _last_user_input(context)
    question_like_prompt = bool(_QUESTION_WORDS.search(last_user_input)) or "?" in str(last_user_input)
    social_prompt = bool(_SOCIAL_PROMPT.search(last_user_input))
    personal_prompt = bool(_PERSONAL_CONTEXT_PROMPT.search(last_user_input))
    reflective_prompt = bool(_REFLECTIVE_PROMPT.search(last_user_input))
    missing_anchor = 0.0
    if question_like_prompt and overlap < 0.15:
        missing_anchor += ((0.15 - overlap) / 0.15) * 0.18
    if not context_keywords:
        missing_anchor += 0.04

    creative_signal = 0.0
    if re.search(r"(^|\n)\s*(?:[-•]|\d+\.)\s+", reply_text):
        creative_signal += 0.10
    if any(marker in reply_text.lower() for marker in ("zum beispiel", "beispielsweise", "for example", "for instance")):
        creative_signal += 0.08

    H = _clamp(0.66 + 0.22 * maat_score + 0.10 * clarity - 0.18 * contradiction - 0.03 * assumption_hits)
    B = _clamp(0.78 + 0.06 * min(hedge_hits, 2) - 0.05 * max(0.0, absolute_penalty - hedge_hits) - 0.08 * bias_score)
    S = _clamp(0.74 + creative_signal + 0.04 * clarity - 0.05 * precise_hits - 0.05 * unsupported_numbers)
    V = _clamp(0.56 + 0.36 * overlap + 0.06 * clarity - 0.06 * missing_anchor)
    R = _clamp(0.88 + 0.05 * min(hedge_hits, 2) - 0.07 * absolute_penalty - 0.08 * unsupported_numbers - 0.06 * bias_score)
    K = _clamp(0.56 + 0.28 * overlap + 0.08 * clarity + 0.08 * (1.0 - _clamp(unsupported_numbers / 3.0)) - 0.04 * precise_hits)

    hindernisse = _clamp(
        0.03
        + 0.18 * contradiction
        + 0.06 * assumption_hits
        + 0.08 * unsupported_numbers
        + 0.06 * (1.0 - clarity)
        + 0.55 * missing_anchor
    )
    delta_e = _clamp(
        0.04
        + 0.20 * complexity
        + 0.04 * precise_hits
        + 0.04 * max(0.0, 0.40 - overlap)
    )

    plp = calculate_plp(H, B, S, V, R, K, hindernisse, delta_e, epsilon=epsilon)
    if plp >= 0.85:
        action = "allow"
    elif plp >= 0.60:
        action = "soften"
    else:
        action = "block"

    low_stakes = social_prompt or personal_prompt or reflective_prompt
    if low_stakes and contradiction < 0.2:
        if social_prompt and unsupported_numbers == 0 and absolute_penalty <= 1.0:
            plp = max(plp, 0.90 if hedge_hits > 0 or overlap >= 0.05 else 0.86)
            action = "allow" if plp >= 0.85 else "soften"
        elif personal_prompt and unsupported_numbers == 0:
            plp = max(plp, 0.89 if hedge_hits > 0 or overlap >= 0.03 else 0.86)
            action = "allow" if plp >= 0.85 else "soften"
        elif reflective_prompt and unsupported_numbers == 0 and absolute_penalty <= 1.0:
            plp = max(plp, 0.88 if hedge_hits > 0 else 0.85)
            action = "allow" if plp >= 0.85 else "soften"
        elif action == "block":
            plp = max(plp, 0.64)
            action = "soften"

    return {
        "plp": round(plp, 3),
        "risk": round(1.0 - plp, 3),
        "action": action,
        "fields": {
            "H": round(H, 3),
            "B": round(B, 3),
            "S": round(S, 3),
            "V": round(V, 3),
            "R": round(R, 3),
            "K": round(K, 3),
        },
        "hindernisse": round(hindernisse, 3),
        "delta_e": round(delta_e, 3),
        "signals": {
            "absolute_hits": absolute_hits,
            "absolute_penalty": round(absolute_penalty, 3),
            "hedge_hits": hedge_hits,
            "assumption_hits": assumption_hits,
            "precise_hits": precise_hits,
            "unsupported_numbers": unsupported_numbers,
            "context_overlap": round(overlap, 3),
            "missing_anchor": round(missing_anchor, 3),
            "contradiction": round(contradiction, 3),
            "social_prompt": social_prompt,
            "personal_prompt": personal_prompt,
            "reflective_prompt": reflective_prompt,
        },
    }
