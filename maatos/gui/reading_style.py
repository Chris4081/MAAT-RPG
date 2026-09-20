"""Consistent large, wrapping text for chat and combat transcripts."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextOption


TEXT_SIZES = {'small': 18, 'medium': 26, 'large': 36}


def set_reader_size(view, size):
    font = view.font()
    font.setPixelSize(size)
    view.setFont(font)
    view.document().setDefaultFont(font)
    view.setStyleSheet('''
        QTextBrowser { font-size: SIZEpx; padding: 16px; }
        QScrollBar:vertical { background: #0b162d; width: 12px; margin: 0; }
        QScrollBar::handle:vertical { background: #435e88; min-height: 30px; border-radius: 5px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
    '''.replace('SIZE', str(size)))
    view.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
    view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)


def large_transcript(view):
    set_reader_size(view, 36)
    view.setMinimumHeight(320)
