"""Native circular sanctuary for MAAT-Snake: Star Covenant."""
import math

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QEvent, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath, QRadialGradient, QPolygonF
from PySide6.QtWidgets import QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar

from shared.core.maat_coil import StarCoil
from shared.core.minigame_i18n import game_info

COLORS = ('#8cddd0', '#91bff0', '#c9a0ed', '#efbe75', '#ef9eb3')


class CovenantBoard(QWidget):
    def __init__(self, dialog):
        super().__init__(dialog)
        self.dialog = dialog
        self.setMinimumSize(280, 280)
        self.setFocusPolicy(Qt.StrongFocus)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor('#06152b'))
        g = self.dialog.game
        side = min(self.width(), self.height()) - 20
        scale = side / 17
        p.translate((self.width() - side) / 2, (self.height() - side) / 2)
        p.scale(scale, scale)
        center = QPointF(8.5, 8.5)
        glow = QRadialGradient(center, 8.2)
        glow.setColorAt(0, QColor('#24455b'))
        glow.setColorAt(1, QColor('#081b34'))
        p.setBrush(glow)
        p.setPen(QPen(QColor('#57718e'), .045))
        p.drawEllipse(center, 7.9, 7.9)
        p.setBrush(Qt.NoBrush)
        for radius in (2.1, 4.5, 7.2):
            p.setPen(QPen(QColor('#284860'), .025))
            p.drawEllipse(center, radius, radius)
        # Star chart rather than a rectangular cell grid.
        for i in range(72):
            angle = i * 2.399963
            radius = 2.5 + (i * 37 % 100) / 20
            p.setPen(QPen(QColor('#6d8caa'), .045))
            p.drawPoint(QPointF(8.5 + math.cos(angle) * radius,
                               8.5 + math.sin(angle) * radius))
        if g.warning:
            color = QColor('#e7748e' if g.dangerous else '#e2b66c')
            color.setAlpha(140 if g.dangerous else 65)
            p.setBrush(color)
            p.setPen(Qt.NoPen)
            for y in range(17):
                for x in range(17):
                    if g.inside((x, y)) and g.in_rift((x, y)):
                        p.drawRoundedRect(QRectF(x + .06, y + .06, .88, .88), .15, .15)
        points = [QPointF(x + .5, y + .5) for x, y in g.shrines]
        p.setPen(QPen(QColor('#587085'), .035, Qt.DashLine))
        p.drawPolygon(QPolygonF(points))
        for i, point in enumerate(points):
            lit = i in g.charged
            color = QColor(COLORS[i])
            p.setPen(QPen(color, .07 if lit else .035))
            p.drawLine(center, point)
            p.setBrush(QColor('#244b59') if lit else QColor('#0c2039'))
            p.drawEllipse(point, .69 if lit else .6, .69 if lit else .6)
            font = p.font(); font.setPixelSize(1); font.setBold(True); p.setFont(font)
            p.setPen(color)
            p.drawText(QRectF(point.x() - .6, point.y() - .6, 1.2, 1.2), Qt.AlignCenter, 'HBSVR'[i])
        ready = len(g.charged) == 5
        p.setPen(QPen(QColor('#ffe1a0' if ready else '#8f9fa7'), .065))
        p.setBrush(QColor('#806332' if ready else '#15324a'))
        p.drawEllipse(center, .8, .8)
        p.setPen(QColor('#fff0be'))
        p.drawText(QRectF(7.7, 7.7, 1.6, 1.6), Qt.AlignCenter, '✦')
        # Fixed translucent ribbon: crossing it is allowed and never lethal.
        trail = QPainterPath()
        tail = g.body[-1]
        trail.moveTo(tail[0] + .5, tail[1] + .5)
        for x, y in reversed(g.body[:-1]):
            trail.lineTo(x + .5, y + .5)
        p.setBrush(Qt.NoBrush)
        for width, color in ((.72, '#234c66'), (.34, '#84d6d1')):
            p.setPen(QPen(QColor(color), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(trail)
        x, y = g.body[0]; x += .5; y += .5
        p.setPen(QPen(QColor('#fff4ce'), .08))
        p.setBrush(QColor('#f49eaa' if g.invulnerable else '#efd17d'))
        p.drawPolygon(QPolygonF([QPointF(x, y - .44), QPointF(x + .37, y),
                                QPointF(x, y + .44), QPointF(x - .37, y)]))
        p.end()

    def keyPressEvent(self, event):
        directions = {Qt.Key_Left: 'L', Qt.Key_A: 'L', Qt.Key_Right: 'R', Qt.Key_D: 'R',
                      Qt.Key_Up: 'U', Qt.Key_W: 'U', Qt.Key_Down: 'D', Qt.Key_S: 'D'}
        if event.key() in directions:
            self.dialog.direction = directions[event.key()]
            event.accept()
        elif event.key() == Qt.Key_Space:
            self.dialog.toggle()
        else:
            super().keyPressEvent(event)


class StarCoilDialog(QDialog):
    music_running = Signal(bool)

    def __init__(self, seed, parent=None, practice=False, language='de'):
        super().__init__(parent)
        self.language = language
        self.game = StarCoil(seed)
        self.game.endless = bool(practice)
        self.direction = self.game.direction
        self.winning_moves = None
        self.resize(780, 820)
        self.setStyleSheet('QDialog {background:#06152b;} QLabel {color:#d6e4f0;font-size:17px;} '
                          'QPushButton {background:#173954;color:#f5dda0;border:1px solid #4e7089;'
                          'border-radius:8px;padding:11px;font-size:17px;} '
                          'QProgressBar {background:#112f48;border:0;border-radius:4px;height:8px;} '
                          'QProgressBar::chunk {background:#87cfc9;border-radius:4px;}')
        layout = QVBoxLayout(self)
        self.title = QLabel(); self.title.setWordWrap(True)
        self.title.setStyleSheet('color:#f1d38c;font-size:27px;font-weight:600;')
        layout.addWidget(self.title)
        self.hint = QLabel(); self.hint.setWordWrap(True); layout.addWidget(self.hint)
        self.stats = QLabel(); self.stats.setWordWrap(True); layout.addWidget(self.stats)
        self.clock_bar = QProgressBar(); self.clock_bar.setTextVisible(False); layout.addWidget(self.clock_bar)
        self.board = CovenantBoard(self); layout.addWidget(self.board, 1)
        self.status = QLabel(); self.status.setWordWrap(True); layout.addWidget(self.status)
        row = QHBoxLayout()
        self.play = QPushButton(); self.play.setAutoDefault(False); self.play.clicked.connect(self.toggle)
        self.back = QPushButton(); self.back.setAutoDefault(False); self.back.clicked.connect(self.reject)
        row.addWidget(self.play); row.addWidget(self.back); layout.addLayout(row)
        self.timer = QTimer(self); self.timer.timeout.connect(self.tick)
        self.set_language(language)

    def text(self, de, en):
        return en if self.language == 'en' else de

    def set_language(self, language):
        self.language = language
        name, goal, xp, gold = game_info('maat_coil', language)
        self.setWindowTitle(name)
        self.title.setText(name)
        self.hint.setText(self.text(
            'Pfeiltasten / WASD · Leertaste: Pause\nAktiviere H, B, S, V und R in beliebiger Reihenfolge. Kehre zum goldenen Mittelpunkt zurück. Deine Lichtspur darfst du kreuzen.',
            'Arrows / WASD · Space: pause\nActivate H, B, S, V and R in any order, then return to the golden center. You may cross your own light trail.') + '\n' +
            (self.text('Spielhalle · Endlos · ohne EP/Gold', 'Arcade · Endless · no XP/gold') if self.game.endless else
             goal + self.text(f' · {xp} EP + {gold} Gold', f' · {xp} XP + {gold} gold')))
        self.back.setText(self.text('Zurück zur Spielhalle', 'Back to arcade') if self.game.endless else self.text('Zurück zum Chat', 'Back to chat'))
        self.refresh()

    def refresh(self):
        g = self.game
        goal = '∞' if g.endless else str(g.target)
        self.stats.setText(self.text(
            f'Bünde {g.score}/{goal}   ·   Schreine {len(g.charged)}/5   ·   Schild {g.shields}/3',
            f'Covenants {g.score}/{goal}   ·   Shrines {len(g.charged)}/5   ·   Shield {g.shields}/3'))
        self.clock_bar.setRange(0, max(100, g.round_budget - g.score * 5))
        self.clock_bar.setValue(g.remaining)
        if g.over:
            self.play.hide()
            message = self.text('Sternenbund vollendet!', 'Star Covenant complete!') if g.reason == 'complete' else self.text('Der Schild ist erloschen. Dieser Versuch ist beendet.', 'The shield has faded. This attempt has ended.')
        elif not self.timer.isActive():
            message = (self.text('Pausiert · Knüpfe weitere Bünde; die Schreine schützen vor Dissonanzwellen.',
                                 'Paused · Complete more covenants; shrines shelter you from dissonance waves.')
                       if g.endless else self.text('Pausiert · Drei Bünde schaffen; die Schreine schützen vor Dissonanzwellen.',
                                                   'Paused · Complete three covenants; shrines shelter you from dissonance waves.'))
        elif g.dangerous:
            message = self.text('Dissonanzwelle! Meide die roten Felder.', 'Dissonance wave! Avoid the red tiles.')
        elif g.warning:
            message = self.text('Goldene Spur: Hier erscheint gleich eine Dissonanzwelle.', 'Golden trail: a dissonance wave will strike here soon.')
        elif len(g.charged) == 5:
            message = self.text('Alle fünf leuchten! Zurück zum Mittelpunkt.', 'All five are lit! Return to the center.')
        else:
            message = self.text('Besuche die unbeleuchteten Schreine. Der Zeitbalken gilt für diesen Bund.', 'Visit the unlit shrines. The time bar applies to this covenant.')
        self.status.setText(message)
        self.play.setText(self.text('Pause', 'Pause') if self.timer.isActive() else self.text('Starten / Fortsetzen', 'Start / Resume'))
        self.board.update()

    def pause(self):
        self.timer.stop(); self.music_running.emit(False); self.refresh()

    def toggle(self):
        if self.game.over:
            return
        if self.timer.isActive():
            self.pause(); return
        self.timer.start(max(90, 175 - self.game.score * 5))
        self.board.setFocus(); self.music_running.emit(True); self.refresh()

    def tick(self):
        self.game.step(self.direction)
        if self.game.over:
            self.timer.stop(); self.music_running.emit(False)
            if self.game.score >= self.game.target:
                self.winning_moves = list(self.game.moves)
        else:
            self.timer.setInterval(max(90, 175 - self.game.score * 5))
        self.refresh()

    def changeEvent(self, event):
        if event.type() == QEvent.ActivationChange and not self.isActiveWindow() and hasattr(self, 'timer'):
            self.pause()
        super().changeEvent(event)

    def done(self, result):
        self.timer.stop(); self.music_running.emit(False)
        super().done(result)
