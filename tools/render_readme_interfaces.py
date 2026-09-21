#!/usr/bin/env python3
"""Render real GUI widgets and original terminal title text with example data.

No model is loaded. Profiles, chat text and state are disposable; the terminal
image is a styled rendering of game_menu._render_title_screen, not an OS capture.
Run in the game's Python environment; optionally pass an output directory.
"""
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import io
import os
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    output = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'docs/images'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='maat-readme-interfaces-') as temporary:
        scratch = Path(temporary)
        os.environ.update(QT_QPA_PLATFORM='offscreen', MAAT_GUI_DATA_ROOT=str(scratch),
                          MAAT_APP_SUPPORT_DIR=str(scratch), PYTHONDONTWRITEBYTECODE='1')
        sys.path.insert(0, str(ROOT / 'maatos'))
        from shared.core import maat_paths
        with patch.object(maat_paths, '_default_app_support_dir', return_value=scratch):
            render(output)


def render(output):
    from PySide6.QtCore import QObject, Signal, QCoreApplication, QEvent
    from PySide6.QtGui import QFont, QFontMetrics, QImage, QPainter, QColor
    from PySide6.QtWidgets import QApplication
    from apps.maat_rpg import session_shared
    from shared.core.rpg_i18n import set_language
    from gui.live_window import LiveWindow
    from gui.live_session import LiveSession
    from apps.maat_rpg.plugins.game_menu.plugin_main import _render_title_screen

    class SilentAudio(QObject):
        status = Signal(str)
        music_enabled = False
        def location(self, *args): pass
        def set_volume(self, *args): pass
        def set_enabled(self, *args): pass
        def handle_event(self, *args): pass
        def close(self): pass

    app = QApplication.instance() or QApplication([])
    examples = {
        'de': ('Was bedeuten die fünf Prinzipien für unsere Reise?',
               'Harmonie, Balance, Schöpfungskraft, Verbundenheit und Respekt '
               'begleiten uns durch Terra. Du kannst sie in deinen Entscheidungen '
               'entdecken: Hörst du erst zu, suchst du einen neuen Weg oder schützt '
               'du jemanden?\n\nErzähl mir, was dir gerade wichtig ist. '
               'Von dort aus beginnt unser nächster Schritt.'),
        'en': ('What do the five principles mean for our journey?',
               'Harmony, Balance, Creative Power, Connection and Respect guide '
               'us through Terra. You can explore them through your choices: '
               'will you listen first, find a new path or protect someone?\n\n'
               'Tell me what matters to you right now. '
               'That is where our next step begins.'),
    }
    for language, (question, reply) in examples.items():
        session_shared.write_application_language(language)
        session_shared.write_profile_settings(1, {
            'language': language, 'music_enabled': False, 'say_tts_enabled': False,
            'gui_text_size': 'medium',
        })
        set_language(language)
        session = LiveSession()
        window = LiveWindow(session=session, audio=SilentAudio())
        try:
            window.title_idle.stop()
            window.phase = 'playing'
            window.model_ready = True
            session.ready, session.busy = True, False
            window.resize(1560, 980)
            window.journal.clear()
            window.world_output.clear()
            window.apply_snapshot(session.get_snapshot())
            window.character_sidebar.update_profile({'level': 1, 'fights_won': 0, 'boss_wins': 0})
            window.navigate(3)
            window.receive({'event': 'model', 'status': 'ready',
                            'name': 'GGUF · Beispielansicht' if language == 'de' else 'GGUF · Preview'})
            window.show()
            app.processEvents()
            window.input.setText(question)
            with patch.object(session, 'send_text'):
                window.send()
            window.receive({'event': 'output', 'text': '\n\n'})
            window.receive({'event': 'chat_response', 'action': 'begin', 'id': 'readme-example'})
            window.receive({'event': 'output', 'text': reply + '\n'})
            window.receive({'event': 'chat_response', 'action': 'end', 'id': 'readme-example'})
            window.text_stream.finish()
            window.footer.setText('Beispieldialog · Lokale KI' if language == 'de'
                                  else 'Example conversation · Local AI')
            window.footer.show()
            window.profile_badge.show()
            app.processEvents()
            window.journal.verticalScrollBar().setValue(0)
            assert window.journal.verticalScrollBar().maximum() == 0, 'Example dialogue must fit'
            assert session.process is None, 'Preview must not launch an AI worker'
            assert window.grab().save(str(output / f'ai-chat-{language}.png'))
        finally:
            session.shutdown()
            window.close()
            window.deleteLater()
            QCoreApplication.sendPostedEvents(window, QEvent.DeferredDelete)
            app.processEvents()

        # Keep the exact title text, spaces and ANSI foreground colours.
        title = _render_title_screen(language)
        lines = title.strip('\n').splitlines()
        font = QFont('Menlo'); font.setPixelSize(22)
        metrics = QFontMetrics(font)
        line_height = metrics.height() + 4
        width = max(1040, max(metrics.horizontalAdvance(re.sub(r'\x1b\[[0-9;]*m', '', line))
                              for line in lines) + 100)
        image = QImage(width, 110 + line_height * len(lines), QImage.Format_ARGB32)
        image.fill(QColor('#050d1d'))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.fillRect(0, 0, width, 56, QColor('#10243c'))
        painter.setFont(font); painter.setPen(QColor('#eee6d5'))
        painter.drawText(36, 36, 'MAAT RPG · Terminal')
        colors = {0: '#eee6d5', 32: '#9cdbb1', 33: '#e7cc8b', 36: '#8bd5df'}
        color = colors[0]
        for row, line in enumerate(lines):
            x, y = 42, 94 + row * line_height
            for token in re.split(r'(\x1b\[[0-9;]*m)', line):
                if token.startswith('\x1b['):
                    for code in token[2:-1].split(';'):
                        color = colors.get(int(code or 0), color)
                    continue
                painter.setPen(QColor(color)); painter.drawText(x, y, token)
                x += metrics.horizontalAdvance(token)
        painter.end()
        assert image.save(str(output / f'terminal-pyramid-{language}.png'))


if __name__ == '__main__':
    with redirect_stdout(io.StringIO()):
        main()
    print('Rendered English/German GUI examples and original terminal title screens.')
