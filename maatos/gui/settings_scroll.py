"""Scroll settings pages without changing the values under the pointer."""
from PySide6.QtCore import QObject, QEvent, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QApplication, QAbstractScrollArea, QAbstractSpinBox, QComboBox,
    QLineEdit, QSlider, QWidget,
)


class _SettingsWheelGuard(QObject):
    def eventFilter(self, watched, event):
        if event.type() != QEvent.Wheel:
            return False
        # Forward both mouse-wheel ticks and trackpad pixels to the containing
        # page. Merely ignoring a filtered event can leave the page stationary.
        area = watched.parentWidget()
        while area is not None and not isinstance(area, QAbstractScrollArea):
            area = area.parentWidget()
        if area is not None:
            viewport = area.viewport()
            forwarded = QWheelEvent(
                QPointF(viewport.mapFromGlobal(event.globalPosition().toPoint())),
                event.globalPosition(), event.pixelDelta(), event.angleDelta(),
                event.buttons(), event.modifiers(), event.phase(), event.inverted(),
                event.source(), event.pointingDevice(),
            )
            QApplication.sendEvent(viewport, forwarded)
        event.accept()
        return True


def protect_settings_scroll(root):
    """Protect existing controls; open combo lists retain their normal scrolling."""
    guard = getattr(root, '_settings_wheel_guard', None)
    if guard is None:
        guard = root._settings_wheel_guard = _SettingsWheelGuard(root)
    for control in [root, *root.findChildren(QWidget)]:
        if isinstance(control, (QComboBox, QAbstractSpinBox, QSlider)):
            control.setFocusPolicy(Qt.StrongFocus)
            control.installEventFilter(guard)
            # Editable combos and spin boxes can receive wheel events on their
            # text editor rather than the outer control.
            for editor in control.findChildren(QLineEdit):
                editor.installEventFilter(guard)
