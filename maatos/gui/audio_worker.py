"""Private audio process. A stuck macOS/Qt driver can be killed independently."""
import json
import sys
import threading
from PySide6.QtCore import QCoreApplication, QObject, QUrl, Signal, Qt
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer


def emit(**message):
    print(json.dumps(message, ensure_ascii=False), flush=True)


class Commands(QObject):
    received = Signal(dict)
    eof = Signal()


def main():
    app = QCoreApplication([])
    commands = Commands()
    devices = QMediaDevices()
    players = {key: QMediaPlayer() for key in ('music', 'fx')}
    outputs = {key: QAudioOutput() for key in players}
    selected = ''
    generations = dict.fromkeys(players, 0)
    for key, player in players.items():
        player.setAudioOutput(outputs[key])
        player.errorOccurred.connect(lambda _, text, channel=key: emit(event='error', text='Audio: ' + text, channel=channel))
        player.mediaStatusChanged.connect(lambda value, channel=key: emit(event='status', channel=channel, value=value.value, generation=generations[channel]))

    def inventory():
        items = list(QMediaDevices.audioOutputs())
        device = next((d for d in items if bytes(d.id()).hex() == selected), None) if selected else QMediaDevices.defaultAudioOutput()
        emit(event='devices', outputs=[(bytes(d.id()).hex(), d.description()) for d in items])
        return device

    def set_device():
        emit(event='device_changing')
        for player in players.values(): player.stop()
        device = inventory()
        if device is not None and not device.isNull():
            for output in outputs.values(): output.setDevice(device)
        emit(event='device_ready', available=device is not None and not device.isNull())

    def dispatch(message):
        nonlocal selected
        action, channel = message.get('op'), message.get('channel', 'music')
        player = players.get(channel)
        try:
            if action == 'device':
                selected = message.get('identifier', '')
                set_device()
            elif action == 'play' and player is not None:
                player.stop()
                generations[channel] = message.get('generation', 0)
                player.setLoops(int(message.get('loops', 1)))
                player.setSource(QUrl.fromLocalFile(message.get('path', '')))
                player.play()
            elif action == 'stop' and player is not None:
                player.stop()
            elif action == 'volume' and channel in outputs:
                outputs[channel].setVolume(float(message.get('value', .35)))
        except Exception as exc:
            emit(event='error', text=str(exc))
        emit(event='ack', id=message.get('id'))

    def read():
        for raw in sys.stdin:
            try: commands.received.emit(json.loads(raw))
            except (ValueError, TypeError): pass
        commands.eof.emit()

    commands.received.connect(dispatch, Qt.QueuedConnection)
    commands.eof.connect(app.quit)
    devices.audioOutputsChanged.connect(set_device)
    set_device()
    threading.Thread(target=read, daemon=True).start()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
