# Ported from supplied super_memory.py, SHA256 5c2edb3abf6cec56a8a684ced9f91766222d7dac00f457fe3c5b807a7cbb0342
# Native RPG bindings replace Gradio, file storage and prompt routing.
# Person storage/recognition/graph intentionally excluded at user request.
"""
MAAT Super Memory Module  (super_memory.py)
===========================================
4 Layers: Working · Episodic · Semantic · Keyword
+ Mini-Dreaming (consolidation on load)

Debug-Ausgabe im Terminal wenn supermem_debug=True:
  [🧠 recall] working:3 episodic:2 keyword:1 → 4 unique
  [🧠 store]  user: "merke dir..." → episodic+semantic+keyword
  [🧠 dream]  3 categories consolidated
"""

import os
import io
import re
import json
import time
import html
import sqlite3
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from shared.core.memory_i18n import tr as memory_text



# ============================================================
# Paths / globals
# ============================================================

_EXT_DIR  = None
_DB_PATH  = None
_KW_PATH  = None
_IO_LOCK  = threading.Lock()



DEFAULTS = {'supermem_enabled': True, 'supermem_autostore': True, 'supermem_autorecall': True, 'supermem_debug': False, 'supermem_top_k': 5, 'supermem_min_score': 0.15, 'supermem_show_source': True, 'supermem_max_episodic': 500, 'supermem_max_semantic': 300, 'supermem_max_keyword': 200, 'supermem_dream_on_load': True, 'supermem_dream_hours': 24, 'supermem_archive_enabled': True, 'supermem_archive_after_days': 30, 'supermem_allow_model_saves': True, 'supermem_show_save_box': True, 'supermem_autostore_assistant': False, 'supermem_autostore_user_min': 0.38, 'supermem_autostore_assistant_min': 0.62, 'supermem_autostore_max_chars': 1200}

_WORKING_MEMORY: List[Dict[str, Any]] = []
_MAX_WORKING = 12
_DEBUG_STATE = {"enabled": False}
_ARCHIVE_LAST_RUN = {"ts": 0.0}
_CURRENT_USER = ""
_RUNTIME_CFG = {'max_episodic': 500, 'max_semantic': 300, 'max_keyword': 200, 'autostore_user_min': 0.38, 'autostore_assistant_min': 0.62, 'autostore_assistant': False, 'autostore_max_chars': 1200, 'archive_enabled': True, 'archive_after_days': 30}

_ACTIVE_STATUS = "active"
_SUPERSEDED_STATUS = "superseded"


# ============================================================
# Debug helpers
# ============================================================

def _debug(*parts):
    if _DEBUG_STATE.get("enabled"):
        print("[🧠 supermem]", *parts, flush=True)

def _debug_recall(results: List[Dict], query: str):
    """Zeigt im Terminal welche Erinnerungen geladen wurden."""
    if not _DEBUG_STATE.get("enabled"):
        return
    by_src = {}
    for r in results:
        s = r.get("source", "?")
        by_src[s] = by_src.get(s, 0) + 1
    src_str = "  ".join(f"{s}:{n}" for s, n in by_src.items())
    print(f"\n[🧠 recall] query='{query[:50]}' → {len(results)} Erinnerungen  ({src_str})")
    for i, r in enumerate(results[:5], 1):
        score  = r.get("score", 0)
        source = r.get("source", "?")
        cat    = r.get("category", "")
        mtype  = r.get("memory_type", "fact")
        author = _memory_author_label(r)
        subject = _memory_subject_label(r)
        author_str = f"|author={author}" if author else ""
        subject_str = f"|subject={subject}" if subject else ""
        txt    = (r.get("content") or "")[:80]
        print(f"  {i}. [{source}|{cat}|{mtype}|{score:.2f}{author_str}{subject_str}] {txt}")
    print()

def _debug_store(role: str, text: str, layers: str):
    if _DEBUG_STATE.get("enabled"):
        print(f"[🧠 store]  {role}: '{text[:60]}' → {layers}", flush=True)

def _debug_skip(reason: str):
    if _DEBUG_STATE.get("enabled"):
        print(f"[🧠 skip]   {reason}", flush=True)


# ============================================================
# Category detection
# ============================================================

_CATEGORY_KEYWORDS = {
    "beziehung": ["freund", "familie", "partner", "liebe", "vertrauen", "nähe", "du", "ich"],
    "technik":   ["ki", "ai", "modell", "python", "gpu", "linux", "code", "plugin", "modul"],
    "emotion":   ["glücklich", "traurig", "angst", "wut", "freude", "hoffnung", "fühle"],
    "meta":      ["bewusstsein", "philosophie", "maat", "harmonie", "balance", "universum"],
    "projekt":   ["maat-ki", "github", "paper", "theorie", "veröffentlich", "research", "zenodo"],
    "wissen":    ["was ist", "erkläre", "definition", "bedeutet", "warum", "wie funktioniert"],
}

