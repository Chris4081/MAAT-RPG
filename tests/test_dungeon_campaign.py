import json
import os
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from test_desktop import APP
from test_live_rpg import Worker
import test_live_window as helpers
from apps.maat_rpg import session_shared
from shared.core.dungeon_campaign import dungeon,catalog,run
from gui.live_window import LiveWindow

class DungeonTests(unittest.TestCase):
    def test_levels_music_and_five_rooms_stop_on_loss(self):
        self.assertEqual([d['level'] for d in catalog(50)],list(range(10,56,5)))
        for i in range(15):
            d=dungeon(i);self.assertEqual(d['level'],10+5*i)
            self.assertTrue(Path(d['theme']).is_file());self.assertTrue(Path(d['boss_music']).is_file())
        core=Mock();core.state.state={'player':{'level':9,'hp':100},'stats':{'fights_won':0}}
        with self.assertRaises(ValueError):run(core,0,Mock(),Mock())
        core.run_fight.assert_not_called();core.state.state['player']['level']=10
        calls=[]
        def fight(*args,**kwargs):
            calls.append(kwargs['context']);core.state.state['player']['hp']-=10
            if len(calls)<3:core.state.state['stats']['fights_won']+=1
        core.run_fight.side_effect=fight;narrate=Mock();notify=Mock()
        self.assertFalse(run(core,0,narrate,notify));self.assertEqual(len(calls),3)
        self.assertEqual(core.state.state['dungeon_runs']['0']['best_room'],2)
        self.assertEqual(core.state.state['player']['hp'],70)
        self.assertFalse(notify.call_args.kwargs['active'])
        audio=[c.kwargs for c in notify.call_args_list if c.args==('audio',)]
        self.assertEqual([c['action'] for c in audio],['play','stop'])
        self.assertTrue(all(c.args[1] is None for c in narrate.call_args_list))
    def test_real_five_fights_keep_story_boss_progress_and_music(self):
        w=Worker(seed={'battle_state.json':{'player':{'level':10,'hp':9999,'max_hp':9999},'stats':{'boss_progress':7,'messages_since_last_fight':4},'world':{'combat_unlocked':False}}})
        all_events=[];battle={}
        try:
            w.send(op='text',text='/dungeon-enter 0')
            for _ in range(180):
                events=w.until(lambda e:e['event']=='prompt' or (e['event']=='busy' and not e['value']),timeout=30);all_events+=events
                for e in events:
                    if e['event']=='battle':battle.update(e)
                e=events[-1]
                if e['event']!='prompt':break
                value={'harmonie':'1','balance':'2','schöpfungskraft':'3','verbundenheit':'4','respekt':'5'}.get(str(battle.get('weakness','')).lower(),'3')
                w.send(op='answer',id=e['id'],value=value)
            else:self.fail('Dungeon did not finish')
            saved=json.loads((Path(w.temp.name)/'state/battle_state.json').read_text())
            self.assertEqual(saved['dungeon_runs']['0']['completed'],1)
            self.assertEqual(saved['dungeon_runs']['0']['best_room'],5)
            self.assertEqual(saved['stats']['boss_progress'],7)
            self.assertEqual(saved['stats']['boss_wins'],0)
            self.assertEqual(saved['stats']['messages_since_last_fight'],4)
            starts=[e for e in all_events if e['event']=='dungeon_progress' and e.get('active')]
            self.assertEqual([e['room'] for e in starts],[1,2,3,4,5])
            music=[e.get('path','') for e in all_events if e['event']=='audio' and e.get('action')=='play']
            self.assertEqual([p for p in music if not p.endswith('levelup.mp3')],[dungeon(0)['theme']])
            track_events=[e for e in all_events if e['event']=='audio' and e.get('owner')=='dungeon-run']
            self.assertEqual([e['action'] for e in track_events],['play','stop'])
            self.assertTrue(track_events[0]['loop'])
            self.assertTrue(all(e.get('music') is None for e in all_events if e['event']=='story_scene'))
            self.assertEqual(len([e for e in all_events if e['event']=='story_scene']),6)
        finally:w.close()
    def test_sidebar_and_battle_before_random_unlock(self):
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            w=LiveWindow(audio=helpers.SilentAudio())
            w.request_title_start()
            w.choose_profile(w.game._profile_slot())
            try:
                helpers.LiveWindowTest.spin(self,lambda:w.game.ready)
                w.phase='playing';w.navigate(3)
                w.game._handle({'event':'profile','data':{'level':10}})
                w.receive({'event':'dungeons','level':10,'records':{}})
                w.open_dungeons();self.assertIs(w.stack.currentWidget(),w.dungeons)
                nav=w.dungeon_button.parentWidget().layout()
                self.assertEqual(nav.indexOf(w.dungeon_button),nav.indexOf(w.nav_buttons[2])+1)
                self.assertTrue(w.dungeons.buttons[0][0].isEnabled());self.assertFalse(w.dungeons.buttons[1][0].isEnabled())
                w.show();APP.processEvents();w.grab().save('/tmp/maat-dungeons.png')
                w.game._handle({'event':'battle','active':True,'enemy_name':'','combat_source':'dungeon'})
                self.assertEqual(w.stack.currentIndex(),2)
                w.game._handle({'event':'battle','active':False})
                w.receive({'event':'dungeon_progress','active':False,'name':'Test','room':0})
                w.update_controls();self.assertIs(w.stack.currentWidget(),w.dungeons)
            finally:w.close();APP.processEvents()

    def test_interrupted_scene_stops_dungeon_music(self):
        core=Mock();core.state.state={'player':{'level':10,'hp':100},'stats':{'fights_won':0}}
        notify=Mock()
        with self.assertRaises(RuntimeError):run(core,0,Mock(side_effect=RuntimeError('scene interrupted')),notify)
        audio=[c.kwargs for c in notify.call_args_list if c.args==('audio',)]
        self.assertEqual([c['action'] for c in audio],['play','stop'])
        core.run_fight.assert_not_called()
