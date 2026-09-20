"""Qt audio driver calls live in a disposable process, never in the GUI thread."""
import json
from pathlib import Path
import sys
from PySide6.QtCore import QObject, QProcess, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QMediaPlayer

# Retired children outlive a window being deleted, until SIGKILL is reaped.
# QProcess destruction itself may wait; never make that part of a device switch.
_RETIRED_PROCESSES = set()


class RemoteOutput:
    def __init__(self, owner, channel):
        self.owner, self.channel = owner, channel
        self._volume = .35

    def setVolume(self, value):
        self._volume = float(value)
        self.owner.send('volume', channel=self.channel, value=self._volume)

    def volume(self):
        return self._volume


class RemotePlayer(QObject):
    errorOccurred = Signal(object, str)
    mediaStatusChanged = Signal(object)

    def __init__(self, owner, channel):
        super().__init__(owner)
        self.owner, self.channel = owner, channel
        self._source, self._loops = QUrl(), 1
        self._status = QMediaPlayer.NoMedia
        self._state = QMediaPlayer.StoppedState
        self._generation = 0

    def setSource(self, value): self._source = value
    def source(self): return self._source
    def setLoops(self, value): self._loops = value
    def mediaStatus(self): return self._status
    def playbackState(self): return self._state

    def play(self):
        self._generation += 1
        self._state = QMediaPlayer.PlayingState
        self.owner.send('play', channel=self.channel, path=self._source.toLocalFile(), loops=self._loops, generation=self._generation)

    def stop(self):
        self._generation += 1
        self._state = QMediaPlayer.StoppedState
        self.owner.send('stop', channel=self.channel)


class AudioProcess(QObject):
    outputs_changed = Signal()
    availability = Signal(bool)
    error = Signal(str)

    def __init__(self, parent=None, *, command=None, timeout_ms=5000):
        super().__init__(parent)
        self.command = command or [sys.executable, '-u', str(Path(__file__).with_name('audio_worker.py'))]
        self.timeout_ms = timeout_ms
        self.players = {key: RemotePlayer(self, key) for key in ('music', 'fx')}
        self.outputs = {key: RemoteOutput(self, key) for key in ('music', 'fx')}
        self.devices = []
        self.process = None
        self._buffer = b''
        self._queue = []
        self._sequence = 0
        self._pending = {}
        self._closed = self._failed = False
        self._retired = set()
        self._last_ping = 0.
        self.watchdog = QTimer(self)
        self.watchdog.setInterval(100)
        self.watchdog.timeout.connect(self._check_timeout)
        self._start()

    def _start(self):
        if self._closed or self.process is not None:
            return
        self._buffer = b''
        self._failed = False
        p = QProcess(self)
        self.process = p
        p.readyReadStandardOutput.connect(lambda: self._read(p))
        p.readyReadStandardError.connect(lambda: p.readAllStandardError())
        p.started.connect(self._flush)
        p.errorOccurred.connect(lambda _: self._fail('Audio-Prozess konnte nicht gestartet werden.') if p is self.process else None)
        p.finished.connect(lambda *_: self._finished(p))
        import time
        self._pending[0] = time.monotonic()
        self.watchdog.start()
        p.start(self.command[0], self.command[1:])

    def send(self, action, **values):
        if self._closed or self._failed:
            return
        self._sequence += 1
        self._queue.append(dict(op=action, id=self._sequence, **values))
        self._flush()

    def select_output(self, identifier):
        self.availability.emit(False)
        if self._failed:
            self._start()
            for channel, output in self.outputs.items():
                self.send('volume', channel=channel, value=output.volume())
        self.send('device', identifier=identifier)

    def _flush(self):
        import time
        p = self.process
        if p is None or p.state() != QProcess.Running:
            return
        for message in self._queue:
            self._pending[message['id']] = time.monotonic()
            p.write((json.dumps(message) + '\n').encode())
        self._queue.clear()

    def _read(self, process):
        if process is not self.process:
            process.readAllStandardOutput()
            return
        self._buffer += bytes(process.readAllStandardOutput())
        while b'\n' in self._buffer:
            raw, self._buffer = self._buffer.split(b'\n', 1)
            try:
                message = json.loads(raw)
            except (ValueError, UnicodeError):
                continue
            if message.get('event') == 'ack':
                self._pending.pop(message.get('id'), None)
            elif message.get('event') == 'devices':
                self.devices = [tuple(item) for item in message.get('outputs', [])]
                self.outputs_changed.emit()
            elif message.get('event') == 'device_changing':
                self.availability.emit(False)
            elif message.get('event') == 'device_ready':
                self._pending.pop(0, None)
                self.availability.emit(bool(message.get('available', True)))
            elif message.get('event') == 'status':
                player = self.players.get(message.get('channel'))
                if player and message.get('generation') == player._generation:
                    player._status = QMediaPlayer.MediaStatus(message['value'])
                    if player._status == QMediaPlayer.EndOfMedia:
                        player._state = QMediaPlayer.StoppedState
                    player.mediaStatusChanged.emit(player._status)
            elif message.get('event') == 'error':
                self.error.emit(message.get('text', 'Audiofehler'))

    def _check_timeout(self):
        import time
        if self._pending and time.monotonic() - min(self._pending.values()) > self.timeout_ms / 1000:
            self._fail('Der Audioausgang reagiert nicht. Bitte einen anderen Ausgang wählen oder Audio neu verbinden.')
        elif not self._pending and time.monotonic() - self._last_ping > 1:
            self._last_ping = time.monotonic()
            self.send('ping')

    def _fail(self, text):
        if self._closed or self._failed:
            return
        self._failed = True
        self._queue.clear()
        self._pending.clear()
        self.watchdog.stop()
        self._retire()
        self.availability.emit(False)
        self.error.emit(text)

    def _retire(self):
        p, self.process = self.process, None
        if p is not None:
            p.setParent(None)
            _RETIRED_PROCESSES.add(p)
            self._retired.add(p)
            if p.state() == QProcess.Starting:
                p.started.connect(p.kill)
            p.kill()
            if p.state() == QProcess.NotRunning:
                self._retired.discard(p)
                _RETIRED_PROCESSES.discard(p)
                p.deleteLater()

    def _finished(self, p):
        from shiboken6 import isValid
        if not isValid(p):
            self._retired.discard(p)
            _RETIRED_PROCESSES.discard(p)
            return
        if p is self.process:
            self._fail('Audio-Prozess wurde beendet. Bitte Audio neu verbinden.')
        self._retired.discard(p)
        _RETIRED_PROCESSES.discard(p)
        p.deleteLater()

    def close(self):
        self._closed = True
        self.watchdog.stop()
        self._queue.clear()
        self._pending.clear()
        self._retire()
        # Only on application shutdown, after SIGKILL; device switching never waits.
        for process in tuple(self._retired):
            process.waitForFinished(250)
