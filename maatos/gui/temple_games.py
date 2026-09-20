"""Native puzzle boards and animated wheel for the temple arcade."""
import math
from PySide6.QtCore import Qt, QTimer, Signal, QEvent, QRectF
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtWidgets import QDialog,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QSizePolicy
from shared.core.minigames import engine,CATALOG
from shared.core.maat_games import HINTS

class Wheel(QWidget):
    def __init__(self,dialog):super().__init__(dialog);self.dialog=dialog;self.setMinimumSize(300,300)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        d=min(self.width(),self.height())-24;cx=self.width()/2;cy=self.height()/2;r=d/2
        rect=QRectF(cx-r,cy-r,d,d);g=self.dialog.game
        p.setFont(QFont('Arial',22))
        for i in range(9):
            p.setPen(QColor('#0b1c34'));p.setBrush(QColor('#ecc66d' if g.cells[i]=='★' else '#24476c'))
            p.drawPie(rect,i*40*16,40*16)
            a=math.radians(i*40+20);x=cx+math.cos(a)*r*.72;y=cy-math.sin(a)*r*.72
            p.setPen(QColor('#ffffff'));p.drawText(QRectF(x-20,y-20,40,40),Qt.AlignCenter,g.cells[i])
        a=math.radians(g.cursor*40+20)
        p.setPen(QColor('#ff7a91'));p.drawLine(int(cx),int(cy),int(cx+math.cos(a)*r*.9),int(cy-math.sin(a)*r*.9))
        p.setBrush(QColor('#ff7a91'));p.drawEllipse(QRectF(cx-12,cy-12,24,24));p.end()

