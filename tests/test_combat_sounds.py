import os
import time
import unittest
import wave
from unittest.mock import Mock, patch

import numpy as np
from test_desktop import APP
from PySide6.QtCore import QCoreApplication, QEvent, QUrl
from PySide6.QtMultimedia import QAudioBufferOutput, QMediaPlayer
from apps.maat_rpg import session_shared
from gui.audio_manager import AudioManager
from gui.combat_sounds import attack_sound, combat_sound


def attack(key, attacker='player'):
    return dict(event='battle_effect', attacker=attacker, attack=key,
                damage=14, enemy_name='Schattenwächter')


class CombatSoundsTests(unittest.TestCase):
    def dispose(self, audio):
        audio.close()
        audio.deleteLater()
        QCoreApplication.sendPostedEvents(audio, QEvent.DeferredDelete)
        APP.processEvents()

    def test_five_distinct_pcm_cues_fit_the_animation_without_clipping(self):
        contents = set()
        for key in 'HBSVR':
            with self.subTest(key=key), wave.open(str(attack_sound(attack(key)))) as wav:
                self.assertEqual((wav.getnchannels(), wav.getsampwidth(), wav.getframerate()), (2, 2, 48000))
                self.assertLess(wav.getnframes()/48000, 7*.225)
                data = wav.readframes(wav.getnframes())
                contents.add(data)
                samples = np.frombuffer(data, dtype='<i2').reshape(-1, 2).astype(float)/32768
                self.assertLess(np.max(np.abs(samples)), .57)
                self.assertGreater(np.sqrt(np.mean(samples**2)), .06)
                self.assertTrue(np.all(samples[-100:] == 0))
                self.assertTrue(np.all(samples[0] == 0))
                # Mono mix must retain the sound, and attack onset must be prompt.
                self.assertGreater(np.sqrt(np.mean(samples.mean(axis=1)**2)), .05)
                self.assertLess(np.flatnonzero(np.max(np.abs(samples), axis=1) > .025)[0]/48000, .03)
        self.assertEqual(len(contents), 5)

    def test_principles_follow_german_english_and_letter_attack_names(self):
        for key, de, en in [('H', 'Harmonie', 'Harmony'), ('B', 'Balance', 'Balance'),
                            ('S', 'Schöpfungskraft', 'Creation'),
                            ('V', 'Verbundenheit', 'Connectedness'), ('R', 'Respekt', 'Respect')]:
            self.assertEqual(attack_sound(attack(key)), attack_sound(attack(de)))
            self.assertEqual(attack_sound(attack(key)), attack_sound(attack(en)))
            self.assertIsNone(attack_sound(attack(key, attacker='enemy')))
        for key in ('skill', 'focus', 'heal', 'potion', 'impulse', 'special'):
            self.assertIsNone(attack_sound(attack(key)))

    def test_all_wavs_decode_on_fx_channel_without_restarting_music(self):
        audio = AudioManager(backend='qt')
        audio.player.setAudioOutput(None)
        audio.fx.setAudioOutput(None)
        capture = QAudioBufferOutput(audio)
        decoded = []
        capture.audioBufferReceived.connect(lambda buffer: decoded.append(buffer.byteCount()))
        audio.fx.setAudioBufferOutput(capture)
        try:
            with patch.object(audio.player, 'play') as music_play, patch.object(audio.player, 'setSource'):
                audio.location(True)
                current = audio.current
                music_play.reset_mock()
                audio.set_volume(23)
                events = [attack(key) for key in 'HBSVR'] + [attack('normal', attacker='enemy')]
                for event in events:
                    decoded.clear()
                    audio.handle_event({'action':'effect', 'attack_event':event})
                    deadline = time.monotonic()+4
                    while not any(decoded) and time.monotonic() < deadline:
                        APP.processEvents()
                        time.sleep(.005)
                    self.assertTrue(any(decoded), event)
                    self.assertEqual(audio.fx.source().toLocalFile(), str(combat_sound(event)))
                    self.assertEqual(audio.fx.loops(), 1)
                    self.assertEqual(audio.current, current)
                self.assertAlmostEqual(audio.fx_output.volume(), .23, places=5)
                music_play.assert_not_called()
                audio.set_enabled(True, False)
                with patch.object(audio.fx, 'play') as play:
                    audio.handle_event({'action':'effect', 'attack_event':attack('H')})
                    play.assert_not_called()
                self.assertEqual(audio.fx.playbackState(), QMediaPlayer.StoppedState)
                audio.set_enabled(False, True)
                audio.handle_event({'action':'effect', 'attack_event':attack('H')})
                self.assertIsNone(audio.current)
                self.assertEqual(audio._fx_path, attack_sound(attack('H')))
                audio.handle_event({'action':'clear'})
                self.assertIsNone(audio._fx_path)
                self.assertEqual(audio.fx.playbackState(), QMediaPlayer.StoppedState)
        finally:
            audio.fx.stop()
            audio.fx.setSource(QUrl())
            audio.fx.setAudioBufferOutput(None)
            capture.audioBufferReceived.disconnect()
            # The test-only PCM tap must die while its QMediaPlayer still exists.
            # Qt 6 can retain that player pointer until the tap's destructor.
            capture.deleteLater()
            QCoreApplication.sendPostedEvents(capture, QEvent.DeferredDelete)
            self.dispose(audio)

    def test_mac_uses_existing_fx_channel_and_recovers_failed_cue(self):
        with patch('gui.audio_manager.sys.platform', 'darwin'), \
                patch('gui.audio_manager.shutil.which', return_value='/usr/bin/afplay'):
            audio = AudioManager()
        try:
            self.assertFalse(audio.native_fx.restart_on_volume_change)
            with patch.object(audio.native_fx, 'play') as native_play, \
                    patch.object(audio.fx, 'play') as qt_play, \
                    patch.object(audio.native_music, 'play') as music_play:
                audio.handle_event({'action':'effect', 'attack_event':attack('R')})
                native_play.assert_called_once_with(attack_sound(attack('R')))
                qt_play.assert_not_called()
                audio.native_fx.error.emit('Simulierter Ausgabefehler')
                qt_play.assert_called_once()
                self.assertEqual(audio.fx.source().toLocalFile(), str(attack_sound(attack('R'))))
                self.assertTrue(audio._native_fx_failed)
                music_play.assert_not_called()
        finally:
            self.dispose(audio)

    def test_live_and_demo_cues_wait_for_queued_animation_start(self):
        from gui.live_window import LiveWindow
        from test_live_window import SilentAudio, LiveWindowTest
        audio = SilentAudio()
        with patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT': str(session_shared.BASE_APP_SUPPORT_DIR)}):
            window = LiveWindow(audio=audio)
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
            try:
                LiveWindowTest.spin(self, lambda:window.game.ready)
                for demo in (False, True):
                    window.phase = 'title_demo' if demo else 'playing'
                    stage = window.title_screen.arena.stage if demo else window.arena.stage
                    stage.clear_effects()
                    audio.events.clear()
                    deliver = window.present_demo if demo else window.receive
                    events = [attack(key) for key in 'HBSVR'] + [dict(attack('normal', attacker='enemy'),
                        player_hp_before=100, player_hp=86)]
                    keys = [e['attack'] for e in events]
                    for event in events:
                        deliver(event)
                    stage.effect_timer.stop()
                    cues = lambda:[e['attack_event']['attack'] for e in audio.events if e['action']=='effect']
                    self.assertEqual(cues(), ['H'])
                    for index in range(1, len(events)):
                        for _ in range(len(stage.frames)):
                            stage.advance_effect()
                        stage.effect_timer.stop()
                        self.assertEqual(cues(), keys[:index+1])
                    self.assertEqual((stage.hit_target, stage.hit_damage), ('player', 14))
                    stage.clear_effects()
                    window.phase = 'menu'
                    stage.show_effect(attack('H'))
                    stage.clear_effects()
                    self.assertEqual(cues(), keys)
            finally:
                window.close()
                window.deleteLater()
                QCoreApplication.sendPostedEvents(window, QEvent.DeferredDelete)
                APP.processEvents()
