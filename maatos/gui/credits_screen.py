"""Cinematic credits roll using the terminal text and bundled artwork."""
import math
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QElapsedTimer,QRectF,Signal
from PySide6.QtGui import QPainter,QPixmap,QColor,QFont,QFontMetrics,QShortcut,QKeySequence
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel

class CreditsCanvas(QWidget):
    def __init__(self):
        super().__init__();self.setMinimumHeight(280);self.offset=0.;self.time=0.;self.lines=[];self.content_height=0
        assets=Path(__file__).parent/'assets'
        self.images=[QPixmap(str(assets/name)) for name in ('story-temple.png','story-reflection.png','intro-awakening.png')]
    def layout_lines(self):
        width=max(180,min(900,self.width()-80));y=0;rows=[]
        for text in self.lines:
            if not text.strip() or text.strip() in ('─','⸻','—'):
                y+=28;continue
            heading=('MAAT-RPG' in text or 'Danksagung' in text or 'Special thanks' in text or text.strip() in ('Ende.', 'The End.'))
            font=QFont('Georgia' if heading else 'Arial');font.setPixelSize(32 if heading else 24)
            height=QFontMetrics(font).boundingRect(0,0,width,10000,Qt.TextWordWrap|Qt.AlignHCenter,text).height()+16
            rows.append((text,font,QRectF((self.width()-width)/2,self.height()+y-self.offset,width,height),heading));y+=height
        self.content_height=y
        return rows
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.fillRect(self.rect(),QColor('#020817'))
        # Slow crossfades and a subtle zoom keep the images alive without distracting.
        phase=self.time/30;index=int(phase)%len(self.images);blend=max(0,(phase%1-.8)/.2)
        for n,opacity in ((index,1.),((index+1)%len(self.images),blend)):
            pix=self.images[n]
            if pix.isNull():continue
            scale=max(self.width()/pix.width(),self.height()/pix.height())*(1.03+.025*math.sin(self.time/20))
            w,h=pix.width()*scale,pix.height()*scale;p.setOpacity(opacity)
            p.drawPixmap(QRectF((self.width()-w)/2,(self.height()-h)/2,w,h),pix,QRectF(pix.rect()))
        p.setOpacity(1);p.fillRect(self.rect(),QColor(1,8,22,205))
        for text,font,rect,heading in self.layout_lines():
            if rect.bottom()<0 or rect.top()>self.height():continue
            fade=min(1,max(0,(self.height()-rect.top())/85),max(0,rect.bottom()/85),self.time/2)
            p.setOpacity(fade);p.setFont(font);p.setPen(QColor('#edce83' if heading else '#f0ece2'))
            p.drawText(rect,Qt.AlignHCenter|Qt.TextWordWrap,text)
        p.setOpacity(1);p.fillRect(QRectF(0,0,self.width(),20),QColor('#020611'));p.fillRect(QRectF(0,self.height()-20,self.width(),20),QColor('#020611'));p.end()

class CreditsScreen(QWidget):
    completed=Signal();audio_requested=Signal(dict)
    def __init__(self):
        super().__init__();self.running=False;self.request_id=None;self.paused=False
        l=QVBoxLayout(self);l.setContentsMargins(0,0,0,0)
        self.canvas=CreditsCanvas();l.addWidget(self.canvas,1)
        row=QHBoxLayout();self.hint=QLabel('ABSPANN · Leertaste: Pause · Esc: Zurück ins Spiel');row.addWidget(self.hint,1)
        self.pause_button=QPushButton('Pause');self.pause_button.clicked.connect(self.toggle_pause);row.addWidget(self.pause_button)
        self.skip_button=QPushButton('Zurück ins Spiel');self.skip_button.clicked.connect(self.finish);row.addWidget(self.skip_button);l.addLayout(row)
        self.timer=QTimer(self);self.timer.setInterval(33);self.timer.timeout.connect(self.tick);self.clock=QElapsedTimer()
        for key,callback in ((Qt.Key_Space,self.toggle_pause),(Qt.Key_Escape,self.finish)):
            shortcut=QShortcut(QKeySequence(key),self);shortcut.setContext(Qt.WidgetWithChildrenShortcut);shortcut.activated.connect(callback)
    def start_scene(self,event):
        self.cancel();self.request_id=event['id'];self.canvas.lines=[str(line) for line in event.get('lines',[])]
        self.language=event.get('language',getattr(self,'language','de'))
        self.canvas.offset=0.;self.canvas.time=0.;self.paused=False;self.pause_button.setText('Pause');self.running=True
        self.translate_controls()
        self.canvas.layout_lines();self.canvas.update();self.clock.start();self.timer.start()
        self.setAccessibleName(event.get('name','MAAT RPG · Abspann'));self.setFocus()
        music=event.get('music')
        if music and Path(music).is_file():self.audio_requested.emit(dict(action='play',owner='credits-screen',path=music,loop=True))
    def tick(self):
        elapsed=min(.15,self.clock.restart()/1000)
        if not self.running or self.paused:return
        self.canvas.time+=elapsed;self.canvas.offset+=elapsed*32;self.canvas.update()
        if self.canvas.offset>self.canvas.height()+self.canvas.content_height+100:self.finish()
    def toggle_pause(self):
        if not self.running:return
        self.paused=not self.paused;self.pause_button.setText('Fortsetzen' if self.paused else 'Pause');self.clock.restart()
        self.translate_controls()
    def translate_controls(self):
        en=getattr(self,'language','de')=='en'
        self.hint.setText('CREDITS · Space: Pause · Esc: Back to game' if en else 'ABSPANN · Leertaste: Pause · Esc: Zurück ins Spiel')
        self.skip_button.setText('Back to game' if en else 'Zurück ins Spiel')
        self.pause_button.setText(('Resume' if en else 'Fortsetzen') if self.paused else 'Pause')
    def finish(self):
        if not self.running:return
        self.cancel();self.completed.emit()
    def cancel(self):
        self.timer.stop()
        if self.running:self.audio_requested.emit(dict(action='stop',owner='credits-screen'))
        self.running=False
