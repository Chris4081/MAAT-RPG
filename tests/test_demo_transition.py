"""Regression coverage for the demo's asynchronous return to the pyramid."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication, QEvent
from test_desktop import APP, ROOT
from test_live_window import SilentAudio
from gui.live_window import LiveWindow
from gui.title_screen import TitleDemo
from apps.maat_rpg import session_shared


class DemoTransitionTests(unittest.TestCase):
    def spin(self, condition):
        deadline = time.monotonic()+10
        while not condition() and time.monotonic()<deadline:
            APP.processEvents(); time.sleep(.01)
        self.assertTrue(condition())

    def dispose(self, widget):
        widget.close(); widget.deleteLater()
        QCoreApplication.sendPostedEvents(widget, QEvent.DeferredDelete)

    def test_return_is_once_deferred_and_can_be_cancelled_by_enter(self):
        with patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            window = LiveWindow(audio=SilentAudio())
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
            try:
                window.show(); self.spin(lambda: window.game.ready and not window.game.busy)
                window.model_ready = True
                window.demo_stage = 1
                window.phase = 'title_demo'
                window.title_screen.show_demo()
                arena = window.title_screen.arena
                arena.update_state(dict(active=True,enemy_name='Boss',enemy_hp=10,enemy_max_hp=10,
                                        player_hp=100,player_max_hp=100,resonance=100))
                arena.stage.show_effect(dict(attacker='player',attack='impulse',damage=10))
                arena.stage.show_effect(dict(attacker='player',attack='Harmonie',damage=10))
                arena.update_state(dict(active=False,enemy_hp=0))
                window.demo_finished(); window.demo_finished()
                self.assertEqual(window.phase, 'title_demo')
                self.assertEqual(window.demo_stage, 1)
                self.assertFalse(arena.stage.effect_timer.isActive())
                self.assertFalse(arena.stage.sway_timer.isActive())
                self.assertFalse(arena.resonance.pulse_timer.isActive())
                self.assertFalse(arena.stage.effects)
                self.spin(lambda: window.phase=='title')
                self.assertEqual(window.demo_stage, 2)
                self.assertTrue(window.isVisible())
                self.assertIs(window.stack.currentWidget(), window.title_screen)
                self.assertEqual(window.title_screen.views.currentIndex(), 0)
                # A queued completion must not reopen the title after Enter or close.
                window.phase='title_demo'
                window.demo_finished()
                window.enter_menu()
                APP.processEvents()
                self.assertEqual(window.phase,'menu')
                self.assertEqual(window.demo_stage,2)
                self.assertFalse(window._demo_return_pending)
                window.phase='title_demo'; window.demo_finished(); window.close()
                APP.processEvents()
                self.assertFalse(window._demo_return_timer.isActive())
                self.assertFalse(window.isVisible())
            finally: self.dispose(window)

    def test_stop_during_presentation_does_not_restart_timer(self):
        runner=TitleDemo()
        try:
            runner.queue.append({'event':'output','text':'Sieg'})
            runner.presented.connect(lambda event: runner.stop())
            runner.advance()
            self.assertFalse(runner.timer.isActive())
            self.assertFalse(runner.queue)
            completed=[]
            runner.completed.connect(lambda:completed.append(True))
            runner.finished=True
            runner.advance(); runner.advance()
            self.assertEqual(completed,[True])
        finally:
            runner.close(); runner.deleteLater()
            QCoreApplication.sendPostedEvents(runner,QEvent.DeferredDelete)

    def test_stopping_running_worker_retires_it_before_removing_its_files(self):
        runner=TitleDemo()
        try:
            runner.start(1)
            self.spin(lambda:runner.ready)
            process=runner.process; private=Path(runner.temp.name)
            runner.stop()
            self.assertIsNone(runner.process)
            self.assertFalse(runner.timer.isActive())
            self.spin(lambda: not runner._retired)
            self.assertFalse(private.exists())
            self.assertFalse(runner.queue)
        finally:
            runner.close(); runner.deleteLater()
            QCoreApplication.sendPostedEvents(runner,QEvent.DeferredDelete)

    def test_python_exception_and_native_handler_use_private_log(self):
        with tempfile.TemporaryDirectory() as folder:
            code = ('from gui.runtime_diagnostics import configure,event; import faulthandler; '
                    'p=configure(); event("demo_return_begin",stage=1); '
                    'assert faulthandler.is_enabled(); raise RuntimeError("transition-test")')
            env=dict(os.environ, MAAT_GUI_DATA_ROOT=folder)
            env.pop('MAAT_APP_SUPPORT_DIR',None)
            result=subprocess.run([sys.executable,'-c',code],env=env,cwd=ROOT/'maatos',capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,1)
            files=list(Path(folder).glob('logs/gui-*.log'))
            self.assertEqual(len(files),1,result.stderr)
            log=files[0].read_text()
            self.assertIn('demo_return_begin',log)
            self.assertIn('RuntimeError: transition-test',log)
            self.assertIn('python_exit',log)
