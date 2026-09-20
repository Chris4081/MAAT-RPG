"""Small, bounded vector animations for Maatis; no gameplay state is changed here."""
import math
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QPointF, QElapsedTimer
from PySide6.QtGui import QColor, QPen, QRadialGradient, QPainterPath
from PySide6.QtSvg import QSvgRenderer

SUPPORT = {'focus', 'heal'}
COLORS = {'wave':'#72dfba', 'balance':'#79bdff', 'creation':'#e8aeff',
          'connection':'#ffcd7d', 'respect':'#ff9fae', 'spark':'#bdeefa',
          'impulse':'#ffe5a1', 'focus':'#93d6ff', 'heal':'#72dfba',
          'guard':'#bdeefa', 'hurt':'#ff8299', 'tired':'#edab81'}


class MaatisPresence:
    def __init__(self, owner):
        art = Path(__file__).with_name('assets') / 'combat/maatis'
        self.poses = {name: QSvgRenderer(str(art / f'{name}.svg'), owner)
                      for name in ('ready', 'blink', 'hurt', 'guard', 'focus', 'heal', 'victory', 'tired')}
        self.victory_clock = QElapsedTimer()
        self.reset()

    def reset(self):
        self.hp_fraction = 1.
        self.resonance = 0
        self.victory = False
        self.victory_clock.invalidate()

    def set_victory(self, won):
        if won != self.victory:
            self.victory_clock.invalidate()
        self.victory = won

    def pose(self, seconds, effect, hit_target, hit_damage):
        if effect:
            if effect.get('attacker') == 'player':
                return ''  # The current attack/support sprite owns this pose.
            if hit_target == 'player':
                return 'hurt' if hit_damage > 0 else 'guard'
        if self.victory:
            return 'victory'
        if self.hp_fraction <= .25:
            return 'tired'
        if self.resonance >= 100:
            return 'charged'
        # Blink frames are separate full-body illustrations, not aligned eyelids:
        # swapping them briefly changes face/body shape and even class accessories.
        # Keep the original portrait here; breathing/sway are drawn by CombatStage.
        cycle = seconds % 6.7
        return 'ready' if 1.8 < cycle < 3.4 else ''

    @staticmethod
    def aligned_bounds(portrait_rect, top, foot):
        """Register old 240-unit effects to the current class's visible body.

        The original robot spans y=20..225; its feet and the PNG feet share
        one anchor. Scaling to the body also keeps rings clear of the HP bar.
        """
        height = portrait_rect.height() * (foot-top) * 240/205
        baseline = portrait_rect.top() + portrait_rect.height()*foot
        return QRectF(portrait_rect.center().x()-height/2,
                      baseline-height*225/240, height, height)

    def paint(self, painter, rect, seconds, kind='', progress=0., front=False):
        """Paint in the robot's 240-unit coordinates, underneath/over its SVG."""
        painter.save()
        painter.translate(rect.x(), rect.y())
        painter.scale(rect.width()/240, rect.height()/240)
        if not kind and self.victory:
            kind = 'victory'
        if kind == 'victory' and not self.victory_clock.isValid():
            # Begin the burst when the winning pose is visible, after queued attacks.
            self.victory_clock.start()
        charged = self.resonance >= 100
        color = QColor(COLORS.get(kind, '#e8c576'))
        pulse = .5 + .5*math.sin(seconds*3.2)
        strength = math.sin(math.pi * min(1., max(0., progress)))
        if not front:
            # Soft energy silhouette; capped particle counts also suit CPU-only systems.
            if kind or charged:
                aura = QRadialGradient(QPointF(120, 145), 107)
                tint = QColor(color); tint.setAlpha(round(35 + 30*pulse))
                aura.setColorAt(0, tint); aura.setColorAt(1, QColor(0, 0, 0, 0))
                painter.setPen(Qt.NoPen); painter.setBrush(aura)
                painter.drawEllipse(QPointF(120, 145), 112, 112)
            if kind in {'focus', 'impulse', 'balance', 'victory'} or charged:
                painter.setBrush(Qt.NoBrush)
                for i in range(2):
                    tint = QColor(color); tint.setAlpha(90 if charged else 60)
                    painter.setPen(QPen(tint, 1.4))
                    radius = 75 + i*19 + pulse*3
                    painter.drawArc(QRectF(120-radius, 136-radius, radius*2, radius*2),
                                    int((seconds*35+i*180)*16), 225*16)
        else:
            # The same diamond stays visible, with a gentle inner light.
            core = QRadialGradient(QPointF(120, 150), 27 if not charged else 38)
            tint = QColor(color); tint.setAlpha(round(50 + pulse*(85 if charged else 35)))
            core.setColorAt(0, tint); core.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(core); painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(120, 150), 35, 35)
            if kind in {'focus', 'heal', 'impulse', 'creation', 'connection', 'victory'} or charged:
                celebration = self.victory_clock.elapsed()/1000 if self.victory_clock.isValid() else 0
                # The victory burst subsides, while the happy pose remains.
                opacity = max(0., 1-celebration/3) if kind == 'victory' else 1.
                for i in range(12):
                    phase = (seconds*.45 + i/12) % 1
                    angle = seconds*.65 + i*2.399
                    radius = 62 + (i % 3)*14
                    x = 120 + math.cos(angle)*radius
                    y = 208 - phase*185
                    tint = QColor(color); tint.setAlpha(round(180*math.sin(phase*math.pi)*opacity))
                    painter.setPen(QPen(tint, 1.8))
                    painter.setBrush(tint)
                    if kind == 'heal':
                        painter.drawLine(QPointF(x-3,y), QPointF(x+3,y))
                        painter.drawLine(QPointF(x,y-3), QPointF(x,y+3))
                    else:
                        painter.drawEllipse(QPointF(x,y), 1.5+(i%2), 1.5+(i%2))
            if kind in {'guard', 'respect'}:
                painter.setBrush(QColor(130, 213, 255, 15))
                painter.setPen(QPen(QColor(166, 222, 255, round(90 + strength*100)), 2))
                painter.drawEllipse(QRectF(31, 28, 180, 195))
                painter.drawArc(QRectF(40, 37, 162, 177), -55*16, 100*16)
            elif kind == 'wave':
                painter.setBrush(Qt.NoBrush)
                for i in range(3):
                    tint = QColor(color); tint.setAlpha(round(170*(1-i*.2)))
                    painter.setPen(QPen(tint, 2))
                    painter.drawArc(QRectF(130+i*12+strength*7, 72-i*10, 52, 105+i*20), -65*16, 130*16)
            elif kind in {'slash', 'claw', 'spark', 'creation', 'impulse'}:
                painter.setBrush(Qt.NoBrush); painter.setPen(QPen(color, 2))
                trail = QPainterPath(QPointF(145, 48))
                trail.cubicTo(196, 65, 233, 110, 220-strength*12, 181)
                painter.setOpacity(.25 + strength*.65)
                painter.drawPath(trail)
            elif kind == 'connection':
                painter.setPen(QPen(color, 1.5)); painter.setBrush(color)
                points = [QPointF(185+math.cos(seconds+i*2.1)*30, 125+math.sin(seconds+i*2.1)*47) for i in range(3)]
                for i, point in enumerate(points):
                    painter.drawLine(point, points[(i+1)%3])
                    painter.drawEllipse(point, 3, 3)
        painter.restore()
