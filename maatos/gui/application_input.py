"""Route application input without a QMainWindow override on widget lifecycle events."""
import weakref
from PySide6.QtCore import QObject, QEvent
from gui.runtime_diagnostics import exception as diagnostic_exception


class ApplicationInputFilter(QObject):
    # Qt sends Create/ChildAdded/Destroy while native widget constructors or
    # destructors are running. Never pass these partially constructed wrappers
    # through Python window methods or QMainWindow.eventFilter.
    EVENTS = frozenset((QEvent.KeyPress, QEvent.KeyRelease, QEvent.MouseButtonPress,
                        QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick, QEvent.WindowActivate,
                        QEvent.WindowStateChange, QEvent.Show, QEvent.ApplicationDeactivate,
                        QEvent.WindowDeactivate))

    def __init__(self, window):
        super().__init__(window)
        self._window = weakref.ref(window)

    def eventFilter(self, watched, event):
        try:
            if event.type() not in self.EVENTS:
                return False
            window = self._window()
            if window is None:
                return False
            return bool(window.handle_application_input(watched, event))
        except Exception:
            # No Python exception may escape a Qt virtual callback. The Intel
            # crash report ends in Shiboken's override-error handler here.
            diagnostic_exception('application_input_failed')
            return False
