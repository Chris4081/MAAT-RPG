"""One-time endgame contracts, backed by the quest plugin."""
from html import escape
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QListWidget, QTextBrowser, QPushButton
from gui.ui_i18n import LocalizedUI


class ContractBoard(LocalizedUI, QWidget):
    purchase_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.data = {}
        self.ready = False
        self.entries = {}
        layout = QVBoxLayout(self)
        self.heading = QLabel('📜  AUFTRAGSBRETT · AB LEVEL 50')
        self.heading.setStyleSheet('font-size:23px;color:#f0d59d;font-weight:700;')
        self.heading.setWordWrap(True)
        layout.addWidget(self.heading)
        note = QLabel('25 einmalige Aufträge für Terra. Fortschritt zählt ab dem Kauf; angenommene Aufträge bleiben ohne Zeitlimit im Questlog.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.filter = QComboBox()
        for name, price in [('Alle Aufträge', 0), ('Expeditionen · 500 Gold', 500), ('Prüfungen · 1.000 Gold', 1000), ('Große Aufträge · 2.000 Gold', 2000)]:
            self.filter.addItem(name, price)
        self.filter.currentIndexChanged.connect(self.rebuild)
        layout.addWidget(self.filter)
        self.list = QListWidget()
        self.list.setMinimumHeight(190)
        self.list.setStyleSheet('QListWidget {background:#0d2039;border:1px solid #49617e;border-radius:8px;font-size:17px;} QListWidget::item {padding:10px;} QListWidget::item:selected {background:#304d6c;color:#ffe1a5;}')
        self.list.currentItemChanged.connect(self.show_details)
        layout.addWidget(self.list)
        self.details = QTextBrowser()
        self.details.setMinimumHeight(200)
        self.details.setStyleSheet('background:#101f36;color:#e0e9f1;border:1px solid #806d49;border-radius:8px;padding:12px;font-size:17px;')
        layout.addWidget(self.details)
        self.buy = QPushButton('Auftrag wählen')
        self.buy.setMinimumHeight(48)
        self.buy.setStyleSheet('QPushButton {background:#be9b55;color:#101c2d;border-radius:8px;font-size:18px;font-weight:700;} QPushButton:disabled {background:#24334a;color:#93a5ba;}')
        self.buy.clicked.connect(self.purchase)
        layout.addWidget(self.buy)
        self.titles = QLabel()
        self.titles.setWordWrap(True)
        self.titles.setStyleSheet('color:#edcd87;font-size:15px;')
        layout.addWidget(self.titles)
        self.rebuild()

    def update_data(self, data, ready):
        entries = {q['id']: dict(q, **q.get('translations', {}).get(self.language, {})) for q in data.get('contracts', [])}
        changed = entries != self.entries or data.get('earned_titles', []) != self.data.get('earned_titles', [])
        self.data, self.ready = dict(data), ready
        self.entries = entries
        if changed:
            self.rebuild()
        else:
            self.show_details()

    def retranslate(self):
        super().retranslate()
        self.update_data(self.data,self.ready)
        self.rebuild()

    def price_text(self,price):
        text=f'{price:,}'
        return text if self.language == 'en' else text.replace(',','.')

    def rebuild(self):
        current = self.list.currentItem()
        selected = current.data(Qt.UserRole) if current else None
        del current  # Keep only the ID across deletion of Qt-owned rows.
        self.list.blockSignals(True)
        self.list.clear()
        for key, q in self.entries.items():
            if self.filter.currentData() not in (0, q['purchase_price']):
                continue
            status = {'active': self.ui('Aktiv'), 'completed': self.ui('✓ Erledigt')}.get(q['status'], self.ui('{price} Gold',price=self.price_text(q['purchase_price'])))
            # Let Qt construct and own native items; avoid Python item-wrapper
            # destruction in QListWidget.clear() (macOS crash reports).
            self.list.addItem(f'{q["name"]}  ·  {status}')
            item = self.list.item(self.list.count() - 1)
            item.setData(Qt.UserRole, key)
            if key == selected:
                self.list.setCurrentItem(item)
        if not self.list.currentItem() and self.list.count():
            self.list.setCurrentRow(0)
        self.list.blockSignals(False)
        titles = self.data.get('earned_titles', [])
        if self.language == 'en':
            from apps.maat_rpg.plugins.quests.english_content import TITLES
            titles = [TITLES.get(title,title) for title in titles]
        self.titles.setText(self.ui('✦ Sammeltitel: {titles}',titles=' · '.join(titles) if titles else self.ui('Die fünf großen Aufträge verleihen besondere Titel.')))
        self.show_details()

    def show_details(self, *_):
        item = self.list.currentItem()
        q = self.entries.get(item.data(Qt.UserRole)) if item else None
        self.buy.setEnabled(False)
        if not q:
            self.details.setPlainText(self.ui('Aufträge werden mit deinem Profil geladen …'))
            self.buy.setText(self.ui('Auftrag wählen'))
            return
        desc = escape(q['desc']).replace('\n', '<br><br>')
        if q.get('path_bonus'):
            desc += '<br><br>' + escape(self.ui(q['path_bonus']))
        progress = '<p>'+escape(self.ui('Fortschritt: {progress} / {target}',progress=q.get('progress',0),target=q['target']))+'</p>' if q['status'] != 'locked' else ''
        self.details.setHtml(f'<h3 style="color:#f0d59d">{escape(q["name"])}</h3><p>{desc}</p>{progress}')
        if q['status'] == 'completed':
            label = '✓ Abgeschlossen · Belohnung erhalten'
        elif q['status'] == 'active':
            label = 'Bereits gekauft · Im Questlog aktiv'
        elif self.data.get('level', 1) < 50:
            label = 'Freigeschaltet ab Level 50'
        elif self.data.get('gold', 0) < q['purchase_price']:
            label = self.ui('Es fehlen {missing} Gold',missing=q['purchase_price'] - self.data.get('gold',0))
        else:
            label = self.ui('Auftrag kaufen · {price} Gold',price=self.price_text(q['purchase_price']))
            self.buy.setEnabled(self.ready)
        self.buy.setText(self.ui(label))

    def purchase(self):
        if not self.buy.isEnabled():
            return
        key = self.list.currentItem().data(Qt.UserRole)
        self.ready = False
        self.buy.setEnabled(False)
        self.purchase_requested.emit(f'/contracts buy {key}')
