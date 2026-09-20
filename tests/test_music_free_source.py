"""Source distribution must work without a soundtrack and keep original cues."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from test_desktop import APP, ROOT
from PySide6.QtCore import QCoreApplication, QEvent, QUrl
from PySide6.QtMultimedia import QAudioBufferOutput
from apps.maat_rpg import session_shared
from gui.audio_manager import AudioManager
from shared.core import audio as terminal_audio
from audio_fixtures import music_fixture


class MusicFreeTests(unittest.TestCase):
    def manager(self):
        audio = AudioManager(backend='qt')
        audio.player.setAudioOutput(None)
        audio.fx.setAudioOutput(None)
        def close():
            audio.close()
            audio.player.setSource(QUrl())
            audio.fx.setSource(QUrl())
            audio.deleteLater()
            QCoreApplication.sendPostedEvents(audio, QEvent.DeferredDelete)
            APP.processEvents()
        self.addCleanup(close)
        return audio

    def test_source_contains_only_original_mp3_cues_and_wav_effects(self):
        files = {p.relative_to(ROOT).as_posix() for p in (ROOT/'maatos').rglob('*')
                 if p.suffix.lower() in {'.mp3', '.m4a'}}
        self.assertEqual(files, {
            'maatos/apps/maat_rpg/plugins/battle/sounds/levelup.mp3',
            'maatos/apps/maat_rpg/plugins/battle/music/victory.mp3',
        })
        self.assertEqual(len(list((ROOT/'maatos/gui/assets/audio').rglob('*.wav'))), 7)

    def test_new_profile_and_terminal_start_with_music_off_but_sound_on(self):
        self.assertFalse(session_shared.SETTINGS_DEFAULTS['music_enabled'])
        audio = self.manager()
        self.assertFalse(audio.music_enabled)
        self.assertTrue(audio.sound_enabled)
        audio.location(True)
        self.assertIsNone(audio.current)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'settings.json'
            with patch.object(terminal_audio, 'state_file', return_value=str(path)):
                self.assertFalse(terminal_audio.music_enabled())
                self.assertTrue(terminal_audio.sound_enabled())
                path.write_text(json.dumps({'music_enabled': True, 'gui_sound_enabled': False}))
                self.assertTrue(terminal_audio.music_enabled())
                self.assertFalse(terminal_audio.sound_enabled())

    def test_missing_music_is_quiet_even_if_user_enables_music(self):
        audio = self.manager()
        messages = []
        audio.status.connect(messages.append)
        with patch.object(audio.player, 'play') as play:
            audio.set_enabled(True, True)
            for language in ('de', 'en'):
                audio.location(True, language)
                for owner, relative in (
                    ('native-intro', 'rpg_intro/intro.mp3'),
                    ('native-title-demo', 'battle/music/battle_normal.mp3'),
                    ('story', 'story_loader/stories/story1_theme.mp3'),
                    ('native-minigame', 'battle/music/Sandsack-Highscore.m4a'),
                    ('credits', 'battle/music/credits_en.mp3'),
                ):
                    audio.handle_event(dict(action='play', owner=owner,
                                            path=str(audio.root/relative), loop=True))
                audio.handle_event(dict(action='play', owner='dungeon', playlist=[
                    str(audio.root/'dungeon_60/music/dungeon_theme.mp3'),
                    str(audio.root/'dungeon_500/music/crystal_boss.mp3')]))
                self.assertIsNone(audio.current)
            play.assert_not_called()
        self.assertEqual(audio.requests, {})
        self.assertEqual(audio.playlists, {})
        self.assertEqual(messages, [])

    def test_missing_replacement_clears_stale_track_and_partial_playlist_works(self):
        audio = self.manager()
        audio.root = music_fixture(self)
        audio.menu = False
        audio.music_enabled = True
        audio.player.setSource = Mock()
        audio.player.play = Mock()
        track = audio.root/'battle/music/battle_normal.mp3'
        missing = audio.root/'missing.mp3'
        audio.handle_event(dict(action='play', owner='story', path=str(track)))
        self.assertEqual(audio.current[0], 'story')
        audio.handle_event(dict(action='play', owner='story', path=str(missing)))
        self.assertIsNone(audio.current)
        audio.handle_event(dict(action='play', owner='dungeon', playlist=[str(missing), str(track)]))
        self.assertEqual(audio.playlists['dungeon']['tracks'], [str(track.resolve())])
        audio.handle_event(dict(action='play', owner='dungeon', playlist=[str(missing)]))
        self.assertIsNone(audio.current)
        self.assertNotIn('dungeon', audio.playlists)

    def test_levelup_and_victory_decode_with_background_music_disabled(self):
        audio = self.manager()
        capture = QAudioBufferOutput(audio)
        decoded = []
        capture.audioBufferReceived.connect(lambda b: decoded.append(b.byteCount()))
        audio.fx.setAudioBufferOutput(capture)
        try:
            for relative in ('battle/sounds/levelup.mp3', 'battle/music/victory.mp3'):
                decoded.clear()
                audio.handle_event(dict(action='play', owner='cue', path=str(audio.root/relative)))
                deadline = time.monotonic()+5
                while not any(decoded) and time.monotonic()<deadline:
                    APP.processEvents()
                    time.sleep(.01)
                self.assertTrue(any(decoded), relative)
                self.assertIsNone(audio.current)
                self.assertFalse(audio.requests)
            audio.set_enabled(False, False)
            with patch.object(audio.fx, 'play') as play:
                audio.handle_event(dict(action='play', owner='cue', path=str(audio.root/'battle/music/victory.mp3')))
                play.assert_not_called()
        finally:
            audio.fx.stop()
            audio.fx.setSource(QUrl())
            audio.fx.setAudioBufferOutput(None)
            capture.audioBufferReceived.disconnect()
            # Qt's test-only PCM tap must be destroyed before its media player.
            capture.deleteLater()
            QCoreApplication.sendPostedEvents(capture, QEvent.DeferredDelete)

    def test_terminal_missing_music_never_launches_a_player(self):
        with patch.object(terminal_audio.subprocess, 'Popen') as spawn:
            path = str(ROOT/'maatos/apps/maat_rpg/plugins/game_menu/menu_theme.mp3')
            self.assertIsNone(terminal_audio.play_audio_process(path))
            player = terminal_audio.ManagedAudioPlayer(path)
            self.assertFalse(player.start_loop())
            self.assertFalse(player.play_once())
            spawn.assert_not_called()

    def test_terminal_victory_is_independent_of_music(self):
        from apps.maat_rpg.plugins.battle import plugin_main as battle
        cue = str(ROOT/'maatos/apps/maat_rpg/plugins/battle/music/victory.mp3')
        with patch.object(battle, 'ManagedAudioPlayer') as player, \
             patch.object(battle, 'music_enabled', return_value=False), \
             patch.object(battle, 'sound_enabled', return_value=True):
            manager = battle.BattleMusicManager(None)
            manager.start()
            player.return_value.start_loop.assert_not_called()
            manager.victory_jingle(cue)
            player.return_value.play_once.assert_called_once_with(cue)
            player.return_value.reset_mock()
            manager.victory_jingle(None)
            player.return_value.play_once.assert_not_called()
