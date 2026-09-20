"""The world endpoint replays the existing ending without campaign side effects."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from test_desktop import APP
from test_live_rpg import Worker
from test_terra_replay import complete
import test_live_window as helpers
from apps.maat_rpg import session_shared
from gui.live_window import LiveWindow
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtTest import QTest


class CreditsWorkerTests(unittest.TestCase):
    def test_both_endings_are_repeatable_and_do_not_change_progress_or_memories(self):
        state=complete();state['world']['terra_replay_pending']='boss-7'
        worker=Worker(seed={'battle_state.json':state})
        try:
            path=Path(worker.temp.name)/'state/battle_state.json'
            before=json.loads(path.read_text())
            for mode in ('adventure','companion'):
                if mode=='companion':worker.command('/ai-start')
                memory_path=Path(worker.temp.name)/'state/ai_companion.json'
                memories=memory_path.read_bytes() if memory_path.exists() else None
                for _ in range(2):
                    worker.send(op='terra_credits',profile_slot=1)
                    events=worker.until(lambda e:e['event']=='busy' and not e['value'])
                    scenes=[e for e in events if e['event']=='story_scene']
                    self.assertEqual(len(scenes),1)
                    self.assertEqual(scenes[0]['module'],'credits' if mode=='adventure' else 'companion_credits')
                    self.assertTrue(Path(scenes[0]['music']).is_file())
                    self.assertIn('Konzept & Universum:       Christof Krieg',scenes[0]['lines'])
                    self.assertTrue(any(e['event']=='speech_stopped' and e['reason']=='credits' for e in events))
                    self.assertFalse(any(e['event']=='battle' for e in events))
                    after=json.loads(path.read_text())
                    for field in ('stats','player','world'):
                        self.assertEqual(before[field],after[field])
                    self.assertEqual(memory_path.read_bytes() if memory_path.exists() else None,memories)
        finally:worker.close()

    def test_worker_rejects_locked_or_other_profile(self):
        for seed,slot in [(complete(),2),({'world':{'combat_unlocked':True},'stats':{'final_wins':4}},1)]:
            worker=Worker(seed={'battle_state.json':seed})
            try:
                worker.send(op='terra_credits',profile_slot=slot)
                events=worker.until(lambda e:e['event']=='busy' and not e['value'])
                self.assertTrue(any(e['event']=='terra_credits_error' for e in events))
                self.assertFalse(any(e['event']=='story_scene' for e in events))
            finally:worker.close()


class CreditsMapTests(unittest.TestCase):
    spin=helpers.LiveWindowTest.spin
    def test_click_plays_cinema_and_returns_to_last_region(self):
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            helpers.unlock_test_arena()
            path=session_shared.profile_slot_root(session_shared.active_profile_slot())/'state/battle_state.json'
            original=path.read_bytes()
            path.write_text(json.dumps(complete()))
            audio=helpers.SilentAudio();w=LiveWindow(audio=audio)
            w.request_title_start()
            w.choose_profile(w.game._profile_slot())
            try:
                w.resize(1220,900);w.show();self.spin(lambda:w.game.ready)
                w.ki_dialog.hide();w.phase='playing';w.navigate(3);w.open_terra_map()
                view=w.terra_view;button=view.board.end_button
                self.assertTrue(button.isHidden())
                view.region_choice.setCurrentIndex(4);APP.processEvents()
                self.assertTrue(button.isVisible());self.assertTrue(button.isEnabled())
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    out=Path(os.environ['MAAT_GUI_SCREENSHOTS']);out.mkdir(parents=True,exist_ok=True)
                    w.grab().save(str(out/'world-end.png'))
                    w.resize(880,650);APP.processEvents();w.grab().save(str(out/'world-end-small.png'))
                    w.resize(1220,900)
                w.game.busy=True;w.update_controls();self.assertFalse(button.isEnabled())
                w.game.busy=False;w.update_controls()
                QTest.mouseClick(button,Qt.LeftButton)
                self.spin(lambda:w.phase=='story')
                self.assertIs(w.stack.currentWidget(),w.credits_screen)
                self.assertTrue(w.credits_screen.running)
                self.assertFalse(w.credits_screen.isWindow())
                self.assertTrue(any(e.get('owner')=='credits-screen' and e['action']=='play' for e in audio.events))
                w.credits_screen.pause_button.click();self.assertTrue(w.credits_screen.paused)
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    w.credits_screen.canvas.time=25;w.credits_screen.canvas.offset=700
                    APP.processEvents();w.grab().save(str(out/'credits-from-map.png'))
                w.credits_screen.skip_button.click()
                self.spin(lambda:not w.game.busy)
                self.assertEqual(w.phase,'playing');self.assertEqual(w.stack.currentIndex(),w.terra_index)
                self.assertEqual(view.region_choice.currentIndex(),4)
                self.assertFalse(w.credits_screen.timer.isActive());self.assertTrue(button.isEnabled())
                self.assertTrue(any(e.get('owner')=='credits-screen' and e['action']=='stop' for e in audio.events))
                # The endpoint remains repeatable and hides on a different region.
                view.region_choice.setCurrentIndex(0);self.assertTrue(button.isHidden())
            finally:
                w.game.shutdown();w.close();w.deleteLater()
                QCoreApplication.sendPostedEvents(w,QEvent.DeferredDelete);APP.processEvents()
                path.write_bytes(original)


if __name__=='__main__':unittest.main()
