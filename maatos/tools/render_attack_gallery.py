"""Render standard and attack sprites side by side for review."""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QPainter, QColor, QFont
from PySide6.QtSvg import QSvgRenderer
from build_attack_art import ART, EFFECTS
app=QApplication.instance() or QApplication([])
characters=[('maatis','Maatis'),('wanderer','Wanderer'),('guardian','Wächter'),('beast','Bestie'),('phantom','Phantom'),('watcher','Beobachter'),('idol','Idol'),('construct','Konstrukt'),('spark','Funke'),('pharaoh','Pharao'),('broken_harmony','Gebrochene Harmonie'),('archon','Archon'),('time','Zeitfürst'),('sun','Leere Sonne'),('avatar','Avatar'),('heart','Herz der Schöpfung'),('crown','Krone der Resonanz'),('axis','Achse des Äons'),('light','Licht der MAAT')]
labels=['Standard','Hieb','Klauen','Welle','Blitz','Sand','Balance','Schöpfung','Verbindung','Respekt','Impuls']
width,height=1760,80+len(characters)*190
canvas=QImage(width,height,QImage.Format_ARGB32)
canvas.fill(QColor('#080f23'))
p=QPainter(canvas)
p.setRenderHint(QPainter.Antialiasing)
p.setFont(QFont('Arial',12));p.setPen(QColor('#dec787'))
for col,title in enumerate(labels):p.drawText(QRectF(col*160,10,160,55),Qt.AlignCenter,title)
for row,(key,name) in enumerate(characters):
 for col,kind in enumerate([None]+list(EFFECTS)):
  x,y=col*160,80+row*190
  p.fillRect(x+4,y+4,152,182,QColor('#10203a'))
  path=ART/f'{key}.svg' if kind is None else ART/'attacks'/f'{key}-{kind}.svg'
  QSvgRenderer(str(path)).render(p,QRectF(x+8,y+4,144,144))
  p.setFont(QFont('Arial',9));p.setPen(QColor('#eee5cc'))
  p.drawText(QRectF(x+6,y+150,148,34),Qt.AlignCenter|Qt.TextWordWrap,name)
p.end()
assert canvas.save(sys.argv[1])
