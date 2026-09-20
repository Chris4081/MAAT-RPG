"""Advance battle narration without activating actions or swallowing text input."""
import re
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (QWidget, QAbstractButton, QLineEdit, QTextEdit,
                               QComboBox, QAbstractSpinBox, QAbstractSlider, QApplication)

ADVANCE_KEYS = (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space)


def focus_narration(window):
    """Keep keyboard playback available when combat buttons become disabled."""
    if QApplication.activeModalWidget() is not None or QApplication.activePopupWidget() is not None:
        return
    focus = QApplication.focusWidget()
    while focus is not None and focus is not window:
        if isinstance(focus, QLineEdit) and not (focus is window.answer and not focus.text()):
            return
        if isinstance(focus, QTextEdit) and not focus.isReadOnly():
            return
        if isinstance(focus, (QComboBox, QAbstractSpinBox, QAbstractSlider)):
            return
        focus = focus.parentWidget()
    window.arena.log.setFocus(Qt.OtherFocusReason)


def advance_state(window):
    if (window.phase != 'playing' or window.stack.currentIndex() != 2
            or window._active_minigame or window._encounter_intro):
        return None
    if window.text_stream.running:
        return 'reading' if (window._battle_active or window._battle_presenting
                             or window._presenting_combat_text) else None
    # Only explicit continue prompts, never attacks, skill choices or free text.
    if window.game.prompt_id and not window._arena_choices and not window.answer.text():
        text = window.prompt_label.text().strip()
        if (re.search(r'\b(?:enter|return)\b|[⏎↵]', text, re.I)
                or re.fullmatch(r'(?:weiter|continue)[\s.…!:]*', text, re.I)):
            return 'confirm'
    return None


class CombatAdvanceInput:
    def __init__(self):
        self.keys_down = set()
        self.mouse_down = False

    def handle(self, window, obj, event):
        kind = event.type()
        # Consume the matching release even if revealing text opened a new
        # scene or enabled a button. Qt must not reuse that gesture there.
        if kind == QEvent.KeyRelease and event.key() in self.keys_down:
            if not event.isAutoRepeat():
                self.keys_down.discard(event.key())
            return True
        if kind == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton and self.mouse_down:
            self.mouse_down = False
            return True
        if kind == QEvent.KeyPress and event.key() in self.keys_down:
            return True
        if kind == QEvent.ApplicationDeactivate or (obj is window and kind == QEvent.WindowDeactivate):
            self.keys_down.clear()
            self.mouse_down = False
            return False
        keyboard = kind == QEvent.KeyPress and event.key() in ADVANCE_KEYS
        mouse = kind in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick) and event.button() == Qt.LeftButton
        if not (keyboard or mouse) or not isinstance(obj, QWidget) or obj.window() is not window:
            return False
        if keyboard and event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
            return False
        if QApplication.activeModalWidget() is not None or QApplication.activePopupWidget() is not None:
            return False
        mode = advance_state(window)
        if mode is None:
            return False
        # Navigation and other page controls are never click-to-continue areas.
        in_arena = obj is window.arena or window.arena.isAncestorOf(obj)
        in_confirmation = mode == 'confirm' and (obj is window.decision or window.decision.isAncestorOf(obj))
        if mouse and not (in_arena or in_confirmation):
            return False
        parent = obj
        while parent is not window and parent is not None:
            if isinstance(parent, QLineEdit):
                # Space remains available for tactical advice and chat drafts.
                if not (parent is window.answer and mode == 'confirm' and not parent.text()):
                    return False
            if isinstance(parent, QTextEdit) and not parent.isReadOnly():
                return False
            if isinstance(parent, (QAbstractButton, QComboBox, QAbstractSpinBox, QAbstractSlider)):
                return False
            parent = parent.parentWidget()
        if keyboard:
            if event.isAutoRepeat():
                return True
            self.keys_down.add(event.key())
        else:
            self.mouse_down = True
        if mode == 'reading':
            window.text_stream.finish()
        else:
            window.game.submit_choice('')
            window.update_controls()
        return True
