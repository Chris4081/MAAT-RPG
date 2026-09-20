"""Conservative, bounded detection of sustained exact loops in a text stream.

This is not a quality score or a word/token quota. Eight contiguous copies of
a short motif are required; normal repeated words, Markdown and numbers pass.
Code, quoted blocks and explicit requests to repeat literal text are exempt.
"""
import math
import re
import unicodedata
from .chat_turn import ChatCancelled


class RepetitionStopped(ChatCancelled):
    def notice(self, language='de'):
        return ('⏹ Repetition detected · Reply stopped. This message earns no progress and is not saved as a memory.'
                if language == 'en' else
                '⏹ Wiederholung erkannt · Antwort gestoppt. Diese Nachricht zählt nicht zum Fortschritt und wird nicht als Erinnerung gespeichert.')


_LITERAL_REQUEST = re.compile(
    r'\b(?:repeat|print|write|output|return|show|wiederhole|schreibe|gib|zeige|drucke)\b'
    r'.{0,120}\b(?:repeat\w*|times|copies|mal|wiederhol\w*)\b', re.I | re.S)
_SMILEY = re.compile(r'[:;=8][-^\']?[)(DP/\\]|\^\^|xD', re.I)


class RepetitionGuard:
    MAX_PERIOD = 160
    WINDOW = MAX_PERIOD * 8

    def __init__(self, query=''):
        self.enabled = not bool(_LITERAL_REQUEST.search(str(query)))
        self.window = ''
        self.line = ''
        self.fence = None
        self.inline = False

    def feed(self, chunk):
        """Return the prefix before detection, and whether generation must stop."""
        if not self.enabled:
            return chunk, False
        for index, char in enumerate(chunk):
            self.line = (self.line + char)[-self.WINDOW:]
            stripped = self.line.lstrip()
            if stripped in ('```', '~~~'):
                self.fence = None if self.fence == stripped else stripped
                self.inline = False
            elif char == '`' and not self.fence:
                self.inline = not self.inline
            skip = self.fence or self.inline or stripped.startswith(('>', '```', '~~~')) or char == '`'
            if char == '\n':
                self.line = ''
                self.inline = False
            if skip:
                self.window = ''
                continue
            normalized = ' ' if char.isspace() else char
            if normalized == ' ' and self.window.endswith(' '):
                continue
            self.window = (self.window + normalized)[-self.WINDOW:]
            if len(self.window) < 40:
                continue
            for width in range(1, min(self.MAX_PERIOD, len(self.window) // 8) + 1):
                unit = self.window[-width:]
                if not self.window.endswith(unit * 8):
                    continue
                words = any(c.isalpha() for c in unit)
                symbols = bool(_SMILEY.search(unit)) or any(unicodedata.category(c) in ('So', 'Sk') for c in unit)
                if not (words or symbols):
                    continue  # Whitespace, punctuation, table rules, numeric data.
                copies = max(8, math.ceil((96 if words and not symbols else 40) / width))
                if self.window.endswith(unit * copies):
                    return chunk[:index], True
        return chunk, False


def guard_chunks(source, *, query='', turn=None):
    guard = RepetitionGuard(query)
    try:
        for chunk in source:
            if not chunk:
                continue
            text, stopped = guard.feed(str(chunk))
            if text:
                yield text
            if stopped:
                if turn:
                    turn.cancel()
                raise RepetitionStopped()
    finally:
        close = getattr(source, 'close', None)
        if close:
            close()
