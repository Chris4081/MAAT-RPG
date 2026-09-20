"""Profile discoveries displayed as an arcade collection."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QWidget,QVBoxLayout,QGridLayout,QLabel,QPushButton,QScrollArea
from shared.core.minigames import CATALOG, SNAKE_GAMES
from shared.core.minigame_i18n import game_info
from gui.ui_i18n import LocalizedUI

def game_dialog(kind,seed,parent=None,practice=False,language='de'):
    if kind not in CATALOG:
        raise ValueError('Unknown minigame')
    if kind=='temple_circles':
        from gui.temple_circles_game import TempleCirclesDialog
        return TempleCirclesDialog(seed,parent,practice=practice,language=language)
    if kind=='maat_coil':
        from gui.maat_coil_game import StarCoilDialog
        return StarCoilDialog(seed,parent,practice=practice,language=language)
    if kind in SNAKE_GAMES:
        from gui.snake_game import SnakeDialog
        return SnakeDialog(seed,parent,practice=practice,kind=kind)
    if kind=='breakout':
        from gui.arcade_game import ArcadeDialog
        return ArcadeDialog(kind,seed,parent,practice=practice)
    from gui.temple_games import TempleDialog
    return TempleDialog(kind,seed,parent,practice=practice)

class GameHall(LocalizedUI, QWidget):
    def __init__(self,discovered,play,parent=None):
        super().__init__(parent);self.setObjectName('gameHall');self._ready=True;self.discovered=set(discovered)
        self.setStyleSheet('QWidget#gameHall {background:#06162d;} QScrollArea {background:#06162d;border:none;} QWidget#hallBody {background:#06162d;} QLabel {color:#cbd9e9;font-size:16px;} QPushButton {background:#244b68;color:#ffe1a1;border-radius:8px;padding:12px;font-size:18px;} QPushButton:disabled {background:#16283c;color:#7f8b9b;} QWidget#gameCard {background:#102943;border:1px solid #345374;border-radius:12px;}')
        l=QVBoxLayout(self);self.title=title=QLabel('✦ DIE SPIELHALLE ✦');title.setStyleSheet('font-size:32px;color:#ebc578');l.addWidget(title)
        self.summary=summary=QLabel(f'{len(set(discovered)&set(CATALOG))} / {len(CATALOG)} Spiele entdeckt\nFinde Spiele zufällig im Chat, um sie hier dauerhaft freizuschalten.\nFreies Spielen zählt für Erfolge, ohne EP/Gold. Belohnungen gibt es bei Chat-Herausforderungen.');summary.setWordWrap(True);l.addWidget(summary)
        scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();body.setObjectName('hallBody');grid=QGridLayout(body);self.buttons={};self.records={};self.names={};self.goals={};self.highscores={}
        for i,(kind,(name,goal,xp,gold)) in enumerate(CATALOG.items()):
            card=QWidget();card.setObjectName('gameCard');cl=QVBoxLayout(card)
            label=QLabel(name);label.setWordWrap(True);cl.addWidget(label);self.names[kind]=label
            from shared.core.arcade_scores import ENDLESS,record_text
            detail=QLabel('Endlos · spiele bis zur Niederlage oder bis du zurückkehrst.' if kind in ENDLESS else goal);detail.setWordWrap(True);cl.addWidget(detail);self.goals[kind]=detail
            record=QLabel(record_text(kind,None));record.setWordWrap(True);record.setStyleSheet('color:#e7cb88;font-size:15px');cl.addWidget(record);self.records[kind]=record
            b=QPushButton('Spielen' if kind in discovered else '🔒 Noch nicht entdeckt');b.setEnabled(kind in discovered)
            b.clicked.connect(lambda checked=False,k=kind:play(k,self));cl.addWidget(b);self.buttons[kind]=b
            grid.addWidget(card,i//2,i%2)
        scroll.setWidget(body);l.addWidget(scroll,1)
    def update_discoveries(self,discovered,highscores=None):
        self.discovered=set(discovered)&set(CATALOG)
        self.highscores=highscores or {}
        self.retranslate()

    def retranslate(self):
        self.title.setText(self.ui('✦ DIE SPIELHALLE ✦'))
        self.summary.setText(self.ui('{count} / {total} Spiele entdeckt\nFinde Spiele zufällig im Chat, um sie hier dauerhaft freizuschalten.\nFreies Spielen zählt für Erfolge, ohne EP/Gold. Belohnungen gibt es bei Chat-Herausforderungen.',count=len(self.discovered),total=len(CATALOG)))
        from shared.core.arcade_scores import ENDLESS,record_text
        for kind,label in self.records.items():
            name,goal,_,_=game_info(kind,self.language)
            self.names[kind].setText(name)
            self.goals[kind].setText(self.ui('Endlos · spiele bis zur Niederlage oder bis du zurückkehrst.') if kind in ENDLESS else goal)
            label.setText(record_text(kind,self.highscores.get(kind),self.language))
        self.set_ready(self._ready)

    def set_ready(self,ready):
        self._ready=ready
        for kind,b in self.buttons.items():
            b.setText(self.ui('Spielen' if kind in self.discovered else '🔒 Noch nicht entdeckt'))
            b.setEnabled(ready and kind in self.discovered)
