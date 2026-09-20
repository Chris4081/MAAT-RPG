"""Replay the real level-up output through a packaged GUI, without an LLM or real save."""
import argparse
from contextlib import redirect_stdout
import faulthandler
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import traceback
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--silent', action='store_true')
    parser.add_argument('--wait-audio-end', action='store_true')
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.game_root))
    faulthandler.enable()
    faulthandler.dump_traceback_later(75, exit=True)
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    with tempfile.TemporaryDirectory(prefix='maat-levelup-probe-') as folder, patch.dict(os.environ), patch('pathlib.Path.home', return_value=Path(folder)):
        for key in tuple(os.environ):
            if key.startswith('MAAT_') and key.endswith('_DIR'):
                os.environ.pop(key)
        os.environ['MAAT_GUI_DATA_ROOT'] = folder
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QCoreApplication, QEvent
        from apps.maat_rpg import session_shared as shared
        from shared.core import gui_bridge
        from gui.audio_manager import AudioManager
        from gui.live_window import LiveWindow
        from apps.maat_rpg.plugins.battle.plugin_main import run_levelup_fx
        from gui.game_worker import RemoteAudio
        shared.write_application_language('en')
        shared.prepare_profile_runtime(1, language_hint='en')
        app = QApplication([])
        audio = AudioManager()
        window = LiveWindow(audio=audio)
        errors = []
        def report_error(*error):
            errors.append(repr(error))
            traceback.print_exception(*error)
        sys.excepthook = report_error
        try:
            window.show(); window.phase='playing'; window.navigate(3)
            audio.set_enabled(False, not args.silent)
            audio.set_volume(0)
            audio_ended, audio_errors = [], []
            if audio.native_fx:
                audio.native_fx.ended.connect(lambda: audio_ended.append(True))
                audio.native_fx.error.connect(audio_errors.append)
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                app.processEvents(); time.sleep(.01)
            captured = []
            gui_bridge.install(lambda kind, **data: captured.append(dict(event=kind, **data)))
            output = io.StringIO()
            with redirect_stdout(output), patch('time.sleep'), \
                    patch('apps.maat_rpg.plugins.battle.plugin_main.ManagedAudioPlayer', RemoteAudio), \
                    patch('gui.game_worker.emit', lambda kind, **data: captured.append(dict(event=kind, **data))):
                run_levelup_fx(2, None, str(args.game_root/'apps/maat_rpg/plugins/battle'))
            gui_bridge.install(None)
            text = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', output.getvalue())
            print(json.dumps(dict(phase='begin', architecture=__import__('platform').machine(),
                                  stars=text.count('✨'), audio_events=len(captured))), flush=True)
            assert any(e['event']=='audio' and e['action']=='play' for e in captured)
            native_notice = any(e['event']=='level_up' for e in captured)
            if native_notice:
                assert not text.strip(), text
            for iteration in range(5):
                ends_before = len(audio_ended)
                window.receive(dict(event='output', text='The journey continues. ' * 15))
                window.text_stream.advance()
                for event in captured:
                    window.receive(event)
                window.receive(dict(event='level_progress', level=iteration+2, xp=0, next_xp=300, gain=12))
                window.receive(dict(event='output', text=text))
                while window.text_stream.running:
                    window.text_stream.advance()
                    app.processEvents(); time.sleep(.003)
                if args.screenshot and iteration == 0:
                    window.grab().save(str(args.screenshot))
                if args.wait_audio_end and not args.silent:
                    deadline = time.monotonic()+9
                    while len(audio_ended)==ends_before and not audio_errors and time.monotonic()<deadline:
                        app.processEvents(); time.sleep(.01)
                    assert not audio_errors, audio_errors
                    assert len(audio_ended)>ends_before, 'Level-up audio did not finish naturally'
                if native_notice:
                    window.level_up_notice.dismiss()
                deadline=time.monotonic()+.25
                while time.monotonic()<deadline:
                    app.processEvents(); time.sleep(.01)
                assert not window.journal.grab().isNull()
                assert not errors, errors
                print('PASS level-up replay', iteration+1, flush=True)
            print('PASS: level-up output, GUI audio dispatch and continued input; natural audio ends:', len(audio_ended), flush=True)
        finally:
            gui_bridge.install(None)
            window.close(); window.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            app.processEvents()
    faulthandler.cancel_dump_traceback_later()


if __name__ == '__main__':
    main()
