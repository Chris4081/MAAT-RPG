"""Mandatory in-game class cards; selection is acknowledged only after saving."""
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QToolButton, QScrollArea
from gui.desktop import label, button
from gui.hero_portrait import portrait_path
from shared.core.hero_classes import CLASSES
from gui.ui_i18n import LocalizedUI


class ClassSelection(LocalizedUI, QWidget):
    selected = Signal(str)

    def __init__(self):
        super().__init__()
        self.request_id = None
        self.choice = None
        self.submitted = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 16, 22, 16)
        heading = label('DEIN ERSTER KAMPF LIEGT HINTER DIR', 'eyebrow')
        heading.setAlignment(Qt.AlignCenter)
        layout.addWidget(heading)
        title = label('Welche Gestalt trägt dein Weg?', 'title')
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        hint = label('Wähle eine Klasse für Maatis. Sie bleibt in diesem Profil erhalten.\n'
                     'Deine Klasse öffnet ihren Talentbaum: Punkte aus Leveln und Kampfquests stärken deinen Weg.', 'muted')
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setContentsMargins(0, 8, 0, 8)
        self.grid.setSpacing(14)
        self.cards = {}
        for i, (key, (name, description)) in enumerate(CLASSES.items()):
            tile = QToolButton()
            tile.setText(name)
            tile.setToolTip(description)
            tile.setAccessibleName(name + '. ' + description)
            tile.setIcon(QIcon(str(portrait_path(key))))
            tile.setIconSize(QSize(160, 160))
            tile.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            tile.setCheckable(True)
            tile.setCursor(Qt.PointingHandCursor)
            tile.setMinimumSize(185, 208)
            tile.setStyleSheet('QToolButton {background:#10213c;color:#eee5cc;border:1px solid #345171;'
                              'border-radius:14px;padding:10px;font-size:22px;} '
                              'QToolButton:hover,QToolButton:focus {border:2px solid #ddc587;} '
                              'QToolButton:checked {background:#223b53;border:3px solid #e8c576;}')
            tile.clicked.connect(lambda checked=False, value=key: self.select(value))
            self.cards[key] = tile
            self.grid.addWidget(tile, i // 3, i % 3)
        self.columns = 3
        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll, 1)
        self.description = label('Wähle oben ein Bild aus.', 'muted')
        self.description.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.description)
        self.confirm = button('Klasse wählen', self.submit, True)
        self.confirm.setMinimumHeight(50)
        self.confirm.setEnabled(False)
        layout.addWidget(self.confirm)

    def retranslate(self):
        super().retranslate()
        for key, tile in self.cards.items():
            name, description = CLASSES[key]
            tile.setText(self.ui(name))
            tile.setToolTip(self.ui(description))
            tile.setAccessibleName(self.ui(name) + '. ' + self.ui(description))
        if self.choice and not self.submitted:
            self.select(self.choice)

    def start(self, identifier):
        self.request_id = identifier
        self.choice = None
        self.submitted = False
        for tile in self.cards.values():
            tile.setChecked(False)
            tile.setEnabled(True)
        self.description.setText(self.ui('Wähle oben ein Bild aus.'))
        self.confirm.setText(self.ui('Klasse wählen'))
        self.confirm.setEnabled(False)
        self.cards['robo'].setFocus()

    def select(self, value):
        if self.submitted:
            return
        self.choice = value
        for key, tile in self.cards.items():
            tile.setChecked(key == value)
        name, description = CLASSES[value]
        self.description.setText(self.ui(description))
        self.confirm.setText(self.ui('Als {name} weiterreisen  →', name=self.ui(name)))
        self.confirm.setEnabled(True)

    def submit(self):
        if self.choice and not self.submitted:
            self.submitted = True
            self.confirm.setEnabled(False)
            self.confirm.setText(self.ui('Klasse wird gespeichert …'))
            for tile in self.cards.values():
                tile.setEnabled(False)
            self.selected.emit(self.choice)

    def show_error(self, message):
        self.submitted = False
        for tile in self.cards.values():
            tile.setEnabled(True)
        self.description.setText(self.ui(message))
        self.confirm.setText(self.ui('Speichern erneut versuchen'))
        self.confirm.setEnabled(bool(self.choice))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        columns = 5 if self.width() >= 1200 else 3 if self.width() >= 670 else 2
        if columns != self.columns:
            self.columns = columns
            for i, tile in enumerate(self.cards.values()):
                self.grid.addWidget(tile, i // columns, i % columns)
        rows = (len(self.cards) + columns - 1) // columns
        side = max(100, min(200, (self.height()-270)//rows-54,
                            (self.width()-60-14*(columns-1))//columns-28))
        for tile in self.cards.values():
            tile.setIconSize(QSize(side, side))
            tile.setMinimumSize(160, side+54)
