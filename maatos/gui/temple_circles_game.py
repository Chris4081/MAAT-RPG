"""MAAT Temple Circles: concentric rune rings, mouse and keyboard controls."""
import math

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QEvent, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QRadialGradient
from PySide6.QtWidgets import QDialog, QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton

from shared.core.temple_circles import TempleCircles
from shared.core.minigame_i18n import game_info

COLORS = dict(zip('HBSVR', ('#8cddd0', '#91bff0', '#c9a0ed', '#efbe75', '#ef9eb3')))


def point(radius, sector):
    angle = -math.pi / 2 + sector * math.tau / 5
    return QPointF(math.cos(angle) * radius, math.sin(angle) * radius)


class CircleBoard(QWidget):
    def __init__(self, dialog):
        super().__init__(dialog)
        self.dialog = dialog
        self.setMinimumSize(280, 280)
        self.setFocusPolicy(Qt.StrongFocus)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor('#06152b'))
        scale = min(self.width(), self.height()) / 490
        p.translate(self.width() / 2, self.height() / 2)
        p.scale(scale, scale)
        g = self.dialog.game
        glow = QRadialGradient(QPointF(0, 0), 232)
        glow.setColorAt(0, QColor('#244660'))
        glow.setColorAt(1, QColor('#081c36'))
        p.setBrush(glow); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(0, 0), 232, 232)
        p.setBrush(Qt.NoBrush)
        for sector in range(5):
            active = sector == g.gate
            color = QColor('#f4d48b' if active else '#345673')
            p.setPen(QPen(color, 4 if active else 1, Qt.SolidLine if active else Qt.DashLine))
            p.drawLine(point(38, sector), point(207, sector))
            tip = point(218, sector)
            p.setBrush(QColor('#e8c579') if sector < g.gate or (g.over and g.reason == 'complete') else QColor('#132a43'))
            p.drawEllipse(tip, 11, 11)
        for i, (ring, radius) in enumerate(zip(g.rings, (73, 130, 186))):
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor('#d9bd7d' if i == self.dialog.selected else '#40607f'), 3 if i == self.dialog.selected else 1.5))
            p.drawEllipse(QPointF(0, 0), radius, radius)
            for sector, rune in enumerate(ring):
                pos = point(radius, sector)
                match = sector == g.gate and rune == g.rune
                p.setPen(QPen(QColor(COLORS[rune]), 2.5 if match else 1))
                p.setBrush(QColor('#305956' if match else '#0b223c'))
                p.drawEllipse(pos, 19, 19)
                font = p.font(); font.setPixelSize(22); font.setBold(True); p.setFont(font)
                p.drawText(QRectF(pos.x()-19, pos.y()-19, 38, 38), Qt.AlignCenter, rune)
        p.setPen(QPen(QColor('#ffe1a0'), 2))
        p.setBrush(QColor('#86713a' if g.aligned else '#19374f'))
        p.drawEllipse(QPointF(0, 0), 33, 33)
        font = p.font(); font.setPixelSize(29); p.setFont(font)
        p.drawText(QRectF(-30, -30, 60, 60), Qt.AlignCenter, g.rune)
        p.end()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_1, Qt.Key_2, Qt.Key_3):
            self.dialog.selected = event.key() - Qt.Key_1
            self.dialog.refresh()
        elif event.key() in (Qt.Key_Left, Qt.Key_A, Qt.Key_Right, Qt.Key_D):
            direction = 'L' if event.key() in (Qt.Key_Left, Qt.Key_A) else 'R'
            self.dialog.act(str(self.dialog.selected) + direction)
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.dialog.act('seal')
        elif event.key() == Qt.Key_Space:
            self.dialog.toggle()
        else:
            super().keyPressEvent(event)


