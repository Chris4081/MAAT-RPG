"""Click-paced original prologue with a local illustration and slow narration."""
from pathlib import Path
import re
from PySide6.QtCore import Qt, QTimer, QElapsedTimer, Signal, QEvent
from PySide6.QtGui import QShortcut, QKeySequence, QTextCursor, QPixmap, QPainter
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QProgressBar
from gui.desktop import label, button
from apps.maat_rpg.plugins.rpg_intro.plugin_main import INTRO_TEXT


class IntroArtwork(QWidget):
    def __init__(self):
        super().__init__()
        self.pixmap = QPixmap(str(Path(__file__).parent/'assets/intro-awakening.png'))
        self.background = Qt.GlobalColor.black
        self.setMinimumHeight(160)
        self.setAccessibleName('Maatis entdeckt das leuchtende Artefakt in der verlassenen Bibliothek')

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.background)
        scaled = self.pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap((self.width()-scaled.width())//2, (self.height()-scaled.height())//2, scaled)
        painter.end()


class IntroScreen(QWidget):
    completed = Signal()
    audio_requested = Signal(dict)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 12, 28, 12)
        layout.setSpacing(12)
        layout.addWidget(label('PROLOG / DAS ERWACHEN', 'eyebrow'))
        self.artwork = IntroArtwork()
        layout.addWidget(self.artwork, 3)
        self.text = QTextBrowser()
        self.text.setObjectName('introText')
        self.text.setMinimumHeight(175)
        self.text.setStyleSheet('QTextBrowser {font-size: 36px; color: #eee5cc; background: #08152c; border: 1px solid #345171; border-radius: 12px; padding: 18px;}')
        layout.addWidget(self.text, 1)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setObjectName('xp')
        layout.addWidget(self.progress)
        row = QHBoxLayout()
        self.hint = label('', 'muted')
        row.addWidget(self.hint, 1)
        self.next_button = button('Weiter  →', self.advance_from_input)
        row.addWidget(self.next_button)
        self.skip_button = button('Intro überspringen', self.finish)
        row.addWidget(self.skip_button)
        layout.addLayout(row)
        for surface in (self.artwork, self.text.viewport()):
            surface.setCursor(Qt.PointingHandCursor)
            surface.installEventFilter(self)
        for key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space, Qt.Key_Escape):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.setAutoRepeat(False)
            shortcut.activated.connect(self.finish if key == Qt.Key_Escape else self.advance_from_input)
        self.timer = QTimer(self)
        self.timer.setInterval(15)
        self.timer.timeout.connect(self.tick)
        self.clock = QElapsedTimer()
        self.running = False
        self.segments = []
        self.segment = self.offset = self.next_character = 0

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            self.advance_from_input()
            return True
        return super().eventFilter(watched, event)

    def start(self, language='de'):
        self.cancel()
        self.language = language
        self.translate_controls()
        # Preserve original wording and ellipses; split full sentences within lines.
        self.segments = [sentence for line in INTRO_TEXT.get(language, INTRO_TEXT['de'])
                         for sentence in re.split(r'(?<=[.!?])\s+', line.strip()) if sentence]
        self.segment = 0
        self.running = True
        self.progress.setRange(0, len(self.segments))
        folder = Path(__file__).resolve().parents[1]/'apps/maat_rpg/plugins/rpg_intro'
        track = folder/('Intro_EN.mp3' if language == 'en' else 'intro.mp3')
        self.audio_requested.emit({'action': 'play', 'owner': 'native-intro', 'path': str(track), 'loop': True})
        self.show_sentence()
        self.text.setFocus()

    def translate_controls(self):
        from gui.ui_i18n import translate_widgets
        translate_widgets(self, getattr(self, 'language', 'de'))

    def show_sentence(self):
        self.text.clear()
        self.offset = self.next_character = 0
        self.progress.setValue(self.segment)
        self.hint.setText('Klick / Enter · Satz anzeigen   |   Esc · Überspringen')
        self.next_button.setText('Satz anzeigen')
        self.translate_controls()
        self.clock.start()
        self.timer.start()

    def tick(self):
        if not self.running or self.offset >= len(self.segments[self.segment]):
            return
        elapsed = self.clock.elapsed()
        if elapsed < self.next_character:
            return
        character = self.segments[self.segment][self.offset]
        self.text.moveCursor(QTextCursor.End)
        self.text.insertPlainText(character)
        self.text.ensureCursorVisible()
        self.offset += 1
        self.next_character = elapsed + (350 if character in '.!?…' else 160 if character in ',:;' else 65)
        if self.offset == len(self.segments[self.segment]):
            self.sentence_ready()

    def sentence_ready(self):
        self.timer.stop()
        last = self.segment == len(self.segments)-1
        self.progress.setValue(self.segment+1)
        self.next_button.setText('Spiel beginnen  →' if last else 'Weiter  →')
        self.hint.setText('Klick / Enter · ' + ('Spiel beginnen' if last else 'Nächster Satz') + '   |   Esc · Überspringen')
        self.translate_controls()

    def advance_from_input(self):
        if self.running:
            self.advance()
            # The final page can clear scene audio while returning to the game.
            # Dispatch afterwards so that transition does not swallow this click.
            self.audio_requested.emit({'action': 'ui_sound', 'name': 'story_advance'})

    def advance(self):
        if not self.running:
            return
        sentence = self.segments[self.segment]
        if self.offset < len(sentence):
            self.text.setPlainText(sentence)
            self.offset = len(sentence)
            self.sentence_ready()
        elif self.segment+1 < len(self.segments):
            self.segment += 1
            self.show_sentence()
        else:
            self.finish()

    def cancel(self):
        self.timer.stop()
        if self.running:
            self.audio_requested.emit({'action': 'stop', 'owner': 'native-intro'})
        self.running = False

    def finish(self):
        if not self.running:
            return
        self.cancel()
        self.completed.emit()
