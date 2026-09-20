"""Follow new transcript content, including deferred QTextDocument relayout."""
from PySide6.QtCore import QObject, QTimer


class TranscriptScroll(QObject):
    def __init__(self, view, page=None, input_widget=None):
        super().__init__(view)
        self.view = view
        self.page = page
        self.input_widget = input_widget
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.scroll_to_bottom)
        view.textChanged.connect(self.follow_new_text)
        view.verticalScrollBar().rangeChanged.connect(self.schedule)

    def follow_new_text(self):
        self.scroll_to_bottom()
        self.schedule()

    def schedule(self, *_):
        # Coalesce token/layout notifications; run once after Qt updates the range.
        if not self.timer.isActive():
            self.timer.start(0)

    def scroll_to_bottom(self):
        bar = self.view.verticalScrollBar()
        bar.setValue(bar.maximum())
        if self.page is not None and self.view.isVisible():
            self.page.ensureWidgetVisible(self.input_widget, 0, 12)
