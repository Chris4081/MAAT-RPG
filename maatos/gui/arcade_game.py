"""Native Seal Breaker challenge."""
from PySide6.QtCore import Qt,QTimer,QRectF,QEvent,Signal
from PySide6.QtGui import QPainter,QColor
from PySide6.QtWidgets import QWidget,QDialog,QVBoxLayout,QLabel,QPushButton
from shared.core.minigames import engine,CATALOG
COLORS=['#82bde5','#e5c476','#c098df','#73c7aa','#e79299','#92a4df','#ecb286']

class ArcadeBoard(QWidget):
    def __init__(self,dialog):
        super().__init__(dialog);self.dialog=dialog;self.setMinimumSize(300,360);self.setFocusPolicy(Qt.StrongFocus)
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#07172e'));g=self.dialog.game
        scale=min(self.width()/480,self.height()/480);p.translate((self.width()-480*scale)/2,(self.height()-480*scale)/2);p.scale(scale,scale)
        for x,y in g.bricks:p.fillRect(QRectF(12+x*58,45+y*24,52,18),QColor(COLORS[y]))
        p.fillRect(QRectF(g.paddle-40,440,80,12),QColor('#82d9c4'))
        p.setBrush(QColor('#ffe3a0'));p.drawEllipse(QRectF(g.x-6,g.y-6,12,12))
        p.end()
    def keyPressEvent(self,event):
        if event.key()==Qt.Key_Space:self.dialog.toggle();return
        key={Qt.Key_Left:'L',Qt.Key_A:'L',Qt.Key_Right:'R',Qt.Key_D:'R',Qt.Key_Up:'U',Qt.Key_W:'U',Qt.Key_Down:'D',Qt.Key_S:'D',Qt.Key_Return:'X',Qt.Key_Enter:'X'}.get(event.key())
        if key and key in self.dialog.game.actions:
            self.dialog.held=key
        else:super().keyPressEvent(event)
    def keyReleaseEvent(self,event):
        if not event.isAutoRepeat() and self.dialog.kind=='breakout' and event.key() in (Qt.Key_Left,Qt.Key_Right,Qt.Key_A,Qt.Key_D):self.dialog.held='.'
        super().keyReleaseEvent(event)

class ArcadeDialog(QDialog):
    music_running=Signal(bool)
    def __init__(self,kind,seed,parent=None,practice=False):
        if kind!='breakout':raise ValueError('ArcadeDialog supports Seal Breaker only')
        super().__init__(parent);self.kind=kind;self.seed=seed;self.game=engine(kind,seed,practice=practice);self.winning_moves=None;self.held='.';self.queue=[]
        name,goal,xp,gold=CATALOG[kind]
        if practice:goal='Endlos · Neue Siegelwellen'
        self.setWindowTitle(name);self.resize(580,740)
        self.setStyleSheet('QDialog {background:#0b1c34;} QLabel {color:#e5edf5;font-size:18px;} QPushButton {padding:12px;background:#304c69;color:#ffe0a0;font-size:18px;}')
        l=QVBoxLayout(self);l.addWidget(QLabel(name.upper()))
        keys='← → / A D: Schläger bewegen'
        self.hint=hint=QLabel(f'{goal} · {xp} EP + {gold} Gold\n{keys}\nLeertaste: Pause');hint.setWordWrap(True);l.addWidget(hint)
        self.board=ArcadeBoard(self);l.addWidget(self.board,1)
        self.status=QLabel('Bereit. Die Herausforderung wartet.');l.addWidget(self.status)
        self.play=QPushButton('Starten');self.play.clicked.connect(self.toggle);l.addWidget(self.play)
        self.back=back=QPushButton('Zurück zum Chat');back.clicked.connect(self.reject);l.addWidget(back)
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick)
    def pause(self):
        self.timer.stop();self.held='.';self.queue=[];self.music_running.emit(False)
        if not self.game.over:self.play.setText('Fortsetzen')
    def toggle(self):
        if self.timer.isActive():self.pause();return
        if self.game.over:return
        self.held='.';self.queue=[];self.timer.start(16)
        self.play.setText('Pause');self.board.setFocus();self.music_running.emit(True);self.board.update()
    def tick(self):
        action=self.held
        self.game.step(action);self.board.update()
        suffix=f' · Leben: {self.game.lives}'
        self.status.setText(f'Punkte: {self.game.score}'+(' · Endlos' if self.game.endless else f'/{self.game.target}')+suffix)
        if self.game.over:
            self.timer.stop();self.music_running.emit(False)
            if self.game.endless:self.status.setText(f'Runde beendet · {self.game.score} Punkte · Zurück speichert die Bestleistung.');self.play.hide()
            elif self.game.score>=self.game.target:self.winning_moves=list(self.game.moves);self.accept()
            else:self.status.setText('Dieser Versuch ist beendet. Zurück zum Chat.');self.play.hide()
    def changeEvent(self,event):
        if event.type()==QEvent.ActivationChange and not self.isActiveWindow() and hasattr(self,'timer'):self.pause()
        super().changeEvent(event)
    def done(self,result):
        self.timer.stop();self.music_running.emit(False);super().done(result)