class TempleCirclesDialog(QDialog):
    music_running = Signal(bool)

    def __init__(self, seed, parent=None, practice=False, language='de'):
        super().__init__(parent)
        self.game = TempleCircles(seed)
        self.game.endless = bool(practice)
        self.language = language
        self.selected = 0
        self.winning_moves = None
        self.resize(780, 850)
        self.setStyleSheet('QDialog {background:#06152b;} QLabel {color:#d6e4f0;font-size:16px;} '
                          'QPushButton {background:#173954;color:#f5dda0;border:1px solid #4e7089;'
                          'border-radius:8px;padding:9px;font-size:16px;} '
                          'QPushButton:disabled {color:#8192a5;border-color:#283c52;}')
        layout = QVBoxLayout(self)
        self.title = QLabel(); self.title.setWordWrap(True)
        self.title.setStyleSheet('color:#f1d38c;font-size:27px;font-weight:600;')
        layout.addWidget(self.title)
        self.hint = QLabel(); self.hint.setWordWrap(True); layout.addWidget(self.hint)
        self.stats = QLabel(); self.stats.setWordWrap(True); layout.addWidget(self.stats)
        self.board = CircleBoard(self); layout.addWidget(self.board, 1)
        self.status = QLabel(); self.status.setWordWrap(True); layout.addWidget(self.status)
        controls = QGridLayout(); self.ring_labels = []; self.turn_buttons = []
        for i in range(3):
            label = QLabel(); label.setAlignment(Qt.AlignCenter); self.ring_labels.append(label)
            controls.addWidget(label, 0, i * 2, 1, 2)
            for j, (direction, symbol) in enumerate((('L', '↶'), ('R', '↷'))):
                button = QPushButton(symbol); button.setAutoDefault(False)
                button.clicked.connect(lambda checked=False, a=str(i)+direction: self.act(a))
                self.turn_buttons.append(button); controls.addWidget(button, 1, i*2+j)
        self.seal = QPushButton(); self.seal.setAutoDefault(False)
        self.seal.clicked.connect(lambda: self.act('seal')); controls.addWidget(self.seal, 2, 0, 1, 6)
        layout.addLayout(controls)
        self.play = QPushButton(); self.play.setAutoDefault(False); self.play.clicked.connect(self.toggle)
        self.back = QPushButton(); self.back.setAutoDefault(False); self.back.clicked.connect(self.reject)
        controls.addWidget(self.play, 3, 0, 1, 3); controls.addWidget(self.back, 3, 3, 1, 3)
        # The lifecycle timer makes pause/music compatible with embedded minigames.
        # It never spends a turn: only a deliberate player action changes the puzzle.
        self.timer = QTimer(self); self.timer.setInterval(250); self.timer.timeout.connect(self.tick)
        self.set_language(language)

    def text(self, de, en):
        return en if self.language == 'en' else de

    def set_language(self, language):
        self.language = language
        name, goal, xp, gold = game_info('temple_circles', language)
        self.title.setText(name); self.setWindowTitle(name)
        self.hint.setText(self.text(
            'Drehe die drei Ringe: Auf dem goldenen Strahl muss überall die Zielrune stehen. Dann das Siegel aktivieren. Jede Drehung und Aktivierung kostet einen Zug.\n1 / 2 / 3: Ring wählen · ← →: drehen · Enter: aktivieren · Leertaste: Pause',
            'Rotate the three rings until the target rune fills the golden ray, then activate the seal. Each rotation and activation costs one move.\n1 / 2 / 3: select ring · ← →: rotate · Enter: activate · Space: pause') + '\n' +
            (self.text('Spielhalle · Endlos · ohne EP/Gold', 'Arcade · Endless · no XP/gold') if self.game.endless
             else goal + self.text(f' · {xp} EP + {gold} Gold', f' · {xp} XP + {gold} gold')))
        for i, label in enumerate(self.ring_labels):
            label.setText(self.text(('1 · Innen', '2 · Mitte', '3 · Außen')[i], ('1 · Inner', '2 · Middle', '3 · Outer')[i]))
        for i, button in enumerate(self.turn_buttons):
            button.setText(self.text('← Links', '← Left') if i % 2 == 0 else self.text('Rechts →', 'Right →'))
        self.back.setText(self.text('Zurück zur Spielhalle', 'Back to arcade') if self.game.endless else self.text('Zurück zum Chat', 'Back to chat'))
        self.seal.setText(self.text('✦ Siegel aktivieren', '✦ Activate seal'))
        self.refresh()

    def refresh(self):
        g = self.game
        goal = '∞' if g.endless else str(g.target)
        self.stats.setText(self.text(
            f'Tempelsiegel {g.score}/{goal} · Ziel {g.rune} · Züge {g.remaining}/{g.budget} · Fokus {g.focus}/3',
            f'Temple seals {g.score}/{goal} · Target {g.rune} · Moves {g.remaining}/{g.budget} · Focus {g.focus}/3'))
        if g.over:
            message = self.text('Die Tempelkreise sind vereint!', 'The temple circles are united!') if g.reason == 'complete' else self.text('Fokus aufgebraucht. Dieser Versuch ist beendet.', 'Focus depleted. This attempt has ended.')
            self.play.hide()
        elif g.reason == 'alignment':
            message = self.text('Die Runen passten nicht zusammen: −1 Fokus. Neuer Versuch am selben Siegel.', 'The runes did not match: −1 focus. Try a new pattern for this seal.')
        elif g.reason == 'moves':
            message = self.text('Züge aufgebraucht: −1 Fokus. Plane auch einen Zug zum Aktivieren ein.', 'No moves left: −1 focus. Save one move to activate the seal.')
        elif not self.timer.isActive():
            message = self.text('Pausiert · Ohne Zeitdruck: Plane deine Drehungen.', 'Paused · No time limit: plan your rotations.')
        elif g.aligned:
            message = self.text('Die Verbindung leuchtet. Aktiviere das Siegel!', 'The connection is lit. Activate the seal!')
        else:
            message = self.text('Bringe die Zielrune auf allen drei Ringen zum goldenen Strahl.', 'Bring the target rune onto the golden ray on all three rings.')
        self.status.setText(message)
        self.play.setText(self.text('Pause', 'Pause') if self.timer.isActive() else self.text('Starten / Fortsetzen', 'Start / Resume'))
        for button in (*self.turn_buttons, self.seal):
            button.setEnabled(self.timer.isActive() and not g.over)
        self.board.update()

    def act(self, action):
        if not self.timer.isActive() or self.game.over:
            return
        if action != 'seal':
            self.selected = int(action[0])
        self.game.step(action)
        self.tick(); self.board.setFocus()

    def tick(self):
        if self.game.over:
            self.timer.stop(); self.music_running.emit(False)
            if self.game.reason == 'complete':
                self.winning_moves = list(self.game.moves)
        self.refresh()

    def pause(self):
        self.timer.stop(); self.music_running.emit(False); self.refresh()

    def toggle(self):
        if self.game.over:
            return
        if self.timer.isActive():
            self.pause()
        else:
            self.timer.start(); self.music_running.emit(True); self.board.setFocus(); self.refresh()

    def changeEvent(self, event):
        if event.type() == QEvent.ActivationChange and not self.isActiveWindow() and hasattr(self, 'timer'):
            self.pause()
        super().changeEvent(event)

    def done(self, result):
        self.timer.stop(); self.music_running.emit(False)
        super().done(result)