def _detect_category(text: str) -> str:
    t = (text or "").lower()
    scores = {cat: sum(1 for w in words if w in t) for cat, words in _CATEGORY_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "allgemein"


# ============================================================
# Text utilities
# ============================================================

def _norm(s: str) -> str:
    return " ".join((s or "").strip().lower().split())

def _tokens(s: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9äöüÄÖÜß_+\-]+", _norm(s))

def _stopwords() -> set:
    return {
        "ich", "du", "der", "die", "das", "ein", "eine", "und", "oder", "aber", "mit",
        "für", "auf", "in", "am", "von", "zu", "ist", "war", "sind", "sein", "habe",
        "hat", "haben", "dass", "ohne", "nicht", "sich", "wie", "was", "wer", "wo",
        "the", "a", "an", "is", "are", "was", "were", "it", "this", "that", "and", "or",
    }

def _keywords(text: str) -> List[str]:
    stop = _stopwords()
    toks = _tokens(text)
    words = [w for w in toks if w not in stop and len(w) > 2]
    words.sort(key=lambda x: -len(x))
    return words[:8]


_TEXT_FOLD_MAP = str.maketrans({
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "ß": "ss",
})


def _fold_text(text: str) -> str:
    return _norm(text).translate(_TEXT_FOLD_MAP)














def _extract_person_names(*args, **kwargs):
    return []


def _memory_person_names(*args, **kwargs):
    return []




def _memory_subject_label(*args, **kwargs):
    return ''


def _split_name_list(raw: Any) -> List[str]:
    names: List[str] = []
    seen = set()
    for part in re.split(r"[,;\n]+", str(raw or "")):
        name = " ".join(part.strip().split())
        key = _fold_text(name)
        if name and key and key not in seen:
            names.append(name)
            seen.add(key)
    return names












def _current_user_name(*args, **kwargs):
    return ''












def _sync_current_user_from_turn(*args, **kwargs):
    return ''


def _wrong_user_model_save_reason(*args, **kwargs):
    return ''




def _author_user_for_role(*args, **kwargs):
    return ''


def _memory_author_label(*args, **kwargs):
    return ''


def _same_user_name(*args, **kwargs):
    return False


def _memory_author_bonus(*args, **kwargs):
    return 0.0


def _time_recall_user_bonus(*args, **kwargs):
    return 0.0


def _time_recall_user_rank(*args, **kwargs):
    return 0


def _user_bucket(*args, **kwargs):
    return ''


def _item_get(item: Any, key: str, default: Any = None) -> Any:
    try:
        return item[key]
    except Exception:
        if isinstance(item, dict):
            return item.get(key, default)
        return default


def _memory_keep_score(item: Any, index: int = 0) -> Tuple[float, float, float, float, int]:
    priority = float(_item_get(item, "priority", 0.50) or 0.50)
    importance = float(_item_get(item, "importance", priority) or priority)
    hits = int(_item_get(item, "hits", 1) or 1)
    confidence = float(_item_get(item, "confidence", 0.70) or 0.70)
    ts = _timestamp_value(_item_get(item, "ts", None))
    if ts is None:
        ts = _memory_timestamp(item) or 0.0
    return (
        importance + priority * 0.45 + confidence * 0.20 + min(hits, 20) * 0.015,
        priority,
        confidence,
        float(ts),
        int(index),
    )


def _protected_sqlite_keep_ids(rows: List[sqlite3.Row], max_total: int) -> List[int]:
    if len(rows) <= max_total:
        return [int(row["id"]) for row in rows]

    ranked = sorted(
        enumerate(rows),
        key=lambda pair: _memory_keep_score(pair[1], pair[0]),
        reverse=True,
    )
    keep = {int(row["id"]) for _, row in ranked[:max_total]}

    if _RUNTIME_CFG.get("protect_user_quotas", True):
        min_per_user = max(0, min(int(_RUNTIME_CFG.get("min_per_user", 80) or 80), max_total))
        per_user: Dict[str, List[Tuple[int, sqlite3.Row]]] = {}
        for idx, row in enumerate(rows):
            bucket = _user_bucket(row)
            if bucket:
                per_user.setdefault(bucket, []).append((idx, row))
        for group in per_user.values():
            group.sort(key=lambda pair: _memory_keep_score(pair[1], pair[0]), reverse=True)
            keep.update(int(row["id"]) for _, row in group[:min_per_user])

    return sorted(keep)


def _prune_sqlite_memory(conn: sqlite3.Connection, table: str, max_total: int) -> None:
    if max_total <= 0:
        return
    if table == "episodic":
        rows = conn.execute("""
            SELECT id, role, author_user, importance, hits, priority, confidence, ts
            FROM episodic
        """).fetchall()
    elif table == "semantic":
        rows = conn.execute("""
            SELECT id, source_role, author_user, priority, confidence, ts
            FROM semantic
        """).fetchall()
    else:
        return

    if len(rows) <= max_total:
        return
    keep_ids = _protected_sqlite_keep_ids(rows, max_total)
    placeholders = ",".join("?" for _ in keep_ids)
    conn.execute(f"DELETE FROM {table} WHERE id NOT IN ({placeholders})", keep_ids)


def _prune_keyword_items(items: List[Dict[str, Any]], max_total: int) -> List[Dict[str, Any]]:
    if max_total <= 0 or len(items) <= max_total:
        return items

    keep = set(range(max(0, len(items) - max_total), len(items)))
    if _RUNTIME_CFG.get("protect_user_quotas", True):
        min_per_user = max(0, min(int(_RUNTIME_CFG.get("min_per_user", 80) or 80), max_total))
        per_user: Dict[str, List[Tuple[int, Dict[str, Any]]]] = {}
        for idx, item in enumerate(items):
            bucket = _user_bucket(item)
            if bucket:
                per_user.setdefault(bucket, []).append((idx, item))
        for group in per_user.values():
            group.sort(key=lambda pair: _memory_keep_score(pair[1], pair[0]), reverse=True)
            keep.update(idx for idx, _ in group[:min_per_user])

    return [item for idx, item in enumerate(items) if idx in keep]




def _clamp01(value: Any, default: float = 0.0) -> float:
    try:
        num = float(value)
    except Exception:
        num = default
    return max(0.0, min(num, 1.0))
























def _merge_csv_values(*values: Any) -> str:
    out: List[str] = []
    seen = set()
    for raw in values:
        for part in re.split(r"[,;]+", str(raw or "")):
            clean = part.strip()
            key = _fold_text(clean)
            if clean and key not in seen:
                out.append(clean)
                seen.add(key)
    return ",".join(out)






def _update_person_graph_from_text(*args, **kwargs):
    return 0


_VALID_MEMORY_TYPES = {
    "identity", "preference", "project", "decision",
    "fact", "temporary", "relationship", "technical",
}

_MEMORY_TYPE_ALIASES = {
    "pref": "preference",
    "preference": "preference",
    "präferenz": "preference",
    "praeferenz": "preference",
    "identity": "identity",
    "identität": "identity",
    "identitaet": "identity",
    "project": "project",
    "projekt": "project",
    "decision": "decision",
    "entscheidung": "decision",
    "fact": "fact",
    "fakt": "fact",
    "temporary": "temporary",
    "temporär": "temporary",
    "temporaer": "temporary",
    "relationship": "relationship",
    "beziehung": "relationship",
    "technical": "technical",
    "technik": "technical",
}

_MEMORY_TYPE_BONUS = {
    "identity": 0.08,
    "preference": 0.07,
    "project": 0.06,
    "decision": 0.06,
    "relationship": 0.05,
    "technical": 0.04,
    "fact": 0.02,
    "temporary": -0.02,
}

_MEMORY_TYPE_PATTERNS = {
    "temporary": [
        "heute", "morgen", "gerade", "gleich", "diese session", "temporär",
        "temporaer", "nur jetzt", "aktuell um", "aktuelle uhrzeit",
    ],
    "decision": [
        "wir haben entschieden", "entscheidung", "ab jetzt", "künftig",
        "kuenftig", "nicht mehr", "stattdessen", "wir nehmen", "wir machen",
        "nutzt jetzt", "verwenden wir",
        "we decided", "we have decided", "from now on", "instead of", "we will use",
    ],
    "preference": [
        "ich mag", "ich möchte", "ich moechte", "ich will", "ich bevorzuge",
        "bevorzugt", "lieber", "präferenz", "praeferenz", "antworte auf deutsch",
        "sprich mich", "soll immer", "soll nicht",
        "i prefer", "i like", "i dislike", "i want", "i would like", "my preference", "please answer",
    ],
    "identity": [
        "mein name", "ich heiße", "ich heisse", "christof ist", "christof krieg",
        "du schreibst mit christof", "entwickler der maat", "it business administrator",
    ],
    "project": [
        "maat", "maat-ki", "paper", "plugin", "zenodo", "arxiv", "research",
        "framework", "theorie", "stoc", "focs", "ccc", "mftoe",
        "my project", "our project", "i work on", "we are building",
    ],
    "technical": [
        "gguf", "mlx", "qwen", "llama.cpp", "loader", "python", "sqlite",
        "mac arm", "apple silicon", "gpu", "cpu", "api", "server", "webui",
        "i work in it", "ich arbeite in der it",
    ],
    "relationship": [
        "susanne", "freund", "familie", "partner", "vertrauen", "nähe",
        "naehe", "beziehung", "maatis", "claude",
    ],
}

_VALID_MAAT_FIELDS = {"H", "B", "S", "V", "R"}

_MAAT_FIELD_ALIASES = {
    "h": "H", "harmonie": "H", "harmony": "H", "struktur": "H", "klarheit": "H",
    "b": "B", "balance": "B", "abwägung": "B", "abwaegung": "B", "gegenperspektive": "B",
    "s": "S", "schöpfung": "S", "schoepfung": "S", "kreativität": "S", "kreativitaet": "S", "creativity": "S",
    "v": "V", "verbundenheit": "V", "connection": "V", "nähe": "V", "naehe": "V",
    "r": "R", "respekt": "R", "respect": "R", "grenze": "R", "sicherheit": "R",
}

_MAAT_FIELD_PATTERNS = {
    "H": ["struktur", "klar", "kurz", "ordnung", "übersicht", "uebersicht", "harmonie", "format"],
    "B": ["balance", "pro/contra", "gegenperspektive", "abwägen", "abwaegen", "ehrlich", "nicht nur zustimmen"],
    "S": ["idee", "kreativ", "schöpfung", "schoepfung", "in entwicklung", "code-snippet", "experiment"],
    "V": ["verbundenheit", "nähe", "naehe", "persönlich", "persoenlich", "schlafenszeit", "tonfall", "beziehung"],
    "R": ["respekt", "keine hallucination", "keine halluzination", "fakten", "grenze", "nicht tun darf", "sicherheit"],
}

_PRIORITY_ALIASES = {
    "low": 0.25, "niedrig": 0.25,
    "normal": 0.50, "medium": 0.55, "mittel": 0.55,
    "high": 0.80, "hoch": 0.80,
    "critical": 0.95, "kritisch": 0.95, "sehr hoch": 0.95,
}

def _detect_memory_type(text: str, explicit: str = "") -> str:
    explicit_norm = _norm(explicit).replace("-", "_")
    explicit_norm = _MEMORY_TYPE_ALIASES.get(explicit_norm, explicit_norm)
    if explicit_norm in _VALID_MEMORY_TYPES:
        return explicit_norm

    t = _norm(text)
    for memory_type, markers in _MEMORY_TYPE_PATTERNS.items():
        if any(marker in t for marker in markers):
            return memory_type
    return "fact"

def _normalize_memory_type(value: Any, text: str = "") -> str:
    explicit = str(value or "").strip()
    if explicit and _MEMORY_TYPE_ALIASES.get(_norm(explicit), _norm(explicit)) != "fact":
        return _detect_memory_type(text, explicit)
    return _detect_memory_type(text)

def _memory_type_bonus(memory_type: str) -> float:
    return float(_MEMORY_TYPE_BONUS.get(memory_type or "fact", 0.0))

def _normalize_maat_field(value: Any = "", text: str = "") -> str:
    explicit = _norm(str(value or ""))
    explicit = _MAAT_FIELD_ALIASES.get(explicit, explicit.upper())
    if explicit in _VALID_MAAT_FIELDS:
        return explicit

    t = _norm(text)
    scores = {
        field: sum(1 for marker in markers if marker in t)
        for field, markers in _MAAT_FIELD_PATTERNS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else ""

def _parse_tags(value: Any = "", text: str = "") -> List[str]:
    raw = str(value or "")
    tags = []
    for part in re.split(r"[,;#\n]+", raw):
        tag = _norm(part).strip().replace(" ", "-")
        if tag and len(tag) > 1:
            tags.append(tag[:40])
    if not tags:
        tags.extend(_keywords(text)[:5])
    seen = set()
    out = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out[:10]

def _format_tags(value: Any = "", text: str = "") -> str:
    return ",".join(_parse_tags(value, text))

def _tag_match_score(query: str, tags: Any) -> float:
    tag_set = set(_parse_tags(tags))
    if not tag_set:
        return 0.0
    q_toks = set(_tokens(query))
    if not q_toks:
        return 0.0
    return len(tag_set & q_toks) / max(len(tag_set), 1)

def _normalize_priority(value: Any = None, text: str = "", always: bool = False) -> float:
    if value not in (None, ""):
        try:
            num = float(str(value).replace(",", "."))
            if num > 1.0:
                num = num / 100.0
            return round(min(max(num, 0.0), 1.0), 3)
        except Exception:
            alias = _PRIORITY_ALIASES.get(_norm(str(value)))
            if alias is not None:
                return alias

    t = _norm(text)
    if always or any(marker in t for marker in ["immer", "dauerhaft", "wichtig", "kritisch", "r=10"]):
        return 0.85
    memory_type = _detect_memory_type(text)
    if memory_type in {"identity", "preference", "decision"}:
        return 0.70
    if memory_type in {"project", "technical", "relationship"}:
        return 0.60
    if memory_type == "temporary":
        return 0.25
    return 0.50

def _recency_bonus(ts: Any) -> float:
    try:
        age_days = max((time.time() - float(ts)) / 86400.0, 0.0)
    except Exception:
        return 0.0
    return 0.04 / (1.0 + age_days / 14.0)

def _confidence(text: str, memory_type: str = "", always: bool = False, priority: Any = None) -> float:
    score = 0.50 + 0.35 * _importance(text)
    if memory_type in {"identity", "preference", "decision", "project"}:
        score += 0.06
    if always:
        score += 0.06
    score += 0.08 * _normalize_priority(priority, text, always)
    if len(_keywords(text)) >= 3:
        score += 0.03
    return round(min(max(score, 0.05), 0.99), 3)

def _status_is_active(status: Any) -> bool:
    return (status or _ACTIVE_STATUS) == _ACTIVE_STATUS

_SUPERSEDE_COMMON = {
    "christof", "nutzt", "arbeitet", "lokal", "jetzt", "gerade",
    "modell", "model", "plugin", "system", "antwort", "antworten",
    "wird", "wurde", "ist", "sind", "haben", "neue", "neuer",
}

_REPLACEMENT_MARKERS = [
    "jetzt", "ab jetzt", "nun", "künftig", "kuenftig", "statt",
    "stattdessen", "nicht mehr", "ersetze", "ersetzt", "wechselt",
    "verwenden wir", "nutzt jetzt", "neu:",
]

_MODEL_FAMILIES = [
    "qwen", "llama", "mistral", "mixtral", "phi", "gemma", "gpt",
    "claude", "mlx", "gguf",
]

def _salient_tokens(text: str) -> set:
    toks = set(_keywords(text)) | {t for t in _tokens(text) if any(ch.isdigit() for ch in t)}
    return {t for t in toks if len(t) > 2 and t not in _SUPERSEDE_COMMON and t not in _stopwords()}

def _numberish_tokens(text: str) -> set:
    return set(re.findall(r"\b[a-z]*\d[\w.+-]*\b|\b\d+(?:[._-]\d+)+[\w.-]*\b", _norm(text)))

def _has_replacement_signal(text: str) -> bool:
    t = _norm(text)
    return any(marker in t for marker in _REPLACEMENT_MARKERS)

def _has_version_conflict(new_text: str, old_text: str) -> bool:
    new_norm = _norm(new_text)
    old_norm = _norm(old_text)
    if not any(fam in new_norm and fam in old_norm for fam in _MODEL_FAMILIES):
        return False
    new_nums = _numberish_tokens(new_norm)
    old_nums = _numberish_tokens(old_norm)
    return bool(new_nums and old_nums and new_nums != old_nums)

def _same_memory_subject(new_text: str, old_text: str, memory_type: str, old_type: str) -> bool:
    if memory_type == "temporary":
        return False
    compatible_types = {memory_type, old_type}
    if len(compatible_types - {"fact", memory_type}) > 0 and memory_type != old_type:
        if {memory_type, old_type} != {"project", "technical"}:
            return False

    new_tokens = _salient_tokens(new_text)
    old_tokens = _salient_tokens(old_text)
    if not new_tokens or not old_tokens:
        return False

    overlap = len(new_tokens & old_tokens)
    subject_score = overlap / max(min(len(new_tokens), len(old_tokens)), 1)
    return overlap >= 2 and subject_score >= 0.45

def _should_supersede(new_text: str, old_text: str, memory_type: str, old_type: str) -> bool:
    if _fingerprint(new_text) == _fingerprint(old_text):
        return False
    if _has_version_conflict(new_text, old_text):
        if memory_type == old_type or {memory_type, old_type} == {"project", "technical"}:
            return True
    if not _same_memory_subject(new_text, old_text, memory_type, old_type):
        return False
    if _has_replacement_signal(new_text) or _has_version_conflict(new_text, old_text):
        return True
    return memory_type in {"decision"} and old_type in {"decision", "fact", "project", "technical"}

def _stable_token_value(tok: str) -> int:
    return int(hashlib.md5(tok.encode("utf-8")).hexdigest()[:8], 16) % 10000

def _sentence_vector(text: str) -> float:
    tokens = _tokens(text.lower())
    if not tokens:
        return 0.0
    vals = [_stable_token_value(tok) for tok in tokens]
    return sum(vals) / len(vals)

def _importance(text: str) -> float:
    t = _norm(text)
    score = 0.10
    if len(t) > 100:           score += 0.10
    if len(_tokens(t)) >= 5:   score += 0.08
    maat_markers = [
        "maat", "bewusstsein", "harmonie", "balance", "respekt",
        "h=", "b=", "s=", "v=", "r=", "stability",
        "plugin", "modul", "engine", "reflection", "identity",
        "qwen", "mistral", "phi-3", "llama", "gguf",
    ]
    for m in maat_markers:
        if m in t: score += 0.06
    if any(p in t for p in ["merke dir", "merk dir", "speichere", "remember", "notiere"]):
        score += 0.20
    return min(score, 1.0)


_LOW_VALUE_EXACT = {
    "hello", "hi", "hey", "thanks", "thank you", "yes", "no", "great", "perfect",
    "danke", "danke dir", "dank dir", "danke schön", "danke schoen",
    "perfekt", "super", "top", "ok", "okay", "alles klar", "ja",
    "nein", "genau", "passt", "nice", "lol", "haha", "hehe", "^^", "=)",
}

_LOW_VALUE_PREFIXES = (
    "danke ", "danke dir ", "ok ", "okay ", "ja ", "nein ",
    "perfekt ", "super ", "top ",
)

_QUESTION_STARTERS = (
    "was ", "wie ", "warum ", "wieso ", "kannst ", "kannst du ",
    "würdest ", "wuerdest ", "soll ich ", "sollen wir ", "where ",
    "what ", "how ", "why ", "can you ",
)

_AUTOSTORE_POSITIVE_MARKERS = (
    "ich bin", "ich arbeite", "ich nutze", "ich verwende", "ich bevorzuge",
    "ich möchte", "ich moechte", "ich will", "mein projekt", "mein paper",
    "mein modell", "meine präferenz", "meine praeferenz", "ab jetzt",
    "wir haben entschieden", "wir nutzen", "wir verwenden", "wir bauen",
    "christof nutzt", "christof arbeitet", "christof bevorzugt",
    "ich mag", "i am", "i'm", "i’m", "i work", "i use", "i prefer", "i like", "i dislike",
    "i want", "i would like", "my project", "our project", "my paper", "my model", "my preference",
    "we decided", "we have decided", "from now on", "we use", "we are building",
)

_AUTOSTORE_LOG_MARKERS = (
    "prompt processing progress", "prompt eval time", "eval time",
    "total time", "traceback", "stack trace", "exception:", "warning:",
    "info     output generated", "tokens/s", "ms per token",
)

_INTERNAL_ARTIFACT_MARKERS = (
    "[maat_chat_summary]", "[maat_chat_memory]", "[/maat_chat_memory]",
    "[maat_context_summary]", "[/maat_context_summary]",
    "[maat_internal", "[maat_thinking", "[maat_active_lessons",
    "[maat_direct_feedback", "[maat_reflex", "[maat_style", "[maat_reply_style",
    "<think", "</think>", "&lt;think", "&lt;/think",
    "<thinking", "</thinking>", "&lt;thinking", "&lt;/thinking",
    "<reasoning", "</reasoning>", "&lt;reasoning", "&lt;/reasoning",
    "here's a thinking process", "here is a thinking process",
)

def _looks_like_command(text: str) -> bool:
    stripped = (text or "").strip()
    return stripped.startswith(("/maat ", "/help", "/clear", "/save", "/delete"))

def _looks_like_low_value_chat(text: str) -> bool:
    t = _norm(text).strip("!.? ")
    if not t:
        return True
    if t in _LOW_VALUE_EXACT:
        return True
    return len(t) < 28 and any(t.startswith(prefix) for prefix in _LOW_VALUE_PREFIXES)

def _looks_like_log_or_trace(text: str) -> bool:
    raw = text or ""
    t = raw.lower()
    if any(marker in t for marker in _AUTOSTORE_LOG_MARKERS):
        return True
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if len(lines) >= 4:
        logish = sum(1 for ln in lines if re.search(r"\b(error|warning|info|debug|traceback|tokens?/s|ms/token|pid)\b", ln, re.I))
        if logish / max(len(lines), 1) >= 0.35:
            return True
    return False

def _looks_like_internal_artifact(text: str) -> bool:
    raw = text or ""
    folded = raw.lower()
    if any(marker in folded for marker in _INTERNAL_ARTIFACT_MARKERS):
        return True
    lines = [ln.strip().lower() for ln in raw.splitlines() if ln.strip()]
    if len(lines) >= 3:
        transcriptish = sum(1 for ln in lines if ln.startswith(("maat ki:", "you:", "user:", "assistant:")))
        if transcriptish >= 2 and any("maat_chat" in ln or "<think" in ln or "&lt;think" in ln for ln in lines):
            return True
    return False

def _looks_like_question_only(text: str) -> bool:
    t = _norm(text)
    if not t:
        return False
    if "?" not in (text or "") and not any(t.startswith(prefix) for prefix in _QUESTION_STARTERS):
        return False
    return not any(marker in t for marker in _AUTOSTORE_POSITIVE_MARKERS + tuple(_REPLACEMENT_MARKERS))

def _autostore_score(role: str, text: str) -> Tuple[float, str, str]:
    t = _norm(text)
    memory_type = _detect_memory_type(text)
    score = _importance(text)
    reasons = []

    if any(marker in t for marker in _AUTOSTORE_POSITIVE_MARKERS):
        score += 0.18
        reasons.append("positive-marker")
    if _has_replacement_signal(text) or _has_version_conflict(text, ""):
        score += 0.16
        reasons.append("replacement")
    if memory_type in {"identity", "preference", "project", "decision", "technical", "relationship"}:
        score += 0.10
        reasons.append(memory_type)
    if len(_keywords(text)) >= 5:
        score += 0.05
        reasons.append("specific")
    if role == "assistant":
        score -= 0.16
        reasons.append("assistant-penalty")
    if _looks_like_question_only(text):
        score -= 0.18
        reasons.append("question")

    return round(min(max(score, 0.0), 1.0), 3), memory_type, "+".join(reasons) or "importance"

def _autostore_decision(role: str, text: str, state: dict) -> Dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {"store": False, "reason": "empty", "score": 0.0, "memory_type": "fact"}
    if _looks_like_internal_artifact(raw):
        return {"store": False, "reason": "internal-artifact", "score": 0.0, "memory_type": "technical"}
    if _looks_like_image_generation_helper(raw):
        return {"store": False, "reason": "image-generation-helper", "score": 0.0, "memory_type": "technical"}
    if _looks_like_command(raw):
        return {"store": False, "reason": "command", "score": 0.0, "memory_type": "fact"}
    if _extract_manual_save(raw):
        return {"store": False, "reason": "manual-save-handled", "score": 0.0, "memory_type": _detect_memory_type(raw)}
    if _looks_like_low_value_chat(raw):
        return {"store": False, "reason": "low-value-chat", "score": 0.0, "memory_type": "fact"}

    tokens = _tokens(raw)
    if len(tokens) < 5 and not any(marker in _norm(raw) for marker in _AUTOSTORE_POSITIVE_MARKERS):
        return {"store": False, "reason": "too-short", "score": 0.0, "memory_type": _detect_memory_type(raw)}

    max_chars = int(state.get("supermem_autostore_max_chars", 1200) or 1200)
    if len(raw) > max_chars and _looks_like_log_or_trace(raw):
        return {"store": False, "reason": "long-log", "score": 0.0, "memory_type": "technical"}
    if _looks_like_log_or_trace(raw) and not any(marker in _norm(raw) for marker in _AUTOSTORE_POSITIVE_MARKERS + tuple(_REPLACEMENT_MARKERS)):
        return {"store": False, "reason": "log-or-trace", "score": 0.0, "memory_type": "technical"}

    if role == "assistant" and not state.get("supermem_autostore_assistant", False):
        return {"store": False, "reason": "assistant-autostore-off", "score": 0.0, "memory_type": _detect_memory_type(raw)}

    score, memory_type, reason = _autostore_score(role, raw)
    threshold = float(
        state.get("supermem_autostore_assistant_min" if role == "assistant" else "supermem_autostore_user_min",
                  0.62 if role == "assistant" else 0.38)
    )
    if score < threshold:
        return {"store": False, "reason": f"below-threshold:{reason}", "score": score, "memory_type": memory_type}

    text_to_store = raw if len(raw) <= max_chars else _compress(raw, max_chars)
    maat_field = _normalize_maat_field("", raw)
    priority = _normalize_priority(None, raw)
    tags = _format_tags("", raw)
    semantic = score >= max(threshold + 0.12, 0.55) or memory_type in {"identity", "preference", "decision", "project"}
    keyword = score >= max(threshold + 0.18, 0.62) or memory_type in {"identity", "preference", "decision"}
    return {
        "store": True,
        "semantic": semantic,
        "keyword": keyword,
        "text": text_to_store,
        "reason": reason,
        "score": score,
        "memory_type": memory_type,
        "maat_field": maat_field,
        "tags": tags,
        "priority": priority,
    }

def _fingerprint(text: str) -> str:
    return hashlib.md5(_norm(text).encode()).hexdigest()[:12]

def _compress(text: str, max_len: int = 300) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 2] + "…"


def _timestamp_value(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        ts = float(value)
        if ts > 0:
            return ts
    except Exception:
        pass
    try:
        raw = str(value).strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        return dt.timestamp()
    except Exception:
        return None


def _memory_timestamp(item: Dict[str, Any]) -> Optional[float]:
    for key in ("ts", "created_at"):
        ts = _timestamp_value(item.get(key))
        if ts is not None:
            return ts
    return None


def _relative_time_label(ts: Any, lang: str = "de") -> str:
    ts_value = _timestamp_value(ts)
    if ts_value is None:
        return ""

    now = time.time()
    diff = max(now - ts_value, 0.0)
    is_en = lang == "en"

    if diff < 60:
        return "just now" if is_en else "gerade eben"
    if diff < 3600:
        mins = max(1, int(diff // 60))
        if is_en:
            return f"{mins} minute{'s' if mins != 1 else ''} ago"
        return f"vor {mins} Minute{'n' if mins != 1 else ''}"

    now_date = datetime.fromtimestamp(now).date()
    then_date = datetime.fromtimestamp(ts_value).date()
    days = max((now_date - then_date).days, 0)

    if days == 0:
        hours = max(1, int(diff // 3600))
        if is_en:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        return f"vor {hours} Stunde{'n' if hours != 1 else ''}"
    if days == 1:
        return "yesterday" if is_en else "gestern"
    if days == 2:
        return "the day before yesterday" if is_en else "vorgestern"
    if days < 7:
        return f"{days} days ago" if is_en else f"vor {days} Tagen"

    weeks = days // 7
    rest_days = days % 7
    if weeks < 9:
        if is_en:
            label = f"{weeks} week{'s' if weeks != 1 else ''} ago"
            if rest_days:
                label = (
                    f"{weeks} week{'s' if weeks != 1 else ''} and "
                    f"{rest_days} day{'s' if rest_days != 1 else ''} ago"
                )
            return label
        label = f"vor {weeks} Woche{'n' if weeks != 1 else ''}"
        if rest_days:
            label += f" und {rest_days} Tag{'en' if rest_days != 1 else ''}"
        return label

    months = max(1, days // 30)
    if is_en:
        return f"{months} month{'s' if months != 1 else ''} ago"
    return f"vor {months} Monat{'en' if months != 1 else ''}"


_TIME_NUMBERS = {
    "null": 0, "zero": 0,
    "ein": 1, "eine": 1, "einer": 1, "einem": 1, "einen": 1,
    "eins": 1, "one": 1, "a": 1, "an": 1,
    "zwei": 2, "two": 2,
    "drei": 3, "three": 3,
    "vier": 4, "four": 4,
    "fuenf": 5, "fünf": 5, "five": 5,
    "sechs": 6, "six": 6,
    "sieben": 7, "seven": 7,
    "acht": 8, "eight": 8,
    "neun": 9, "nine": 9,
    "zehn": 10, "ten": 10,
    "elf": 11, "eleven": 11,
    "zwoelf": 12, "zwölf": 12, "twelve": 12,
    "dreizehn": 13, "thirteen": 13,
    "vierzehn": 14, "fourteen": 14,
    "fuenfzehn": 15, "fünfzehn": 15, "fifteen": 15,
    "sechzehn": 16, "sixteen": 16,
    "siebzehn": 17, "seventeen": 17,
    "achtzehn": 18, "eighteen": 18,
    "neunzehn": 19, "nineteen": 19,
    "zwanzig": 20, "twenty": 20,
    "einundzwanzig": 21, "twentyone": 21, "twenty-one": 21,
    "zweiundzwanzig": 22, "twentytwo": 22, "twenty-two": 22,
    "dreiundzwanzig": 23, "twentythree": 23, "twenty-three": 23,
    "vierundzwanzig": 24, "twentyfour": 24, "twenty-four": 24,
    "fuenfundzwanzig": 25, "fünfundzwanzig": 25, "twentyfive": 25, "twenty-five": 25,
    "sechsundzwanzig": 26, "twentysix": 26, "twenty-six": 26,
    "siebenundzwanzig": 27, "twentyseven": 27, "twenty-seven": 27,
    "achtundzwanzig": 28, "twentyeight": 28, "twenty-eight": 28,
    "neunundzwanzig": 29, "twentynine": 29, "twenty-nine": 29,
    "dreissig": 30, "dreißig": 30, "thirty": 30,
    "einunddreissig": 31, "einunddreißig": 31, "thirtyone": 31, "thirty-one": 31,
}

_ORDINAL_TIME_NUMBERS = {
    "erster": 1, "erste": 1, "ersten": 1, "erstem": 1, "erstes": 1,
    "zweiter": 2, "zweite": 2, "zweiten": 2,
    "dritter": 3, "dritte": 3, "dritten": 3,
    "vierter": 4, "vierte": 4, "vierten": 4,
    "fuenfter": 5, "fünfter": 5, "fuenfte": 5, "fünfte": 5, "fuenften": 5, "fünften": 5,
}

_LAST_TIME_QUERY_HINT: Dict[str, Any] = {"unit": "", "ts": 0.0}


def _remember_time_unit(unit: str) -> None:
    if unit in {"day", "week", "month", "year"}:
        _LAST_TIME_QUERY_HINT["unit"] = unit
        _LAST_TIME_QUERY_HINT["ts"] = time.time()


def _recent_time_unit(max_age_seconds: int = 900) -> str:
    if time.time() - float(_LAST_TIME_QUERY_HINT.get("ts", 0.0) or 0.0) > max_age_seconds:
        return ""
    return str(_LAST_TIME_QUERY_HINT.get("unit", "") or "")


def _time_number(value: str, default: int = 1) -> int:
    raw = _fold_text(value or "")
    if not raw:
        return int(default)
    raw = re.sub(r"(?:st|nd|rd|th)$", "", raw)
    if raw.isdigit():
        return max(int(default), int(raw)) if default <= 0 else max(1, int(raw))
    return int(_TIME_NUMBERS.get(raw, _ORDINAL_TIME_NUMBERS.get(raw, default)))


def _midnight(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _day_time_window(days_ago: int, label: str) -> Dict[str, Any]:
    today = _midnight(datetime.fromtimestamp(time.time()))
    start = today - timedelta(days=max(days_ago, 0))
    end = start + timedelta(days=1)
    return {"start": start.timestamp(), "end": end.timestamp(), "label": label, "kind": "day"}


def _around_time_window(days_ago: int, radius_days: int, label: str, kind: str) -> Dict[str, Any]:
    today = _midnight(datetime.fromtimestamp(time.time()))
    center = today - timedelta(days=max(days_ago, 0))
    start = center - timedelta(days=max(radius_days, 0))
    end = center + timedelta(days=max(radius_days, 0) + 1)
    return {
        "start": start.timestamp(),
        "end": end.timestamp(),
        "center": center.timestamp(),
        "label": label,
        "kind": kind,
    }


def _previous_calendar_week() -> Dict[str, Any]:
    today = _midnight(datetime.fromtimestamp(time.time()))
    this_monday = today - timedelta(days=today.weekday())
    start = this_monday - timedelta(days=7)
    end = this_monday
    return {"start": start.timestamp(), "end": end.timestamp(), "label": "letzte Woche", "kind": "week"}


def _previous_calendar_month() -> Dict[str, Any]:
    today = _midnight(datetime.fromtimestamp(time.time()))
    first_this = today.replace(day=1)
    last_prev = first_this - timedelta(days=1)
    first_prev = last_prev.replace(day=1)
    return {"start": first_prev.timestamp(), "end": first_this.timestamp(), "label": "letzter Monat", "kind": "month"}


def _previous_calendar_year() -> Dict[str, Any]:
    today = _midnight(datetime.fromtimestamp(time.time()))
    first_this = today.replace(month=1, day=1)
    first_prev = first_this.replace(year=first_this.year - 1)
    return {"start": first_prev.timestamp(), "end": first_this.timestamp(), "label": "letztes Jahr", "kind": "year"}


_MONTH_ALIASES = {
    "januar": 1, "jan": 1, "january": 1,
    "februar": 2, "feb": 2, "february": 2,
    "maerz": 3, "märz": 3, "mar": 3, "march": 3,
    "april": 4, "apr": 4,
    "mai": 5, "may": 5,
    "juni": 6, "jun": 6, "june": 6,
    "juli": 7, "jul": 7, "july": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "okt": 10, "oct": 10, "october": 10,
    "november": 11, "nov": 11,
    "dezember": 12, "dez": 12, "dec": 12, "december": 12,
}

_MONTH_NAMES_DE = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
}


def _month_start(year: int, month: int) -> datetime:
    return _midnight(datetime(year=year, month=month, day=1))


def _next_month_start(year: int, month: int) -> datetime:
    if month == 12:
        return _month_start(year + 1, 1)
    return _month_start(year, month + 1)


def _current_week_window() -> Dict[str, Any]:
    today = _midnight(datetime.fromtimestamp(time.time()))
    start = today - timedelta(days=today.weekday())
    end = today + timedelta(days=1)
    return {"start": start.timestamp(), "end": end.timestamp(), "label": "diese Woche", "kind": "week"}


def _last_days_window(days: int) -> Dict[str, Any]:
    today = _midnight(datetime.fromtimestamp(time.time()))
    start = today - timedelta(days=max(days, 1))
    end = today + timedelta(days=1)
    return {"start": start.timestamp(), "end": end.timestamp(), "label": f"letzte {days} Tage", "kind": "range"}


def _days_ago_window(days: int, label: str) -> Dict[str, Any]:
    # Exact day lookups are useful for recent memories. For older ranges,
    # users usually mean "around then", so avoid empty results from one-day drift.
    if days <= 31:
        return _day_time_window(days, label)
    radius = 3 if days <= 180 else 7
    return _around_time_window(days, radius, label, "day")


def _current_month_window() -> Dict[str, Any]:
    today = _midnight(datetime.fromtimestamp(time.time()))
    start = _month_start(today.year, today.month)
    end = today + timedelta(days=1)
    return {"start": start.timestamp(), "end": end.timestamp(), "label": "dieser Monat", "kind": "month"}


def _current_year_window() -> Dict[str, Any]:
    today = _midnight(datetime.fromtimestamp(time.time()))
    start = _midnight(datetime(year=today.year, month=1, day=1))
    end = today + timedelta(days=1)
    return {"start": start.timestamp(), "end": end.timestamp(), "label": "dieses Jahr", "kind": "year"}


def _since_month_window(month_name: str, year_text: str = "") -> Optional[Dict[str, Any]]:
    month = _MONTH_ALIASES.get(_fold_text(month_name))
    if not month:
        return None
    today = _midnight(datetime.fromtimestamp(time.time()))
    year = int(year_text) if str(year_text or "").isdigit() else today.year
    start = _month_start(year, month)
    end = today + timedelta(days=1)
    label = f"seit {_MONTH_NAMES_DE.get(month, month)} {year}"
    return {"start": start.timestamp(), "end": end.timestamp(), "label": label, "kind": "since"}


def _absolute_day_window(day_text: str, month_name: str, year_text: str = "") -> Optional[Dict[str, Any]]:
    month = _MONTH_ALIASES.get(_fold_text(month_name))
    if not month:
        return None
    day = _time_number(day_text, 0)
    if day < 1 or day > 31:
        return None
    today = _midnight(datetime.fromtimestamp(time.time()))
    year = int(year_text) if str(year_text or "").isdigit() else today.year
    try:
        start = _midnight(datetime(year=year, month=month, day=day))
    except ValueError:
        return None
    end = start + timedelta(days=1)
    label = f"{day}. {_MONTH_NAMES_DE.get(month, month)} {year}"
    return {"start": start.timestamp(), "end": end.timestamp(), "label": label, "kind": "day"}


def _absolute_numeric_day_window(day_text: str, month_text: str, year_text: str = "") -> Optional[Dict[str, Any]]:
    if not str(day_text or "").isdigit() or not str(month_text or "").isdigit():
        return None
    day = int(day_text)
    month = int(month_text)
    if day < 1 or day > 31 or month < 1 or month > 12:
        return None
    today = _midnight(datetime.fromtimestamp(time.time()))
    if str(year_text or "").isdigit():
        year = int(year_text)
        if year < 100:
            year += 2000 if year < 70 else 1900
    else:
        year = today.year
    try:
        start = _midnight(datetime(year=year, month=month, day=day))
    except ValueError:
        return None
    end = start + timedelta(days=1)
    label = f"{day:02d}.{month:02d}.{year}"
    return {"start": start.timestamp(), "end": end.timestamp(), "label": label, "kind": "day"}


def _time_query_window(query: str) -> Optional[Dict[str, Any]]:
    text = _fold_text(query or "")
    if not text:
        return None

    # Conversational shorthand: after "vor 2 Wochen", a follow-up like
    # "und vor 3?" means "vor 3 Wochen" for a short time.
    shorthand = re.search(r"\b(?:und|oder)?\s*vor\s+([a-z0-9äöüß]+)\s*\??\s*$", text)
    if shorthand and not re.search(r"\b(tag|tage|tagen|woche|wochen|monat|monaten|jahr|jahren|day|days|week|weeks|month|months|year|years)\b", text):
        value = _time_number(shorthand.group(1), 0)
        unit = _recent_time_unit()
        if value > 0 and unit == "week":
            label = f"vor {value} Woche{'n' if value != 1 else ''}"
            return _around_time_window(value * 7, 2, label, "week")
        if value > 0 and unit == "day":
            return _day_time_window(value, f"vor {value} Tag{'en' if value != 1 else ''}")

    if re.search(r"\bvorgestern\b|\bday before yesterday\b", text):
        _remember_time_unit("day")
        return _day_time_window(2, "vorgestern")
    if re.search(r"\bgestern\b|\byesterday\b", text):
        _remember_time_unit("day")
        return _day_time_window(1, "gestern")

    m = re.search(r"\bletzte(?:n|r|s)?\s+(\d{1,3})\s+tage\b|\blast\s+(\d{1,3})\s+days\b", text)
    if m:
        days = int(m.group(1) or m.group(2))
        _remember_time_unit("day")
        return _last_days_window(max(1, min(days, 365)))

    if re.search(r"\bdiese\s+woche\b|\bdieser\s+woche\b|\bthis\s+week\b", text):
        return _current_week_window()

    if re.search(r"\bdiesen\s+monat\b|\bdiesem\s+monat\b|\bdieser\s+monat\b|\bthis\s+month\b", text):
        return _current_month_window()

    if re.search(r"\bdieses\s+jahr\b|\bdiesem\s+jahr\b|\bthis\s+year\b", text):
        return _current_year_window()

    m = re.search(r"\b(\d{1,2})\s*[./-]\s*(\d{1,2})(?:\s*[./-]\s*(\d{2,4}))?\b", text)
    if m:
        window = _absolute_numeric_day_window(m.group(1), m.group(2), m.group(3) or "")
        if window:
            _remember_time_unit("day")
            return window

    m = re.search(r"\b(20\d{2}|19\d{2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{1,2})\b", text)
    if m:
        window = _absolute_numeric_day_window(m.group(3), m.group(2), m.group(1))
        if window:
            _remember_time_unit("day")
            return window

    m = re.search(
        r"\b(?:am|vom|an\s+dem)\s+([a-z0-9äöüß]+)\.?\s+([a-zäöüß]+)(?:\s+(\d{4}))?\b",
        text,
    )
    if m:
        window = _absolute_day_window(m.group(1), m.group(2), m.group(3) or "")
        if window:
            _remember_time_unit("day")
            return window

    m = re.search(
        r"\b(?:on)\s+([a-z]+)\s+([a-z0-9]+)(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b",
        text,
    )
    if m:
        window = _absolute_day_window(m.group(2), m.group(1), m.group(3) or "")
        if window:
            _remember_time_unit("day")
            return window

    m = re.search(r"\bseit\s+([a-zäöüß]+)(?:\s+(\d{4}))?\b|\bsince\s+([a-z]+)(?:\s+(\d{4}))?\b", text)
    if m:
        month_name = m.group(1) or m.group(3)
        year_text = m.group(2) or m.group(4) or ""
        window = _since_month_window(month_name, year_text)
        if window:
            return window

    m = re.search(r"\bvor\s+([a-z0-9äöüß]+)\s+tag(?:en|e)?\b", text)
    if m:
        days = _time_number(m.group(1))
        _remember_time_unit("day")
        return _days_ago_window(days, f"vor {days} Tag{'en' if days != 1 else ''}")

    m = re.search(
        r"\bvor\s+([a-z0-9äöüß]+)\s+woche(?:n)?"
        r"(?:\s+und\s+([a-z0-9äöüß]+)\s+tag(?:en|e)?)?\b",
        text,
    )
    if m:
        weeks = _time_number(m.group(1))
        rest_days = _time_number(m.group(2), 0) if m.group(2) else 0
        days = weeks * 7 + rest_days
        label = f"vor {weeks} Woche{'n' if weeks != 1 else ''}"
        if rest_days:
            label += f" und {rest_days} Tag{'en' if rest_days != 1 else ''}"
        # "vor 2 Wochen" is usually approximate in chat, so use a small
        # tolerance window to avoid zero hits from minor date drift.
        radius = 2 if rest_days == 0 else 1
        _remember_time_unit("week")
        return _around_time_window(days, radius, label, "week")

    if re.search(r"\bletzte\s+woche\b|\bletzten\s+woche\b|\blast\s+week\b", text):
        _remember_time_unit("week")
        return _previous_calendar_week()

    m = re.search(r"\bvor\s+([a-z0-9äöüß]+)\s+monat(?:e|en)?\b", text)
    if m:
        months = _time_number(m.group(1))
        label = f"vor {months} Monat{'en' if months != 1 else ''}"
        _remember_time_unit("month")
        return _around_time_window(months * 30, 3, label, "month")

    if re.search(r"\bletzten?\s+monat\b|\blast\s+month\b", text):
        _remember_time_unit("month")
        return _previous_calendar_month()

    m = re.search(r"\bvor\s+([a-z0-9äöüß]+)\s+jahr(?:en)?\b", text)
    if m:
        years = _time_number(m.group(1))
        label = f"vor {years} Jahr{'en' if years != 1 else ''}"
        _remember_time_unit("year")
        return _around_time_window(years * 365, 14, label, "year")

    if re.search(r"\bletztes\s+jahr\b|\bletzten\s+jahr\b|\blast\s+year\b", text):
        _remember_time_unit("year")
        return _previous_calendar_year()

    m = re.search(r"\b([a-z0-9]+)\s+day(?:s)?\s+ago\b", text)
    if m:
        days = _time_number(m.group(1))
        _remember_time_unit("day")
        return _days_ago_window(days, f"{days} day{'s' if days != 1 else ''} ago")

    m = re.search(r"\b([a-z0-9]+)\s+week(?:s)?(?:\s+and\s+([a-z0-9]+)\s+day(?:s)?)?\s+ago\b", text)
    if m:
        weeks = _time_number(m.group(1))
        rest_days = _time_number(m.group(2), 0) if m.group(2) else 0
        days = weeks * 7 + rest_days
        label = f"{weeks} week{'s' if weeks != 1 else ''}"
        if rest_days:
            label += f" and {rest_days} day{'s' if rest_days != 1 else ''}"
        radius = 2 if rest_days == 0 else 1
        _remember_time_unit("week")
        return _around_time_window(days, radius, label + " ago", "week")

    return None


# ============================================================
# Database — with guard
# ============================================================

def _get_conn(*args, **kwargs):
    raise RuntimeError("Native Super Memory storage is not bound")

def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str):
    cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        _debug(f"DB migrated: {table}.{column}")

def _init_db():
    with _get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS episodic (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ts         REAL,
            role       TEXT,
            author_user TEXT DEFAULT '',
            content    TEXT,
            compressed TEXT,
            keywords   TEXT,
            category   TEXT,
            memory_type TEXT DEFAULT 'fact',
            maat_field TEXT DEFAULT '',
            tags       TEXT DEFAULT '',
            priority   REAL DEFAULT 0.50,
            importance REAL,
            status     TEXT DEFAULT 'active',
            superseded_by INTEGER,
            confidence REAL DEFAULT 0.70,
            fp         TEXT UNIQUE,
            hits       INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS semantic (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            ts       REAL,
            text     TEXT UNIQUE,
            vector   REAL,
            category TEXT,
            memory_type TEXT DEFAULT 'fact',
            maat_field TEXT DEFAULT '',
            tags     TEXT DEFAULT '',
            source_role TEXT DEFAULT '',
            author_user TEXT DEFAULT '',
            priority REAL DEFAULT 0.50,
            status   TEXT DEFAULT 'active',
            superseded_by INTEGER,
            confidence REAL DEFAULT 0.70,
            fp       TEXT UNIQUE
        );
        CREATE TABLE IF NOT EXISTS monthly_archive (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            period      TEXT,
            period_start REAL,
            period_end   REAL,
            category    TEXT,
            memory_type TEXT DEFAULT 'project',
            maat_field  TEXT DEFAULT '',
            tags        TEXT DEFAULT '',
            summary     TEXT,
            source_count INTEGER DEFAULT 0,
            priority    REAL DEFAULT 0.50,
            importance  REAL DEFAULT 0.50,
            status      TEXT DEFAULT 'active',
            created_at  REAL,
            updated_at  REAL,
            fp          TEXT UNIQUE,
            UNIQUE(period, category)
        );
        """)

        _ensure_column(conn, "episodic", "memory_type", "TEXT DEFAULT 'fact'")
        _ensure_column(conn, "episodic", "author_user", "TEXT DEFAULT ''")
        _ensure_column(conn, "episodic", "maat_field", "TEXT DEFAULT ''")
        _ensure_column(conn, "episodic", "tags", "TEXT DEFAULT ''")
        _ensure_column(conn, "episodic", "priority", "REAL DEFAULT 0.50")
        _ensure_column(conn, "episodic", "status", "TEXT DEFAULT 'active'")
        _ensure_column(conn, "episodic", "superseded_by", "INTEGER")
        _ensure_column(conn, "episodic", "confidence", "REAL DEFAULT 0.70")
        _ensure_column(conn, "semantic", "memory_type", "TEXT DEFAULT 'fact'")
        _ensure_column(conn, "semantic", "maat_field", "TEXT DEFAULT ''")
        _ensure_column(conn, "semantic", "tags", "TEXT DEFAULT ''")
        _ensure_column(conn, "semantic", "source_role", "TEXT DEFAULT ''")
        _ensure_column(conn, "semantic", "author_user", "TEXT DEFAULT ''")
        _ensure_column(conn, "semantic", "priority", "REAL DEFAULT 0.50")
        _ensure_column(conn, "semantic", "status", "TEXT DEFAULT 'active'")
        _ensure_column(conn, "semantic", "superseded_by", "INTEGER")
        _ensure_column(conn, "semantic", "confidence", "REAL DEFAULT 0.70")

        conn.executescript("""
        CREATE INDEX IF NOT EXISTS ep_ts  ON episodic(ts);
        CREATE INDEX IF NOT EXISTS ep_cat ON episodic(category);
        CREATE INDEX IF NOT EXISTS ep_type ON episodic(memory_type);
        CREATE INDEX IF NOT EXISTS ep_field ON episodic(maat_field);
        CREATE INDEX IF NOT EXISTS ep_status ON episodic(status);
        CREATE INDEX IF NOT EXISTS sm_vec ON semantic(vector);
        CREATE INDEX IF NOT EXISTS sm_type ON semantic(memory_type);
        CREATE INDEX IF NOT EXISTS sm_field ON semantic(maat_field);
        CREATE INDEX IF NOT EXISTS sm_status ON semantic(status);
        CREATE INDEX IF NOT EXISTS ar_period ON monthly_archive(period);
        CREATE INDEX IF NOT EXISTS ar_window ON monthly_archive(period_start, period_end);
        CREATE INDEX IF NOT EXISTS ar_status ON monthly_archive(status);
        """)
    _debug("DB initialised:", _DB_PATH)


# ============================================================
# Working memory (RAM)
# ============================================================

_IMAGE_GENERATION_HELPER_MARKERS = (
    "der nutzer möchte ein bild erzeugen",
    "der nutzer moechte ein bild erzeugen",
    "lokale image-ai-erweiterung",
    "antworte nur kurz mit bild wird erstellt",
    "antworte nur kurz mit: bild wird erstellt",
    "maat-image-chat-card",
)

def _looks_like_image_generation_helper(text: str) -> bool:
    t = _norm(text or "")
    return any(marker in t for marker in _IMAGE_GENERATION_HELPER_MARKERS)

def _add_working(role: str, text: str):
    if _looks_like_image_generation_helper(text or ""):
        _debug_skip("working memory: image-helper text skipped")
        return
    _WORKING_MEMORY.append({
        "role": role,
        "author_user": _author_user_for_role(role),
        "text": text,
        "ts": time.time(),
    })
    if len(_WORKING_MEMORY) > _MAX_WORKING:
        _WORKING_MEMORY.pop(0)

def _recall_working(query: str, top_k: int = 3, state: Optional[dict] = None) -> List[Dict[str, Any]]:
    if not _WORKING_MEMORY:
        return []
    q_toks = set(_tokens(query))
    scored = []
    current_user = (state or {}).get("supermem_current_user") or _current_user_name()
    for item in reversed(_WORKING_MEMORY):
        if _looks_like_image_generation_helper(str(item.get("text", ""))):
            continue
        role = _norm(str(item.get("role", "")))
        author_user = str(item.get("author_user", "") or "").strip()
        if role in {"user", "human"} and author_user and current_user and not _same_user_name(author_user, current_user):
            continue
        toks  = set(_tokens(item["text"]))
        union = len(q_toks | toks)
        score = len(q_toks & toks) / union if union else 0.0
        score += _memory_author_bonus(item, state)
        scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"score": round(s, 3), "source": "working", **it}
            for s, it in scored[:top_k] if s > 0.05]


# ============================================================
# Episodic memory
# ============================================================

def _add_episodic(
    role: str,
    text: str,
    memory_type: str = "",
    tags: str = "",
    maat_field: str = "",
    priority: Any = None,
    author_user: str = "",
) -> Tuple[Optional[int], bool]:
    fp = _fingerprint(text)
    memory_type = _normalize_memory_type(memory_type, text)
    maat_field = _normalize_maat_field(maat_field, text)
    tags = _format_tags(tags, text)
    priority = _normalize_priority(priority, text)
    confidence = _confidence(text, memory_type, priority=priority)
    author_user = " ".join(str(author_user or _author_user_for_role(role)).strip().split())
    with _IO_LOCK:
        with _get_conn() as conn:
            existing = conn.execute("SELECT id FROM episodic WHERE fp=?", (fp,)).fetchone()
            if existing:
                conn.execute("""
                    UPDATE episodic
                    SET hits=hits+1,
                        status=?,
                        superseded_by=NULL,
                        confidence=MAX(COALESCE(confidence, 0.70), ?),
                        priority=MAX(COALESCE(priority, 0.50), ?),
                        author_user=CASE WHEN author_user IS NULL OR author_user='' THEN ? ELSE author_user END,
                        tags=CASE WHEN tags IS NULL OR tags='' THEN ? ELSE tags END,
                        maat_field=CASE WHEN maat_field IS NULL OR maat_field='' THEN ? ELSE maat_field END,
                        memory_type=CASE
                            WHEN memory_type IS NULL OR memory_type='' OR memory_type='fact'
                            THEN ?
                            ELSE memory_type
                        END
                    WHERE id=?
                """, (_ACTIVE_STATUS, confidence, priority, author_user, tags, maat_field, memory_type, existing["id"]))
                _debug(f"episodic hit++: {text[:50]}")
                return int(existing["id"]), False
            else:
                cur = conn.execute("""
                    INSERT INTO episodic
                      (ts, role, author_user, content, compressed, keywords, category, memory_type, maat_field, tags, priority, importance, status, superseded_by, confidence, fp)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    time.time(), role, author_user, text, _compress(text),
                    ",".join(_keywords(text)),
                    _detect_category(text), memory_type, maat_field, tags, priority,
                    _importance(text), _ACTIVE_STATUS, None, confidence, fp,
                ))
                new_id = int(cur.lastrowid)
                max_ep = int(_RUNTIME_CFG.get("max_episodic", 500))
                _prune_sqlite_memory(conn, "episodic", max_ep)
                return new_id, True
    return None, False

def _recall_episodic(query: str, top_k: int = 5, min_score: float = 0.15, state: Optional[dict] = None) -> List[Dict[str, Any]]:
    q_toks = set(_keywords(query))
    if not q_toks:
        return []
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, role, author_user, content, compressed, keywords, category, memory_type, maat_field, tags, priority, importance, hits, ts, status, confidence "
            "FROM episodic WHERE COALESCE(status, 'active') = 'active' ORDER BY ts DESC LIMIT 200"
        ).fetchall()
    scored = []
    for row in rows:
        toks  = set(_tokens(row["keywords"] or "")) | set(_keywords(row["content"] or ""))
        if not toks:
            toks = set(_tokens(row["content"] or ""))
        overlap = len(q_toks & toks)
        if overlap <= 0:
            continue
        union = len(q_toks | toks)
        score = max(overlap / max(len(q_toks), 1) * 0.45, overlap / union if union else 0.0)
        score += 0.08 * float(row["importance"])
        score += 0.01 * min(int(row["hits"]), 5)
        memory_type = _normalize_memory_type(row["memory_type"], row["content"])
        score += _memory_type_bonus(memory_type)
        score += _recency_bonus(row["ts"])
        score += 0.04 * float(row["confidence"] or 0.70)
        score += 0.05 * float(row["priority"] or 0.50)
        score += 0.08 * _tag_match_score(query, row["tags"] or row["keywords"] or "")
        score += _memory_author_bonus(dict(row), state)
        if score >= min_score:
            item = dict(row)
            item["memory_type"] = memory_type
            item["maat_field"] = _normalize_maat_field(row["maat_field"], row["content"])
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]
    if top:
        ids = [str(it["id"]) for _, it in top if it.get("id") is not None]
        if ids:
            with _IO_LOCK:
                with _get_conn() as conn:
                    conn.execute(f"UPDATE episodic SET hits=hits+1 WHERE id IN ({','.join('?' for _ in ids)})", ids)
    return [{"score": round(s, 3), "source": "episodic", **it} for s, it in top]


# ============================================================
# Semantic memory
# ============================================================

def _add_semantic(
    text: str,
    memory_type: str = "",
    tags: str = "",
    maat_field: str = "",
    priority: Any = None,
    source_role: str = "",
    author_user: str = "",
):
    fp  = _fingerprint(text)
    vec = _sentence_vector(text)
    memory_type = _normalize_memory_type(memory_type, text)
    maat_field = _normalize_maat_field(maat_field, text)
    tags = _format_tags(tags, text)
    priority = _normalize_priority(priority, text)
    confidence = _confidence(text, memory_type, priority=priority)
    author_user = " ".join(str(author_user or _author_user_for_role(source_role)).strip().split())
    with _IO_LOCK:
        with _get_conn() as conn:
            existing = conn.execute("SELECT id FROM semantic WHERE fp=?", (fp,)).fetchone()
            if existing:
                conn.execute("""
                    UPDATE semantic
                    SET status=?,
                        superseded_by=NULL,
                        confidence=MAX(COALESCE(confidence, 0.70), ?),
                        priority=MAX(COALESCE(priority, 0.50), ?),
                        source_role=CASE WHEN source_role IS NULL OR source_role='' THEN ? ELSE source_role END,
                        author_user=CASE WHEN author_user IS NULL OR author_user='' THEN ? ELSE author_user END,
                        tags=CASE WHEN tags IS NULL OR tags='' THEN ? ELSE tags END,
                        maat_field=CASE WHEN maat_field IS NULL OR maat_field='' THEN ? ELSE maat_field END,
                        memory_type=CASE
                            WHEN memory_type IS NULL OR memory_type='' OR memory_type='fact'
                            THEN ?
                            ELSE memory_type
                        END
                    WHERE id=?
                """, (_ACTIVE_STATUS, confidence, priority, source_role, author_user, tags, maat_field, memory_type, existing["id"]))
            else:
                conn.execute("""
                    INSERT INTO semantic (ts, text, vector, category, memory_type, maat_field, tags, source_role, author_user, priority, status, superseded_by, confidence, fp)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (time.time(), text, vec, _detect_category(text), memory_type, maat_field, tags, source_role, author_user, priority, _ACTIVE_STATUS, None, confidence, fp))
            max_sm = int(_RUNTIME_CFG.get("max_semantic", 300))
            _prune_sqlite_memory(conn, "semantic", max_sm)

def _recall_semantic(query: str, top_k: int = 3, min_score: float = 0.15, state: Optional[dict] = None) -> List[Dict[str, Any]]:
    qv = _sentence_vector(query)
    q_toks = set(_keywords(query))
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT text, vector, category, memory_type, maat_field, tags, source_role, author_user, priority, ts, status, confidence
            FROM semantic WHERE COALESCE(status, 'active') = 'active'
        """).fetchall()
    scored = []
    for row in rows:
        dist  = abs(float(row["vector"]) - qv)
        vector_score = 1.0 / (1.0 + dist / 1000.0)
        row_toks = set(_keywords(row["text"] or ""))
        overlap = len(q_toks & row_toks) / max(len(q_toks), 1) if q_toks else 0.0
        score = 0.70 * vector_score + 0.30 * overlap
        memory_type = _normalize_memory_type(row["memory_type"], row["text"])
        if overlap > 0:
            score += _memory_type_bonus(memory_type) * 0.5
        score += 0.02 * float(row["confidence"] or 0.70)
        score += 0.03 * float(row["priority"] or 0.50)
        score += 0.06 * _tag_match_score(query, row["tags"] or "")
        score += _memory_author_bonus(dict(row), state)
        if score >= min_score:
            item = dict(row)
            item["memory_type"] = memory_type
            item["maat_field"] = _normalize_maat_field(row["maat_field"], row["text"])
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"score": round(s, 3), "source": "semantic",
             "content": it["text"], **it} for s, it in scored[:top_k]]


# ============================================================
# Keyword memory
# ============================================================

def _load_keywords(*args, **kwargs):
    raise RuntimeError("Native Super Memory storage is not bound")

def _save_keywords(*args, **kwargs):
    raise RuntimeError("Native Super Memory storage is not bound")

def _add_keyword(
    memory: str,
    keywords: str = "",
    always: bool = False,
    memory_type: str = "",
    tags: str = "",
    maat_field: str = "",
    priority: Any = None,
    source_role: str = "",
    author_user: str = "",
) -> Tuple[bool, str]:
    memory = (memory or "").strip()
    if not memory or len(memory) < 8:
        return False, "Too short."
    memory_type = _normalize_memory_type(memory_type, memory)
    maat_field = _normalize_maat_field(maat_field, memory)
    tags = _format_tags(tags or keywords, memory)
    priority = _normalize_priority(priority, memory, always)
    confidence = _confidence(memory, memory_type, always, priority)
    author_user = " ".join(str(author_user or _author_user_for_role(source_role)).strip().split())
    items = _load_keywords()
    fp    = _fingerprint(memory)
    for it in items:
        if _fingerprint(it.get("memory", "")) == fp:
            changed = False
            if not it.get("memory_type"):
                it["memory_type"] = memory_type
                changed = True
            if not it.get("maat_field"):
                it["maat_field"] = maat_field
                changed = True
            if not it.get("tags"):
                it["tags"] = tags
                changed = True
            if float(it.get("priority", 0.50) or 0.50) < priority:
                it["priority"] = priority
                changed = True
            if keywords and not it.get("keywords"):
                it["keywords"] = keywords
                changed = True
            if source_role and not it.get("source_role"):
                it["source_role"] = source_role
                changed = True
            if author_user and not it.get("author_user"):
                it["author_user"] = author_user
                changed = True
            if always and not it.get("always"):
                it["always"] = True
                changed = True
            if it.get("status") != _ACTIVE_STATUS:
                it["status"] = _ACTIVE_STATUS
                it["superseded_by"] = None
                changed = True
            if float(it.get("confidence", 0.70) or 0.70) < confidence:
                it["confidence"] = confidence
                changed = True
            if changed:
                _save_keywords(items)
            return False, "Already exists."
    items.append({
        "memory":     memory,
        "keywords":   keywords or ",".join(_keywords(memory)[:4]),
        "always":     bool(always),
        "memory_type": memory_type,
        "maat_field": maat_field,
        "tags":       tags,
        "source_role": source_role,
        "author_user": author_user,
        "priority":   priority,
        "status":     _ACTIVE_STATUS,
        "superseded_by": None,
        "confidence": confidence,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "fp":         fp,
    })
    items = _prune_keyword_items(items, int(_RUNTIME_CFG.get("max_keyword", 200)))
    _save_keywords(items)
    return True, "Saved."

def _recall_keywords(query: str, top_k: int = 4, state: Optional[dict] = None) -> List[Dict[str, Any]]:
    items  = _load_keywords()
    lower  = query.lower()
    q_toks = set(_tokens(query))
    scored = []
    for it in items:
        if not _status_is_active(it.get("status")):
            continue
        kws   = [k.strip().lower() for k in (it.get("keywords", "")).split(",") if k.strip()]
        memory_type = _normalize_memory_type(it.get("memory_type") or it.get("type"), it.get("memory", ""))
        maat_field = _normalize_maat_field(it.get("maat_field") or it.get("field"), it.get("memory", ""))
        keyword_score = sum(1.0 for kw in kws if kw in lower or kw in q_toks) / max(len(kws), 1)
        score = 0.30 + 0.70 * keyword_score if it.get("always") else keyword_score
        score += 0.05 * float(it.get("priority", 0.50) or 0.50)
        score += 0.08 * _tag_match_score(query, it.get("tags") or it.get("keywords") or "")
        if score > 0.05:
            score += _memory_type_bonus(memory_type) * 0.5
            score += 0.03 * float(it.get("confidence", 0.70) or 0.70)
            score += _memory_author_bonus(it, state)
        if score > 0.05:
            item = dict(it)
            item["memory_type"] = memory_type
            item["maat_field"] = maat_field
            item["status"] = it.get("status") or _ACTIVE_STATUS
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"score": round(s, 3), "source": "keyword",
             "content": it["memory"], **it} for s, it in scored[:top_k]]


