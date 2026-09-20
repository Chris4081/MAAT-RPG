"""Post-intro perspective selection using the two local character portraits."""
from pathlib import Path
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QToolButton
from gui.desktop import label
from gui.hero_portrait import portrait_path


class PerspectiveScreen(QWidget):
    selected = Signal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.addStretch()
        heading = label('WÄHLE DEINE PERSPEKTIVE', 'eyebrow')
        heading.setAlignment(Qt.AlignCenter)
        layout.addWidget(heading)
        title = label('Zwei Perspektiven. Eine Welt.', 'title')
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        cards = QHBoxLayout()
        cards.setSpacing(24)
        self.cards = {}
        for mode, filename, text in [
            ('adventure', 'maatis-human.png', 'MAATIS\nDer klassische Modus\nDu reist durch Terra und sprichst mit der MAAT-KI.'),
            ('companion', 'ai-keeper.png', 'ICH BIN DIE KI\nDer Begleitermodus\nMaatis fragt dich. Du antwortest als seine KI.'),
        ]:
            card = QToolButton()
            card.setText(text)
            card.setIcon(QIcon(str(portrait_path('normal') if mode == 'adventure' else Path(__file__).parent/'assets'/filename)))
            card.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            card.setCursor(Qt.PointingHandCursor)
            card.setMinimumWidth(300)
            card.setIconSize(QSize(300,300))
            card.setMinimumHeight(425)
            card.setStyleSheet('QToolButton {background:#10213c; color:#eee5cc; border:1px solid #345171; border-radius:16px; padding:18px; font-size:17px;} QToolButton:hover, QToolButton:focus {border:2px solid #ddc587; background:#172d4c;}')
            card.clicked.connect(lambda checked=False, value=mode:self.selected.emit(value))
            cards.addWidget(card, 1)
            self.cards[mode] = card
        layout.addLayout(cards)
        hint = label('Beide Modi bleiben erhalten. Wähle Maatis oder seine Begleiter-KI.', 'muted')
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        layout.addStretch()

    def set_hero_class(self, value):
        self.cards['adventure'].setIcon(QIcon(str(portrait_path(value))))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        side = max(140, min(340, (self.width()-140)//2, self.height()-275))
        for card in self.cards.values():
            card.setIconSize(QSize(side, side))
            card.setMinimumHeight(side + 125)
