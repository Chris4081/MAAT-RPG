"""Profile-specific, optional ZIM selection; archive I/O stays in the RPG worker."""
from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QFileDialog, QTextBrowser


class WikiSettings(QWidget):
    test_requested = Signal(str)

    def __init__(self, load, save):
        super().__init__()
        self.load, self.save = load, save
        layout = QVBoxLayout(self)
        title = QLabel('Offline-Wikipedia · optional')
        title.setStyleSheet('font-size:24px;color:#dec68b;font-weight:600;')
        layout.addWidget(title)
        info = QLabel('Wähle eine lokale Wikipedia-ZIM. Die Datei wird am gewählten Ort gelesen; es gibt keine Online-Abfragen. Ohne Datei bleibt die Suche inaktiv.')
        info.setWordWrap(True);layout.addWidget(info)
        languages=QLabel('Die Suche erkennt deutsche und englische Fragen. Die Artikelsprache richtet sich nach deiner ZIM; für englische Artikeltitel empfiehlt sich eine englische Wikipedia-ZIM.')
        languages.setWordWrap(True);layout.addWidget(languages)
        self.rights_notice = QLabel()
        self.rights_notice.setObjectName('offlineWikiRightsNotice')
        self.rights_notice.setWordWrap(True)
        layout.addWidget(self.rights_notice)
        row = QHBoxLayout()
        self.path = QLineEdit();self.path.setReadOnly(True);self.path.setPlaceholderText('Keine ZIM-Datei gewählt')
        choose = QPushButton('ZIM-Datei wählen …');choose.clicked.connect(self.choose)
        clear = QPushButton('Entfernen');clear.clicked.connect(lambda:self.select_path(''))
        row.addWidget(self.path,1);row.addWidget(choose);row.addWidget(clear);layout.addLayout(row)
        self.auto = QCheckBox('Passende Begriffe automatisch in der Offline-Wikipedia nachschlagen')
        self.auto.toggled.connect(lambda value:self.save({'offline_wiki_auto':value}))
        layout.addWidget(self.auto)
        hint = QLabel('Wiki-Wissen ist getrennt vom Spielkontext. Llama: ein Artikel mit maximal 400 Zeichen. Andere Modelle: bei Vergleichen bis zu zwei Artikel mit zusammen maximal 1.000 Zeichen. Gespräch und Erinnerungen bleiben erhalten.')
        hint.setWordWrap(True);layout.addWidget(hint)
        row = QHBoxLayout()
        self.term = QLineEdit();self.term.setPlaceholderText('Testbegriff, z. B. Pyramide')
        self.test = QPushButton('Offline-Suche testen');self.test.clicked.connect(self.run_test)
        row.addWidget(self.term,1);row.addWidget(self.test);layout.addLayout(row)
        self.result = QTextBrowser();self.result.setMaximumHeight(170);self.result.setOpenExternalLinks(False)
        layout.addWidget(self.result)
        self.refresh()

    def ui(self, text):
        from gui.ui_i18n import tr
        return tr(text, self.load().get('language', 'de'))

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        config = self.load()
        self.rights_notice.setText(self.ui('MAAT RPG liefert keine ZIM-Dateien oder Wikipedia-Inhalte mit. Für dein selbst gewähltes Archiv gelten dessen Quellen- und Lizenzangaben. Wenn du Artikeltexte oder daraus bearbeitete Texte weitergibst, beachte die jeweilige Lizenz, Quellenangabe und gegebenenfalls Weitergabe unter gleichen Bedingungen.'))
        self.path.setText(config.get('offline_wiki_zim_path', ''))
        self.auto.blockSignals(True);self.auto.setChecked(config.get('offline_wiki_auto', True));self.auto.blockSignals(False)
        self.result.setPlainText(self.ui('Keine ZIM ausgewählt.' if not self.path.text() else 'Datei gespeichert. Mit einem Testbegriff kannst du sie prüfen.'))

    def choose(self):
        path, _ = QFileDialog.getOpenFileName(self, self.ui('Lokale Wikipedia-ZIM auswählen'), self.path.text(), 'ZIM-Archive (*.zim)')
        if path:
            self.select_path(path)

    def select_path(self, path):
        if path and (Path(path).suffix.lower() != '.zim' or not Path(path).is_file()):
            self.result.setPlainText(self.ui('Bitte eine vorhandene .zim-Datei wählen.'))
            return
        self.save({'offline_wiki_zim_path':path})
        self.refresh()

    def run_test(self):
        if not self.term.text().strip():
            self.result.setPlainText(self.ui('Bitte einen Suchbegriff eingeben.'))
            return
        self.test_requested.emit(self.term.text().strip())
