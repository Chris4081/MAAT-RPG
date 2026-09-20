"""Profile-scoped chat archive and Super Memory saves."""
from datetime import date
from html import escape
import sqlite3
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                              QListWidget, QListWidgetItem, QTextBrowser, QPushButton,
                              QSplitter, QMessageBox, QTabWidget)
from shared.core.chat_history import ChatHistory, UNLOCK_MESSAGES, PAGE_SIZE
from gui.ui_i18n import LocalizedUI

MONTHS = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli',
          'August', 'September', 'Oktober', 'November', 'Dezember']


class Memories(LocalizedUI, QWidget):
    def __init__(self):
        super().__init__()
        self.store = None
        self.count = 0
        self.page = 0
        self.day_rows = []
        self.setObjectName('memories')
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet('''
            QWidget {background:#07172e;color:#b9cbde;}
            QWidget#memories {background:#07172e;}
            QLabel {background:transparent;color:#b9cbde;font-size:16px;}
            QComboBox,QListWidget,QTextBrowser,QLineEdit,QPlainTextEdit,QSpinBox,QDoubleSpinBox {background:#0c203a;color:#eee6d5;
                border:1px solid #294868;border-radius:9px;padding:9px;font-size:17px;}
            QListWidget::item {padding:12px;border-bottom:1px solid #1d3652;}
            QListWidget::item:selected {background:#254968;color:#ffe1a0;}
            QPushButton {padding:9px 14px;background:#163451;color:#e6ddc9;
                border:1px solid #365678;border-radius:7px;font-size:15px;}
            QPushButton:hover {background:#254968;}
            QPushButton:disabled {color:#607286;border-color:#20374d;}
            QPushButton#deleteHistory {background:#352339;color:#efb6b4;}
            QTabWidget::pane {border:1px solid #294868;border-radius:8px;background:#07172e;padding:10px;}
            QTabBar::tab {background:#102b48;color:#b9cbde;padding:11px 18px;border:1px solid #294868;border-bottom:none;}
            QTabBar::tab:selected {background:#234862;color:#ffe1a0;border-top:2px solid #d4b475;}
            QTabBar::tab:hover {background:#1a3b58;}
            QScrollArea {border:none;}
            QScrollBar {background:#08192e;}
            QScrollBar:vertical {width:10px;}
            QScrollBar::handle {background:#375778;border-radius:4px;min-height:30px;}
            QScrollBar::add-line,QScrollBar::sub-line {height:0;width:0;}
            QCheckBox {padding:8px;font-size:16px;}
        ''')
        layout = QVBoxLayout(self); layout.setContentsMargins(20,20,20,20); layout.setSpacing(14)
        heading = QLabel('◈ Erinnerungen'); heading.setStyleSheet('color:#eed49c;font-size:32px;')
        layout.addWidget(heading)
        self.subtitle = QLabel('Deine Gespräche · Nach Tagen geordnet · Lokal in deinem Profil')
        self.subtitle.setWordWrap(True); layout.addWidget(self.subtitle)
        self.lock = QLabel(); self.lock.setWordWrap(True); layout.addWidget(self.lock)
        self.body = QTabWidget()
        archive = QWidget(); body = QVBoxLayout(archive); body.setContentsMargins(0,12,0,0)
        self.body.addTab(archive,'Chatverlauf')
        from gui.super_memory_panel import SuperMemoryPanel
        self.saves = SuperMemoryPanel(); self.body.addTab(self.saves,'Saves · Super Memory')
        layout.addWidget(self.body, 1)
        filters = QHBoxLayout()
        self.year = QComboBox(); self.year.setAccessibleName('Jahr filtern')
        self.month = QComboBox(); self.month.setAccessibleName('Monat filtern'); self.month.addItem('Alle Monate', None)
        for i, name in enumerate(MONTHS, 1): self.month.addItem(name, i)
        self.order = QComboBox(); self.order.setAccessibleName('Tage sortieren')
        self.order.addItem('Neueste Tage zuerst', True); self.order.addItem('Älteste Tage zuerst', False)
        for widget in (self.year, self.month, self.order): filters.addWidget(widget, 1)
        refresh = QPushButton('Aktualisieren'); refresh.clicked.connect(self.refresh); filters.addWidget(refresh)
        body.addLayout(filters)
        self.summary = QLabel(); body.addWidget(self.summary)
        split = QSplitter(Qt.Horizontal)
        self.days = QListWidget(); self.days.setMinimumWidth(180); self.days.setWordWrap(True)
        self.days.setAccessibleName('Gespräche nach Tag'); split.addWidget(self.days)
        detail = QWidget(); right = QVBoxLayout(detail); right.setContentsMargins(10,0,0,0)
        title_row = QHBoxLayout()
        self.day_title = QLabel('Wähle einen Tag'); self.day_title.setStyleSheet('color:#eed49c;font-size:22px;')
        title_row.addWidget(self.day_title, 1)
        self.delete_day = QPushButton('Tagesverlauf löschen'); self.delete_day.setObjectName('deleteHistory')
        self.delete_day.clicked.connect(self.confirm_delete_day); title_row.addWidget(self.delete_day)
        right.addLayout(title_row)
        self.transcript = QTextBrowser(); self.transcript.setOpenLinks(False); self.transcript.setOpenExternalLinks(False)
        self.transcript.anchorClicked.connect(self.delete_link); right.addWidget(self.transcript, 1)
        pages = QHBoxLayout()
        self.previous = QPushButton('← Zurück'); self.next = QPushButton('Weiter →'); self.page_label = QLabel()
        self.page_label.setWordWrap(True)
        self.previous.clicked.connect(lambda:self.change_page(-1)); self.next.clicked.connect(lambda:self.change_page(1))
        pages.addWidget(self.previous); pages.addWidget(self.page_label,1); pages.addWidget(self.next); right.addLayout(pages)
        split.addWidget(detail); split.setStretchFactor(0,1); split.setStretchFactor(1,3); split.setSizes([230,760])
        body.addWidget(split, 1)
        self.note = QLabel('Chatverlauf und KI-Saves haben getrennte Löschfunktionen. Beide bleiben lokal in deinem Profil.')
        self.note.setWordWrap(True); layout.addWidget(self.note)
        privacy = QLabel('Archivlöschung mit Überschreiben · KI-Erinnerungen und Backups bleiben separat.')
        privacy.setWordWrap(True)
        privacy.setToolTip('Gelöschte Datenbankinhalte werden mit Nullen überschrieben. '
                           'Eine physische Löschung aus SSD-Reserven, Dateisystem-Snapshots oder Backups ist damit nicht garantiert. '
                           'Der laufende Chat und die KI-Erinnerungen werden nicht gelöscht.')
        layout.addWidget(privacy)
        self.receipt = QLabel(); self.receipt.setWordWrap(True); self.receipt.setStyleSheet('color:#94cdd2;')
        layout.addWidget(self.receipt)
        self.error = QLabel(); self.error.setWordWrap(True); self.error.setStyleSheet('color:#f2b4a9;'); layout.addWidget(self.error)
        self.days.currentRowChanged.connect(self.select_day)
        for combo in (self.year, self.month, self.order): combo.currentIndexChanged.connect(self.filter_days)
        self.set_count(0)

    def retranslate(self):
        super().retranslate()
        self.body.setTabText(0,self.ui('Chatverlauf'))
        self.saves.set_language(self.language)
        self.set_count(self.count)
        self.filter_days()

    def set_profile(self, root):
        self.saves.set_profile(root)
        self.store = None; self.page = 0; self.day_rows = []
        self.days.clear(); self.transcript.clear(); self.error.clear(); self.receipt.clear()
        self.month.setCurrentIndex(0); self.order.setCurrentIndex(0)
        self.year.blockSignals(True); self.year.clear(); self.year.addItem(self.ui('Alle Jahre'), None); self.year.blockSignals(False)
        self.set_count(0)
        try:
            self.store = ChatHistory(root)
        except (OSError, sqlite3.Error) as exc:
            self.show_error(exc)

    def set_count(self, count):
        was_unlocked = self.count >= UNLOCK_MESSAGES
        self.count = max(0, int(count))
        unlocked = self.count >= UNLOCK_MESSAGES
        self.lock.setText(self.ui('🔒 Dein Gesprächsarchiv öffnet sich nach fünf Chatnachrichten. · {count}/5',count=min(self.count,5)))
        self.lock.setVisible(not unlocked); self.body.setVisible(unlocked)
        if not unlocked:
            self.days.clear(); self.day_rows = []; self.transcript.clear()
        elif not was_unlocked:
            self.refresh()

    def show_error(self, exc):
        self.error.setText(self.ui('Der Chatverlauf ist gerade nicht verfügbar. Bitte erneut aktualisieren.'))
        self.error.setToolTip(str(exc))

    def deletion_failed(self, exc):
        self.receipt.clear()
        self.error.setText(self.ui('Löschen fehlgeschlagen. Bitte erneut versuchen; die Löschung wurde nicht bestätigt.'))
        self.error.setToolTip(str(exc))

    def refresh(self):
        if not self.store or self.count < UNLOCK_MESSAGES: return
        self.saves.refresh()
        try:
            selected_year = self.year.currentData()
            self.year.blockSignals(True)
            self.year.clear(); self.year.addItem(self.ui('Alle Jahre'), None)
            for year in self.store.years(): self.year.addItem(year, year)
            self.year.setCurrentIndex(max(0,self.year.findData(selected_year)))
            self.year.blockSignals(False)
            self.filter_days()
        except (OSError, sqlite3.Error) as exc:
            self.year.blockSignals(False); self.show_error(exc)

    def filter_days(self, *_):
        if not self.store or self.count < UNLOCK_MESSAGES: return
        old = self.selected_day()
        old_page = self.page
        try:
            self.day_rows = self.store.days(self.year.currentData(), self.month.currentData(), self.order.currentData())
            self.error.clear(); self.days.blockSignals(True); self.days.clear()
            for row in self.day_rows:
                amount = f"{row['count']} " + self.ui('Nachricht' if row['count']==1 else 'Nachrichten')
                item = QListWidgetItem(date.fromisoformat(row['day']).strftime('%Y-%m-%d' if self.language=='en' else '%d.%m.%Y') + '\n' + amount)
                item.setData(Qt.UserRole,row['day']); self.days.addItem(item)
            selected = next((i for i,r in enumerate(self.day_rows) if r['day']==old), 0)
            self.days.setCurrentRow(selected if self.day_rows else -1); self.days.blockSignals(False)
            total = sum(r['count'] for r in self.day_rows)
            self.summary.setText(self.ui('{days} Tage · {messages} Nachrichten im gewählten Zeitraum',days=len(self.day_rows),messages=total))
            self.page = old_page if self.selected_day()==old else 0
            self.render_day()
        except (OSError, sqlite3.Error) as exc:
            self.days.blockSignals(False); self.show_error(exc)

    def selected_day(self):
        item = self.days.currentItem()
        return item.data(Qt.UserRole) if item else None

    def select_day(self, *_):
        self.page = 0; self.render_day()

    def change_page(self, delta):
        self.page = max(0, self.page + delta); self.render_day()

    def render_day(self):
        day = self.selected_day()
        row = next((r for r in self.day_rows if r['day']==day), None)
        self.delete_day.setEnabled(bool(row)); self.previous.setEnabled(False); self.next.setEnabled(False)
        if not row or not self.store:
            self.day_title.setText(self.ui('Dein Gesprächsarchiv')); self.page_label.clear()
            self.transcript.setHtml(self.ui('<h2 style="color:#eed49c">Noch ganz still hier.</h2><p>In diesem Zeitraum sind keine Gespräche gespeichert. Wähle einen anderen Monat oder beginne ein neues Gespräch.</p>'))
            return
        try:
            pages = max(1, (row['count'] + PAGE_SIZE - 1) // PAGE_SIZE); self.page = min(self.page,pages-1)
            messages = self.store.messages(day,self.page)
        except (OSError, sqlite3.Error) as exc:
            self.show_error(exc); return
        self.day_title.setText(date.fromisoformat(day).strftime('%Y-%m-%d' if self.language=='en' else '%d.%m.%Y'))
        parts = ['<style>p{margin:8px 0;}a{color:#a9bdd3;}</style>']
        for entry in messages:
            who = ('Du · Begleiter-KI' if entry['mode']=='companion' else 'Du') if entry['role']=='user' else ('Maatis' if entry['mode']=='companion' else 'KI')
            mode = {'adventure':'Maatis-Modus','companion':'KI-Modus','legacy':'Bisheriger Verlauf'}.get(entry['mode'],'')
            who,mode=self.ui(who),self.ui(mode)
            color = '#dfc78e' if entry['role']=='user' else '#94cdd2'
            content = escape(entry['content']).replace('\n','<br>')
            parts.append(f'<p style="color:{color}"><b>{who}</b> · {escape(entry["timestamp"][11:16])} · {mode}</p>'
                         f'<p style="color:#e7e6de;font-size:18px;">{content}</p>'
                         f'<p><a href="delete:{entry["id"]}">{self.ui("Nachricht löschen")}</a></p><hr color="#294868">')
        self.transcript.setHtml(''.join(parts))
        self.page_label.setText(self.ui('Seite {page} von {pages}',page=self.page+1,pages=pages))
        self.page_label.setToolTip(self.ui('Gespräche in zeitlicher Reihenfolge · Bis zu 100 Nachrichten je Seite'))
        self.previous.setEnabled(self.page>0); self.next.setEnabled(self.page+1<pages)

    def delete_link(self, url):
        if url.scheme() != 'delete' or not self.store or self.count < UNLOCK_MESSAGES: return
        try:
            identifier = int(url.path()); entry = self.store.get(identifier)
            if not entry or entry['day'] != self.selected_day(): return
            store = self.store
            prompt = (self.ui('Diese Nachricht aus dem Chatarchiv löschen?\n\n') + entry['content'][:160] +
                      self.ui('\n\nKI-Erinnerungen und Spielstand bleiben erhalten.'))
            if QMessageBox.question(self,self.ui('Nachricht löschen'),prompt,QMessageBox.Yes|QMessageBox.No,QMessageBox.No) != QMessageBox.Yes: return
            if self.store is not store: return
            store.delete_message(identifier)
            self.transcript.clear()
            self.refresh()
            self.receipt.setText(self.ui('Nachricht aus dem Archiv gelöscht · Datenbankinhalt überschrieben.'))
        except (ValueError, OSError, sqlite3.Error) as exc: self.deletion_failed(exc)

    def confirm_delete_day(self):
        day = self.selected_day()
        row = next((r.copy() for r in self.day_rows if r['day']==day), None)
        if not row or not self.store or self.count < UNLOCK_MESSAGES: return
        store = self.store
        prompt = (self.ui('Den Tagesverlauf vom {date} mit {count} Nachrichten löschen?',date=day if self.language=='en' else date.fromisoformat(day).strftime('%d.%m.%Y'),count=row['count'])+
                  self.ui('\n\nKI-Erinnerungen und Spielstand bleiben erhalten.'))
        if QMessageBox.question(self,self.ui('Tagesverlauf löschen'),prompt,QMessageBox.Yes|QMessageBox.No,QMessageBox.No) != QMessageBox.Yes: return
        if self.store is not store: return
        try:
            removed = store.delete_day(day,row['last_id'])
            self.transcript.clear()
            self.refresh()
            self.receipt.setText(self.ui('{count} Nachrichten aus dem Archiv gelöscht · Datenbankinhalte überschrieben.',count=removed))
        except (OSError, sqlite3.Error) as exc: self.deletion_failed(exc)
