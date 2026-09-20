"""In-game navigation and a quiet, token-independent unread chat indicator."""
import math
from PySide6.QtCore import QObject, Qt, QTimer, QElapsedTimer, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QTextCursor
from PySide6.QtWidgets import QPushButton


class ChatNavigationButton(QPushButton):
    def __init__(self, text, callback):
        super().__init__(text)
        self.clicked.connect(callback)
        self.setCursor(Qt.PointingHandCursor)
        self.unread = False
        self.pulse_clock = QElapsedTimer()
        self.pulse_timer = QTimer(self)
        self.pulse_timer.setInterval(50)
        self.pulse_timer.timeout.connect(self.update)
        self._describe()

    def _describe(self):
        description = ('Neue Chatnachrichten oder Einträge im Verlauf · Zum Lesen öffnen'
                       if self.unread else 'Mit MAAT-KI schreiben und den Spielverlauf lesen')
        self.setToolTip(description)
        self.setAccessibleDescription(description)

    def set_unread(self, value):
        value = bool(value)
        if self.unread == value:
            return  # A streamed token must not restart the pulse.
        self.unread = value
        self._describe()
        if value:
            self.pulse_clock.start()
            if self.isVisible(): self.pulse_timer.start()
        else:
            self.pulse_timer.stop()
            self.pulse_clock.invalidate()
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        if self.unread: self.pulse_timer.start()

    def hideEvent(self, event):
        self.pulse_timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.unread:
            return
        seconds = self.pulse_clock.elapsed()/1000 if self.pulse_clock.isValid() else 0
        pulse = .5 + .5*math.sin(seconds*math.tau/2.8)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(2,2,-2,-2)
        # Painted in the widget: no native graphics effects or layout changes.
        painter.setPen(QPen(QColor(242,201,104,round(145+95*pulse)),1.5))
        painter.setBrush(QColor(242,201,104,round(8+12*pulse)))
        painter.drawRoundedRect(rect,6,6)
        center = QPointF(self.width()-13,self.height()/2)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(242,201,104,round(25+35*pulse)))
        painter.drawEllipse(center,7,7)
        painter.setBrush(QColor('#f2c968'))
        painter.drawEllipse(center,3.5,3.5)
        painter.end()


class ChatActivity(QObject):
    """Observe actual transcript additions, including plugin logs and rewards.

The bounded transcript snapshot distinguishes formatting changes from new text.
There is one unread flag, not a message counter that would count stream chunks.
"""
    def __init__(self, view, button, is_open, enabled):
        super().__init__(view)
        self.view, self.button = view, button
        self.is_open, self.enabled = is_open, enabled
        self.previous = view.toPlainText()
        view.document().contentsChange.connect(self.changed)

    def changed(self, position, removed, added):
        current, previous = self.view.toPlainText(), self.previous
        self.previous = current
        if not current.strip():
            self.button.set_unread(False)
            return
        if current == previous or added <= 0 or not self.enabled():
            return
        cursor = QTextCursor(self.view.document())
        cursor.setPosition(min(position,self.view.document().characterCount()-1))
        cursor.setPosition(min(position+added,self.view.document().characterCount()-1),QTextCursor.KeepAnchor)
        if not cursor.selectedText().strip():
            return
        self.button.set_unread(not self.is_open())

    def acknowledge_if_open(self, *_):
        if self.is_open(): self.button.set_unread(False)

    def reset(self):
        self.previous = self.view.toPlainText()
        self.button.set_unread(False)
