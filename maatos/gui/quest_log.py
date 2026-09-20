"""Read-only quest journal backed by the original quest plugin."""
from html import escape
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QListWidget, QTextBrowser, QProgressBar, QPushButton


from gui.ui_i18n import LocalizedUI


class QuestLog(LocalizedUI, QWidget):
    command_requested = Signal(str)
    GROUPS = [('active','Aktiv'),('daily','Täglich'),('available','Verfügbar'),('locked','Noch verborgen'),('completed','Abgeschlossen')]

    def __init__(self):
        super().__init__()
        self.data = {'groups':{}}
        layout=QVBoxLayout(self)
        layout.setContentsMargins(12,12,12,12)
        self.summary=QLabel('Deine Reise beginnt. Aufgaben erscheinen mit deinem Fortschritt.')
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet('color:#d9c48e; font-size:20px; padding:8px;')
        layout.addWidget(self.summary)
        self.filter=QComboBox()
        for key,title in self.GROUPS:self.filter.addItem(title,key)
        self.filter.currentIndexChanged.connect(self.refresh)
        filters=QHBoxLayout()
        filters.addWidget(self.filter,1)
        self.category=QComboBox()
        for key,title in (('all','Alle Aufgaben'),('combat','⚔ Kampf'),('dungeon','▣ Dungeons'),('dungeon_plus','∞ Dungeon+')):
            self.category.addItem(title,key)
        self.category.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.category,1)
        layout.addLayout(filters)
        self.list=QListWidget()
        self.list.setMinimumHeight(165)
        self.list.setMaximumHeight(245)
        self.list.setStyleSheet('QListWidget{background:#0a1931;border:1px solid #2b4868;border-radius:8px;} QListWidget::item{padding:12px;border-bottom:1px solid #18314c;} QListWidget::item:selected{background:#234868;color:#fff1c8;}')
        self.list.currentItemChanged.connect(self.show_quest)
        layout.addWidget(self.list)
        self.detail=QTextBrowser()
        self.detail.setMinimumHeight(160)
        self.detail.setStyleSheet('background:#0c203b;border:1px solid #2b4868;border-radius:8px;padding:12px;')
        layout.addWidget(self.detail)
        self.progress=QProgressBar()
        self.progress.setStyleSheet('QProgressBar{background:#132f4c;border:0;border-radius:5px;text-align:center;min-height:24px;} QProgressBar::chunk{background:#65bcb3;border-radius:5px;}')
        layout.addWidget(self.progress)
        self.accept=QPushButton('Quest annehmen')
        self.accept.clicked.connect(self.accept_selected)
        self.accept.hide()
        layout.addWidget(self.accept)
        self.refresh()

    def retranslate(self):
        super().retranslate()
        self.update_data(self.data)

    def update_data(self,data):
        self.data=dict(data,groups=dict(data.get('groups',{})))
        groups=self.data['groups']
        groups['daily']=[q for group in ('active','completed') for q in groups.get(group,[]) if q.get('is_daily')]
        self.summary.setText(self.ui('DEIN QUESTLOG   ·   {active} aktiv   ·   {completed} abgeschlossen',active=len(groups.get('active',[])),completed=len(groups.get('completed',[]))))
        self.filter.blockSignals(True)
        for i,(key,title) in enumerate(self.GROUPS):
            self.filter.setItemText(i,f'{self.ui(title)}  ·  {len(groups.get(key,[]))}')
        self.filter.blockSignals(False)
        self.refresh()

    def refresh(self):
        current=self.list.currentItem()
        selected=current.data(Qt.UserRole).get('id') if current else None
        del current
        self.list.blockSignals(True)
        self.list.clear()
        for q in self.data.get('groups',{}).get(self.filter.currentData(),[]):
            if self.category.currentData() != 'all' and q.get('category') != self.category.currentData():
                continue
            subtitle=q.get('progress_text','') if self.filter.currentData() in ('active','daily') and not q.get('completed') else q.get('status_label','')
            # Native Qt-owned rows avoid Python wrapper destruction on refresh.
            self.list.addItem(q.get('name','Quest')+'\n'+subtitle)
            item=self.list.item(self.list.count()-1)
            item.setData(Qt.UserRole,q)
            if q.get('id')==selected:self.list.setCurrentItem(item)
        if self.list.currentRow()<0 and self.list.count():self.list.setCurrentRow(0)
        self.list.blockSignals(False)
        self.show_quest(self.list.currentItem())

    def show_quest(self,item,*args):
        self.accept.hide()
        self.progress.hide()
        if item is None:
            self.detail.setHtml('<h2 style="color:#d9c48e">'+self.ui('Ein neuer Weg wartet')+'</h2><p style="color:#b2c5d9">'+self.ui('Hier gibt es noch keine Aufgaben. Sprich mit der KI und erkunde die Welt, um deine Reise fortzusetzen.')+'</p>')
            return
        q=item.data(Qt.UserRole)
        esc=lambda value:escape(str(value or ''))
        reward='' if q.get('completed') or self.filter.currentData()=='completed' else "<p style='color:#e6cd85'>"+self.ui('Belohnung beim aktuellen Level: {xp} EP',xp=q.get('effective_xp',0))+"</p>"
        if q.get('talent_points'):
            reward += '<p style="color:#9edbc7">'+self.ui('✦ 1 Talentpunkt erhalten · nach der Klassenwahl nutzbar' if q.get('completed') else '✦ 1 Talentpunkt bei Abschluss · nach der Klassenwahl nutzbar')+'</p>'
        self.detail.setHtml(f"<h2 style='color:#f0dfb1'>{esc(q.get('name'))}</h2><p style='color:#abc5de'>{esc(q.get('status_label'))}</p><p style='color:#e0e9f2;font-size:18px'>{esc(q.get('desc'))}</p>{reward}<p style='color:#8cd0c6'>{esc(q.get('path_bonus'))}</p>")
        if q.get('target') and self.filter.currentData() in ('active','daily') and not q.get('completed'):
            target=max(1,int(q['target']))
            value=min(target,max(0,int(q.get('progress',0))))
            self.progress.setRange(0,target)
            self.progress.setValue(value)
            self.progress.setFormat(q.get('progress_text') or f'{value}/{target}')
            self.progress.show()
        self.accept.setVisible(self.filter.currentData()=='available')

    def select_quest(self,identifier=''):
        self.category.setCurrentIndex(0)
        group=next((key for key,_ in self.GROUPS if any(q.get('id')==identifier for q in self.data.get('groups',{}).get(key,[]))),'active') if identifier else 'active'
        self.filter.setCurrentIndex(self.filter.findData(group))
        self.refresh()
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole).get('id')==identifier:
                self.list.setCurrentRow(i)
                self.list.scrollToItem(self.list.item(i))
                break
        self.list.setFocus()

    def accept_selected(self):
        item=self.list.currentItem()
        if item and self.filter.currentData()=='available':
            self.command_requested.emit('/quest accept '+item.data(Qt.UserRole)['id'])
