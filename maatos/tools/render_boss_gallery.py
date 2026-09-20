"""Review the actual 25 boss assets and the 20 new normal-attack sprites."""
import os
import sys
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QPen
from PySide6.QtSvg import QSvgRenderer
from shared.core.boss_art import BOSS_ART, BOSS_MOTIFS, BOSS_EFFECTS


def render(output):
    app = QApplication.instance() or QApplication([])
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    first = ['Pharao', 'Gebrochene Harmonie', 'Archon', 'Zeitfürst', 'Leere Sonne']
    art = ROOT/'gui/assets/combat'
    for attacks in (False, True):
        cells = list(BOSS_ART.items())[5:] if attacks else list(BOSS_ART.items())
        columns = 4 if attacks else 5
        cell_w, cell_h = (355, 275) if attacks else (280, 290)
        image = QImage(columns*cell_w+40, 110+5*cell_h, QImage.Format_ARGB32_Premultiplied)
        image.fill(QColor('#061225'))
        p = QPainter(image)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QColor('#e8c576')); p.setFont(QFont('Georgia', 26))
        p.drawText(28, 42, 'MAAT · DIE 25 HÜTER TERRAS' if not attacks else 'MAAT · ÄGYPTISCHE ATTACKEN')
        p.setPen(QColor('#aebfd4')); p.setFont(QFont('Helvetica', 13))
        p.drawText(28, 75, 'Bosse 1–5: bestehende Formen · Bosse 6–25: neue ägyptische Motive' if not attacks else 'Standbild → Angriff · dieselben Figuren und Effekte wie im Spiel')
        for i, (number, key) in enumerate(cells):
            x, y = 20+i%columns*cell_w, 95+i//columns*cell_h
            p.setBrush(QColor('#0c2038'));p.setPen(QPen(QColor('#29455e'), 1))
            p.drawRoundedRect(QRectF(x, y, cell_w-12, cell_h-12), 12, 12)
            if attacks:
                paths = [(art/(key+'.svg'), QRectF(x+8, y+23, 159, 195)),
                         (art/'attacks'/f'{key}-{BOSS_EFFECTS[key]}.svg', QRectF(x+177, y+23, 159, 195))]
            else:
                paths = [(art/(key+'.svg'), QRectF(x+18, y+15, cell_w-48, 217))]
            for path, rect in paths:
                svg = QSvgRenderer(str(path));assert svg.isValid(), path
                svg.render(p, rect)
            p.setPen(QColor('#e8c576'));p.setFont(QFont('Helvetica', 13))
            name = BOSS_MOTIFS[number][0] if number in BOSS_MOTIFS else first[number-1]
            p.drawText(QRectF(x+10, y+cell_h-61, cell_w-32, 45), Qt.AlignCenter|Qt.TextWordWrap, f'{number:02d} · {name}')
        p.end()
        target = output/('attacks.png' if attacks else 'bosses.png')
        assert image.save(str(target))
        print(target)


if __name__ == '__main__':
    render(sys.argv[1])
