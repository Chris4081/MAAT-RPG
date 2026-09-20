#!/usr/bin/env python3
"""Render authored Qt minigame views with synthetic seeds and no game profile."""
from pathlib import Path
import os
import sys
import json
import hashlib
import tempfile
from collections import deque

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'maatos'
if not GAME.is_dir():
    GAME = ROOT / 'MAAT RPG.app/Contents/Resources/maatos'


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'gui-preview/minigame-review-v2'
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='maat-arcade-render-') as scratch:
        os.environ.update(QT_QPA_PLATFORM='offscreen', MAAT_GUI_DATA_ROOT=scratch,
                          MAAT_APP_SUPPORT_DIR=scratch)
        sys.path.insert(0, str(GAME))
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt, QRectF
        from PySide6.QtGui import QPainter, QColor, QImage
        from gui.game_hall import game_dialog
        from shared.core.minigames import CATALOG
        app = QApplication.instance() or QApplication([])
        frames = []
        for kind in CATALOG:
            dialog = game_dialog(kind, 7)
            dialog.show(); app.processEvents()
            if kind == 'temple_circles':
                # Actual legal moves, two completed seals and one aligned ring.
                def align(index):
                    game = dialog.game
                    right = (game.gate - game.rings[index].index(game.rune)) % 5
                    for _ in range(right if right <= 2 else 5 - right):
                        game.step(str(index) + ('R' if right <= 2 else 'L'))
                for _ in range(2):
                    for index in range(3): align(index)
                    dialog.game.step('seal')
                align(0); dialog.toggle()
                for language in ('de', 'en'):
                    dialog.set_language(language); app.processEvents()
                    dialog.grab().save(str(target / ('temple-circles-' + language + '.png')))
                dialog.set_language('de')
            if kind == 'maat_coil':
                # Reach two shrines with actual engine steps, without advancing Qt timers.
                for destination in dialog.game.shrines[:2]:
                    queue = deque([(dialog.game.body[0], [])]); seen = {dialog.game.body[0]}
                    while queue:
                        cell, moves = queue.popleft()
                        if cell == destination:
                            for action in moves: dialog.game.step(action)
                            break
                        for action, (dx, dy) in {'L':(-1,0),'R':(1,0),'U':(0,-1),'D':(0,1)}.items():
                            nxt = cell[0]+dx, cell[1]+dy
                            if nxt not in seen and dialog.game.inside(nxt):
                                seen.add(nxt); queue.append((nxt,moves+[action]))
                dialog.refresh()
                for language in ('de', 'en'):
                    dialog.set_language(language); app.processEvents()
                    dialog.grab().save(str(target / ('maat-coil-' + language + '.png')))
                dialog.set_language('de')
            image = dialog.grab()
            image.save(str(target / (kind + '.png')))
            frames.append((kind, image))
            dialog.close(); dialog.deleteLater(); app.processEvents()
        for page in range((len(frames)+5)//6):
            canvas = QImage(1440, 1200, QImage.Format_ARGB32)
            canvas.fill(QColor('#06152b')); painter = QPainter(canvas)
            for i,(kind, image) in enumerate(frames[page*6:page*6+6]):
                x,y = i%3*480,i//3*600
                painter.setPen(QColor('#f1d38c')); painter.drawText(x+12,y+24,kind)
                scaled = image.scaled(460,558,Qt.KeepAspectRatio,Qt.SmoothTransformation)
                painter.drawPixmap(x+(480-scaled.width())//2,y+32,scaled)
            painter.end(); canvas.save(str(target / f'overview-{page+1}.png'))
        manifest = {'kind':'synthetic Qt development captures', 'seed':7,
                    'profile_data':False, 'date':'2026-09-20', 'images':[]}
        for path in sorted(target.glob('*.png')):
            manifest['images'].append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(f'Rendered {len(frames)} minigames and DE/EN Star Covenant / Temple Circles.')


if __name__ == '__main__':
    main()
