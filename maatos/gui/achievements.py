"""Searchable, categorized achievement cards backed by the terminal save data."""
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QLineEdit,QScrollArea,QProgressBar,QFrame
from gui.ui_i18n import LocalizedUI
from shared.core.achievement_catalog import localize

class Achievements(LocalizedUI, QWidget):
    def __init__(self):
        super().__init__();self.rows={};self.known=None;self.data={};self.displayed_data={};self._new_ids=set()
        self.setObjectName('achievementPage')
        self.setStyleSheet('QWidget#achievementPage,QWidget#achievementBody {background:#071a30;} QLabel {color:#c9d8e8;} QScrollArea {border:none;background:#071a30;} QProgressBar {background:#10253e;color:#d6e5f3;border:1px solid #314b68;border-radius:5px;text-align:center;min-height:20px;} QProgressBar::chunk {background:#487c70;border-radius:4px;}')
        l=QVBoxLayout(self)
        title=QLabel('🏆 Deine Erfolge');title.setStyleSheet('font-size:28px;color:#efcf88');l.addWidget(title)
        self.summary=QLabel('Erfolge werden geladen …');l.addWidget(self.summary)
        self.progress=QProgressBar();l.addWidget(self.progress)
        self.notice=QLabel();self.notice.setWordWrap(True);self.notice.setStyleSheet('color:#99dfbd;font-size:18px');l.addWidget(self.notice)
        row=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Erfolge durchsuchen …');row.addWidget(self.search,1)
        self.category=QComboBox();self.category.addItem('Alle Kategorien','');row.addWidget(self.category)
        self.status=QComboBox();self.status.addItems(['Alle','Freigeschaltet','Noch offen']);row.addWidget(self.status);l.addLayout(row)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);body=QWidget();body.setObjectName('achievementBody');self.cards=QVBoxLayout(body);self.cards.addStretch();self.scroll.setWidget(body);l.addWidget(self.scroll,1)
        hint=QLabel('Minispiel-Siege zählen ab diesem Update. Entdeckte Spiele werden übernommen.\nMinispiel-Erfolge sind Abzeichen ohne zusätzliche EP/Gold. Terminal-Belohnungen bleiben unverändert.');hint.setWordWrap(True);l.addWidget(hint)
        self.search.textChanged.connect(self.filter);self.category.currentTextChanged.connect(self.filter);self.status.currentIndexChanged.connect(self.filter)
    def reset(self):
        self.known=None;self._new_ids=set();self.notice.clear();self.update_data({'groups':{},'total':0,'unlocked':0});self.known=None
    def retranslate(self):
        super().retranslate()
        self.render_data()
    def update_data(self,data):
        self.data=data
        unlocked={r['id'] for group in data.get('groups',{}).values() for r in group if r['unlocked']}
        if self.known is not None:
            new=unlocked-self.known
            if new:self._new_ids=new
        self.known=unlocked
        self.render_data()
    def render_data(self):
        data=self.displayed_data=localize(self.data,self.language)
        names=[r['name'] for rows in data.get('groups',{}).values() for r in rows if r['id'] in self._new_ids]
        self.notice.setText(self.ui('✨ Neu freigeschaltet: {names}',names=' · '.join(names)) if names else '')
        total=data.get('total',0);done=data.get('unlocked',0)
        self.summary.setText(self.ui('{done} / {total} Erfolge freigeschaltet',done=done,total=total));self.progress.setRange(0,max(1,total));self.progress.setValue(done)
        selected=self.category.currentData()
        self.category.blockSignals(True)
        self.category.clear();self.category.addItem(self.ui('Alle Kategorien'),'')
        for category in data.get('groups',{}):self.category.addItem(self.ui(category),category)
        self.category.setCurrentIndex(max(0,self.category.findData(selected)))
        self.category.blockSignals(False)
        present=set()
        for category,entries in data.get('groups',{}).items():
            for r in entries:
                key=r['id'];present.add(key)
                if key not in self.rows:
                    card=QFrame();card.setStyleSheet('QFrame {background:#102841;border:1px solid #35516b;border-radius:9px;} QLabel {border:none;background:transparent;}')
                    cl=QVBoxLayout(card);name=QLabel();name.setWordWrap(True);name.setStyleSheet('font-size:19px;border:none');cl.addWidget(name)
                    desc=QLabel();desc.setWordWrap(True);cl.addWidget(desc)
                    bar=QProgressBar();cl.addWidget(bar)
                    self.cards.insertWidget(self.cards.count()-1,card)
                    self.rows[key]=(card,name,desc,bar)
                card,name,desc,bar=self.rows[key]
                name.setText(('✓ ' if r['unlocked'] else '◇ ')+r['name'])
                name.setStyleSheet('border:none;font-size:19px;color:'+('#a1e3bc' if r['unlocked'] else '#e2ca99'))
                reward=self.ui(' · {xp} EP (Terminal)',xp=r['xp']) if r.get('xp') else ''
                desc.setText(self.ui(category)+' · '+r['description']+reward)
                bar.setRange(0,r['target']);bar.setValue(r['current']);bar.setFormat(self.ui('Freigeschaltet') if r['unlocked'] else f"{r['current']} / {r['target']}")
        for key,(card,*_) in self.rows.items():
            if key not in present:card.hide()
        self.filter()
    def filter(self,*args):
        query=self.search.text().casefold();category=self.category.currentData();status=self.status.currentIndex()
        for group,entries in self.displayed_data.get('groups',{}).items():
            for r in entries:
                visible=(not category or category==group) and (not query or query in (r['name']+' '+r['description']).casefold()) and (status==0 or (status==1)==r['unlocked'])
                if r['id'] in self.rows:self.rows[r['id']][0].setVisible(visible)
    def select_category(self,key=''):
        self.category.setCurrentIndex(max(0,self.category.findData(key)))