# ============================================================
# Superseding / memory hygiene
# ============================================================

def _mark_keyword_superseded(old_content: str, new_fp: str) -> int:
    items = _load_keywords()
    changed = 0
    old_fp = _fingerprint(old_content)
    for it in items:
        if not _status_is_active(it.get("status")):
            continue
        if it.get("fp") == old_fp or _fingerprint(it.get("memory", "")) == old_fp:
            it["status"] = _SUPERSEDED_STATUS
            it["superseded_by"] = new_fp
            changed += 1
    if changed:
        _save_keywords(items)
    return changed

def _supersede_related_memories(new_id: Optional[int], new_text: str, memory_type: str) -> int:
    if not new_id or memory_type == "temporary":
        return 0

    new_fp = _fingerprint(new_text)
    changed = 0
    with _IO_LOCK:
        with _get_conn() as conn:
            rows = conn.execute("""
                SELECT id, content, memory_type, status
                FROM episodic
                WHERE id != ? AND COALESCE(status, 'active') = 'active'
                ORDER BY ts DESC LIMIT 500
            """, (new_id,)).fetchall()

            old_ids = []
            old_fps = []
            for row in rows:
                old_type = _normalize_memory_type(row["memory_type"], row["content"])
                if _should_supersede(new_text, row["content"], memory_type, old_type):
                    old_ids.append(int(row["id"]))
                    old_fps.append(_fingerprint(row["content"]))
                    changed += 1

            if old_ids:
                placeholders = ",".join("?" for _ in old_ids)
                conn.execute(f"""
                    UPDATE episodic
                    SET status=?, superseded_by=?
                    WHERE id IN ({placeholders})
                """, [_SUPERSEDED_STATUS, new_id, *old_ids])

            if old_fps:
                placeholders = ",".join("?" for _ in old_fps)
                conn.execute(f"""
                    UPDATE semantic
                    SET status=?, superseded_by=?
                    WHERE fp IN ({placeholders})
                """, [_SUPERSEDED_STATUS, new_id, *old_fps])

    # Keyword JSON has its own storage, so update it outside the DB transaction.
    if changed:
        with _get_conn() as conn:
            rows = conn.execute("SELECT content FROM episodic WHERE superseded_by=?", (new_id,)).fetchall()
        for row in rows:
            _mark_keyword_superseded(row["content"], new_fp)
        _debug(f"superseded {changed} old memories for: {new_text[:60]}")
    return changed


