"""Level-gated bestiary using the same portraits and name pools as combat."""
import hashlib
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QComboBox,QListWidget,QStackedWidget
from gui.battle_arena import ART,artwork_for
from shared.core.monster_catalog import entries,UNLOCK_LEVEL,ENEMY_KINDS,CAMPAIGN_BOSS_COUNT,FINAL_NAMES
from gui.ui_i18n import LocalizedUI

class MonsterCatalog(LocalizedUI, QWidget):
    def __init__(self):
        super().__init__();self.setObjectName('monsterCatalog');self.setAttribute(Qt.WA_StyledBackground,True);self.rows=entries();self.level=1
        self.setStyleSheet('QWidget#monsterCatalog {background:#07172e;} QLabel {color:#dedfce;font-size:18px;} QLineEdit,QComboBox,QListWidget {background:#102943;color:#e7dfcb;padding:10px;border:1px solid #345374;border-radius:8px;font-size:17px;} QListWidget::item {padding:10px;} QListWidget::item:selected {background:#34516c;color:#ffe2a0;}')
        layout=QVBoxLayout(self);self.heading=QLabel('✦ Monsterkatalog');self.heading.setStyleSheet('color:#e9c77e;font-size:30px');layout.addWidget(self.heading)
        self.pages=QStackedWidget();layout.addWidget(self.pages,1)
        self.lock=QLabel();self.lock.setAlignment(Qt.AlignCenter);self.lock.setWordWrap(True);self.pages.addWidget(self.lock)
        content=QWidget();body=QVBoxLayout(content)
        self.note=note=QLabel(self.catalog_note());note.setWordWrap(True);body.addWidget(note)
        filters=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Monster suchen …');filters.addWidget(self.search)
        self.category=QComboBox()
        for category in ['Alle','Gegnertypen','Bosse','Finalgegner']:self.category.addItem(category,category)
        filters.addWidget(self.category);body.addLayout(filters)
        row=QHBoxLayout();self.list=QListWidget();self.list.setWordWrap(True);self.list.setMinimumWidth(260);row.addWidget(self.list,1)
        detail=QVBoxLayout();self.name=QLabel();self.name.setWordWrap(True);self.name.setStyleSheet('color:#f0cd7a;font-size:26px');detail.addWidget(self.name)
        self.art=QSvgWidget();self.art.setMinimumSize(180,180);detail.addWidget(self.art,1)
        self.description=QLabel();self.description.setWordWrap(True);detail.addWidget(self.description);row.addLayout(detail,2);body.addLayout(row,1)
        self.pages.addWidget(content);self.search.textChanged.connect(self.filter);self.category.currentTextChanged.connect(self.filter);self.list.currentRowChanged.connect(self.select);self.set_level(1)
    def set_level(self,level):
        level=int(level);changed=(self.level>=UNLOCK_LEVEL)!=(level>=UNLOCK_LEVEL);self.level=level
        self.lock.setText(self.ui('🔒 Monsterkatalog\nFreischaltung ab Level {unlock}\nDein Level: {level}',unlock=UNLOCK_LEVEL,level=level))
        self.pages.setCurrentIndex(1 if level>=UNLOCK_LEVEL else 0)
        if level<UNLOCK_LEVEL:
            self.search.clear();self.category.setCurrentIndex(0);self.list.clear();self.name.clear();self.description.clear();self.art.hide()
        elif changed or not self.list.count():self.filter()
    def filter(self):
        self.list.clear()
        if self.level<UNLOCK_LEVEL:return
        self.filtered=[r for r in self.rows if (self.category.currentData()=='Alle' or r['category']==self.category.currentData()) and self.search.text().casefold() in r['name'].casefold()]
        for r in self.filtered:self.list.addItem(('👑 ' if r['category']!='Gegnertypen' else '◆ ')+r['name'])
        if self.filtered:self.list.setCurrentRow(0)
        else:self.name.setText(self.ui('Keine passenden Einträge'));self.description.clear();self.art.hide()
    def select(self,index):
        if self.level<UNLOCK_LEVEL or index<0:return
        r=self.filtered[index];self.name.setText(r['name']);self.description.setText(self.ui(r['category'])+'\n\n'+r['details'])
        digest=hashlib.sha256(r['art_name'].encode()).digest();tint=QColor.fromHsv(175+digest[0]%150,90+digest[1]%65,225)
        svg=(ART/(artwork_for(r['art_name'])+'.svg')).read_text().replace('#c69ce9',tint.name()).replace('#535b83',tint.darker(245).name())
        self.art.load(svg.encode());self.art.renderer().setAspectRatioMode(Qt.KeepAspectRatio);self.art.show()

    def retranslate(self):
        self.rows=entries(self.language)
        self.heading.setText(self.ui('✦ Monsterkatalog'))
        self.note.setText(self.catalog_note())
        self.search.setPlaceholderText(self.ui('Monster suchen …'))
        self.category.blockSignals(True)
        for index in range(self.category.count()):self.category.setItemText(index,self.ui(self.category.itemData(index)))
        self.category.blockSignals(False)
        self.set_level(self.level)
        self.filter()

    def catalog_note(self):
        return self.ui('Das Bestiarium von Terra · {types} Gegnertypen und {bosses} Bossformen.\nZufallskämpfe, Arena und Dungeons nutzen diese Grundformen. Besondere Dungeon-Wächter sind hier nicht enthalten.',
                       types=len(ENEMY_KINDS),bosses=CAMPAIGN_BOSS_COUNT+len(FINAL_NAMES))