class TempleDialog(QDialog):
    music_running=Signal(bool)
    def __init__(self,kind,seed,parent=None,practice=False):
        super().__init__(parent);self.kind=kind;self.game=engine(kind,seed,practice=practice);self.winning_moves=None;self.running=False
        self.setWindowTitle(CATALOG[kind][0]);self.resize(640,720)
        self.setStyleSheet('QDialog {background:#08192f;} QLabel {color:#e6dfca;font-size:18px;} QPushButton {background:#193b5c;color:#e9dfba;border:1px solid #426181;border-radius:8px;padding:8px;font-size:22px;} QPushButton:disabled {color:#6c8199;}')
        layout=QVBoxLayout(self);title=QLabel(CATALOG[kind][0]);title.setStyleSheet('font-size:28px;color:#f0cd7a');layout.addWidget(title)
        extra={**HINTS, 'memory':'Klicke zwei Karten. Das nächste Klicken verdeckt ein falsches Paar.', 'mines':'Zahlen zählen Fallen in den 8 Nachbarfeldern. Der erste Klick ist sicher.', 'lights':'Ein Klick schaltet das Feld und seine direkten Nachbarn um.', 'slide':'Klicke eine Zahl neben dem freien Feld.', 'maze':'Pfeiltasten oder Richtungsknöpfe: ● zum ★ bewegen.', 'sokoban':'Kisten lassen sich schieben, nicht ziehen. Richtungstasten bewegen ●.', 'four':'Klicke eine Spalte. Du spielst ●, der Wächter ◆.', 'three':'Klicke ein freies Feld. Du spielst ●, der Wächter ◆.', 'reflex':'Klicke den Stern! Vier Fehler beenden den Versuch.', 'wheel':'Ein Dreh pro Versuch. 4 von 9 Feldern gewinnen; kein Einsatz.'}[kind]
        hint=QLabel(('Endlos · Sammle Sterne bis zum vierten Fehler' if self.game.endless else CATALOG[kind][1])+'\n'+extra);hint.setWordWrap(True);layout.addWidget(hint)
        self.tiles=[]
        if kind=='wheel':
            self.board=Wheel(self);layout.addWidget(self.board,1)
            self.spin_button=QPushButton('🎡 Rad drehen');self.spin_button.clicked.connect(lambda:self.act('0'));layout.addWidget(self.spin_button)
        else:
            self.board=QWidget();grid=QGridLayout(self.board);grid.setSpacing(4)
            for i in range(len(self.game.cells)):
                b=QPushButton();b.setMinimumSize(28,28);b.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
                b.clicked.connect(lambda checked=False,n=i:self.act(str(n)));grid.addWidget(b,i//self.game.w,i%self.game.w);self.tiles.append(b)
            layout.addWidget(self.board,1)
        if kind in ('maze','sokoban'):
            row=QHBoxLayout()
            for key,label in [('L','←'),('U','↑'),('D','↓'),('R','→')]:
                b=QPushButton(label);b.clicked.connect(lambda checked=False,k=key:self.act(k));row.addWidget(b)
            layout.addLayout(row)
        self.status=QLabel('Bereit');layout.addWidget(self.status)
        self.play=QPushButton('Starten');self.play.clicked.connect(self.toggle);layout.addWidget(self.play)
        self.back=back=QPushButton('Spiel verlassen');back.clicked.connect(self.reject);layout.addWidget(back)
        self.timer=QTimer(self);self.timer.timeout.connect(lambda:self.act('.'))
        if kind in ('maze','sokoban'):
            for b in self.findChildren(QPushButton):b.installEventFilter(self)
        self.refresh()
    def toggle(self):
        if self.game.over:return
        if self.running:self.pause();return
        self.running=True;self.music_running.emit(True);self.play.setText('Pause')
        if self.kind in ('wheel','reflex','maat_echo'):self.timer.start(100)
        self.refresh()
    def pause(self):
        self.running=False;self.timer.stop();self.music_running.emit(False);self.play.setText('Fortsetzen');self.refresh()
    def act(self,action):
        if not self.running or self.game.over:return
        self.game.step(action);self.refresh()
        if self.game.over:
            self.running=False;self.timer.stop();self.music_running.emit(False);self.play.hide()
            if self.game.score>=self.game.target:self.winning_moves=list(self.game.moves)
            self.refresh()
    def refresh(self):
        for i,b in enumerate(self.tiles):
            tile=self.game.tile(i)
            b.setText(tile);b.setEnabled(self.running and not self.game.over and not (self.kind=='maat_echo' and self.game.ticks))
            bg='#193b5c';fg='#e9dfba'
            if tile=='■':bg='#091529';fg='#304863'
            elif tile in ('★','☀','▣'):bg='#765c27';fg='#ffe8a3'
            elif tile=='◆' or tile=='✹':bg='#71324d';fg='#ffd6df'
            elif tile=='●' or (self.kind=='memory' and i in self.game.matched):bg='#21594f';fg='#b6f1dd'
            if self.kind=='maat_creation':
                bg=('#193b5c','#21594f','#765c27')[self.game.cells[i]]
                fg='#b6f1dd' if self.game.cells[i]==self.game.goal[i] else '#ffe8a3'
            elif self.kind=='maat_rings' and self.game.cells[i]==0:bg='#21594f';fg='#b6f1dd'
            b.setStyleSheet(f'background:{bg};color:{fg};')
            # A paused board must not expose the memory sequence or the active target.
            if not self.running and not self.game.over and self.kind in ('memory','reflex'):b.setText('·')
        if self.kind=='wheel':self.spin_button.setEnabled(self.running and not self.game.spinning);self.board.update()
        self.status.setWordWrap(True)
        self.status.setText('Pausiert · Fortsetzen' if self.kind=='maat_echo' and not self.running and not self.game.over else self.game.note or ('Spiel läuft' if self.running else 'Pausiert · Starten/Fortsetzen'))
    def eventFilter(self,watched,event):
        if event.type()==QEvent.KeyPress and event.key() in (Qt.Key_Left,Qt.Key_Right,Qt.Key_Up,Qt.Key_Down,Qt.Key_Space):
            self.keyPressEvent(event);return True
        return super().eventFilter(watched,event)
    def keyPressEvent(self,event):
        key={Qt.Key_Left:'L',Qt.Key_Right:'R',Qt.Key_Up:'U',Qt.Key_Down:'D'}.get(event.key())
        if key and self.kind in ('maze','sokoban'):self.act(key)
        elif event.key()==Qt.Key_Space:self.toggle()
        else:super().keyPressEvent(event)
    def changeEvent(self,event):
        if event.type()==QEvent.ActivationChange and not self.isActiveWindow() and hasattr(self,'timer'):self.pause()
        super().changeEvent(event)
    def done(self,result):
        self.timer.stop();self.running=False;self.music_running.emit(False);super().done(result)