# ============================================================
# Save trigger parser
# ============================================================

_MANUAL_SAVE_PATTERNS = [
    re.compile(r'^\s*please\s+remember(?:\s+that)?\s*:?\s+(.+)$', re.IGNORECASE | re.DOTALL),
    re.compile(r'^\s*(?:please\s+)?save\s+(?:this|the following)\s*:\s*(.+)$', re.IGNORECASE | re.DOTALL),
    re.compile(r'^\s*remember\s*:\s*(.+)$',        re.IGNORECASE),
    re.compile(r'^\s*remember\s+(.+)$',             re.IGNORECASE),
    re.compile(r'^\s*merke\s+dir\s*:\s*(.+)$',      re.IGNORECASE),
    re.compile(r'^\s*merke\s+dir\s+(.+)$',          re.IGNORECASE),
    re.compile(r'^\s*merk\s+dir\s*:\s*(.+)$',       re.IGNORECASE),
    re.compile(r'^\s*merk\s+dir\s+(.+)$',           re.IGNORECASE),
    re.compile(r'^\s*speichere\s*:\s*(.+)$',         re.IGNORECASE),
    re.compile(r'^\s*speichere\s+(.+)$',             re.IGNORECASE),
    re.compile(r'^\s*bitte\s+merke\s+dir\s+(.+)$',  re.IGNORECASE),
    re.compile(r'^\s*bitte\s+speichere\s+(.+)$',    re.IGNORECASE),
    re.compile(r'^\s*notiere\s*:\s*(.+)$',           re.IGNORECASE),
    re.compile(r'^\s*notiere\s+(.+)$',               re.IGNORECASE),
]

