"""Non-blocking presentation stream; decisions wait until text is visible."""
from PySide6.QtCore import QObject, QTimer, Signal


class TextStream(QObject):
    chunk = Signal(str)
    drained = Signal()

    def __init__(self, parent=None, interval=12):
        super().__init__(parent)
        self.pending = ''
        self._marks = []
        self.timer = QTimer(self)
        self.timer.setInterval(interval)
        self.timer.timeout.connect(self.advance)

    @property
    def running(self):
        return bool(self.pending)

    def append(self, text):
        self.pending += text
        if self.pending and not self.timer.isActive():
            self.timer.start()

    def mark(self, callback):
        """Run at this exact presentation boundary, before subsequently queued text."""
        if self.pending:
            self._marks.append((len(self.pending), callback))
        else:
            callback()

    def _emit_prefix(self, size):
        if self._marks:
            size = min(size, self._marks[0][0])
        text, self.pending = self.pending[:size], self.pending[size:]
        due = [callback for offset, callback in self._marks if offset == size]
        self._marks = [(offset-size, callback) for offset, callback in self._marks if offset > size]
        self.chunk.emit(text)
        for callback in due:
            callback()

    def advance(self):
        if not self.pending:
            self.timer.stop()
            return
        # Catch up gently for long tables, keeping ordinary narrative characterwise.
        size = 1 if len(self.pending) < 1000 else 3
        self._emit_prefix(size)
        if not self.pending:
            self.timer.stop()
            self.drained.emit()

    def finish(self):
        self.timer.stop()
        while self.pending:
            self._emit_prefix(len(self.pending))
        self.drained.emit()

    def clear(self):
        self.timer.stop()
        self.pending = ''
        self._marks.clear()
