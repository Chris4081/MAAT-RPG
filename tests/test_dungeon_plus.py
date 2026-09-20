import json
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from test_desktop import APP
from test_live_rpg import Worker
from shared.core.dungeon_campaign import run_endless,dungeon
from gui.dungeons import Dungeons
from gui.audio_manager import AudioManager
from PySide6.QtMultimedia import QMediaPlayer

class PlusTests(unittest.TestCase):
    def test_unlock_and_more_than_five_waves(self):
        core=Mock();core.state.state={'player':{'level':49,'hp':999},'stats':{'fights_won':0}}
        with self.assertRaises(ValueError):run_endless(core,Mock(),Mock())
        core.state.state['player']['level']=50;contexts=[]
        def fight(kind,context):
            contexts.append(context)
            if len(contexts)<=12:core.state.state['stats']['fights_won']+=1
        core.run_fight.side_effect=fight;notify=Mock()
        self.assertEqual(run_endless(core,Mock(),notify),12)
        self.assertEqual(len(contexts),13)
        state=core.state.state['dungeon_plus'];self.assertEqual(state['best_wave'],12);self.assertEqual(state['total_wins'],12)
        self.assertGreater(contexts[-1]['battle_profile']['enemy']['hp_mult'],contexts[0]['battle_profile']['enemy']['hp_mult'])
        audio=[c.kwargs for c in notify.call_args_list if c.args==('audio',)]
        self.assertEqual([e['action'] for e in audio],['play','stop']);self.assertEqual(len(audio[0]['playlist']),3)
        w=Dungeons()
        try:
            for level in (49,50):
                w.update_data(level,{},state);w.set_ready(True);self.assertEqual(w.plus_button.isEnabled(),level==50)
            self.assertIn('12 Wellen',w.plus_info.text())
        finally:w.deleteLater();APP.processEvents()
    def test_music_playlist_both_backends_cycles_and_stops(self):
        tracks=[dungeon(i)['theme'] for i in range(3)]
        for native in (False,True):
            with patch('gui.audio_manager.shutil.which',return_value='/usr/bin/afplay' if native else None):
                a=AudioManager()
                try:
                    a.menu=False
                    with patch.object(a.player,'play') as play:
                        if native:a.native_music.play=Mock()
                        a.handle_event({'action':'play','owner':'dungeon-plus','playlist':tracks})
                        for n in range(7):
                            self.assertEqual(a.current[1],tracks[n%3]);self.assertFalse(a.current[2])
                            before=(a.native_music.play.call_count if native else play.call_count)
                            a.location(False);a.handle_event({'action':'stop','owner':'story-screen'})
                            self.assertEqual((a.native_music.play.call_count if native else play.call_count),before)
                            if native:a._native_ended()
                            else:
                                with patch.object(a.player,'mediaStatus',return_value=QMediaPlayer.EndOfMedia):a._ended(QMediaPlayer.EndOfMedia)
                        a.set_enabled(False,True);self.assertIsNone(a.current)
                        a.set_enabled(True,True);self.assertEqual(a.current[1],tracks[1])
                        a.handle_event({'action':'stop','owner':'dungeon-plus'});self.assertFalse(a.playlists);self.assertIsNone(a.current)
                        a._native_ended();self.assertIsNone(a.current)
                finally:a.close();a.deleteLater();APP.processEvents()
    def test_real_worker_six_wins_then_flee(self):
        w=Worker(seed={'battle_state.json':{'player':{'level':50,'hp':99999,'max_hp':99999},'stats':{'boss_progress':3},'world':{'combat_unlocked':False}}})
        events=[];wave=1;battle={}
        try:
            w.send(op='text',text='/dungeon-plus')
            for _ in range(250):
                batch=w.until(lambda e:e['event']=='prompt' or (e['event']=='busy' and not e['value']),timeout=30);events+=batch
                for e in batch:
                    if e['event']=='dungeon_progress' and e.get('active'):wave=e['room']
                    if e['event']=='battle':battle.update(e)
                e=batch[-1]
                if e['event']!='prompt':break
                value='6' if wave==7 else {'harmonie':'1','balance':'2','schöpfungskraft':'3','verbundenheit':'4','respekt':'5'}.get(str(battle.get('weakness','')).lower(),'3')
                w.send(op='answer',id=e['id'],value=value)
            else:self.fail('No exit after flee')
            saved=json.loads((Path(w.temp.name)/'state/battle_state.json').read_text())
            self.assertEqual(saved['dungeon_plus']['best_wave'],6);self.assertEqual(saved['dungeon_plus']['last_wave'],6)
            self.assertEqual(saved['stats']['boss_progress'],3)
            audio=[e for e in events if e['event']=='audio' and e.get('owner')=='dungeon-plus']
            self.assertEqual([e['action'] for e in audio],['play','stop'])
            other=[e for e in events if e['event']=='audio' and e.get('action')=='play' and e.get('owner')!='dungeon-plus' and not e.get('path','').endswith('levelup.mp3')]
            self.assertFalse(other)
        finally:w.close()