def _extract_manual_save(text: str) -> Optional[str]:
    raw = (text or "").strip()
    for pat in _MANUAL_SAVE_PATTERNS:
        m = pat.match(raw)
        if m:
            value = (m.group(1) or "").strip()
            if value:
                return value
    return None

def _is_memory_question(text: str) -> bool:
    t = (text or "").lower()
    patterns = [
        "was habe ich", "was hab ich", "was habe ich dir gesagt",
        "was haben wir", "was haben wir gemacht", "was war gestern",
        "was war vorgestern", "was war vor", "was haben wir vor",
        "wann haben wir", "wann wurde", "seit wann", "woran haben wir",
        "welche fortschritte", "hauptthema", "wie hat sich",
        "woran erinnerst du dich", "was hast du gespeichert",
        "was weißt du über mich", "erinnerst du dich",
        "what did i", "what did we", "what happened yesterday",
        "what happened", "when did we", "when was", "since when",
        "what do you remember", "what do you know about me",
    ]
    return any(p in t for p in patterns) or bool(_person_relation_terms_from_query(t))


# ============================================================
# Memory fusion
# ============================================================

def _time_window_score(ts: Any, window: Dict[str, Any], base: float = 0.82) -> float:
    ts_value = _timestamp_value(ts)
    if ts_value is None:
        return base
    start = float(window.get("start", ts_value))
    end = float(window.get("end", ts_value))
    center = float(window.get("center", (start + end) / 2.0))
    span = max(end - start, 1.0)
    distance = abs(ts_value - center) / max(span / 2.0, 1.0)
    return base + max(0.0, 0.12 * (1.0 - min(distance, 1.0)))


def _month_archive_window_for(window: Dict[str, Any]) -> Dict[str, Any]:
    center_ts = float(window.get("center", (float(window["start"]) + float(window["end"])) / 2.0))
    center = datetime.fromtimestamp(center_ts)
    start = _month_start(center.year, center.month)
    end = _next_month_start(center.year, center.month)
    label = f"{_MONTH_NAMES_DE.get(center.month, center.month)} {center.year} (Archiv-Fallback)"
    return {"start": start.timestamp(), "end": end.timestamp(), "center": center_ts, "label": label, "kind": "archive_month", "fallback": "archive_month"}


def _time_fallback_windows(window: Dict[str, Any]) -> List[Dict[str, Any]]:
    if window.get("kind") != "day":
        return []
    start_dt = datetime.fromtimestamp(float(window["start"]))
    base_label = str(window.get("label", "Datum"))
    out = []
    for radius in (1, 3):
        start = _midnight(start_dt - timedelta(days=radius))
        end = _midnight(start_dt + timedelta(days=radius + 1))
        out.append({
            "start": start.timestamp(),
            "end": end.timestamp(),
            "center": float(window["start"]),
            "label": f"{base_label} ±{radius} Tag{'e' if radius != 1 else ''}",
            "kind": "day_fallback",
            "fallback": f"nearby_{radius}d",
            "exact_label": base_label,
        })
    out.append(_month_archive_window_for(window))
    return out


def _collect_time_window_memories(
    window: Dict[str, Any],
    state: dict,
    top_k: int,
    archive_only: bool = False,
    include_archive: bool = True,
) -> List[Dict[str, Any]]:
    top_k = max(1, min(int(top_k or state.get("supermem_top_k", 5) or 5), 10))
    start = float(window["start"])
    end = float(window["end"])
    scored: List[Tuple[float, Dict[str, Any]]] = []

    try:
        with _get_conn() as conn:
            ep_rows = conn.execute("""
                SELECT id, role, author_user, content, compressed, keywords, category, memory_type, maat_field, tags,
                       priority, importance, hits, ts, status, confidence
                FROM episodic
                WHERE COALESCE(status, 'active') = 'active'
                  AND ts >= ? AND ts < ?
                ORDER BY ts DESC LIMIT 300
            """, (start, end)).fetchall()

            sm_rows = conn.execute("""
                SELECT text, category, memory_type, maat_field, tags, source_role, author_user, priority, ts, status, confidence
                FROM semantic
                WHERE COALESCE(status, 'active') = 'active'
                  AND ts >= ? AND ts < ?
                ORDER BY ts DESC LIMIT 300
            """, (start, end)).fetchall()

            if include_archive:
                ar_rows = conn.execute("""
                    SELECT period, period_start, period_end, category, memory_type, maat_field, tags,
                           summary, source_count, priority, importance, status, updated_at
                    FROM monthly_archive
                    WHERE COALESCE(status, 'active') = 'active'
                      AND period_start < ? AND period_end > ?
                    ORDER BY period_start DESC LIMIT 120
                """, (end, start)).fetchall()
            else:
                ar_rows = []
    except Exception as e:
        _debug(f"time recall db error: {e}")
        ep_rows = []
        sm_rows = []
        ar_rows = []

    if archive_only:
        ep_rows = []
        sm_rows = []

    for row in ep_rows:
        memory_type = _normalize_memory_type(row["memory_type"], row["content"])
        score = _time_window_score(row["ts"], window, 0.84)
        score += 0.04 * float(row["importance"] or 0.50)
        score += 0.02 * min(int(row["hits"] or 0), 5)
        score += 0.04 * float(row["priority"] or 0.50)
        score += 0.03 * float(row["confidence"] or 0.70)
        score += _memory_type_bonus(memory_type) * 0.5
        item = dict(row)
        item["source"] = "time"
        item["content"] = row["content"]
        item["memory_type"] = memory_type
        item["maat_field"] = _normalize_maat_field(row["maat_field"], row["content"])
        item["time_window"] = window["label"]
        score += _memory_author_bonus(item, state)
        score += _time_recall_user_bonus(item, state)
        scored.append((score, item))

    for row in sm_rows:
        memory_type = _normalize_memory_type(row["memory_type"], row["text"])
        score = _time_window_score(row["ts"], window, 0.78)
        score += 0.04 * float(row["priority"] or 0.50)
        score += 0.03 * float(row["confidence"] or 0.70)
        score += _memory_type_bonus(memory_type) * 0.5
        item = dict(row)
        item["source"] = "time"
        item["content"] = row["text"]
        item["memory_type"] = memory_type
        item["maat_field"] = _normalize_maat_field(row["maat_field"], row["text"])
        item["time_window"] = window["label"]
        score += _memory_author_bonus(item, state)
        score += _time_recall_user_bonus(item, state)
        scored.append((score, item))

    for row in ar_rows:
        memory_type = _normalize_memory_type(row["memory_type"], row["summary"])
        center = (float(row["period_start"] or start) + float(row["period_end"] or end)) / 2.0
        score = _time_window_score(center, window, 0.80)
        score += 0.05 * min(int(row["source_count"] or 0), 20) / 20.0
        score += 0.05 * float(row["priority"] or 0.50)
        score += 0.04 * float(row["importance"] or 0.50)
        score += _memory_type_bonus(memory_type) * 0.5
        item = dict(row)
        item["source"] = "archive"
        item["content"] = row["summary"]
        item["ts"] = center
        item["memory_type"] = memory_type
        item["maat_field"] = _normalize_maat_field(row["maat_field"], row["summary"])
        item["time_window"] = window["label"]
        scored.append((score, item))

    for it in _load_keywords():
        if archive_only:
            break
        if not _status_is_active(it.get("status")):
            continue
        ts_value = _memory_timestamp(it)
        if ts_value is None or not (start <= ts_value < end):
            continue
        memory = it.get("memory", "")
        memory_type = _normalize_memory_type(it.get("memory_type") or it.get("type"), memory)
        score = _time_window_score(ts_value, window, 0.76)
        score += 0.05 * float(it.get("priority", 0.50) or 0.50)
        score += 0.03 * float(it.get("confidence", 0.70) or 0.70)
        if it.get("always"):
            score += 0.05
        score += _memory_type_bonus(memory_type) * 0.5
        item = dict(it)
        item["source"] = "time"
        item["content"] = memory
        item["memory_type"] = memory_type
        item["maat_field"] = _normalize_maat_field(it.get("maat_field") or it.get("field"), memory)
        item["time_window"] = window["label"]
        score += _memory_author_bonus(item, state)
        score += _time_recall_user_bonus(item, state)
        scored.append((score, item))

    scored.sort(key=lambda x: (_time_recall_user_rank(x[1], state), x[0]), reverse=True)
    results = []
    seen = set()
    for score, item in scored:
        content = item.get("content") or item.get("text") or item.get("compressed", "")
        fp = _fingerprint(content)
        if fp in seen:
            continue
        seen.add(fp)
        item["score"] = round(score, 3)
        results.append(item)
        if len(results) >= top_k:
            break

    ids = [str(it["id"]) for it in results if it.get("id") is not None]
    if ids:
        try:
            with _IO_LOCK:
                with _get_conn() as conn:
                    conn.execute(f"UPDATE episodic SET hits=hits+1 WHERE id IN ({','.join('?' for _ in ids)})", ids)
        except Exception as e:
            _debug(f"time recall hit update skipped: {e}")

    _debug(f"time recall window={window['label']} hits={len(results)}")
    return results


def _recall_time_memories(query: str, state: dict) -> List[Dict[str, Any]]:
    window = _time_query_window(query)
    if not window:
        return []

    top_k = max(1, min(int(state.get("supermem_top_k", 5) or 5), 10))
    exact_include_archive = window.get("kind") != "day"
    results = _collect_time_window_memories(window, state, top_k, include_archive=exact_include_archive)
    if results or window.get("kind") != "day":
        return results

    for fallback in _time_fallback_windows(window):
        archive_only = fallback.get("fallback") == "archive_month"
        fallback_results = _collect_time_window_memories(
            fallback,
            state,
            top_k,
            archive_only=archive_only,
            include_archive=archive_only,
        )
        if not fallback_results:
            continue
        for item in fallback_results:
            item["time_exact_miss"] = window.get("label", "")
            item["time_fallback"] = fallback.get("label", "")
            item["time_window"] = fallback.get("label", item.get("time_window", ""))
            if archive_only:
                item["source"] = "archive"
        _debug(f"time recall fallback exact={window['label']} fallback={fallback['label']} hits={len(fallback_results)}")
        return fallback_results

    _debug(f"time recall exact miss window={window['label']} no fallback hits")
    return []


_TIMELINE_QUERY_STOP = {
    "wann", "haben", "wir", "ich", "du", "den", "die", "das", "der", "dem", "ein",
    "eine", "einen", "einer", "einem", "eingebaut", "gebaut", "gemacht", "war",
    "wurde", "seit", "entwickelt", "fortschritte", "gab", "projekt", "thema",
    "what", "when", "did", "we", "build", "built", "add", "added", "make",
    "made", "happen", "happened", "since", "develop",
}


def _timeline_topic_terms(query: str) -> List[str]:
    toks = [t for t in _tokens(query) if len(t) > 2]
    terms = []
    for tok in toks:
        folded = _fold_text(tok)
        if folded in _TIMELINE_QUERY_STOP:
            continue
        if folded in {"gestern", "vorgestern", "woche", "wochen", "monat", "monaten", "jahr", "jahren"}:
            continue
        terms.append(tok)
    seen = set()
    out = []
    for term in terms:
        key = _fold_text(term)
        if key not in seen:
            seen.add(key)
            out.append(term)
    return out[:6]


def _is_timeline_topic_question(query: str) -> bool:
    text = _fold_text(query or "")
    return bool(
        re.search(r"\bwann\s+haben\s+wir\b|\bwann\s+wurde\b|\bseit\s+[a-z]", text)
        or re.search(r"\bwhen\s+did\s+we\b|\bwhen\s+was\b|\bsince\s+[a-z]", text)
    )


def _recall_timeline_topic_memories(query: str, state: dict) -> List[Dict[str, Any]]:
    if not _is_timeline_topic_question(query):
        return []

    terms = _timeline_topic_terms(query)
    if not terms:
        return []
    folded_terms = [_fold_text(t) for t in terms]
    top_k = max(1, min(int(state.get("supermem_top_k", 5) or 5), 10))
    scored: List[Tuple[float, Dict[str, Any]]] = []

    try:
        with _get_conn() as conn:
            rows = conn.execute("""
                SELECT id, role, author_user, content, compressed, keywords, category, memory_type, maat_field, tags,
                       priority, importance, hits, ts, status, confidence
                FROM episodic
                WHERE COALESCE(status, 'active') = 'active'
                ORDER BY ts DESC LIMIT 1200
            """).fetchall()
            archive_rows = conn.execute("""
                SELECT period, period_start, period_end, category, memory_type, maat_field, tags,
                       summary, source_count, priority, importance, status, updated_at
                FROM monthly_archive
                WHERE COALESCE(status, 'active') = 'active'
                ORDER BY period_start DESC LIMIT 600
            """).fetchall()
    except Exception as e:
        _debug(f"timeline topic db error: {e}")
        rows = []
        archive_rows = []

    for row in rows:
        blob = _fold_text(" ".join(str(x or "") for x in [row["content"], row["keywords"], row["tags"]]))
        overlap = sum(1 for term in folded_terms if term in blob)
        if overlap <= 0:
            continue
        memory_type = _normalize_memory_type(row["memory_type"], row["content"])
        score = 0.72 + 0.12 * min(overlap, 3)
        score += 0.04 * float(row["importance"] or 0.50)
        score += 0.02 * min(int(row["hits"] or 0), 5)
        score += 0.04 * float(row["priority"] or 0.50)
        score += 0.03 * float(row["confidence"] or 0.70)
        score += _memory_type_bonus(memory_type) * 0.5
        score += _recency_bonus(row["ts"])
        item = dict(row)
        item["source"] = "timeline"
        item["content"] = row["content"]
        item["memory_type"] = memory_type
        item["maat_field"] = _normalize_maat_field(row["maat_field"], row["content"])
        item["timeline_terms"] = ",".join(terms)
        score += _memory_author_bonus(item, state)
        scored.append((score, item))

    for row in archive_rows:
        blob = _fold_text(" ".join(str(x or "") for x in [row["summary"], row["tags"], row["period"]]))
        overlap = sum(1 for term in folded_terms if term in blob)
        if overlap <= 0:
            continue
        memory_type = _normalize_memory_type(row["memory_type"], row["summary"])
        center = (float(row["period_start"] or 0) + float(row["period_end"] or 0)) / 2.0
        score = 0.70 + 0.10 * min(overlap, 3)
        score += 0.05 * min(int(row["source_count"] or 0), 20) / 20.0
        score += 0.04 * float(row["priority"] or 0.50)
        score += 0.04 * float(row["importance"] or 0.50)
        score += _memory_type_bonus(memory_type) * 0.5
        score += _recency_bonus(center)
        item = dict(row)
        item["source"] = "archive"
        item["content"] = row["summary"]
        item["ts"] = center
        item["memory_type"] = memory_type
        item["maat_field"] = _normalize_maat_field(row["maat_field"], row["summary"])
        item["timeline_terms"] = ",".join(terms)
        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    seen = set()
    for score, item in scored:
        content = item.get("content") or ""
        fp = _fingerprint(content)
        if fp in seen:
            continue
        seen.add(fp)
        item["score"] = round(score, 3)
        results.append(item)
        if len(results) >= top_k:
            break

    ids = [str(it["id"]) for it in results if it.get("id") is not None]
    if ids:
        with _IO_LOCK:
            with _get_conn() as conn:
                conn.execute(f"UPDATE episodic SET hits=hits+1 WHERE id IN ({','.join('?' for _ in ids)})", ids)

    _debug(f"timeline topic terms={','.join(terms)} hits={len(results)}")
    return results






def _person_relation_terms_from_query(*args, **kwargs):
    return []


def _recall_person_graph(*args, **kwargs):
    return []


def _recall_person_memories(*args, **kwargs):
    return []


def recall_all(query: str, state: dict) -> List[Dict[str, Any]]:
    k     = max(1, min(int(state.get("supermem_top_k", 5) or 5), 10))
    minsc = float(state.get("supermem_min_score", 0.15))

    w_res  = _recall_working(query, top_k=3, state=state)
    time_res = _recall_time_memories(query, state)
    timeline_res = _recall_timeline_topic_memories(query, state)
    graph_res = _recall_person_graph(query, state)
    person_res = _recall_person_memories(query, state)
    kw_res = _recall_keywords(query, top_k=k, state=state)
    ep_res = _recall_episodic(query, top_k=k, min_score=minsc, state=state)
    sm_res = _recall_semantic(query, top_k=3, min_score=minsc, state=state)

    _debug(f"recall raw: working={len(w_res)} time={len(time_res)} timeline={len(timeline_res)} graph={len(graph_res)} person={len(person_res)} keyword={len(kw_res)} "
           f"episodic={len(ep_res)} semantic={len(sm_res)}")

    by_fp: Dict[str, Dict[str, Any]] = {}
    for item in w_res + time_res + timeline_res + graph_res + person_res + kw_res + ep_res + sm_res:
        content = item.get("content") or item.get("text") or item.get("compressed", "")
        fp      = _fingerprint(content)
        item["content"] = content
        existing = by_fp.get(fp)
        if existing is None or float(item.get("score", 0) or 0) > float(existing.get("score", 0) or 0):
            by_fp[fp] = item

    results = list(by_fp.values())
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    results = results[:k]
    _debug_recall(results, query)
    return results


