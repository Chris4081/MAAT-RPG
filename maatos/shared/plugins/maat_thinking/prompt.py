"""MAAT quality instructions adapted from the user's level-based template.

Levels are prompt strength, not measured quality or a native reasoning budget.
The RPG uses the silent branch only: 100 when enabled, 0 when disabled.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from shared.core.rpg_i18n import get_language


def normalize_level(value: object) -> int:
    if isinstance(value, str):
        value = value.strip().lower().replace('maat', '').replace('%', '')
        if value in {'off', 'aus', 'none', 'no', 'false'}:
            return 0
    try:
        level = int(float(value))
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, min(100, level))


def _target_for_level(level: int) -> float:
    return round(6.8 + 2.7 * level / 100, 1) if level > 0 else 0.0


def _repairs_for_level(level: int) -> int:
    return 0 if level <= 0 else 1 if level < 40 else 2 if level < 80 else 3


def _depth_for_level(level: int) -> str:
    return 'off' if level <= 0 else 'light' if level < 35 else 'balanced' if level < 75 else 'deep'


def _language(language: str | None) -> str:
    return language if language in ('de', 'en') else get_language(('de', 'en'))


def level_status(value: object, language: str | None = None) -> dict[str, object]:
    level = normalize_level(value)
    target, repairs, depth = _target_for_level(level), _repairs_for_level(level), _depth_for_level(level)
    if _language(language) == 'en':
        hint = (f'MAAT{level} · Internal quality target {target:.1f}/10 · Up to {repairs} revisions'
                if level else 'MAAT Thinking is off.')
    else:
        hint = (f'MAAT{level} · Internes Qualitätsziel {target:.1f}/10 · Bis zu {repairs} Überarbeitungen'
                if level else 'MAAT Thinking ist aus.')
    return dict(level=level, label=f'MAAT{level}', target=target, repairs=repairs,
                depth=depth, enabled=level > 0, hint=hint)


@lru_cache(maxsize=2)
def _template(language: str) -> str:
    return (Path(__file__).with_name('prompts') / f'{language}.txt').read_text(encoding='utf-8').strip()


def build_prompt_block(value: object, language: str | None = None) -> str:
    language = _language(language)
    status = level_status(value, language)
    if not status['enabled']:
        return ''
    depth_rules = {
        'de': {
            'light': 'Nur grobe Schwächen reparieren; keine unnötige Länge erzeugen.',
            'balanced': 'Struktur, passenden Stil und konkrete Nützlichkeit verbessern.',
            'deep': 'Zusätzlich Quellenlage, Gegenbeispiele, Randfälle, Format und Nutzbarkeit streng prüfen.',
        },
        'en': {
            'light': 'Repair only major weaknesses; do not add unnecessary length.',
            'balanced': 'Improve structure, appropriate style and practical usefulness.',
            'deep': 'Also scrutinize available evidence, counterexamples, edge cases, format and usability.',
        },
    }
    return _template(language).format(**status, depth_rule=depth_rules[language][status['depth']])
