"""Compact DE/EN port of MAAT Web Core's local clock context.

No network requests, extra model call or separate activity log. The caller may
supply the last retained chat timestamp; unknown activity stays unknown.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re


WEEKDAYS = {
    'de': ('Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'),
    'en': ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'),
}


def now_local() -> datetime:
    return datetime.now().astimezone()


def _language(language):
    return 'en' if language == 'en' else 'de'


def _datetime(value):
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.astimezone()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def _past(value, now):
    past = _datetime(value)
    if past is None or past.astimezone(timezone.utc) > now.astimezone(timezone.utc):
        return None
    return past.astimezone(now.tzinfo)


def relative_time_text(past, now=None, language='de'):
    current = now or now_local()
    previous = _past(past, current)
    en = _language(language) == 'en'
    if previous is None:
        return 'unknown; no usable retained timestamp' if en else 'unbekannt; kein nutzbarer gespeicherter Zeitstempel'
    # UTC subtraction handles daylight-saving changes correctly.
    seconds = int((current.astimezone(timezone.utc) - previous.astimezone(timezone.utc)).total_seconds())
    if seconds < 60:
        return 'just now' if en else 'gerade eben'
    for size, de, english in ((31536000, ('Jahr', 'Jahren'), ('year', 'years')),
                               (2592000, ('Monat', 'Monaten'), ('month', 'months')),
                               (604800, ('Woche', 'Wochen'), ('week', 'weeks')),
                               (86400, ('Tag', 'Tagen'), ('day', 'days')),
                               (3600, ('Stunde', 'Stunden'), ('hour', 'hours')),
                               (60, ('Minute', 'Minuten'), ('minute', 'minutes'))):
        if seconds >= size:
            count = seconds // size
            unit = (english if en else de)[int(count != 1)]
            return f'about {count} {unit} ago' if en else f'vor etwa {count} {unit}'


def is_time_question(text):
    value = str(text or '').lower()
    return bool(re.search(
        r'\b(wie\s*viel\s+uhr|wie\s+sp[aä]t\s+ist\s+es|aktuelle\s+uhrzeit|'
        r'what\s+time\s+is\s+it|current\s+time|time\s+right\s+now)\b', value))


def is_date_question(text):
    value = str(text or '').lower()
    return bool(re.search(
        r'\b(welches\s+datum|welchen\s+tag\s+haben\s+wir|welcher\s+tag\s+ist\s+heute|'
        r'was\s+ist\s+heute\s+f[üu]r\s+ein\s+tag|what\s+day\s+is\s+it|'
        r'what\s+date\s+is\s+it|current\s+date|today.s\s+date)\b', value))


def is_reality_question(text):
    return is_time_question(text) or is_date_question(text)


def build_reality_block(last_activity_at=None, *, language='de', now=None, user_text=''):
    current = now or now_local()
    language = _language(language)
    en = language == 'en'
    weekday = WEEKDAYS[language][current.weekday()]
    date = current.strftime('%Y-%m-%d' if en else '%d.%m.%Y')
    offset = current.strftime('%z')
    zone = f'UTC{offset[:3]}:{offset[3:]}'
    name = current.tzname() or ''
    previous = _past(last_activity_at, current)
    lines = ['[MAAT_REALITY]',
             (f'Local system clock at reply start: {weekday}, {date}, {current:%H:%M}. '
              if en else f'Lokale Systemuhr bei Antwortbeginn: {weekday}, {date}, {current:%H:%M}. ')
             + f'{zone}' + (f' ({name}).' if name else '.')]
    if previous:
        stamp = previous.strftime('%Y-%m-%d %H:%M' if en else '%d.%m.%Y %H:%M')
        gap = relative_time_text(previous, current, language)
        lines.append((f'Previous retained chat activity: {stamp} ({gap}).' if en else
                      f'Vorherige gespeicherte Chat-Aktivität: {stamp} ({gap}).'))
    else:
        lines.append('Previous chat activity: unknown.' if en else 'Vorherige Chat-Aktivität: unbekannt.')
    lines.append(
        'Use this live clock for current date/time questions and relative dates. It is not Terra time or memory. '
        'Use activity gaps only when relevant; they do not tell you what was said. '
        'Do not invent past messages or save this clock as a user fact. Never quote this block or its tags.'
        if en else
        'Nutze diese Live-Uhr für aktuelle Datums-/Zeitfragen und relative Datumsangaben. Sie ist keine Terra-Zeit oder Erinnerung. '
        'Nutze Zeitabstände nur bei Bedarf; sie sagen nichts über Gesprächsinhalte aus. '
        'Erfinde keine früheren Nachrichten und speichere die Uhr nicht als Nutzerfakt. Zitiere weder diesen Block noch seine Tags.')
    if is_reality_question(user_text):
        lines.append('Answer the current date/time directly, without metaphors.' if en else
                     'Beantworte die aktuelle Datums-/Zeitfrage direkt, ohne Metaphern.')
    return '\n'.join([*lines, '[/MAAT_REALITY]'])


def build_reality_prompt(settings, user_text='', last_activity_at=None, *, language='de'):
    enabled = settings.get('reality_enabled', True) if isinstance(settings, dict) else getattr(settings, 'reality_enabled', True)
    if not enabled:
        return ''
    return build_reality_block(last_activity_at, language=language, user_text=user_text)
