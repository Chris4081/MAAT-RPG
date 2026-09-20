"""Render the actual new SVG portraits and default attack assets for review."""
import os
import sys
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QImage,QPainter,QColor,QFont,QPen
from PySide6.QtSvg import QSvgRenderer
from shared.core.monster_catalog import ENEMY_KINDS,KIND_ART,ENEMY_EFFECTS,EFFECT_LABELS

def render(output):
    app=QApplication.instance() or QApplication([])
    canvas=QImage(1500,1770,QImage.Format_ARGB32_Premultiplied);canvas.fill(QColor('#061225'))
    p=QPainter(canvas);p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QColor('#e5c47f'));p.setFont(QFont('Helvetica',26));p.drawText(32,49,'MAAT · DAS BESTIARIUM VON TERRA')
    p.setPen(QColor('#aabbd0'));p.setFont(QFont('Helvetica',13));p.drawText(33,77,'20 ägyptische Gegnerformen · Standbild und Angriff aus den echten Spielgrafiken')
    art=ROOT/'gui/assets/combat'
    for i,kind in enumerate(ENEMY_KINDS):
        x=24+(i%4)*369;y=105+(i//4)*330;key=KIND_ART[kind];effect=ENEMY_EFFECTS.get(key,'slash')
        p.setPen(QPen(QColor('#28435a'),1));p.setBrush(QColor('#0b1e35'));p.drawRoundedRect(QRectF(x,y,345,310),12,12)
        p.setPen(QColor('#e5c47f'));p.setFont(QFont('Helvetica',18));p.drawText(QRectF(x+12,y+12,321,35),Qt.AlignCenter,kind)
        for file,dx in [(key+'.svg',8),(f'attacks/{key}-{effect}.svg',177)]:
            renderer=QSvgRenderer(str(art/file));assert renderer.isValid(),file
            renderer.render(p,QRectF(x+dx,y+53,160,180))
        p.setFont(QFont('Helvetica',11));p.setPen(QColor('#aabbd0'))
        p.drawText(QRectF(x+8,y+242,160,22),Qt.AlignCenter,'Standbild')
        p.drawText(QRectF(x+177,y+242,160,22),Qt.AlignCenter,'Angriff')
        p.setPen(QColor('#86ddd5'));p.setFont(QFont('Helvetica',12))
        p.drawText(QRectF(x+12,y+271,321,22),Qt.AlignCenter,EFFECT_LABELS[effect][0])
    p.end();Path(output).parent.mkdir(parents=True,exist_ok=True);assert canvas.save(str(output))
    print(output)

if __name__=='__main__':render(sys.argv[1])