def _format_recall_block(memories: List[Dict[str, Any]],
                          show_source: bool = True, lang: str = "de") -> str:
    if not memories:
        return ""
    header = (f"[MAAT_MEMORY — {len(memories)} recalled memories]"
              if lang == "en" else
              f"[MAAT_MEMORY — {len(memories)} erinnerte Erinnerungen]")
    lines = [header]
    for i, m in enumerate(memories, 1):
        src     = f" ({m['source']})" if show_source else ""
        cat     = m.get("category", "")
        mtype   = _normalize_memory_type(m.get("memory_type"), m.get("content", ""))
        field   = _normalize_maat_field(m.get("maat_field"), m.get("content", ""))
        prio    = float(m.get("priority", 0.50) or 0.50)
        time_label = _relative_time_label(_memory_timestamp(m), lang)
        tag     = "/".join(part for part in [cat, mtype, field] if part)
        cat_str = f" [{tag}]" if tag else ""
        author = _memory_author_label(m)
        subject = _memory_subject_label(m)
        author_str = f" author={author}" if author else ""
        subject_str = f" subject={subject}" if subject else ""
        person_str = f" persons={m.get('person_names')}" if m.get("person_names") else ""
        window_str = f" window={m.get('time_window')}" if m.get("time_window") else ""
        terms_str = f" terms={m.get('timeline_terms')}" if m.get("timeline_terms") else ""
        time_str = f" time={time_label}" if time_label else ""
        prio_str = f" priority={prio:.2f}" if prio >= 0.75 else ""
        txt_limit = 900 if m.get("source") == "person_graph" else 200
        txt     = (m.get("content") or "")[:txt_limit]
        lines.append(f"{i}.{src}{cat_str}{author_str}{subject_str}{person_str}{window_str}{terms_str}{time_str}{prio_str} {txt}")
    return "\n".join(lines)


# ============================================================
# Mini-dreaming
# ============================================================

def _archive_month_window(ts_value: float) -> Tuple[str, float, float]:
    dt = datetime.fromtimestamp(float(ts_value))
    start = _month_start(dt.year, dt.month)
    end = _next_month_start(dt.year, dt.month)
    return f"{dt.year:04d}-{dt.month:02d}", start.timestamp(), end.timestamp()


def _archive_tags(rows: List[sqlite3.Row]) -> str:
    counts: Dict[str, int] = {}
    for row in rows:
        raw = " ".join(str(row[k] or "") for k in ("tags", "keywords", "content") if k in row.keys())
        for tag in _parse_tags(raw):
            if tag in {"memory", "erinnerung", "normal", "false", "true"}:
                continue
            counts[tag] = counts.get(tag, 0) + 1
    return ",".join(k for k, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:10])


def _archive_summary(period: str, category: str, rows: List[sqlite3.Row]) -> str:
    title = f"[Maat-Archive:{period}:{category}] {len(rows)} Erinnerungen"
    tags = _archive_tags(rows)
    tag_part = f" Themen: {tags}." if tags else ""
    sorted_rows = sorted(
        rows,
        key=lambda r: (
            float(r["priority"] or 0.50),
            float(r["importance"] or 0.50),
            int(r["hits"] or 0),
            float(r["ts"] or 0),
        ),
        reverse=True,
    )
    snippets = []
    for row in sorted_rows[:8]:
        day = datetime.fromtimestamp(float(row["ts"] or 0)).strftime("%d.%m.")
        snippets.append(f"{day} {_compress(row['content'] or '', 130)}")
    return _compress(f"{title}.{tag_part} Kernpunkte: " + " | ".join(snippets), 1200)


def _run_monthly_archive(days_old: int = 30) -> str:
    if not _DB_PATH:
        return "Archive skipped: DB not ready."

    days_old = max(1, int(days_old or 30))
    cutoff = time.time() - days_old * 86400
    try:
        with _get_conn() as conn:
            rows = conn.execute("""
                SELECT id, content, keywords, category, memory_type, maat_field, tags,
                       priority, importance, hits, ts, status, confidence
                FROM episodic
                WHERE COALESCE(status, 'active') = 'active'
                  AND ts < ?
                ORDER BY ts DESC LIMIT 5000
            """, (cutoff,)).fetchall()
    except Exception as e:
        _debug(f"archive db read error: {e}")
        return f"Archive error: {e}"

    if not rows:
        _debug("archive: no old memories")
        return "Archive: no old memories."

    grouped: Dict[Tuple[str, str], List[sqlite3.Row]] = {}
    windows: Dict[str, Tuple[float, float]] = {}
    for row in rows:
        period, start, end = _archive_month_window(float(row["ts"]))
        category = row["category"] or _detect_category(row["content"] or "")
        grouped.setdefault((period, category), []).append(row)
        windows[period] = (start, end)

    now = time.time()
    changed = 0
    with _IO_LOCK:
        with _get_conn() as conn:
            for (period, category), group in grouped.items():
                start, end = windows[period]
                summary = _archive_summary(period, category, group)
                fp = _fingerprint(f"{period}:{category}:{summary}")
                priority = max(float(r["priority"] or 0.50) for r in group)
                importance = max(float(r["importance"] or 0.50) for r in group)
                memory_type = _normalize_memory_type(group[0]["memory_type"], summary)
                maat_field = _normalize_maat_field(group[0]["maat_field"], summary)
                tags = _archive_tags(group)
                existing = conn.execute(
                    "SELECT id, summary, source_count FROM monthly_archive WHERE period=? AND category=?",
                    (period, category),
                ).fetchone()
                if existing:
                    if existing["summary"] == summary and int(existing["source_count"] or 0) == len(group):
                        continue
                    conn.execute("""
                        UPDATE monthly_archive
                        SET period_start=?, period_end=?, memory_type=?, maat_field=?, tags=?,
                            summary=?, source_count=?, priority=?, importance=?,
                            status=?, updated_at=?, fp=?
                        WHERE id=?
                    """, (
                        start, end, memory_type, maat_field, tags, summary, len(group),
                        priority, importance, _ACTIVE_STATUS, now, fp, existing["id"],
                    ))
                else:
                    conn.execute("""
                        INSERT INTO monthly_archive
                          (period, period_start, period_end, category, memory_type, maat_field,
                           tags, summary, source_count, priority, importance, status, created_at, updated_at, fp)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        period, start, end, category, memory_type, maat_field, tags, summary,
                        len(group), priority, importance, _ACTIVE_STATUS, now, now, fp,
                    ))
                changed += 1

    msg = f"Archive complete: {changed} monthly summaries updated."
    _debug(msg)
    return msg


def _maybe_run_monthly_archive(state: dict, force: bool = False) -> None:
    if not state.get("supermem_archive_enabled", True):
        return
    now = time.time()
    if not force and now - float(_ARCHIVE_LAST_RUN.get("ts", 0.0) or 0.0) < 12 * 3600:
        return
    _ARCHIVE_LAST_RUN["ts"] = now
    try:
        _run_monthly_archive(int(state.get("supermem_archive_after_days", 30)))
    except Exception as e:
        print(f"[🧠 supermem] archive error: {e}")


def _run_dreaming(hours_back: int = 24) -> str:
    cutoff = time.time() - hours_back * 3600
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT content, category FROM episodic
            WHERE ts >= ? AND COALESCE(status, 'active') = 'active'
            ORDER BY importance DESC LIMIT 100
        """, (cutoff,)).fetchall()

    if not rows:
        _debug("dreaming: no new memories")
        return "No new memories to consolidate."

    by_cat: Dict[str, List[str]] = {}
    for row in rows:
        by_cat.setdefault(row["category"], []).append(row["content"])

    count = 0
    for cat, texts in by_cat.items():
        summary     = _compress(" ".join(texts[:5]), max_len=300)
        dream_text  = f"[Maat-Dream:{cat}] {summary}"
        _add_semantic(dream_text)
        count += 1
        _debug(f"dreaming: consolidated '{cat}' ({len(texts)} entries)")

    msg = f"Dreaming complete: {count} categories consolidated."
    print(f"[🧠 dream]  {msg}")
    return msg


# ============================================================
# Model-driven save parser
# ============================================================

_SAVE_PATTERNS = [
    re.compile(r'(?is)\bsave\s*:\s*\((.*?)\)\s*'),
    re.compile(r'(?is)\bsave\s*:\s*({.*?})\s*'),
    re.compile(r'(?is)\bsave\s*:\s*(.+?)(?:\n|$)'),
]

_SAVE_KV_RE = re.compile(
    r'(?is)\b(memory|keywords|tags|always|type|memory_type|field|maat_field|priority)\s*=\s*(.*?)'
    r'(?=(?:,\s*|\s+)(?:memory|keywords|tags|always|type|memory_type|field|maat_field|priority)\s*=|$)'
)

_SAVE_START_RE = re.compile(r"(?is)\bsave\s*:\s*")


def _clean_save_value(value: str) -> str:
    value = (value or "").strip().strip(",")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    return value

def _parse_save_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "ja", "on"}

def _parse_save_fields(raw: str) -> Optional[Dict[str, Any]]:
    fields: Dict[str, str] = {}
    for match in _SAVE_KV_RE.finditer(raw):
        key = match.group(1).lower()
        fields[key] = _clean_save_value(match.group(2))
    if not fields:
        return None
    return {
        "memory":   fields.get("memory", "").strip(),
        "keywords": fields.get("keywords", "").strip(),
        "tags":     fields.get("tags", "").strip(),
        "always":   _parse_save_bool(fields.get("always", False)),
        "memory_type": _normalize_memory_type(fields.get("memory_type") or fields.get("type"), fields.get("memory", "")),
        "maat_field": _normalize_maat_field(fields.get("maat_field") or fields.get("field"), fields.get("memory", "")),
        "priority": _normalize_priority(fields.get("priority"), fields.get("memory", ""), _parse_save_bool(fields.get("always", False))),
    }

def _parse_save(raw: str) -> Optional[Dict[str, Any]]:
    raw = (raw or "").strip()
    if not raw:
        return None
    if raw.startswith("(") and raw.endswith(")"):
        raw = raw[1:-1].strip()
    if raw.startswith("{"):
        try:
            obj = json.loads(raw)
            return {
                "memory":   str(obj.get("memory", raw)).strip(),
                "keywords": str(obj.get("keywords", "")).strip(),
                "tags":     str(obj.get("tags", "")).strip(),
                "always":   _parse_save_bool(obj.get("always", False)),
                "memory_type": _normalize_memory_type(obj.get("memory_type") or obj.get("type"), obj.get("memory", "")),
                "maat_field": _normalize_maat_field(obj.get("maat_field") or obj.get("field"), obj.get("memory", "")),
                "priority": _normalize_priority(obj.get("priority"), obj.get("memory", ""), _parse_save_bool(obj.get("always", False))),
            }
        except Exception:
            pass

    parsed_fields = _parse_save_fields(raw)
    if parsed_fields and parsed_fields.get("memory"):
        return parsed_fields

    return {
        "memory": raw,
        "keywords": "",
        "tags": "",
        "always": False,
        "memory_type": _detect_memory_type(raw),
        "maat_field": _normalize_maat_field("", raw),
        "priority": _normalize_priority(None, raw),
    }


def _scan_wrapped_save(text: str, start: int, opener: str, closer: str) -> Tuple[int, str]:
    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth <= 0:
                return i + 1, text[start + 1:i]
        i += 1

    line_end = text.find("\n", start)
    if line_end < 0:
        line_end = len(text)
    return line_end, text[start + 1:line_end].rstrip(") }")


def _iter_save_spans(text: str) -> List[Tuple[int, int, str]]:
    spans: List[Tuple[int, int, str]] = []
    pos = 0
    while True:
        m = _SAVE_START_RE.search(text, pos)
        if not m:
            break

        value_start = m.end()
        while value_start < len(text) and text[value_start].isspace():
            value_start += 1

        if value_start >= len(text):
            spans.append((m.start(), value_start, ""))
            break

        first = text[value_start]
        if first == "(":
            end, raw = _scan_wrapped_save(text, value_start, "(", ")")
        elif first == "{":
            end, raw_inner = _scan_wrapped_save(text, value_start, "{", "}")
            raw = "{" + raw_inner + "}"
        else:
            end = text.find("\n", value_start)
            if end < 0:
                end = len(text)
            raw = text[value_start:end]

        spans.append((m.start(), end, raw.strip()))
        pos = max(end, m.end() + 1)
    return spans


def _save_protected_spans(text: str) -> List[Tuple[int, int]]:
    raw = text or ""
    patterns = [
        r"(?is)<think\b[^>]*>.*?</think>",
        r"(?is)&lt;think\b[^&]*?&gt;.*?&lt;/think&gt;",
        r"(?is)<thinking\b[^>]*>.*?</thinking>",
        r"(?is)&lt;thinking\b[^&]*?&gt;.*?&lt;/thinking&gt;",
        r"(?is)<reasoning\b[^>]*>.*?</reasoning>",
        r"(?is)&lt;reasoning\b[^&]*?&gt;.*?&lt;/reasoning&gt;",
        r"(?is)<details\b[^>]*(?:maat-memory-save-box|thinking-block|thinking|reasoning)[^>]*>.*?</details>",
        r"(?is)<details\b[^>]*>\s*<summary\b[^>]*>\s*(?:details|thinking|reasoning|gedanken|denken).*?</summary>.*?</details>",
        r"(?is)\[thinking[^\]]*\].*?\[/thinking\]",
        r"(?is)\[reasoning[^\]]*\].*?\[/reasoning\]",
        r"(?is)\[MAAT_CHAT_SUMMARY\].*?(?=(?:\[MAAT_CHAT_SUMMARY\])|\Z)",
        r"(?is)\[MAAT_CHAT_MEMORY[^\]]*\].*?\[/MAAT_CHAT_MEMORY\]",
        r"(?is)\[MAAT_CONTEXT_SUMMARY[^\]]*\].*?\[/MAAT_CONTEXT_SUMMARY\]",
        r"(?is)\[MAAT_INTERNAL[^\]]*\].*?\[/MAAT_INTERNAL\]",
        r"(?is)\[MAAT_THINKING[^\]]*\].*?\[/MAAT_THINKING\]",
        r"(?is)\[MAAT_REFLEX[^\]]*\].*?\[/MAAT_REFLEX\]",
        r"(?is)\[MAAT_STYLE[^\]]*\].*?\[/MAAT_STYLE\]",
        r"(?is)\[MAAT_DIRECT_FEEDBACK[^\]]*\].*?\[/MAAT_DIRECT_FEEDBACK\]",
        r"(?is)\[MAAT_ACTIVE_LESSONS[^\]]*\].*?\[/MAAT_ACTIVE_LESSONS\]",
    ]
    spans: List[Tuple[int, int]] = []
    for pattern in patterns:
        spans.extend((m.start(), m.end()) for m in re.finditer(pattern, raw))
    spans.sort()
    return spans


_INTERNAL_CONTEXT_MARKERS = (
    "[MAAT_LOCAL_ONLY]",
    "[MAAT_INTERNAL_CONTEXT_COMPRESSION]",
    "[MAAT_CONTEXT_SUMMARY]",
    "[/MAAT_CONTEXT_SUMMARY]",
    "[MAAT_CHAT_MEMORY]",
    "[MAAT_CHAT_SUMMARY]",
)


def _is_internal_context_text(text: str) -> bool:
    raw = str(text or "")
    return any(marker in raw for marker in _INTERNAL_CONTEXT_MARKERS)


def _position_in_spans(pos: int, spans: List[Tuple[int, int]]) -> bool:
    return any(start <= pos < end for start, end in spans)


def _strip_orphan_save_tail(text: str) -> str:
    """
    Entfernt kaputte Reststücke wie:
    ". Wir haben ... keywords=..., tags=..., type=..., priority=normal)"
    die entstehen, wenn ein Modell save-Felder ohne gültiges save:(...) ausgibt.
    """
    if not text:
        return text
    lines = text.rstrip().splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""

    tail = lines[-1].strip()
    orphan_tail_re = re.compile(
        r"(?is)^\s*[.\-–—]*\s*.*?"
        r"\bkeywords\s*=.*?\btags\s*=.*?"
        r"\b(?:always|type|memory_type|field|maat_field|priority)\s*=.*?\)?\s*$"
    )
    if not tail.lower().startswith("save:") and orphan_tail_re.search(tail):
        lines.pop()
    return "\n".join(lines).strip()


def _extract_model_saves(output: str) -> Tuple[str, List[Dict[str, Any]]]:
    modified = output or ""
    saves: List[Dict[str, Any]] = []
    spans = _iter_save_spans(modified)
    if not spans:
        return _strip_orphan_save_tail(modified), saves
    protected_spans = _save_protected_spans(modified)

    pieces = []
    last = 0
    for start, end, raw in spans:
        pieces.append(modified[last:start])
        parsed = _parse_save(raw)
        if parsed and parsed.get("memory") and not _position_in_spans(start, protected_spans):
            saves.append(parsed)
        elif parsed and parsed.get("memory"):
            _debug(f"model save ignored inside thinking/internal block: {parsed['memory'][:60]}")
        last = end
    pieces.append(modified[last:])
    modified = "".join(pieces)
    return _strip_orphan_save_tail(modified), saves


def _priority_label(priority: Any) -> str:
    try:
        value = float(priority)
    except Exception:
        value = _normalize_priority(priority)
    if value >= 0.90:
        return "critical"
    if value >= 0.70:
        return "high"
    if value <= 0.30:
        return "low"
    return "normal"


def _format_save_directive(parsed: Dict[str, Any]) -> str:
    memory = (parsed.get("memory") or "").strip()
    keywords = (parsed.get("keywords") or "").strip()
    tags = (parsed.get("tags") or "").strip()
    always = "true" if parsed.get("always") else "false"
    memory_type = _normalize_memory_type(parsed.get("memory_type") or parsed.get("type"), memory)
    field = _normalize_maat_field(parsed.get("maat_field") or parsed.get("field"), memory)
    priority = _priority_label(parsed.get("priority"))
    return (
        "save: ("
        f"memory={memory}, "
        f"keywords={keywords}, "
        f"tags={tags}, "
        f"always={always}, "
        f"type={memory_type}, "
        f"field={field}, "
        f"priority={priority}"
        ")"
    )


