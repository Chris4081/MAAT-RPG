"""Passive level-up notice with painted stars, independent of emoji fonts."""
import math
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QColor, QPainter, QPolygonF
from PySide6.QtWidgets import QFrame, QWidget, QLabel, QHBoxLayout, QVBoxLayout


class LevelStars(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 48)

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#e4c97e'))
            for x, y, radius in ((15, 29, 10), (40, 20, 17), (65, 29, 10)):
                points = []
                for step in range(10):
                    angle = -math.pi / 2 + step * math.pi / 5
                    r = radius if step % 2 == 0 else radius * .44
                    points.append(QPointF(x + math.cos(angle) * r, y + math.sin(angle) * r))
                painter.drawPolygon(QPolygonF(points))
        finally:
            painter.end()


class LevelUpNotice(QFrame):
    """One owned widget and timer; repeated level-ups replace the same notice."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('levelUpNotice')
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet('''
            QFrame#levelUpNotice { background:#142843; border:1px solid #b99a56; border-radius:9px; }
            QFrame#levelUpNotice QLabel { background:transparent; border:none; color:#eee8d3; }
            QLabel#levelUpHeading { color:#e4c97e; font-size:22px; font-weight:600; }
        ''')
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 8, 14, 8)
        row.addWidget(LevelStars(self))
        words = QVBoxLayout()
        self.heading = QLabel()
        self.heading.setObjectName('levelUpHeading')
        self.detail = QLabel()
        for label in (self.heading, self.detail):
            label.setTextFormat(Qt.PlainText)
            label.setWordWrap(True)
            words.addWidget(label)
        row.addLayout(words, 1)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.dismiss)
        self.hide()

    def present(self, event):
        en = event.get('language') == 'en'
        heading = ('Level up' if en else 'Levelaufstieg') + f" · Level {event['level']}"
        details = [str(event.get('title') or '')]
        if event.get('max_hp') is not None:
            details.append(f"Max HP: {event['max_hp']}")
        if event.get('skill'):
            details.append(('New skill: ' if en else 'Neuer Skill: ') + str(event['skill']))
        detail = ' · '.join(part for part in details if part)
        self.heading.setText(heading)
        self.detail.setText(detail)
        self.setAccessibleName(heading + '. ' + detail)
        self.show()
        self.timer.start(6500)
        return heading + '\n' + detail

    def dismiss(self):
        self.timer.stop()
        self.hide()
