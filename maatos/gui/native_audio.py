"""Asynchronous macOS audio. Each channel controls only its own afplay process."""
from PySide6.QtCore import QObject, QProcess, QTimer, Signal


class NativeAudioChannel(QObject):
    error = Signal(str)
    ended = Signal()

    def __init__(self, executable, parent=None, *, restart_on_volume_change=True):
        super().__init__(parent)
        self.executable = executable
        self.process = None
        self.path = None
        self.loop = False
        self.volume = .35
        self.restart_on_volume_change = restart_on_volume_change
        self._retired = set()
        self._retries = 0
        self.restart_timer = QTimer(self)
        self.restart_timer.setSingleShot(True)
        self.restart_timer.timeout.connect(self._start)
        self.volume_timer = QTimer(self)
        self.volume_timer.setSingleShot(True)
        self.volume_timer.setInterval(180)
        self.volume_timer.timeout.connect(self._apply_volume)

    def play(self, path, loop=False):
        self.stop()
        self._retries = 0
        self.path, self.loop = str(path), loop
        self._start()

    def _start(self):
        if not self.path or self.process is not None:return
        if self._retired:
            self.restart_timer.start(100)
            return
        process = QProcess(self)
        self.process = process
        process.finished.connect(lambda code, status: self._finished(process, code))
        process.errorOccurred.connect(lambda error: self._failed(process, process.errorString()))
        process.start(self.executable, ['-v', str(self.volume), self.path])

    def _failed(self, process, message):
        if process is self.process:
            self.error.emit(message)
            self.stop()

    def _finished(self, process, code):
        if process is not self.process:
            self._retired.discard(process)
            process.deleteLater()
            if self.path and not self.process:
                self.restart_timer.start(100)
            return
        message = bytes(process.readAllStandardError()).decode('utf-8', 'replace').strip()
        self.process = None
        process.deleteLater()
        if code and 'AudioQueueStart failed' in message and self._retries < 2:
            self._retries += 1
            self.restart_timer.start(250*self._retries)
            return
        if code:
            self.path = None
            self.error.emit(message or f'Audio beendet mit Fehler {code}')
        elif self.loop and self.path:
            self._start()
        else:
            self.path = None
            self.ended.emit()

    def set_volume(self, volume):
        volume=max(0.,min(1.,float(volume)))
        if volume == self.volume:return
        self.volume = volume
        if self.process and self.restart_on_volume_change:
            self.volume_timer.start()

    def _apply_volume(self):
        # afplay has no runtime volume API; debounce changes before restarting.
        if self.path:
            self.play(self.path, self.loop)

    def stop(self):
        self.volume_timer.stop()
        self.restart_timer.stop()
        process, self.process = self.process, None
        self.path = None
        if process:
            self._retired.add(process)
            process.kill()
            if process.state() == QProcess.NotRunning:
                self._retired.discard(process)
                process.deleteLater()

    def close(self):
        self.stop()
        for process in list(self._retired):
            process.waitForFinished(500)