def _format_save_box(saves: List[Dict[str, Any]], language=None) -> str:
    if not saves:
        return ""
    boxes = []
    for i, save in enumerate(saves, 1):
        title = memory_text('Erinnerung angelegt',language) if len(saves)==1 else memory_text('Erinnerung {index}/{total} angelegt',language,index=i,total=len(saves))
        more = memory_text('mehr anzeigen',language)
        block_id = f"maat-memory-save-{int(time.time() * 1000)}-{i}"
        escaped = html.escape(_format_save_directive(save), quote=False)
        boxes.append(
            f"\n<details class=\"maat-memory-save-box\" data-block-id=\"{block_id}\" "
            f"style=\"border:1px solid rgba(160,160,180,.35);border-radius:8px;"
            f"padding:10px 14px;margin:8px 0;background:rgba(30,32,40,.35);\">\n"
            f"  <summary class=\"maat-memory-save-header\" style=\"cursor:pointer;font-weight:700;\">\n"
            f"    <span class=\"maat-memory-save-title\">🧠 {title} — {more}</span>\n"
            f"  </summary>\n"
            f"  <div class=\"maat-memory-save-content pretty_scrollbar\" style=\"margin-top:12px;\">\n"
            f"    <pre style=\"white-space:pre-wrap;overflow:auto;border:1px solid rgba(160,160,180,.35);"
            f"border-radius:5px;padding:12px;background:rgba(5,8,14,.55);\"><code class=\"nohighlight\">{escaped}</code></pre>\n"
            f"  </div>\n"
            f"</details>\n"
        )
    return "\n\n".join(boxes)


def _append_save_box(output: str, saves: List[Dict[str, Any]]) -> str:
    box = _format_save_box(saves)
    if not box:
        return output or ""
    base = (output or "").strip()
    return (base + "\n\n" + box).strip() if base else box


# ============================================================
# Store helper
# ============================================================

def _store_autostore(role: str, decision: Dict[str, Any], state: Optional[dict] = None):
    text = (decision.get("text") or "").strip()
    if not text:
        return
    memory_type = _normalize_memory_type(decision.get("memory_type"), text)
    maat_field = _normalize_maat_field(decision.get("maat_field"), text)
    tags = decision.get("tags") or ""
    priority = decision.get("priority")
    author_user = _author_user_for_role(role)
    layers = []

    episodic_id, created = _add_episodic(role, text, memory_type, tags, maat_field, priority, author_user)
    layers.append("episodic")
    if decision.get("semantic"):
        _add_semantic(text, memory_type, tags, maat_field, priority, role, author_user)
        layers.append("semantic")
    if decision.get("keyword"):
        ok, _ = _add_keyword(text, memory_type=memory_type, tags=tags, maat_field=maat_field, priority=priority, source_role=role, author_user=author_user)
        if ok:
            layers.append("keyword")

    superseded = _supersede_related_memories(episodic_id, text, memory_type) if created else 0
    if superseded:
        layers.append(f"superseded={superseded}")
    graph_updates = _update_person_graph_from_text(role, text, state, tags=tags, memory_type=memory_type, maat_field=maat_field)
    if graph_updates:
        layers.append(f"graph={graph_updates}")

    _debug_store(role, text, f"autostore:{'+'.join(layers)}:{memory_type}:score={decision.get('score', 0):.2f}")

def _store_all_layers(
    role: str,
    text: str,
    always_keyword: bool = False,
    memory_type: str = "",
    keywords: str = "",
    tags: str = "",
    maat_field: str = "",
    priority: Any = None,
    state: Optional[dict] = None,
):
    text = (text or "").strip()
    if not text:
        return
    memory_type = _normalize_memory_type(memory_type, text)
    maat_field = _normalize_maat_field(maat_field, text)
    tags = tags or keywords
    priority = _normalize_priority(priority, text, always_keyword)
    author_user = _author_user_for_role(role)
    layers = []
    episodic_id, created = _add_episodic(role, text, memory_type, tags, maat_field, priority, author_user);  layers.append("episodic")
    _add_semantic(text, memory_type, tags, maat_field, priority, role, author_user);        layers.append("semantic")
    ok, _ = _add_keyword(text, keywords=keywords, always=always_keyword, memory_type=memory_type, tags=tags, maat_field=maat_field, priority=priority, source_role=role, author_user=author_user)
    if ok: layers.append("keyword")
    superseded = _supersede_related_memories(episodic_id, text, memory_type) if created else 0
    if superseded:
        layers.append(f"superseded={superseded}")
    graph_updates = _update_person_graph_from_text(role, text, state, tags=tags, memory_type=memory_type, maat_field=maat_field)
    if graph_updates:
        layers.append(f"graph={graph_updates}")
    _debug_store(role, text, f"{'+'.join(layers)}:{memory_type}")


# ============================================================
# Loader hooks
# ============================================================



# Memory hint prompt (injiziert beim ersten Turn)

_HINT_SENT = {"done": False}









def _is_code_or_file_task(text: str) -> bool:
    lower = (text or "").lower()
    if re.search(r"\.(?:py|tex|md|txt|html?|json|csv)\b", lower):
        return True
    if any(word in lower for word in ("datei", "file", "download", "anhang", "attachment")):
        return True
    return bool(re.search(
        r"\b(?:code|programm|program|script|skript|pygame|tool|app|spiel|game|latex|markdown|html|json|csv)\b",
        lower,
    ) and re.search(
        r"\b(?:baue|bau|schreibe|schreib|erstelle|erstell|mache|mach|generiere|create|build)\b",
        lower,
    ))


def _join_hidden_blocks(*blocks: str) -> str:
    return "\n\n".join(block for block in blocks if block)


def _strip_current_user_blocks(text: str) -> str:
    return re.sub(
        r"(?is)\[MAAT_CURRENT_USER\].*?\[/MAAT_CURRENT_USER\]",
        " ",
        str(text or ""),
    ).strip()






def _publish_recall_state(shared: dict, query: str, memories: List[Dict[str, Any]]) -> None:
    is_memory_question = _is_memory_question(query or "")
    info = {
        "query": query or "",
        "count": len(memories),
        "memory_question": is_memory_question,
        "current_user": _current_user_name(),
        "sources": [m.get("source", "?") for m in memories],
        "ts": time.time(),
    }
    shared["super_memory_last_recall"] = info

    # Keep a short-lived grounding anchor for follow-up questions. This prevents
    # anti-hallu from forgetting that the previous answer was memory-grounded.
    grounded = [m for m in memories if m.get("source") != "working"]
    if grounded:
        def _preview_text(item: Dict[str, Any]) -> str:
            limit = 700 if item.get("source") == "person_graph" else 160
            return str(item.get("content", ""))[:limit]

        shared["super_memory_last_grounding"] = {
            **info,
            "count": len(grounded),
            "sources": [m.get("source", "?") for m in grounded],
            "preview": [_preview_text(m) for m in grounded[:5]],
        }




def after_output(user_input: str, output: str, state_obj, state: dict, shared: dict) -> dict:
    if _is_internal_context_text(user_input or "") or _is_internal_context_text(output or ""):
        _debug_skip("internal/local-only context compression: store skipped")
        return {"output": output or ""}
    _sync_current_user_from_turn(user_input or "", state, shared, state_obj)
    if not state.get("supermem_enabled", True):
        return {}
    if state.get("_maat_image_chat_active") or state.get("_maat_image_chat_skip_memory"):
        _debug_skip("image generation turn: store skipped")
        return {}

    modified = output or ""
    saves: List[Dict[str, Any]] = []

    # Model save: always strip save:(...) from visible output. Storing it still
    # respects supermem_allow_model_saves.
    modified, saves = _extract_model_saves(modified)
    allow_model_saves = state.get("supermem_allow_model_saves", True)
    stored_saves: List[Dict[str, Any]] = []
    direct_graph_done = False

    def _direct_turn_person_graph_update(reason: str = "") -> None:
        nonlocal direct_graph_done
        if direct_graph_done or stored_saves:
            return
        direct_graph_done = True
        try:
            graph_updates = _update_person_graph_from_text(
                "user",
                user_input or "",
                state,
                tags="turn,person_graph",
                memory_type="relationship",
                maat_field="V",
            )
            if graph_updates:
                suffix = f" ({reason})" if reason else ""
                _debug(f"person graph direct-turn updates={graph_updates}{suffix}")
        except Exception as e:
            _debug(f"person graph direct-turn error: {e}")

    if saves and allow_model_saves:
        for parsed in saves:
            wrong_user_reason = _wrong_user_model_save_reason(parsed, user_input or "", state)
            if wrong_user_reason:
                _debug_skip(f"model save rejected: {wrong_user_reason}")
                continue
            _store_all_layers(
                "assistant",
                parsed["memory"],
                always_keyword=parsed.get("always", False),
                memory_type=parsed.get("memory_type", ""),
                keywords=parsed.get("keywords", ""),
                tags=parsed.get("tags", ""),
                maat_field=parsed.get("maat_field", ""),
                priority=parsed.get("priority"),
                state=state,
            )
            _update_person_graph_from_text(
                "user",
                parsed["memory"],
                state,
                tags=parsed.get("tags", ""),
                memory_type=parsed.get("memory_type", ""),
                maat_field=parsed.get("maat_field", ""),
            )
            stored_saves.append(parsed)
            print(f"[🧠 supermem] model save: '{parsed['memory'][:60]}'")
        if not stored_saves:
            _direct_turn_person_graph_update("model-save-rejected")
    elif saves:
        _debug_skip("model save stripped: model-saves-off")
        _direct_turn_person_graph_update("model-saves-off")

    _add_working("assistant", modified or output or "")

    if state.get("supermem_autostore", True):
        # A model note may be vague or repeat an old save. It must not suppress
        # independently useful user statements; storage deduplicates exact text.
        user_decision = _autostore_decision("user", user_input or "", state)
        _debug(f"autostore user: store={user_decision.get('store')} score={user_decision.get('score'):.2f} reason={user_decision.get('reason')}")
        if user_decision.get("store"):
            _store_autostore("user", user_decision, state)
        else:
            _direct_turn_person_graph_update("autostore-below-threshold")
            _debug_skip(f"user autostore: {user_decision.get('reason')}")

        assistant_decision = _autostore_decision("assistant", modified or "", state)
        _debug(f"autostore assistant: store={assistant_decision.get('store')} score={assistant_decision.get('score'):.2f} reason={assistant_decision.get('reason')}")
        if assistant_decision.get("store"):
            _store_autostore("assistant", assistant_decision, state)
        else:
            _debug_skip(f"assistant autostore: {assistant_decision.get('reason')}")
    else:
        _direct_turn_person_graph_update("autostore-off")

    _maybe_run_monthly_archive(state)

    if stored_saves and allow_model_saves and state.get("supermem_show_save_box", True):
        modified = _append_save_box(modified, stored_saves)

    if modified != (output or ""):
        return {"output": modified.strip()}

    return {}


# ============================================================
# Commands
# ============================================================

def _timeline_month_title(year: int, month: int, language='de') -> str:
    return f"{memory_text(_MONTH_NAMES_DE.get(month, str(month)),language)} {year}"


def _timeline_scope_from_cmd(cmd: str, language='de') -> Tuple[Optional[float], Optional[float], str]:
    text = _fold_text(cmd or "")
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    year = int(year_match.group(1)) if year_match else None

    month = None
    for name, number in _MONTH_ALIASES.items():
        if re.search(rf"\b{re.escape(name)}\b", text):
            month = number
            break

    if month and not year:
        year = datetime.fromtimestamp(time.time()).year

    if month and year:
        start = _month_start(year, month)
        end = _next_month_start(year, month)
        return start.timestamp(), end.timestamp(), _timeline_month_title(year, month,language)

    if year:
        start = _midnight(datetime(year=year, month=1, day=1))
        end = _midnight(datetime(year=year + 1, month=1, day=1))
        return start.timestamp(), end.timestamp(), str(year)

    return None, None, memory_text('alle Erinnerungen',language)


def _timeline_limit_from_cmd(cmd: str) -> int:
    text = cmd or ""
    m = re.search(r"\b(?:limit|top)\s+(\d{1,3})\b", text, re.IGNORECASE)
    if not m:
        return 120
    return max(10, min(int(m.group(1)), 500))


def _timeline_entry_from_row(row: sqlite3.Row, source: str = "episodic") -> Optional[Dict[str, Any]]:
    ts = _timestamp_value(row["ts"] if "ts" in row.keys() else None)
    content = row["content"] if "content" in row.keys() else ""
    if ts is None or not content:
        return None
    mtype = _normalize_memory_type(row["memory_type"] if "memory_type" in row.keys() else "", content)
    field = _normalize_maat_field(row["maat_field"] if "maat_field" in row.keys() else "", content)
    return {
        "ts": ts,
        "content": content,
        "category": row["category"] if "category" in row.keys() else _detect_category(content),
        "memory_type": mtype,
        "maat_field": field,
        "priority": float(row["priority"] if "priority" in row.keys() and row["priority"] is not None else 0.50),
        "importance": float(row["importance"] if "importance" in row.keys() and row["importance"] is not None else _importance(content)),
        "source": source,
    }


