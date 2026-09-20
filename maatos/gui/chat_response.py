"""Revise one streamed reply in place; never append a second copy."""
from PySide6.QtGui import QTextCursor, QTextBlockFormat


class ChatResponse:
    def __init__(self, views, formatting=None):
        self.views = views
        self.formatting = formatting or (lambda: False)
        self.formatted = False
        self.identifier = None
        self.ranges = []

    @staticmethod
    def at_end(view):
        cursor = QTextCursor(view.document())
        cursor.movePosition(QTextCursor.End)
        cursor.setKeepPositionOnInsert(True)
        return cursor

    def handle(self, event):
        action, identifier = event.get('action'), event.get('id')
        if action == 'begin':
            from gui.reply_formatting import trim_transcript
            self.formatted = bool(self.formatting())
            for view in self.views:
                trim_transcript(view)
            self.identifier = identifier
            self.ranges = [dict(start=self.at_end(view), end=None, raw='', displayed='') for view in self.views]
            return
        if identifier != self.identifier:
            return
        if action == 'end':
            for view, span in zip(self.views, self.ranges):
                span['end'] = self.at_end(view)
                span['raw'] = span['displayed'] = self.selected(span)
                self.render(view, span)
        elif action == 'replace':
            original, revised = event.get('original', ''), event.get('text', '')
            if not original or original == revised:
                return
            for view, span in zip(self.views, self.ranges):
                if span['end'] is None or self.selected(span) != span['displayed']:
                    continue
                # The range includes stream decoration (blank lines), but no
                # later XP/quest output. Cleared/truncated documents are ignored.
                before, match, after = span['raw'].partition(original)
                if match:
                    span['raw'] = before + revised + after
                    self.render(view, span, replace=True)
            self.identifier = None
            self.ranges = []

    @staticmethod
    def cursor(span):
        cursor = QTextCursor(span['start'].document())
        cursor.setPosition(span['start'].position())
        cursor.setPosition(span['end'].position(), QTextCursor.KeepAnchor)
        return cursor

    @classmethod
    def selected(cls, span):
        return cls.cursor(span).selectedText().replace('\u2029','\n').replace('\u2028','\n')

    def render(self, view, span, replace=False):
        from gui.reply_formatting import has_formatting, formatted_fragment, reply_text_format
        raw = span['raw']
        rich = self.formatted and has_formatting(raw)
        if not rich and not replace:
            return
        if self.selected(span) != span['displayed']:
            return  # Cleared/truncated/changed documents must not replay old text.
        cursor = self.cursor(span)
        cursor.beginEditBlock()
        if rich:
            # Preserve the stream's leading/trailing blank lines outside Markdown.
            body = raw.strip('\n')
            leading = len(raw)-len(raw.lstrip('\n'))
            trailing = len(raw)-len(raw.rstrip('\n'))
            fragment = formatted_fragment(body, view.document().defaultFont())
            cursor.removeSelectedText()
            cursor.setCharFormat(reply_text_format())
            cursor.insertText('\n'*leading)
            cursor.insertFragment(fragment)
            cursor.setCharFormat(reply_text_format())
            cursor.insertText('\n'*max(1,trailing))
            cursor.setBlockFormat(QTextBlockFormat())
        else:
            cursor.insertText(raw,reply_text_format())
        end = cursor.position()
        cursor.endEditBlock()
        span['end'].setPosition(end)
        span['displayed'] = self.selected(span)
        view.ensureCursorVisible()
