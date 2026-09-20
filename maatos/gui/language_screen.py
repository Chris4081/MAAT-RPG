"""Application language selection, before the title screen and its music."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from gui.desktop import label, button
from gui.hero_portrait import HeroPortrait


class LanguageScreen(QWidget):
    selected = Signal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        heading = label('MAAT RPG · WILLKOMMEN / WELCOME', 'eyebrow')
        heading.setAlignment(Qt.AlignCenter)
        layout.addWidget(heading)
        layout.addStretch()
        self.artwork = HeroPortrait(160)
        layout.addWidget(self.artwork, 0, Qt.AlignHCenter)
        title = label('Sprache wählen / Choose your language', 'title')
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)
        layout.addWidget(title)
        row = QHBoxLayout()
        row.setSpacing(20)
        self.buttons = {}
        for language, caption in (('de', 'Deutsch'), ('en', 'English')):
            choice = button(caption, lambda checked=False, code=language: self.selected.emit(code), True)
            choice.setMinimumHeight(86)
            choice.setStyleSheet('QPushButton {font-size:28px;background:#102743;color:#eee5cc;border:1px solid #8a784b;border-radius:14px;padding:20px;} QPushButton:hover,QPushButton:focus {background:#1b3c5d;border:2px solid #edce7e;}')
            row.addWidget(choice, 1)
            self.buttons[language] = choice
        layout.addLayout(row)
        hint = label('Deine Auswahl gilt für das gesamte Spiel. Du kannst sie später in den Einstellungen ändern.\nYour choice applies to the whole game. You can change it later in Settings.', 'muted')
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch()
        self.back = button('← Zurück / Back', lambda: self.cancelled.emit())
        self.back.hide()
        layout.addWidget(self.back)

    cancelled = Signal()

    def start(self, language='de', allow_cancel=False):
        self.back.setVisible(allow_cancel)
        for choice in self.buttons.values():
            choice.setEnabled(True)
        self.buttons.get(language, self.buttons['de']).setFocus()