def _timeline_entry_from_keyword(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not _status_is_active(item.get("status")):
        return None
    ts = _memory_timestamp(item)
    content = item.get("memory", "")
    if ts is None or not content:
        return None
    mtype = _normalize_memory_type(item.get("memory_type") or item.get("type"), content)
    field = _normalize_maat_field(item.get("maat_field") or item.get("field"), content)
    return {
        "ts": ts,
        "content": content,
        "category": item.get("category") or _detect_category(content),
        "memory_type": mtype,
        "maat_field": field,
        "priority": float(item.get("priority", 0.50) or 0.50),
        "importance": float(item.get("importance", _importance(content)) or 0.50),
        "source": "keyword",
    }


def _timeline_meta(entry: Dict[str, Any]) -> str:
    parts = [
        entry.get("category", ""),
        _normalize_memory_type(entry.get("memory_type"), entry.get("content", "")),
        _normalize_maat_field(entry.get("maat_field"), entry.get("content", "")),
    ]
    return "/".join(part for part in parts if part)


def _collect_timeline_entries(limit: int = 1200,
                              start: Optional[float] = None,
                              end: Optional[float] = None) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    try:
        with _get_conn() as conn:
            where = ["COALESCE(status, 'active') = 'active'"]
            params: List[Any] = []
            if start is not None and end is not None:
                where.append("ts >= ? AND ts < ?")
                params.extend([start, end])
            params.append(limit)
            rows = conn.execute(f"""
                SELECT content, category, memory_type, maat_field, priority, importance, ts, tags, keywords
                FROM episodic
                WHERE {' AND '.join(where)}
                ORDER BY ts DESC LIMIT ?
            """, params).fetchall()

            ar_where = ["COALESCE(status, 'active') = 'active'"]
            ar_params: List[Any] = []
            if start is not None and end is not None:
                ar_where.append("period_start < ? AND period_end > ?")
                ar_params.extend([end, start])
            ar_params.append(limit)
            archive_rows = conn.execute(f"""
                SELECT period, period_start, period_end, category, memory_type, maat_field, tags,
                       summary, source_count, priority, importance, status, updated_at
                FROM monthly_archive
                WHERE {' AND '.join(ar_where)}
                ORDER BY period_start DESC LIMIT ?
            """, ar_params).fetchall()
    except Exception as e:
        _debug(f"timeline collect db error: {e}")
        rows = []
        archive_rows = []

    for row in rows:
        entry = _timeline_entry_from_row(row)
        if entry:
            entry["tags"] = row["tags"] if "tags" in row.keys() else ""
            entry["keywords"] = row["keywords"] if "keywords" in row.keys() else ""
            entries.append(entry)

    for item in _load_keywords():
        entry = _timeline_entry_from_keyword(item)
        if not entry:
            continue
        ts = float(entry["ts"])
        if start is not None and end is not None and not (start <= ts < end):
            continue
        entry["tags"] = item.get("tags", "")
        entry["keywords"] = item.get("keywords", "")
        entries.append(entry)

    for row in archive_rows:
        center = (float(row["period_start"] or 0) + float(row["period_end"] or 0)) / 2.0
        entry = {
            "ts": center,
            "content": row["summary"],
            "category": row["category"],
            "memory_type": _normalize_memory_type(row["memory_type"], row["summary"]),
            "maat_field": _normalize_maat_field(row["maat_field"], row["summary"]),
            "priority": float(row["priority"] or 0.50),
            "importance": float(row["importance"] or 0.50),
            "source": "archive",
            "tags": row["tags"] or "",
            "keywords": row["period"] or "",
        }
        entries.append(entry)

    deduped: List[Dict[str, Any]] = []
    seen = set()
    for entry in sorted(entries, key=lambda x: x.get("ts", 0), reverse=True):
        fp = _fingerprint(entry.get("content", ""))
        if fp in seen:
            continue
        seen.add(fp)
        deduped.append(entry)
        if len(deduped) >= limit:
            break
    return deduped


def cmd_memory_timeline(cmd: str = "/maat timeline", state: dict = None, language='de') -> str:
    start, end, scope = _timeline_scope_from_cmd(cmd,language)
    limit = _timeline_limit_from_cmd(cmd)
    deduped = _collect_timeline_entries(limit=limit, start=start, end=end)

    if not deduped:
        return memory_text('Timeline leer für: {scope}',language,scope=scope)

    grouped: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
    for entry in deduped:
        dt = datetime.fromtimestamp(float(entry["ts"]))
        grouped.setdefault((dt.year, dt.month), []).append(entry)

    month_keys = sorted(grouped.keys(), reverse=True)
    if start is None:
        month_keys = month_keys[:12]

    lines = [f"MAAT Timeline ({scope})", memory_text('Quelle: bestehende `ts`/`created_at`-Zeitstempel, keine Migration nötig.',language), ""]
    for key in month_keys:
        year, month = key
        items = grouped[key]
        lines.append(f"**{_timeline_month_title(year, month,language)}**")
        shown = 0
        for entry in items:
            if shown >= 8:
                break
            dt = datetime.fromtimestamp(float(entry["ts"]))
            rel = _relative_time_label(entry["ts"], language)
            meta = _timeline_meta(entry)
            meta_part = f" [{meta}]" if meta else ""
            prio = float(entry.get("priority", 0.50) or 0.50)
            prio_part = f" p={prio:.2f}" if prio >= 0.75 else ""
            rel_part = f" · {rel}" if rel else ""
            lines.append(f"- {dt.strftime('%d.%m.')} {rel_part}{meta_part}{prio_part}: {_compress(entry.get('content', ''), 120)}")
            shown += 1
        remaining = len(items) - shown
        if remaining > 0:
            lines.append(memory_text('- ... {count} weitere Erinnerungen in diesem Monat',language,count=remaining))
        lines.append("")

    return "\n".join(lines).strip()


_MILESTONE_ACTION_MARKERS = (
    "eingebaut", "integriert", "gebaut", "entwickelt", "erstellt", "fertig",
    "abgeschlossen", "entschieden", "veröffentlicht", "veroeffentlicht",
    "publiziert", "gestartet", "begonnen", "finalisiert", "umgestellt",
    "repariert", "gefixt", "verbessert", "created", "built", "integrated",
    "finished", "published", "started", "decided", "fixed", "improved",
)

_MILESTONE_TOPIC_MARKERS = (
    "maat", "cci", "b_dynamic", "balance", "style", "timeline", "memory",
    "paper", "arxiv", "zenodo", "mftoe", "gguf", "mlx", "musicgen",
    "super memory", "structural", "selection", "kosmologie", "cosmology",
)

_MILESTONE_LEADING_CHAT_RE = re.compile(
    r"(?is)^\s*(?:kurz\s+gesagt\s*:\s*)?"
    r"(?:hallo|hey|hi|guten\s+morgen|guten\s+abend)\s+[\wäöüÄÖÜß-]+"
    r"(?:\s*[!.,:;)\]😊😄😂🚀✨^^:DxdXD-]*)?\s+"
)

_MILESTONE_SCORE_RE = re.compile(
    r"(?is)^\s*H\s*=\s*[\d.,]+\s*(?:\||,)\s*B\s*=\s*[\d.,]+.*?"
    r"(?:Stability|Stabilit(?:y|ät))\s*(?:≈|=)\s*[\d.,]+\s*"
)

_TOPIC_STOPWORDS = _stopwords() | {
    "christof", "haben", "wurde", "wird", "gemacht", "gebaut", "eingebaut",
    "entwickelt", "erstellt", "dass", "diese", "dieser", "dieses", "heute",
    "gestern", "vorgestern", "woche", "monat", "jahr", "projekt", "memory",
    "erinnerung", "save", "normal", "false", "true",
}


def _topic_terms_from_entry(entry: Dict[str, Any]) -> List[str]:
    raw = " ".join(str(entry.get(k, "") or "") for k in ("tags", "keywords", "content"))
    terms = []
    for tok in _tokens(raw):
        folded = _fold_text(tok).strip("-_")
        if len(folded) < 3 or folded in _TOPIC_STOPWORDS:
            continue
        if folded.isdigit():
            continue
        terms.append(folded)
    seen = set()
    out = []
    for term in terms:
        if term not in seen:
            seen.add(term)
            out.append(term)
    return out[:12]


def _entry_milestone_score(entry: Dict[str, Any]) -> float:
    text = _norm(_milestone_clean_content(entry.get("content", "")))
    score = float(entry.get("priority", 0.50) or 0.50) * 0.45
    score += float(entry.get("importance", 0.50) or 0.50) * 0.35
    if entry.get("memory_type") in {"project", "decision", "technical"}:
        score += 0.18
    if any(marker in text for marker in _MILESTONE_ACTION_MARKERS):
        score += 0.16
    if any(marker in text for marker in _MILESTONE_TOPIC_MARKERS):
        score += 0.12
    if _is_milestone_noise(entry):
        score -= 0.40
    return round(score, 3)


def _milestone_clean_content(content: str) -> str:
    text = html.unescape(str(content or "")).strip()
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = _MILESTONE_SCORE_RE.sub(" ", text).strip()
    text = _MILESTONE_LEADING_CHAT_RE.sub(" ", text).strip()
    text = re.sub(r"(?is)^\s*(?:meine\s+position\s+dazu\s*:|gegenperspektive\s*:)\s*", " ", text).strip()
    text = re.sub(r"\s+", " ", text).strip()
    return text or str(content or "").strip()


def _is_milestone_noise(entry: Dict[str, Any]) -> bool:
    raw = str(entry.get("content", "") or "").strip()
    clean = _milestone_clean_content(raw)
    low = _norm(clean)
    has_marker = (
        any(marker in low for marker in _MILESTONE_ACTION_MARKERS)
        or any(marker in low for marker in _MILESTONE_TOPIC_MARKERS)
    )
    if re.match(r"(?is)^\s*(?:hallo|hey|hi)\b", raw) and len(_tokens(clean)) <= 5:
        return True
    if _MILESTONE_SCORE_RE.match(raw) and not has_marker:
        return True
    if len(_tokens(clean)) <= 3 and not has_marker:
        return True
    return False


def _milestone_per_day_from_cmd(cmd: str) -> int:
    text = cmd or ""
    m = re.search(r"\b(?:day|tag|daily|pro\s+tag)\s*(?:top|limit)?\s*(\d{1,2})\b", text, re.IGNORECASE)
    if not m:
        m = re.search(r"\b(?:top|limit)\s*(\d{1,2})\s*(?:per\s+day|pro\s+tag|je\s+tag)\b", text, re.IGNORECASE)
    return max(1, min(int(m.group(1)), 10)) if m else 3


def _project_age_label(entries: List[Dict[str, Any]]) -> str:
    if not entries:
        return "-"
    oldest = min(float(e["ts"]) for e in entries if e.get("ts"))
    days = max(int((time.time() - oldest) // 86400), 0)
    years = days // 365
    months = (days % 365) // 30
    if years and months:
        return f"{years} Jahr{'e' if years != 1 else ''} und {months} Monat{'e' if months != 1 else ''}"
    if years:
        return f"{years} Jahr{'e' if years != 1 else ''}"
    if months:
        return f"{months} Monat{'e' if months != 1 else ''}"
    return f"{days} Tag{'e' if days != 1 else ''}"


def _top_topics(entries: List[Dict[str, Any]], limit: int = 8) -> List[Tuple[str, int]]:
    counts: Dict[str, int] = {}
    for entry in entries:
        for term in _topic_terms_from_entry(entry):
            counts[term] = counts.get(term, 0) + 1
    return sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:limit]


def cmd_memory_milestones(cmd: str = "/maat milestones", state: dict = None, language='de') -> str:
    start, end, scope = _timeline_scope_from_cmd(cmd,language)
    per_day = _milestone_per_day_from_cmd(cmd)
    entries = _collect_timeline_entries(limit=_timeline_limit_from_cmd(cmd), start=start, end=end)
    if not entries:
        return memory_text('Keine Meilensteine für: {scope}',language,scope=scope)

    scored = []
    for entry in entries:
        score = _entry_milestone_score(entry)
        if score >= 0.52 and not _is_milestone_noise(entry):
            scored.append((score, entry))

    if not scored:
        scored = [
            (_entry_milestone_score(e), e)
            for e in entries[:40]
            if not _is_milestone_noise(e)
        ] or [(_entry_milestone_score(e), e) for e in entries[:40]]

    by_month_day: Dict[Tuple[int, int], Dict[Tuple[int, int, int], List[Tuple[float, Dict[str, Any]]]]] = {}
    for score, entry in scored:
        dt = datetime.fromtimestamp(float(entry["ts"]))
        by_month_day.setdefault((dt.year, dt.month), {}).setdefault((dt.year, dt.month, dt.day), []).append((score, entry))

    lines = [
        memory_text('MAAT Meilensteine ({scope})',language,scope=scope),
        memory_text('Quelle: verdichtete aktive Erinnerungen. Pro Tag werden die Top {count} nach Milestone-Score gezeigt.',language,count=per_day),
        "",
    ]
    for year, month in sorted(by_month_day.keys(), reverse=True)[:18]:
        days = by_month_day[(year, month)]
        lines.append(f"**{year}-{month:02d} · {_timeline_month_title(year, month,language)}**")
        for day_key in sorted(days.keys(), reverse=True):
            day_items = sorted(days[day_key], key=lambda x: (x[0], x[1].get("ts", 0)), reverse=True)
            day_dt = datetime(*day_key)
            lines.append(f"- **{day_dt.strftime('%d.%m.')}**")
            for score, entry in day_items[:per_day]:
                meta = _timeline_meta(entry)
                meta_part = f" [{meta}]" if meta else ""
                snippet = _compress(_milestone_clean_content(entry.get("content", "")), 150)
                lines.append(f"  -{meta_part} score={score:.2f}: {snippet}")
            remaining = len(day_items) - per_day
            if remaining > 0:
                lines.append(memory_text('  - ... {count} weitere mögliche Meilensteine an diesem Tag',language,count=remaining))
        lines.append("")
    return "\n".join(lines).strip()


def cmd_memory_recent(language='de') -> str:
    try:
        with _get_conn() as conn:
            rows = conn.execute(
                """
                SELECT content, category, memory_type, maat_field, priority, status, ts
                FROM episodic
                WHERE COALESCE(status, 'active') = 'active'
                ORDER BY ts DESC LIMIT 8
                """
            ).fetchall()
    except Exception as e:
        return f"Error: {e}"
    if not rows:
        return "Episodic memory empty."
    lines = ["Recent memories:"]
    for i, r in enumerate(rows, 1):
        rel = _relative_time_label(r["ts"], language)
        ts  = datetime.fromtimestamp(r["ts"]).strftime("%d.%m %H:%M")
        when = f"{ts} · {rel}" if rel else ts
        txt = (r["content"] or "")[:80]
        mtype = _normalize_memory_type(r["memory_type"], r["content"])
        field = _normalize_maat_field(r["maat_field"], r["content"])
        field_part = f"/{field}" if field else ""
        lines.append(f"{i}. [{when}] [{r['category']}/{mtype}{field_part}/{r['status'] or _ACTIVE_STATUS}/p={float(r['priority'] or 0.50):.2f}] {txt}")
    return "\n".join(lines)






























def cmd_memory_search(cmd: str, state: dict, language='de') -> str:
    m = re.match(r"^/maat memory search (.+)$", cmd)
    if not m:
        return "Usage: /maat memory search <query>"
    query   = m.group(1).strip()
    results = recall_all(query, state)
    if not results:
        return f"No memories for: {query}"
    lines = [f"Memories for '{query}':"]
    for i, r in enumerate(results, 1):
        src = r.get("source", "?")
        mtype = _normalize_memory_type(r.get("memory_type"), r.get("content", ""))
        field = _normalize_maat_field(r.get("maat_field"), r.get("content", ""))
        rel = _relative_time_label(_memory_timestamp(r), language)
        author = _memory_author_label(r)
        txt = (r.get("content") or "")[:100]
        field_part = f"|{field}" if field else ""
        time_part = f"|{rel}" if rel else ""
        author_part = f"|{author}" if author else ""
        lines.append(f"{i}. [{src}|{mtype}{field_part}{time_part}{author_part}] {txt}")
    return "\n".join(lines)

def cmd_memory_top(cmd: str, state: dict) -> str:
    m = re.match(r"^/maat memory top\s+(\d+)$", cmd, re.IGNORECASE)
    if not m:
        return "Usage: /maat memory top <1-10>"
    state["supermem_top_k"] = max(1, min(int(m.group(1)), 10))
    return f"Max geladene Erinnerungen: {state['supermem_top_k']}"


def _browser_type_matches(entry: Dict[str, Any], memory_type: str) -> bool:
    wanted = (memory_type or "Alle").strip().lower()
    if wanted in {"", "alle", "all"}:
        return True
    found = _normalize_memory_type(entry.get("memory_type"), entry.get("content", ""))
    return found == wanted


def _browser_query_matches(entry: Dict[str, Any], query: str) -> bool:
    query = (query or "").strip()
    if not query:
        return True
    haystack = " ".join(
        str(entry.get(key, "") or "")
        for key in ("content", "keywords", "tags", "category", "memory_type", "maat_field", "period")
    ).lower()
    if query.lower() in haystack:
        return True
    terms = [tok for tok in _tokens(query) if len(tok) >= 2]
    if not terms:
        return False
    return all(term in haystack for term in terms)


def _browser_entry(source: str, content: str, ts: Any = None, **meta) -> Dict[str, Any]:
    return {
        "source": source,
        "content": content or "",
        "ts": _timestamp_value(ts) or 0.0,
        "category": meta.get("category") or _detect_category(content or ""),
        "memory_type": _normalize_memory_type(meta.get("memory_type"), content or ""),
        "maat_field": _normalize_maat_field(meta.get("maat_field"), content or ""),
        "tags": meta.get("tags") or "",
        "keywords": meta.get("keywords") or "",
        "role": meta.get("role") or "",
        "source_role": meta.get("source_role") or "",
        "author_user": meta.get("author_user") or "",
        "priority": float(meta.get("priority", 0.50) or 0.50),
        "importance": float(meta.get("importance", 0.50) or 0.50),
        "period": meta.get("period") or "",
        "source_count": int(meta.get("source_count", 0) or 0),
    }


def _collect_saves_browser_entries(source: str = "Alle",
                                   memory_type: str = "Alle",
                                   query: str = "",
                                   limit: int = 50) -> List[Dict[str, Any]]:
    source_key = (source or "Alle").strip().lower()
    limit = max(1, min(int(limit or 50), 200))
    entries: List[Dict[str, Any]] = []

    try:
        with _get_conn() as conn:
            if source_key in {"alle", "all", "episodic"}:
                rows = conn.execute("""
                    SELECT role, author_user, content, ts, keywords, category, memory_type, maat_field,
                           tags, priority, importance
                    FROM episodic
                    WHERE COALESCE(status, 'active') = 'active'
                    ORDER BY ts DESC LIMIT 500
                """).fetchall()
                for row in rows:
                    entries.append(_browser_entry(
                        "episodic", row["content"], row["ts"],
                        role=row["role"], author_user=row["author_user"],
                        keywords=row["keywords"], category=row["category"],
                        memory_type=row["memory_type"], maat_field=row["maat_field"],
                        tags=row["tags"], priority=row["priority"], importance=row["importance"],
                    ))

            if source_key in {"alle", "all", "semantic"}:
                rows = conn.execute("""
                    SELECT text, ts, category, memory_type, maat_field, tags, source_role, author_user, priority
                    FROM semantic
                    WHERE COALESCE(status, 'active') = 'active'
                    ORDER BY ts DESC LIMIT 500
                """).fetchall()
                for row in rows:
                    entries.append(_browser_entry(
                        "semantic", row["text"], row["ts"],
                        category=row["category"], memory_type=row["memory_type"],
                        source_role=row["source_role"], author_user=row["author_user"],
                        maat_field=row["maat_field"], tags=row["tags"],
                        priority=row["priority"], importance=row["priority"],
                    ))

            if source_key in {"alle", "all", "archive", "archiv"}:
                rows = conn.execute("""
                    SELECT period, period_start, period_end, category, memory_type,
                           maat_field, tags, summary, source_count, priority, importance
                    FROM monthly_archive
                    WHERE COALESCE(status, 'active') = 'active'
                    ORDER BY period_start DESC LIMIT 500
                """).fetchall()
                for row in rows:
                    center = (float(row["period_start"] or 0) + float(row["period_end"] or 0)) / 2.0
                    entries.append(_browser_entry(
                        "archive", row["summary"], center,
                        period=row["period"], category=row["category"],
                        memory_type=row["memory_type"], maat_field=row["maat_field"],
                        tags=row["tags"], source_count=row["source_count"],
                        priority=row["priority"], importance=row["importance"],
                    ))
    except Exception as e:
        _debug(f"saves browser db error: {e}")

    if source_key in {"alle", "all", "keyword"}:
        for item in _load_keywords():
            if not _status_is_active(item.get("status")):
                continue
            entries.append(_browser_entry(
                "keyword", item.get("memory", ""), _memory_timestamp(item),
                source_role=item.get("source_role", ""),
                author_user=item.get("author_user", ""),
                keywords=item.get("keywords", ""), tags=item.get("tags", ""),
                memory_type=item.get("memory_type") or item.get("type"),
                maat_field=item.get("maat_field") or item.get("field"),
                priority=item.get("priority", 0.50),
                importance=item.get("priority", 0.50),
            ))

    filtered = [
        entry for entry in entries
        if _browser_type_matches(entry, memory_type) and _browser_query_matches(entry, query)
    ]
    filtered.sort(key=lambda x: (float(x.get("ts") or 0.0), float(x.get("priority") or 0.0)), reverse=True)
    return filtered[:limit]


def build_saves_browser(query: str = "",
                        source: str = "Alle",
                        memory_type: str = "Alle",
                        limit: int = 50) -> str:
    if not _DB_PATH:
        return "Super Memory ist noch nicht initialisiert. Nach `/maat reload` erneut öffnen."

    entries = _collect_saves_browser_entries(source, memory_type, query, limit)
    query_part = f" · Suche: `{query.strip()}`" if (query or "").strip() else ""
    lines = [
        f"## MAAT Saves",
        f"{len(entries)} Treffer · Quelle: {source or 'Alle'} · Typ: {memory_type or 'Alle'}{query_part}",
        "",
    ]

    if not entries:
        lines.append("Keine passenden Erinnerungen gefunden.")
        return "\n".join(lines)

    for i, entry in enumerate(entries, 1):
        ts = float(entry.get("ts") or 0.0)
        when = "ohne Datum"
        rel = ""
        if ts > 0:
            when = datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M")
            rel = _relative_time_label(ts, "de")
        rel_part = f" · {rel}" if rel else ""
        field = entry.get("maat_field") or ""
        field_part = f"/{field}" if field else ""
        period = entry.get("period") or ""
        period_part = f" · {period}" if period else ""
        count_part = ""
        if entry.get("source") == "archive" and int(entry.get("source_count") or 0) > 0:
            count_part = f" · {int(entry.get('source_count') or 0)} Saves"
        meta = (
            f"{entry.get('source', '?')}/{entry.get('category', '')}/"
            f"{entry.get('memory_type', 'fact')}{field_part}"
        )
        author = _memory_author_label(entry)
        author_part = f" · {html.escape(author)}" if author else ""
        content = html.escape(_compress(entry.get("content", ""), 1200), quote=False)
        tags = html.escape(str(entry.get("tags") or entry.get("keywords") or ""), quote=False)
        tag_block = f"\n\nTags/Keywords: `{tags}`" if tags else ""
        lines.append(
            f"<details>\n"
            f"<summary><strong>{i}. {when}{rel_part}{period_part}</strong> "
            f"<code>{html.escape(meta)}</code>{author_part}{count_part}</summary>\n\n"
            f"<pre><code>{content}</code></pre>{tag_block}\n"
            f"</details>"
        )

    return "\n\n".join(lines)


def _cmd_memory_save(cmd: str) -> str:
    m = re.match(r"^/maat memory save (.+)$", cmd, re.IGNORECASE)
    if not m:
        return "Usage: /maat memory save <text>"
    text = m.group(1).strip()
    if not text:
        return "No text provided."
    _store_all_layers("user", text, always_keyword=False)
    return f"Saved: '{text[:60]}'"







# ============================================================
# UI
# ============================================================



# ============================================================
# Init
# ============================================================
