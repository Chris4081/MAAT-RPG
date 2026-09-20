import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication, QEvent
from test_desktop import APP
from gui.title_screen import TitleDemo
from apps.maat_rpg import session_shared

class DemoProgressionTests(unittest.TestCase):
    def test_demo_uses_next_boss_and_level_without_changing_save(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'state').mkdir()
            state_path=root/'state/battle_state.json'
            story_path=root/'state/companion_story_state.json'
            story_path.write_text(json.dumps({'choices':{'combat_vow':'protect'},'journal':[{'private':'not copied'}]}))
            (root/'state/settings_state.json').write_text(json.dumps({'gui_perspective':'companion'}))
            for stage,level,boss,final,suffix in [(1,12,1,0,'#2'),(1,24,2,0,'#3'),(2,24,2,1,'(Final 2)')]:
                with self.subTest(stage=stage,level=level,boss=boss):
                    state_path.write_text(json.dumps({'player':{'level':level,'hp':1,'max_hp':400,'xp':250},'stats':{'boss_wins':boss,'final_wins':final},'world':{'principles_restored':final}}))
                    before={p.name:p.read_bytes() for p in (root/'state').iterdir()}
                    runner=TitleDemo();seen=[];runner.presented.connect(seen.append)
                    try:
                        with patch.object(session_shared,'profile_slot_root',return_value=root):
                            runner.start(stage,profile_slot=2)
                        copied=json.loads((Path(runner.temp.name)/'state/story_state.json').read_text())
                        self.assertEqual(copied['choices']['combat_vow'],'protect')
                        self.assertNotIn('journal',copied)
                        end=time.monotonic()+25
                        while not runner.finished and time.monotonic()<end:
                            APP.processEvents();time.sleep(.01)
                        self.assertTrue(runner.finished)
                        events=seen+list(runner.queue)
                        self.assertFalse([e for e in events if e['event']=='error'])
                        # The blank encounter marker precedes the narrated boss entrance.
                        hud=next(e for e in events if e['event']=='battle' and e.get('enemy_name') and 'enemy_max_hp' in e)
                        self.assertEqual(hud['player_level'],level)
                        self.assertEqual(hud['player_hp'],400)
                        self.assertTrue(hud['enemy_name'].endswith(suffix),hud['enemy_name'])
                        self.assertEqual(hud['fight_type'],'boss' if stage==1 else 'final')
                        self.assertEqual(before,{p.name:p.read_bytes() for p in (root/'state').iterdir()})
                    finally:
                        runner.stop();runner.deleteLater()
                        QCoreApplication.sendPostedEvents(runner,QEvent.DeferredDelete)
