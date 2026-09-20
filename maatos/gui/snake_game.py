"""Keyboard-controlled native Snake challenge, paused when focus is lost."""
from PySide6.QtCore import Qt,QTimer,QRectF,QEvent,Signal
from PySide6.QtGui import QPainter,QColor
from PySide6.QtWidgets import QWidget,QDialog,QVBoxLayout,QLabel,QPushButton
from shared.core.minigames import Snake,engine,CATALOG

class Board(QWidget):
    def __init__(self, dialog):
        super().__init__(dialog)
        self.dialog=dialog
        self.setMinimumSize(400,320)
        self.setFocusPolicy(Qt.StrongFocus)
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#07172e'))
        g=self.dialog.game
        cell=min(self.width()/g.width,self.height()/g.height)
        ox=(self.width()-cell*g.width)/2;oy=(self.height()-cell*g.height)/2
        p.setPen(QColor('#243f5a'))
        for y in range(g.height):
            for x in range(g.width):p.drawRect(QRectF(ox+x*cell,oy+y*cell,cell,cell))
        for x,y in getattr(g,'walls',()):
            p.fillRect(QRectF(ox+x*cell+1,oy+y*cell+1,cell-2,cell-2),QColor('#8b759d'))
        for (x,y),rune in getattr(g,'decoys',{}).items():
            p.setPen(QColor('#ee8da7'));p.drawText(QRectF(ox+x*cell,oy+y*cell,cell,cell),Qt.AlignCenter,rune)
        for i,(x,y) in enumerate(g.body):
            p.fillRect(QRectF(ox+x*cell+2,oy+y*cell+2,cell-4,cell-4),QColor('#ffe0a0' if i==0 else '#65c5b4'))
        x,y=g.food;p.setBrush(QColor('#e3a954'));p.drawEllipse(QRectF(ox+x*cell+3,oy+y*cell+3,cell-6,cell-6))
        if getattr(g,'maat',False):
            p.setPen(QColor('#07172e'));p.drawText(QRectF(ox+x*cell,oy+y*cell,cell,cell),Qt.AlignCenter,'HBSVR'[g.score%5])
        p.end()
    def keyPressEvent(self,event):
        keys={Qt.Key_Left:'L',Qt.Key_A:'L',Qt.Key_Right:'R',Qt.Key_D:'R',Qt.Key_Up:'U',Qt.Key_W:'U',Qt.Key_Down:'D',Qt.Key_S:'D'}
        if event.key() in keys:self.dialog.direction=keys[event.key()];event.accept()
        elif event.key()==Qt.Key_Space:self.dialog.toggle()
        else:super().keyPressEvent(event)
    def focusOutEvent(self,event):
        if not self.dialog.isActiveWindow():self.dialog.pause()
        super().focusOutEvent(event)

class SnakeDialog(QDialog):
    music_running=Signal(bool)
    def __init__(self,seed,parent=None,practice=False,kind="maat_snake"):
        super().__init__(parent)
        self.unit='Runen' if kind=='maat_snake' else 'Früchte'
        self.seed=seed;self.game=engine(kind,seed,practice=practice);self.direction='R';self.winning_moves=None
        self.setWindowTitle(CATALOG[kind][0]);self.resize(620,620)
        self.setStyleSheet('QDialog {background:#0b1c34;color:#e5edf5;} QLabel {color:#e5edf5;font-size:18px;} QPushButton {padding:12px;background:#304c69;color:#ffe0a0;font-size:18px;}')
        l=QVBoxLayout(self)
        title=QLabel(CATALOG[kind][0]+' · '+('ENDLOS' if practice else '15 '+self.unit));l.addWidget(title)
        self.hint=hint=QLabel('Pfeiltasten / WASD · Leertaste: Pause\nWände und eigener Körper sind gefährlich.\nBelohnung: 40 EP + 15 Gold');hint.setWordWrap(True);l.addWidget(hint)
        hint.setText('Pfeiltasten / WASD · Leertaste: Pause\n'+CATALOG[kind][1]+('\nNur die nächste Rune berühren! Andere Runen beenden den Versuch.' if kind=='maat_snake' else '\nWände und eigener Körper sind gefährlich.')+f'\nBelohnung: {CATALOG[kind][2]} EP + {CATALOG[kind][3]} Gold')
        self.board=Board(self);l.addWidget(self.board,1)
        self.status=QLabel('Bereit · Das Tempo steigt mit jedem Fund.');l.addWidget(self.status)
        self.play=QPushButton('Starten');self.play.clicked.connect(self.toggle);l.addWidget(self.play)
        self.back=back=QPushButton('Zurück zum Chat');back.clicked.connect(self.reject);l.addWidget(back)
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick)
    def pause(self):
        self.timer.stop();self.music_running.emit(False)
        if not self.game.over:self.play.setText('Fortsetzen')
    def toggle(self):
        if self.timer.isActive():self.pause();return
        if self.game.over:return
        self.timer.start(max(85,170-self.game.score*5));self.play.setText('Pause');self.board.setFocus();self.music_running.emit(True);self.board.update()
    def tick(self):
        self.game.step(self.direction);self.direction=self.game.direction;self.board.update()
        self.status.setText(f'{self.unit}: {self.game.score}'+(' · Endlos' if self.game.endless else ' / 15'))
        if getattr(self.game,'maat',False):self.status.setText(self.status.text()+' · Nächste Rune: '+'HBSVR'[self.game.score%5])
        if self.game.over:
            self.timer.stop();self.music_running.emit(False)
            if self.game.endless:
                self.status.setText(f'Runde beendet · {self.game.score} {self.unit} · Zurück speichert die Bestleistung.');self.play.hide()
            elif self.game.score==15:
                self.winning_moves=list(self.game.moves);self.accept()
            else:self.status.setText(f'Verloren · {self.game.score}/15 {self.unit}. Dieser Versuch ist beendet.');self.play.hide()
        else:self.timer.setInterval(max(85,170-self.game.score*5))
    def changeEvent(self,event):
        if event.type()==QEvent.ActivationChange and not self.isActiveWindow() and hasattr(self,"timer"):
            self.pause()
        super().changeEvent(event)
    def done(self,result):
        self.timer.stop();self.music_running.emit(False);super().done(result)
