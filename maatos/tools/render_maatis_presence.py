"""Render the actual combat widget's Maatis states for visual review, without a model."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QColor, QFont
from gui.battle_arena import CombatStage


class PreviewClock:
    def __init__(self, ms=500): self.ms = ms
    def elapsed(self): return self.ms
    def isValid(self): return True
    def start(self): pass
    def invalidate(self): pass


def render(destination):
    app = QApplication.instance() or QApplication([])
    stage = CombatStage()
    stage.resize(680, 292)
    stage.set_enemy('Schattenwächter')
    stage.sway_clock = PreviewClock(1800)
    stage.effect_clock = PreviewClock(570)
    stage.hit_clock = PreviewClock(380)
    stage.presence.victory_clock = PreviewClock(500)
    scenes = [('Bereit', None), ('Harmonie', 'Harmonie'), ('Balance', 'Balance'),
              ('Schöpfungskraft', 'Schöpfungskraft'), ('Verbundenheit', 'Verbundenheit'),
              ('Respekt', 'Respekt'), ('Fokus', 'focus'), ('Heiltrank', 'heal'),
              ('Treffer', 'hurt'), ('Abwehr', 'guard'), ('MAAT-Impuls', 'impulse'), ('Sieg', 'victory')]
    canvas = QImage(1440, 1156, QImage.Format_ARGB32)
    canvas.fill(QColor('#080f23'))
    paint = QPainter(canvas)
    paint.setPen(QColor('#e8c576')); paint.setFont(QFont('Georgia', 29))
    paint.drawText(QRectF(20, 12, 1400, 57), Qt.AlignCenter, 'MAATIS · Ein kleiner Funke Leben')
    paint.setPen(QColor('#a7bad1')); paint.setFont(QFont('Arial', 13))
    paint.drawText(QRectF(20, 70, 1400, 26), Qt.AlignCenter, 'Neue Posen und Energieeffekte · direkt aus der Kampfansicht')
    for index, (title, action) in enumerate(scenes):
        stage.clear_effects()
        stage.presence.reset()
        if action == 'victory':
            stage.presence.set_victory(True)
        elif action:
            stage.show_effect(dict(attacker='enemy' if action in ('hurt','guard') else 'player',
                                   attack=action, damage=14 if action == 'hurt' else 0 if action in ('guard','focus','heal') else 20,
                                   heal=24 if action == 'heal' else 8))
            stage.effect_frame = 3
            stage.effect_timer.stop(); stage.hit_timer.stop()
            if action not in ('hurt','guard','focus','heal'):
                stage.hit_target = None
        if action == 'impulse': stage.presence.resonance = 100
        image = stage.grab().toImage().copy(0, 0, 340, 292)
        x, y = (index%4)*360+10, 108+(index//4)*344
        paint.drawImage(x, y, image)
        paint.setPen(QColor('#eee5ce')); paint.setFont(QFont('Arial', 17))
        paint.drawText(QRectF(x, y+294, 340, 40), Qt.AlignCenter, title)
    paint.end()
    assert canvas.save(str(destination))
    stage.close()


if __name__ == '__main__':
    render(sys.argv[1])
