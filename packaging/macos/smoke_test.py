"""Run the installed runtime without using personal profiles or loading GGUFs."""
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


def main():
    import numpy
    import yaml
    import requests
    import libzim
    from llama_cpp import llama_cpp
    assert Path(llama_cpp.__file__).resolve().is_relative_to(Path(__file__).resolve().parent), 'external llama installation'
    from PySide6 import __version__ as qt_version
    from PySide6.QtCore import QObject, Signal, QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication, QWidget, QPushButton
    from PySide6.QtMultimedia import QMediaPlayer
    from PySide6.QtSvg import QSvgRenderer
    import ssl
    import sqlite3
    report = dict(architecture=platform.machine(), python=sys.version.split()[0], qt=qt_version,
                  numpy=numpy.__version__, wiki='available', ssl=ssl.OPENSSL_VERSION,
                  sqlite=sqlite3.sqlite_version,
                  gpu_offload=bool(llama_cpp.llama_supports_gpu_offload()),
                  cpu_variant=os.environ.get('MAAT_CPU_VARIANT','native'),
                  backend_info=llama_cpp.llama_print_system_info().decode('utf-8','replace'),
                  llama_library=str(llama_cpp._lib._name))
    if report['architecture'] == 'x86_64':
        parent = Path(report['llama_library']).parent
        assert (parent.name == 'avx2') == (report['cpu_variant'] == 'avx2'), 'wrong Intel library selected'
        assert (parent/'libggml-cpu.0.dylib').is_file(), 'missing selected CPU backend'

    class SilentAudio(QObject):
        status = Signal(str)
        music_enabled = False
        def __init__(self):
            super().__init__()
            self.events = []
        def location(self, *args): pass
        def set_volume(self, *args): pass
        def set_enabled(self, *args): pass
        def close(self): pass
        def handle_event(self, event): self.events.append(event)

    with tempfile.TemporaryDirectory(prefix='maat-bundle-check-') as temp:
        root = Path(temp)
        with patch('pathlib.Path.home', return_value=root), patch.dict(os.environ):
            for key in list(os.environ):
                if key.startswith('MAAT_') and key.endswith('_DIR'):
                    os.environ.pop(key)
            support = root / 'Library/Application Support/MAAT-RPG'
            os.environ['MAAT_GUI_DATA_ROOT'] = str(support)
            app = QApplication.instance() or QApplication([])
            def spin_until(predicate, seconds=12):
                deadline = time.monotonic() + seconds
                while not predicate() and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.01)
                assert predicate(), 'runtime operation did not finish'

            # Exercise the real packaged audio helper, without playing sound.
            from gui.audio_process import AudioProcess
            audio = AudioProcess(timeout_ms=10000)
            audio_errors, availability = [], []
            audio.error.connect(audio_errors.append)
            audio.availability.connect(availability.append)
            try:
                spin_until(lambda: bool(availability) or bool(audio_errors))
                assert not audio_errors, audio_errors
                for output in audio.outputs.values():
                    output.setVolume(0)
                audio.select_output(audio.devices[0][0] if audio.devices else '')
                spin_until(lambda: not audio._pending or bool(audio_errors))
                assert not audio_errors, audio_errors
                report.update(audio_helper='ok', audio_output_switch='ok',
                              audio_devices=len(audio.devices), audio_playback_tested=False)
            finally:
                audio.close()
                spin_until(lambda: not audio._retired)
                audio.deleteLater()
                app.processEvents()
            from gui.live_window import LiveWindow
            from apps.maat_rpg import session_shared
            window = LiveWindow(audio=SilentAudio())
            try:
                assert window.phase == 'language'
                assert window.game.process is None
                window.language_screen.buttons['en'].click()
                assert window.phase == 'title'
                assert window.game.process is None
                assert window.title_screen.landscape.key == 'pyramid'
                window.request_title_start()
                assert window.phase == 'profiles'
                assert len(window.profile_screen.cards) == 0
                assert session_shared.create_profile('Installer test') == 1
                window.choose_profile(1)
                assert window.phase == 'title'
                deadline = time.monotonic() + 30
                while not window.game.ready and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.01)
                assert window.game.ready, 'game worker did not become ready'
                worker_logs = list((support/'logs').glob('worker-*.log'))
                assert worker_logs, 'worker startup diagnostics missing'
                worker_log = worker_logs[-1].read_text()
                assert 'cpu_variant=' + repr(os.environ.get('MAAT_CPU_VARIANT', 'default')) in worker_log, 'worker changed CPU variant'
                report['worker_cpu_variant'] = os.environ.get('MAAT_CPU_VARIANT', 'default')
                assert session_shared.profile_language(1) == 'en'
                window.ki_dialog.hide()
                window.enter_menu()
                assert window.reveal_button.text() == 'Reveal text'
                tuning = window.model_tuning
                from shared.core.gguf_adapters import selected_adapter
                assert window.backend_combo.count() == 1
                assert window.backend_combo.currentData() == selected_adapter()
                assert window.context_size.maximum() == 100000
                assert window.context_size.value() == 20000
                assert tuning.intel_adapter == (selected_adapter() == 'llama_intel')
                report['gguf_adapter'] = selected_adapter()
                assert tuning.settings()['mode'] == 'auto'
                tuning.mode.setCurrentIndex(tuning.mode.findData('manual'))
                tuning.fields['threads'].setValue(3)
                assert tuning.settings()['manual']['threads'] == 3
                tuning.mode.setCurrentIndex(tuning.mode.findData('auto'))
                assert tuning.settings()['mode'] == 'auto'
                # Verify the actual bundled PNG decoder, all region images and
                # the title/menu wiring in both architectures, without a model.
                from shared.core.terra_journey import snapshot as journey_snapshot
                from gui.title_artwork import REGION_KEYS, REGIONS_EN
                for region, key in enumerate(REGION_KEYS):
                    journey = journey_snapshot({'world':{'combat_unlocked':True},
                        'stats':{'boss_wins':region*5, 'final_wins':region}})
                    window.update_title_artwork(journey)
                    art = window.title_screen.landscape
                    assert art.key == key and not art.image.isNull(), key
                    assert window.menu_pyramid.image.cacheKey() == art.image.cacheKey()
                    assert art.caption() == REGIONS_EN[region]
                    assert not art.grab().isNull()
                window.update_title_artwork(journey_snapshot({}))
                assert window.title_screen.landscape.key == 'pyramid'
                report.update(title_artwork='ok', title_artwork_regions=len(REGION_KEYS))
                # Regress the Intel report's button-construction/input-filter
                # path while a level/profile refresh and text display overlap.
                window.phase='playing'; window.navigate(3)
                dungeon_body=window.dungeons.scroll.widget()
                dungeon_buttons=list(window.dungeons.buttons)
                with patch('gui.application_input.diagnostic_exception') as filter_errors:
                    for level in range(2, 12):
                        window.receive(dict(event='output', text='The journey continues. ' * 3))
                        window.receive(dict(event='level_up', level=level, title='Traveller', max_hp=100+level*10, language='en'))
                        snapshot=window.game.get_snapshot()
                        snapshot.player.level=level
                        window.apply_snapshot(snapshot)
                        window.receive(dict(event='dungeons', level=level, records={}, plus={}))
                        assert window.dungeons.scroll.widget() is dungeon_body
                        assert window.dungeons.buttons == dungeon_buttons
                        panel=QWidget(window)
                        for i in range(20): QPushButton(f'Talent {i}', panel)
                        panel.deleteLater()
                        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                        app.processEvents()
                        window.text_stream.finish()
                    filter_errors.assert_not_called()
                assert not window.level_up_notice.grab().isNull()
                assert 'Level 11' in window.chat_level_text.text()
                window.level_up_notice.dismiss()
                report.update(level_up='ok', input_filter='ok', dungeon_refresh='ok', level_refreshes=10, buttons_created=200)
                # A post-stream edit must replace the reply at its queued
                # boundary and preserve subsequent game notifications.
                window.journal.clear(); window.world_output.clear()
                for event in (
                    dict(event='chat_response', action='begin', id='bundle'),
                    dict(event='output', text='Hello!\nHello!\n'),
                    dict(event='chat_response', action='end', id='bundle'),
                    dict(event='output', text='Quest complete\n'),
                    dict(event='chat_response', action='replace', id='bundle',
                         original='Hello!\nHello!', text='Hello!')):
                    window.receive(event)
                window.text_stream.finish()
                assert window.journal.toPlainText() == 'Hello!\nQuest complete\n'
                assert window.world_output.toPlainText() == window.journal.toPlainText()
                layout = window.chat_level_panel.layout()
                assert layout.indexOf(window.chat_xp_bar) < layout.indexOf(window.model_timing) < layout.indexOf(window.wiki_source)
                window.receive(dict(event='wiki_context', titles=['Mona Lisa'], terms=['Mona Lisa']))
                wiki = window.wiki_source.text()
                window.model_timing.handle(dict(event='model_load_started', name='Preview.gguf', backend=selected_adapter()))
                assert 'Loading AI model' in window.model_timing.title.text()
                window.model_timing.handle(dict(event='model', status='ready'))
                window.model_timing.handle(dict(event='chat_generation'))
                window.model_timing.handle(dict(event='chat_first_token'))
                assert 'First token received' in window.model_timing.detail.text()
                assert window.wiki_source.text() == wiki
                report.update(chat_response='ok', model_timing='ok')
                window.arena.update_state(dict(active=True, enemy_name='Shadow Guardian',
                    round_number=1, player_hp=90, player_max_hp=100, enemy_hp=60, enemy_max_hp=80))
                app.processEvents()
                assert not window.arena.grab().isNull()
                report.update(profile='isolated', language_choice='ok', game_worker='ok',
                              battle_render='ok', model_settings='ok', model_loaded=False)
            finally:
                window.game.shutdown()
                window.close()
                window.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                app.processEvents()
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
