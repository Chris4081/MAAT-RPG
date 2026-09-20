"""Level-gated native dungeon selection."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QPushButton,QScrollArea
from shared.core.dungeon_campaign import catalog
from gui.ui_i18n import LocalizedUI

class Dungeons(LocalizedUI, QWidget):
    enter_requested=Signal(int)
    plus_requested=Signal()
    def __init__(self):
        super().__init__();self.level=1;self.ready=False;self.signature=None;self.buttons=[];self.rows={}
        l=QVBoxLayout(self);title=QLabel('🏰 Dungeons');title.setStyleSheet('font-size:32px;color:#ecc77b');l.addWidget(title)
        info=QLabel('Ab Level 10 · Alle 5 Level ein neuer Dungeon\nFünf Gegner hintereinander. KP und Tränke werden zwischen den Kämpfen nicht zurückgesetzt. Flucht oder Niederlage beendet den Durchlauf.');info.setWordWrap(True);l.addWidget(info)
        self.progress=QLabel('Wähle deine nächste Expedition.');l.addWidget(self.progress)
        self.plus_info=QLabel('∞ Dungeon+ · Endlose Wellen ab Level 50');self.plus_info.setWordWrap(True);l.addWidget(self.plus_info)
        self.plus_button=QPushButton('🔒 Dungeon+ · Level 50');self.plus_button.clicked.connect(self.plus_requested.emit);l.addWidget(self.plus_button)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);l.addWidget(self.scroll,1)
        self.body=QWidget(self.scroll);self.body_layout=QVBoxLayout(self.body)
        self.body_layout.addStretch();self.scroll.setWidget(self.body)
        self.setStyleSheet('QLabel{color:#d5dfeb;font-size:18px;} QPushButton{padding:12px;background:#244968;color:#ffe0a0;border-radius:8px;font-size:18px;} QPushButton:disabled{background:#14283f;color:#8596aa;}')
        self.update_data(1,{})
    def retranslate(self):
        super().retranslate()
        self.update_data(self.level,self.records,self.plus)

    def update_data(self,level,records,plus=None):
        plus=plus or {}
        self.records,self.plus=records,plus
        self.plus_info.setText(self.ui('∞ Dungeon+ · Endlose Wellen ab Level 50\nRekord: {best} Wellen · Durchläufe: {attempts} · Siege gesamt: {wins}\nMusik 1 → 2 → 3 in Dauerschleife · Flucht oder Niederlage beendet den Lauf.',best=plus.get('best_wave',0),attempts=plus.get('attempts',0),wins=plus.get('total_wins',0)))
        signature=(level,repr(records),self.language)
        if signature==self.signature:return
        self.level=level;self.buttons=[];visible=set()
        for d in catalog(level,records,language=self.language):
            unlocked=level>=d['level'];r=d['record']
            key=d['id'];visible.add(key)
            if key not in self.rows:
                # Own each row for the screen's lifetime. A level/profile update
                # must not rebuild all native buttons (Intel crash report).
                row=QWidget(self.body);layout=QVBoxLayout(row)
                title=QLabel(row);title.setWordWrap(True);layout.addWidget(title)
                info=QLabel(row);info.setWordWrap(True);layout.addWidget(info)
                b=QPushButton(row)
                b.clicked.connect(lambda checked=False,i=key:self.enter_requested.emit(i))
                layout.addWidget(b)
                self.body_layout.insertWidget(self.body_layout.count()-1,row)
                self.rows[key]=(row,title,info,b)
            row,title,info,b=self.rows[key]
            title.setText(f"{'✦' if unlocked else '🔒'} {d['name']} · Level {d['level']}")
            info.setText(self.ui('5 Räume · Abschlüsse: {completed} · Bester Durchlauf: {best}/5',completed=r.get('completed',0),best=r.get('best_room',0)))
            b.setText(self.ui('Dungeon betreten') if unlocked else self.ui('Ab Level {level}',level=d['level']))
            self.buttons.append((b,d['level']))
        for key,(row,*_) in self.rows.items():row.setVisible(key in visible)
        self.set_ready(self.ready)
        self.signature=signature
    def set_ready(self,ready):
        self.ready=ready
        self.plus_button.setEnabled(ready and self.level>=50)
        self.plus_button.setText(self.ui('∞ Dungeon+ betreten' if self.level>=50 else '🔒 Dungeon+ · Level 50'))
        for b,level in self.buttons:b.setEnabled(ready and self.level>=level)
