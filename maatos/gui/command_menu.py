"""Categorized command navigation using the runtime's actual command catalog."""
from PySide6.QtCore import Qt, Signal
from gui.ui_i18n import LocalizedUI
from shared.core.command_i18n import tr
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

CATEGORIES = {
    '⚔ Kämpfe & Dungeons': {'fight','fightboss','fightfinal','fightmod','battletest','dungeon60','d500','d1000'},
    '📜 Quests & Erfolge': {'contracts','quests','quest','questcheck','erfolge','ach'},
    '✦ Charakter & Ausrüstung': {'xp','shop','usepotion','test_fields','maatbond'},
    '☾ Welt & Geschichte': {'intro','journal','lore','origin','whoismaat','wiki','storyreset'},
    '◈ KI & Erinnerungen': {'maat','bki','bias','emotion','mem','mem6','memauto','antirepeat','perspective','prethought','userstyle','think','uncertainty','plp','evo'},
    '⚙ Einstellungen & System': {'help','menu','clear','exit','model','models','restart','safe-restart','profile','plugins','plugin','mods','mod','sysinfo','meminfo','update','say','time','zeit','runtime','laufzeit','timeinfo','zeitkontext','timelog','timestats'},
}
TITLES={'contracts':'Auftragsbrett · Level 50','fight':'Arena betreten','fightboss':'Fälliger Boss','fightfinal':'Fälliger Finalboss','dungeon60':'Dungeon · 60','d500':'Dungeon · 500','d1000':'Dungeon · 1000','quests':'Questlog','quest':'Quest verwalten','xp':'Level & Werte','shop':'Laden','usepotion':'Heiltrank verwenden','journal':'Chronik','models':'KI & Modelle','intro':'Einleitung','erfolge':'Erfolge','ach':'Emotionale Erfolge','mem':'Erinnerungen','mem6':'Erinnerungen · v6','say':'Sprachausgabe','help':'Befehlsübersicht'}


class CommandMenu(LocalizedUI, QTreeWidget):
    chosen=Signal(dict)
    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setMinimumHeight(280)
        self.setMaximumHeight(420)
        self.setIndentation(22)
        self.setStyleSheet('QTreeWidget{background:#0a1931;border:1px solid #2b4868;border-radius:8px;} QTreeWidget::item{padding:9px;} QTreeWidget::item:selected{background:#234868;color:#fff1c8;}')
        self.currentItemChanged.connect(self.select)
        self.catalog=[]
        self.query=""

    def retranslate(self):
        self.populate(self.catalog, self.query)

    def localized(self, item):
        return dict(item, description=tr(item.get("description", ""), self.language))

    def populate(self,items,query=''):
        self.catalog=list(items)
        self.query=query
        self.clear()
        categories={}
        roots={}
        for data in sorted(items,key=lambda d:d['command']):
            data=self.localized(data)
            parts=data['command'].lstrip('/').split()
            base=parts[0]
            category=next((name for name,keys in CATEGORIES.items() if base in keys),'◇ Weitere Plugins')
            title=tr(TITLES.get(base,base),self.language)
            category=tr(category,self.language)
            if query.casefold() not in (data['command']+' '+data['description']+' '+title+' '+category).casefold():continue
            if category not in categories:
                categories[category]=QTreeWidgetItem(self,[category])
                font=categories[category].font(0)
                font.setBold(True)
                font.setPointSize(14)
                categories[category].setFont(0,font)
            if base not in roots:
                roots[base]=QTreeWidgetItem(categories[category],[title+'   /'+base])
            node=roots[base]
            if len(parts)>1:node=QTreeWidgetItem(node,[' '.join(parts[1:])])
            node.setData(0,Qt.UserRole,data)
            node.setToolTip(0,data['description'])
        for name,item in categories.items():
            item.setText(0,f'{name}   ·   {item.childCount()}')
            item.setExpanded(bool(query))
        if query:self.expandAll()
        self.resizeColumnToContents(0)

    def select(self,item,*args):
        self.chosen.emit(item.data(0,Qt.UserRole) if item and item.data(0,Qt.UserRole) else {})
