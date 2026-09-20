"""Native dated saves, consolidation and options; no person-profile controls."""
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,
    QListWidget,QListWidgetItem,QTextBrowser,QLineEdit,QPushButton,QSplitter,
    QMessageBox,QTabWidget,QFormLayout,QCheckBox,QSpinBox,QDoubleSpinBox,QScrollArea,QPlainTextEdit)
from shared.core.super_memory import SuperMemory
from gui.ui_i18n import LocalizedUI

MONTHS = ['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember']
TYPES = {'fact':'Fakt','project':'Projekt','decision':'Entscheidung','preference':'Vorliebe',
         'goal':'Ziel','insight':'Erkenntnis','identity':'Eigene Aussage','relationship':'Gespräch'}


class SuperMemoryPanel(LocalizedUI, QWidget):
    def __init__(self):
        super().__init__()
        self.store=None; self.rows=[]; self.page=0; self.editable=True
        layout=QVBoxLayout(self); layout.setContentsMargins(0,12,0,0)
        title=QLabel('🧠 Super Memory'); title.setStyleSheet('color:#eed49c;font-size:25px;'); layout.addWidget(title)
        intro=QLabel('Deine gespeicherten Gesprächsnotizen · Llama: bis zu 3 · Andere Modelle: bis zu 5 Erinnerungen pro Antwort')
        intro.setWordWrap(True); layout.addWidget(intro)
        self.tabs=tabs=QTabWidget(); layout.addWidget(tabs,1)
        browser=QWidget(); body=QVBoxLayout(browser); tabs.addTab(browser,'Saves')
        filters=QHBoxLayout()
        self.year=QComboBox(); self.year.addItem('Alle Jahre','')
        self.month=QComboBox(); self.month.addItem('Alle Monate','')
        for i,name in enumerate(MONTHS,1):self.month.addItem(name,f'{i:02d}')
        self.day=QComboBox(); self.day.addItem('Alle Tage','')
        for i in range(1,32):self.day.addItem(str(i),f'{i:02d}')
        for combo,name in ((self.year,'Jahr'),(self.month,'Monat'),(self.day,'Tag')):
            combo.setAccessibleName('Saves nach '+name+' filtern'); filters.addWidget(combo)
            combo.currentIndexChanged.connect(self.filter_rows)
        self.search=QLineEdit(); self.search.setPlaceholderText('In Erinnerungen suchen …')
        self.search.textChanged.connect(self.filter_rows); filters.addWidget(self.search,1)
        reload=QPushButton('Aktualisieren'); reload.clicked.connect(self.refresh); filters.addWidget(reload)
        body.addLayout(filters)
        self.summary=QLabel(); body.addWidget(self.summary)
        split=QSplitter(Qt.Horizontal)
        self.list=QListWidget(); self.list.setWordWrap(True); self.list.setMinimumWidth(250)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.currentItemChanged.connect(self.show_entry); split.addWidget(self.list)
        self.detail=QTextBrowser(); split.addWidget(self.detail); split.setSizes([340,650]); body.addWidget(split,1)
        nav=QHBoxLayout()
        self.previous=QPushButton('← Zurück'); self.next=QPushButton('Weiter →')
        self.previous.clicked.connect(lambda:self.change_page(-1)); self.next.clicked.connect(lambda:self.change_page(1))
        nav.addWidget(self.previous); nav.addWidget(self.next); nav.addStretch()
        self.delete_buttons={}
        for scope,label in [('entry','Save löschen'),('day','Tag löschen'),('month','Monat löschen'),('year','Jahr löschen')]:
            b=QPushButton(label); b.clicked.connect(lambda checked=False,s=scope:self.confirm_delete(s))
            b.setStyleSheet('QPushButton {background:#352339;color:#efb6b4;} QPushButton:disabled {background:#132237;color:#68758a;}')
            if scope!='entry':b.setToolTip('Wähle oben '+{'day':'Jahr, Monat und Tag','month':'Jahr und Monat','year':'ein Jahr'}[scope]+'.')
            self.delete_buttons[scope]=b; nav.addWidget(b)
        body.addLayout(nav)
        add=QWidget(); form=QVBoxLayout(add); tabs.addTab(add,'Erinnerung anlegen')
        hint=QLabel('Speichere eine konkrete Notiz. Im Chat geht auch „Merke dir: …“ oder /mem save <Text>.')
        hint.setWordWrap(True); form.addWidget(hint)
        self.new_text=QPlainTextEdit(); self.new_text.setPlaceholderText('Woran soll sich die KI erinnern?'); form.addWidget(self.new_text,1)
        meta=QHBoxLayout(); self.memory_type=QComboBox()
        for label,value in [('Fakt','fact'),('Projekt','project'),('Entscheidung','decision'),('Vorliebe','preference'),('Ziel','goal'),('Erkenntnis','insight')]:self.memory_type.addItem(label,value)
        self.tags=QLineEdit(); self.tags.setPlaceholderText('Stichwörter, durch Komma getrennt')
        self.priority=QComboBox(); self.priority.addItem('Normal',.65); self.priority.addItem('Wichtig',.85); self.priority.addItem('Sehr wichtig',1.0)
        for w in (self.memory_type,self.tags,self.priority):meta.addWidget(w)
        form.addLayout(meta)
        self.save_button=QPushButton('Erinnerung speichern'); self.save_button.clicked.connect(self.save_entry); form.addWidget(self.save_button)
        insights=QWidget(); view=QVBoxLayout(insights); tabs.addTab(insights,'Zeitverlauf & Pflege')
        recall_hint=QLabel('Frage im Chat: „Was habe ich gestern gesagt?“, „am 15.06.2026?“ oder „vor einem Monat?“\n'
                          'English: “What did I say yesterday?”, “on June 15, 2026?” or “a year ago?”\n'
                          'Die KI sucht in deinen gespeicherten Saves; der vollständige Chatverlauf bleibt separat.')
        recall_hint.setWordWrap(True); view.addWidget(recall_hint)
        row=QHBoxLayout(); self.report_kind=QComboBox()
        for label,kind in [('Statistik','stats'),('Zeitverlauf','timeline'),('Meilensteine','milestones'),('Letzte Saves','recent')]:self.report_kind.addItem(label,kind)
        row.addWidget(self.report_kind); report=QPushButton('Anzeigen'); report.clicked.connect(self.show_report); row.addWidget(report)
        self.dream=QPushButton('Zusammenfassen'); self.dream.clicked.connect(lambda:self.maintain('dream')); row.addWidget(self.dream)
        self.archive=QPushButton('Monatsarchive bilden'); self.archive.clicked.connect(lambda:self.maintain('archive')); row.addWidget(self.archive)
        view.addLayout(row); self.report=QTextBrowser(); view.addWidget(self.report,1)
        options=QScrollArea(); options.setWidgetResizable(True); pane=QWidget(); options.setWidget(pane); settings=QFormLayout(pane); tabs.addTab(options,'Einstellungen')
        self.options={}
        booleans=[('enabled','Super Memory aktiv'),('autostore','Wichtige Nutzernachrichten automatisch merken'),
            ('autorecall','Passende Erinnerungen für Antworten abrufen'),('allow_model_saves','KI darf eigene Saves anlegen'),
            ('show_save_box','Speicherhinweis anzeigen'),('show_source','Datum und Speicherquelle im Kontext'),
            ('autostore_assistant','Auch wichtige KI-Antworten automatisch merken'),('dream_on_load','Beim Start zusammenfassen'),
            ('archive_enabled','Monatszusammenfassungen automatisch erstellen')]
        for key,label in booleans:
            w=QCheckBox(label); settings.addRow(w); self.options['supermem_'+key]=w
        for key,label,lo,hi in [('max_episodic','Episodischer Suchspeicher',50,10000),('max_semantic','Semantischer Suchspeicher',50,10000),
            ('max_keyword','Stichwort-Suchspeicher',50,10000),('dream_hours','Zusammenfassen: letzte Stunden',1,8760),
            ('archive_after_days','Monatsarchiv: älter als Tage',1,3650),('autostore_max_chars','Zeichen pro automatischem Save',100,20000)]:
            w=QSpinBox(); w.setRange(lo,hi); settings.addRow(label,w); self.options['supermem_'+key]=w
        for key,label in [('min_score','Abrufschwelle'),('autostore_user_min','Speicherschwelle: Nutzer'),('autostore_assistant_min','Speicherschwelle: KI')]:
            w=QDoubleSpinBox(); w.setRange(0,1); w.setSingleStep(.05); settings.addRow(label,w); self.options['supermem_'+key]=w
        self.settings_save=QPushButton('Einstellungen speichern'); self.settings_save.clicked.connect(self.save_settings); settings.addRow(self.settings_save)
        from gui.settings_scroll import protect_settings_scroll
        protect_settings_scroll(pane)
        info=QLabel('Die Suchspeicher werden begrenzt; deine Saves bleiben in der Liste erhalten.\nKeine Personenprofile und kein Beziehungsgraph.'); info.setWordWrap(True); settings.addRow(info)
        privacy=QLabel('Löschen überschreibt die Einträge in der aktiven Datenbank und entfernt zugehörige Suchkopien. '
            'Abgeleitete Zusammenfassungen werden verworfen. Chatarchiv, frühere deaktivierte Speicherdateien und Backups sind separat.')
        privacy.setWordWrap(True); privacy.setToolTip('SQLite secure_delete und leeres Journal. Physisches Entfernen aus SSD-Reserven, Snapshots oder Backups kann die App nicht garantieren.'); layout.addWidget(privacy)
        self.status=QLabel(); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.update_controls()

    def retranslate(self):
        super().retranslate()
        for i,title in enumerate(('Saves','Erinnerung anlegen','Zeitverlauf & Pflege','Einstellungen')):
            self.tabs.setTabText(i,self.ui(title))
        self.new_text.setPlaceholderText(self.ui('Woran soll sich die KI erinnern?'))
        self.render_rows()
        if self.report.toPlainText():self.show_report()

    def set_profile(self, root):
        self.profile_root=root
        self.store=None; self.rows=[]; self.list.clear(); self.detail.clear(); self.report.clear(); self.new_text.clear(); self.tags.clear(); self.status.clear()
        for w in (self.year,self.month,self.day):w.blockSignals(True)
        self.year.clear(); self.year.addItem(self.ui('Alle Jahre'),''); self.month.setCurrentIndex(0); self.day.setCurrentIndex(0)
        for w in (self.year,self.month,self.day):w.blockSignals(False)
        self.search.clear()
        try:
            self.store=SuperMemory(root)
            self.load_options()
        except Exception:self.status.setText(self.ui('Super Memory ist gerade nicht verfügbar. Bitte erneut versuchen.'))
        self.update_controls()

    def set_editable(self, enabled):
        self.editable=bool(enabled); self.update_controls()

    def update_controls(self):
        ready=bool(self.store) and self.editable
        for w in (self.save_button,self.settings_save,self.dream,self.archive):w.setEnabled(ready)
        selected=self.list.currentItem() is not None
        for scope,b in self.delete_buttons.items():
            b.setEnabled(ready and (selected if scope=='entry' else bool(self.period(scope))))

    def period(self, scope='day'):
        year=self.year.currentData() or ''; month=self.month.currentData() or ''; day=self.day.currentData() or ''
        if not year:return ''
        if scope=='year':return year
        if not month:return ''
        if scope=='month':return year+'-'+month
        return year+'-'+month+'-'+day if day else ''

    def refresh(self):
        try:
            if not self.store:
                if not getattr(self,'profile_root',None):return
                self.store=SuperMemory(self.profile_root)
            current=self.year.currentData(); self.year.blockSignals(True)
            self.year.clear(); self.year.addItem(self.ui('Alle Jahre'),'')
            for y in sorted({r['day'][:4] for r in self.store.entries()},reverse=True):self.year.addItem(y,y)
            self.year.setCurrentIndex(max(0,self.year.findData(current))); self.year.blockSignals(False)
            self.filter_rows(); self.load_options()
        except Exception:
            self.year.blockSignals(False); self.status.setText(self.ui('Saves konnten nicht geladen werden. Bitte aktualisieren.'))

    def filter_rows(self,*_):
        if not self.store:return
        try:
            self.rows=self.store.entries(query=self.search.text())
            for pos,combo in ((slice(0,4),self.year),(slice(5,7),self.month),(slice(8,10),self.day)):
                if combo.currentData():self.rows=[r for r in self.rows if r['day'][pos]==combo.currentData()]
            self.page=0; self.render_rows()
        except Exception:self.status.setText(self.ui('Saves konnten nicht geladen werden. Bitte aktualisieren.'))

    def render_rows(self):
        current=self.list.currentItem()
        selected=current.data(Qt.UserRole)['id'] if current else None
        del current
        self.list.blockSignals(True)
        self.list.clear(); self.detail.clear()
        for r in self.rows[self.page*100:(self.page+1)*100]:
            stamp=datetime.fromtimestamp(r['ts']).strftime('%Y-%m-%d · %H:%M' if self.language=='en' else '%d.%m.%Y · %H:%M')
            self.list.addItem(f"{stamp} · {self.ui(TYPES.get(r['memory_type'],r['memory_type']))}\n{SuperMemory.source_label(r,self.language=='en')}\n{r['content'][:90]}"+('…' if len(r['content'])>90 else ''))
            item=self.list.item(self.list.count()-1);item.setData(Qt.UserRole,r)
            if r['id']==selected:self.list.setCurrentItem(item)
        self.summary.setText(self.ui('{count} Saves · Seite {page}/{pages}',count=len(self.rows),page=self.page+1,pages=max(1,(len(self.rows)+99)//100)))
        self.previous.setEnabled(self.page>0); self.next.setEnabled((self.page+1)*100<len(self.rows))
        if self.list.count() and not self.list.currentItem():self.list.setCurrentRow(0)
        self.list.blockSignals(False)
        if self.list.count():self.show_entry(self.list.currentItem())
        else:self.detail.setPlainText(self.ui('Noch keine passenden Saves. Du kannst eine Erinnerung anlegen oder im Chat „Merke dir: …“ schreiben.'))
        self.update_controls()

    def change_page(self,delta):
        self.page=max(0,min(max(0,(len(self.rows)-1)//100),self.page+delta)); self.render_rows()

    def show_entry(self,item,*_):
        if item:
            r=item.data(Qt.UserRole)
            state='Aktuell' if r['status']=='active' else 'Durch eine neuere Erinnerung ersetzt'
            self.detail.setPlainText(self.ui('{date}\n{type} · {state}\nStichwörter: {tags}\nQuelle: {source} · Priorität: {priority}\n\n{content}',
                date=datetime.fromtimestamp(r['ts']).strftime('%Y-%m-%d at %H:%M' if self.language=='en' else '%d.%m.%Y um %H:%M'),
                type=self.ui(TYPES.get(r['memory_type'],r['memory_type'])),state=self.ui(state),tags=r['tags'] or '—',
                source=SuperMemory.source_label(r,self.language=='en'),priority=f"{r['priority']:.0%}",content=r['content']))
        self.update_controls()

    def confirm_delete(self,scope):
        if not self.store or not self.editable:return
        try:
            if scope=='entry':
                item=self.list.currentItem()
                if not item:return
                records=[item.data(Qt.UserRole)]; label=self.ui('diesen Save')
            else:
                period=self.period(scope)
                if not period:return
                records=self.store.entries(period=period); label=self.ui({'day':'den Tag','month':'den Monat','year':'das Jahr'}[scope])+' '+period
            ids=[r['id'] for r in records]
            if not ids:self.status.setText(self.ui('In diesem Zeitraum sind keine Saves vorhanden.')); return
            answer=QMessageBox.question(self,self.ui('Saves endgültig löschen'),
                self.ui('{count} Saves für {label} löschen?\n\nAlle zugehörigen Suchkopien werden entfernt und überschrieben. '
                'Zusammenfassungen werden verworfen. Der laufende KI-Gesprächskontext wird vor der nächsten Antwort geleert. '
                'Das Chatarchiv bleibt erhalten. Diese Aktion lässt sich nicht rückgängig machen.',count=len(ids),label=label),
                QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
            if answer!=QMessageBox.Yes:return
            count=self.store.delete(ids)
            self.list.clear(); self.detail.clear(); self.report.clear(); self.rows=[]
            self.refresh(); self.status.setText(self.ui('{count} Saves gelöscht · Datenbankinhalte überschrieben · Suchkopien bereinigt.',count=count))
        except Exception:self.status.setText(self.ui('Löschen fehlgeschlagen. Die Löschung wurde nicht bestätigt; bitte erneut versuchen.'))

    def save_entry(self):
        if not self.store or not self.editable:return
        try:
            self.store.save(self.new_text.toPlainText(),memory_type=self.memory_type.currentData(),tags=self.tags.text(),priority=self.priority.currentData())
            self.new_text.clear(); self.refresh(); self.status.setText(self.ui('Erinnerung gespeichert.'))
        except ValueError as exc:self.status.setText(self.ui(str(exc)))
        except Exception:self.status.setText(self.ui('Die Erinnerung konnte nicht gespeichert werden. Bitte erneut versuchen.'))

    def show_report(self):
        if not self.store:return
        try:self.report.setPlainText(self.store.report(self.report_kind.currentData(),self.period('month') or self.period('year'),language=self.language))
        except Exception:self.status.setText(self.ui('Die Übersicht konnte nicht geladen werden.'))

    def maintain(self,kind):
        if not self.store or not self.editable:return
        try:self.status.setText(self.store.report(kind,language=self.language)); self.show_report()
        except Exception:self.status.setText(self.ui('Zusammenfassen fehlgeschlagen. Bitte erneut versuchen.'))

    def load_options(self):
        if not self.store:return
        with self.store.operation():
            for key,w in self.options.items():
                value=self.store.settings[key]
                if isinstance(w,QCheckBox):w.setChecked(value)
                else:w.setValue(value)

    def save_settings(self):
        if not self.store or not self.editable:return
        try:
            self.store.configure(**{k:w.isChecked() if isinstance(w,QCheckBox) else w.value() for k,w in self.options.items()})
            self.status.setText(self.ui('Speichereinstellungen gespeichert. Sie gelten ab der nächsten Nachricht.'))
        except Exception:self.status.setText(self.ui('Einstellungen konnten nicht gespeichert werden.'))
