"""Qt Multimedia playback, owned by this window only; no system-wide killall."""
from pathlib import Path
import sys
import shutil
from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices


class AudioManager(QObject):
    status = Signal(str)
    outputs_changed = Signal()

    def __init__(self, parent=None, backend='auto'):
        super().__init__(parent)
        self.root = Path(__file__).resolve().parents[1] / 'apps/maat_rpg/plugins'
        # Source releases ship sound effects, but no background soundtrack.
        self.music_enabled = False
        self.sound_enabled = True
        self.volume = .35
        self.requests = {}
        self.playlists = {}
        self.menu = True
        self.language = 'de'
        self.current = None
        self.output_id = ""
        self._output_unavailable=False
        self.native_music = self.native_fx = None
        self._fx_path = None
        self._native_music_failed = self._native_fx_failed = False
        self.process_audio = None
        native = shutil.which('afplay') if sys.platform == 'darwin' and backend != 'qt' else None
        if native:
            from gui.native_audio import NativeAudioChannel
            self.native_music = NativeAudioChannel(native, self)
            self.native_fx = NativeAudioChannel(native, self, restart_on_volume_change=False)
            self.native_music.error.connect(lambda message: self._native_error(False, message))
            self.native_fx.error.connect(lambda message: self._native_error(True, message))
            self.native_music.ended.connect(self._native_ended)
        if backend != 'qt':
            from gui.audio_process import AudioProcess
            self.process_audio = AudioProcess(self)
            self.player, self.fx = (self.process_audio.players[key] for key in ('music', 'fx'))
            self.output, self.fx_output = (self.process_audio.outputs[key] for key in ('music', 'fx'))
            self.process_audio.outputs_changed.connect(self.outputs_changed)
            self.process_audio.availability.connect(self._device_availability)
            self.process_audio.error.connect(self.status)
            self.player.mediaStatusChanged.connect(self._ended)
            return
        self.player = QMediaPlayer(self)
        self.devices = QMediaDevices(self)
        self.devices.audioOutputsChanged.connect(self._refresh_device)
        self.output = QAudioOutput(QMediaDevices.defaultAudioOutput(), self)
        self.player.setAudioOutput(self.output)
        self.output.setVolume(self.volume)
        self.player.errorOccurred.connect(lambda err, text: self.status.emit('Audio: ' + text))
        self.player.mediaStatusChanged.connect(self._ended)
        self.fx = QMediaPlayer(self)
        self.fx_output = QAudioOutput(QMediaDevices.defaultAudioOutput(), self)
        self.fx.setAudioOutput(self.fx_output)
        self.fx_output.setVolume(self.volume)
        self.fx.errorOccurred.connect(lambda err, text: self.status.emit('Sound: ' + text))

    def _native_error(self, effect, message):
        # A failed native channel must not leave current pointing to silent audio.
        if effect:
            self._native_fx_failed=True
            self.status.emit('Sound-Ausgabe wird auf Qt umgestellt: '+message)
            if self._fx_path is not None:
                self.play_sound(self._fx_path)
        else:
            self._native_music_failed=True
            self.native_music.stop()
            self.current=None
            self._select()
            self.status.emit('Native Audioausgabe fehlgeschlagen; alternative Wiedergabe aktiv. Bei Stille bitte einen anderen Audioausgang wählen.')

    def available_outputs(self):
        if self.process_audio is not None:
            return list(self.process_audio.devices)
        return [(bytes(d.id()).hex(), d.description()) for d in QMediaDevices.audioOutputs()]

    def select_output(self, identifier):
        if identifier == self.output_id:return
        self.output_id=identifier
        self._refresh_device()

    def _refresh_device(self):
        if self.process_audio is not None:
            self.player.stop()
            self.fx.stop()
            self._fx_path = None
            if self.native_music:
                self.native_music.stop(); self.native_fx.stop()
            self._native_music_failed = self._native_fx_failed = bool(self.output_id)
            self._output_unavailable = False
            self.current = None
            self.process_audio.select_output(self.output_id)
            self._select()
            return
        device = next((d for d in QMediaDevices.audioOutputs() if bytes(d.id()).hex()==self.output_id), None) if self.output_id else QMediaDevices.defaultAudioOutput()
        self.player.stop()
        self.fx.stop()
        self._fx_path = None
        if self.native_music:
            self.native_music.stop();self.native_fx.stop()
        self._output_unavailable=device is None or device.isNull()
        if device is None:
            self.current=None
            self.status.emit('Der gewählte Audioausgang ist nicht verbunden. Bitte unter Musik & Sound einen verfügbaren Ausgang wählen.')
            self.outputs_changed.emit()
            return
        self.output.setDevice(device)
        self.fx_output.setDevice(device)
        if device.isNull():
            self.status.emit('Kein Audio-Ausgabegerät verfügbar')
        else:
            # Explicit outputs use Qt: afplay cannot target a selected device.
            self._native_music_failed=self._native_fx_failed=bool(self.output_id)
            self.current=None
            self._select()
        self.outputs_changed.emit()

    def _device_availability(self, available):
        self._output_unavailable = not available
        if not available:
            self.status.emit('Der gewählte Audioausgang ist nicht verbunden. Bitte unter Musik & Sound einen verfügbaren Ausgang wählen.')
        self._select()

    def set_volume(self, value):
        self.volume = max(0, min(100, value)) / 100
        self.output.setVolume(self.volume)
        self.fx_output.setVolume(self.volume)
        if self.native_music:
            if not self._native_music_failed:self.native_music.set_volume(self.volume)
            if not self._native_fx_failed:self.native_fx.set_volume(self.volume)

    def set_enabled(self, music, sound):
        self.music_enabled = bool(music)
        self.sound_enabled = bool(sound)
        if not sound:
            self._fx_path = None
            self.fx.stop()
            if self.native_fx:
                self.native_fx.stop()
        self._select()

    def location(self, menu, language='de'):
        self.menu, self.language = menu, language
        self._select()

    def handle_event(self, event):
        action = event.get('action')
        owner = event.get('owner')
        if action == 'ui_sound':
            if event.get('name') == 'story_advance':
                self.play_sound(Path(__file__).parent / 'assets/audio/ui-v1/story_advance.wav')
            return
        if action == 'effect':
            from gui.combat_sounds import combat_sound
            path = combat_sound(event.get('attack_event') or {})
            if path is not None:
                self.play_sound(path)
            return
        if action == 'clear':
            self._fx_path = None
            self.requests.clear()
            self.playlists.clear()
            self.fx.stop()
            if self.native_fx:
                self.native_fx.stop()
        elif action == 'stop':
            self.requests.pop(owner, None)
            self.playlists.pop(owner,None)
        elif action == 'play':
            if event.get('playlist'):
                tracks=[str(Path(p).resolve()) for p in event['playlist'] if Path(p).is_file()]
                if not tracks:
                    self.playlists.pop(owner, None)
                    self.requests.pop(owner, None)
                    self._select()
                    return
                self.playlists[owner]={'tracks':tracks,'index':0}
                self.requests.pop(owner,None)
                self.requests[owner]=(tracks[0],False)
                self._select()
                return
            path = Path(event.get('path', ''))
            if not path.is_file():
                # Music is optional. Drop stale playback for this owner quietly.
                self.playlists.pop(owner, None)
                self.requests.pop(owner, None)
                self._select()
                return
            if path.name in {'levelup.mp3', 'victory.mp3'}:
                self.play_sound(path)
                return
            self.playlists.pop(owner,None)
            self.requests.pop(owner, None)
            self.requests[owner] = (str(path.resolve()), bool(event.get('loop')))
        self._select()

    def play_sound(self, path):
        """One short cue on the existing FX channel, independent of music/TTS."""
        if not self.sound_enabled or self._output_unavailable:
            return
        path = Path(path).resolve()
        if not path.is_file():
            self.status.emit('Sounddatei fehlt: ' + str(path))
            return
        self._fx_path = path
        if self.native_fx and not self._native_fx_failed:
            self.native_fx.play(path)
        else:
            self.fx.stop()
            self.fx.setLoops(1)
            self.fx.setSource(QUrl.fromLocalFile(str(path)))
            self.fx.play()

    def _select(self):
        desired = None
        if self.music_enabled and not self._output_unavailable:
            if self.requests:
                owner = next(reversed(self.requests))
                path, loop = self.requests[owner]
                desired = (owner, path, loop)
            elif self.menu:
                track = self.root / 'game_menu' / ('menu_theme_en.mp3' if self.language == 'en' else 'menu_theme.mp3')
                if track.is_file():
                    desired = ('menu', str(track), True)
        if desired == self.current:
            return
        self.current = desired
        self.player.stop()
        if self.native_music:
            self.native_music.stop()
        if desired:
            _, path, loop = desired
            if self.native_music and not self._native_music_failed:
                self.native_music.play(path, loop)
            else:
                self.player.setLoops(QMediaPlayer.Infinite if loop else 1)
                self.player.setSource(QUrl.fromLocalFile(path))
                self.player.play()
            self.status.emit('♫ ' + Path(path).stem)
        else:
            self.status.emit('Musik pausiert')

    def _track_finished(self):
        if not self.current or self.current[2]:return
        owner=self.current[0]
        playlist=self.playlists.get(owner)
        if playlist:
            playlist['index']=(playlist['index']+1)%len(playlist['tracks'])
            self.requests[owner]=(playlist['tracks'][playlist['index']],False)
        else:self.requests.pop(owner,None)
        self.current=None
        self._select()

    def _native_ended(self):
        if self._native_music_failed:return
        self._track_finished()

    def _ended(self, status):
        if self.native_music and not self._native_music_failed:return
        if (status == QMediaPlayer.EndOfMedia and self.current
                and not self.current[2]
                and self.player.mediaStatus() == QMediaPlayer.EndOfMedia):
            self._track_finished()

    def close(self):
        self._fx_path = None
        self.playlists.clear()
        self.requests.clear()
        self.current = None
        self.player.stop()
        self.fx.stop()
        if self.native_music:
            self.native_music.close()
            self.native_fx.close()
        if self.process_audio is not None:
            self.process_audio.close()
