"""Postgame map selection and real encounters without a GGUF or user profiles."""
import io
import json
import os
from copy import deepcopy
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
from test_live_rpg import Worker
import test_live_window as helpers
from apps.maat_rpg import session_shared
from apps.maat_rpg.plugins.battle import plugin_main as battle
from shared.core import terra_replay as replay, terra_journey as journey, gui_bridge
from gui.live_window import LiveWindow
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtTest import QTest


def complete():
    return {'player':{'hp':99999,'max_hp':99999,'level':50},
            'stats':{'boss_wins':25,'final_wins':5,'boss_progress':7,'fights_won':300},
            'hero_class':{'selected':'robo'},
            'world':{'combat_unlocked':True,'principles_restored':5,'last_boss_checkpoint':25,
                     'credits_played':True,'companion_credits_played':True}}


class ReplayCoreTests(unittest.TestCase):
    def make_core(self, folder):
        core=battle.BattleCore(folder)
        core.state.state=core.state._default()
        for key,value in complete().items():core.state.state.setdefault(key,{}).update(value)
        core.state.state_path=str(Path(folder)/'state.json')
        core.state.save()
        core._load_story_state=lambda:{'played':[1,2,3],'choices':{},'journal':[]}
        core._save_story_state=Mock()
        core._register_boss_codex_entry=Mock()
        core._slow_line=Mock()
        core._prompt=Mock(return_value='1')
        return core

    def test_catalog_gate_queue_persistence_and_failed_write(self):
        rows=replay.targets()
        self.assertEqual(len(rows),30)
        self.assertEqual(len({r['id'] for r in rows}),30)
        self.assertTrue(all(len([r for r in rows if r['region']==i])==6 for i in range(5)))
        for key in ('boss-0','boss-26','final-6',None,'../../story'):
            with self.assertRaises(ValueError):replay.resolve(complete(),key)
        state=complete();state['stats']['final_wins']=4
        with self.assertRaises(ValueError):replay.resolve(state,'boss-1')
        with tempfile.TemporaryDirectory() as folder:
            core=self.make_core(folder)
            replay.queue(core.state,'boss-7')
            saved=json.loads(Path(core.state.state_path).read_text())
            self.assertEqual(replay.pending(saved)['id'],'boss-7')
            with patch.object(replay.os,'replace',side_effect=OSError('test write error')):
                with self.assertRaises(OSError):replay.queue(core.state,'final-5')
            self.assertEqual(core.state.state,saved)
            self.assertEqual(json.loads(Path(core.state.state_path).read_text()),saved)
            self.assertEqual(replay.take_pending(core.state)['id'],'boss-7')
            self.assertIsNone(replay.take_pending(core.state))
            self.assertIsNone(replay.pending(json.loads(Path(core.state.state_path).read_text())))

    def test_all_replay_rewards_preserve_campaign_and_story(self):
        with tempfile.TemporaryDirectory() as folder,redirect_stdout(io.StringIO()):
            core=self.make_core(folder);state=core.state.state
            world=deepcopy(state['world']);skills=list(state['player']['skills'])
            scenes=Mock()
            for row in replay.targets():
                kind,ctx=replay.encounter_context(state,row['id'],{'run_scene':scenes})
                xp,gold=state['player']['xp'],state['player']['gold']
                result=core._reward_on_victory(kind,100,ctx)
                self.assertGreater(state['player']['xp'],xp)
                self.assertGreater(state['player']['gold'],gold)
                self.assertIn('XP',result)
                self.assertEqual(state['world'],world)
                self.assertEqual((state['stats']['boss_wins'],state['stats']['final_wins'],state['stats']['boss_progress']),(25,5,7))
                self.assertEqual(state['player']['skills'],skills)
            self.assertEqual(state['stats']['terra_replay_wins'],30)
            core._save_story_state.assert_not_called();scenes.assert_not_called()

    def test_random_selection_is_atomic_and_preserves_encounter_timing(self):
        with tempfile.TemporaryDirectory() as folder:
            core=self.make_core(folder)
            core.state.state['stats']['messages_since_last_fight']=8
            replay.queue(core.state,'boss-7')
            saved=json.loads(Path(core.state.state_path).read_text())
            with patch.object(replay.os,'replace',side_effect=OSError('test write error')):
                with self.assertRaises(OSError):replay.select_random(core.state)
            self.assertEqual(core.state.state,saved)
            self.assertEqual(json.loads(Path(core.state.state_path).read_text()),saved)
            replay.select_random(core.state)
            saved['world'].pop('terra_replay_pending')
            self.assertEqual(core.state.state,saved)
            self.assertEqual(json.loads(Path(core.state.state_path).read_text()),saved)
            core.state.state['stats']['final_wins']=4
            with self.assertRaises(ValueError):replay.select_random(core.state)

    def test_postgame_normal_wins_never_restart_boss_or_final_progression(self):
        with tempfile.TemporaryDirectory() as folder,redirect_stdout(io.StringIO()):
            core=self.make_core(folder);state=core.state.state
            # An old endgame save may already have overflow from previous wins.
            state['stats'].update(boss_progress=100,boss_wins=30)
            before=deepcopy(state)
            for source in ['random','arena']*15:
                self.assertEqual(core._auto_fight_type(),'normal')
                core._reward_on_victory('normal',100,{'combat_source':source})
                self.assertEqual(core._auto_fight_type(),'normal')
            self.assertEqual(state['stats']['boss_progress'],100)
            self.assertEqual(state['stats']['boss_wins'],30)
            self.assertEqual(state['stats']['final_wins'],5)
            self.assertEqual(state['stats']['fights_won'],before['stats']['fights_won']+30)
            self.assertEqual(state['stats']['random_wins'],15)
            self.assertEqual(state['stats']['arena_wins'],15)
            self.assertGreater(state['player']['gold'],before['player']['gold'])
            self.assertEqual(journey.snapshot(state)['kind'],'complete')

    def test_real_boss_and_final_names_profiles_music_and_defeat(self):
        with tempfile.TemporaryDirectory() as folder,redirect_stdout(io.StringIO()),patch.object(battle,'BattleMusicManager'):
            core=self.make_core(folder)
            core._choose_music=Mock(return_value=(None,None))
            events=[];gui_bridge.install(lambda kind,**data:events.append(dict(event=kind,**data)))
            try:
                for key,win in [('boss-1',True),('boss-25',False),('final-1',True),('final-5',False)]:
                    state=core.state.state
                    state['player']['hp']=99999 if win else 1
                    core._enemy_stats=Mock(return_value=(1 if win else 999999,10000,100))
                    kind,ctx=replay.encounter_context(state,key,{'gui_mode':True,'fast_output':True})
                    world=deepcopy(state['world']);wins=state['stats']['fights_won']
                    events.clear()
                    result=core.run_fight(kind,ctx)
                    row=replay.resolve(state,key)
                    self.assertTrue(any(e.get('enemy_name')==row['name'] and e.get('active') for e in events))
                    self.assertEqual(core._choose_music.call_args.args[1 if kind=='boss' else 2],row['index'])
                    self.assertEqual(state['world'],world)
                    self.assertEqual((state['stats']['boss_wins'],state['stats']['final_wins'],state['stats']['boss_progress']),(25,5,7))
                    self.assertEqual(state['stats']['fights_won'],wins+(1 if win else 0))
                    self.assertEqual(state['player']['hp']>1,win)
                    self.assertNotIn('Zurück zum Speicherpunkt',result)
            finally:gui_bridge.install(None)

    def test_only_a_triggered_chat_encounter_consumes_selection(self):
        with tempfile.TemporaryDirectory() as folder,redirect_stdout(io.StringIO()):
            core=self.make_core(folder)
            plugin=battle.Plugin.__new__(battle.Plugin)
            plugin.core=core;plugin.state=core.state;plugin.plugin_dir=folder
            core.run_fight=Mock(return_value='replay battle log')
            replay.queue(core.state,'final-3')
            core.state.state['stats']['messages_since_last_fight']=0
            plugin.before_chat('/xp',{})
            plugin.before_chat('Hallo Terra',{})
            self.assertEqual(replay.pending(core.state.state)['id'],'final-3')
            self.assertEqual(core.run_fight.call_count,0)
            # Manual arena does not steal a selection reserved for the chat.
            plugin.command('/fight',{})
            self.assertEqual(replay.pending(core.state.state)['id'],'final-3')
            self.assertNotIn('terra_replay',core.run_fight.call_args.args[1])
            core.state.state['stats']['messages_since_last_fight']=8
            ctx={'test':True}
            plugin.before_chat('Ich gehe meinen Weg weiter.',ctx)
            kind,context=core.run_fight.call_args.args
            self.assertEqual(kind,'final');self.assertEqual(context['terra_replay']['id'],'final-3')
            self.assertEqual(context['combat_source'],'random')
            self.assertNotIn('arena_difficulty',context)
            self.assertEqual(ctx['battle_log'],['replay battle log'])
            self.assertIsNone(replay.pending(core.state.state))

            # A boss choice is a one-off encounter; normal enemies resume afterwards.
            core.state.state['stats']['boss_progress']=100
            core.state.state['stats']['messages_since_last_fight']=8
            plugin.before_chat('Die Reise geht weiter.',{'test':True})
            kind,context=core.run_fight.call_args.args
            self.assertEqual(kind,'normal')
            self.assertIn('arena_difficulty',context)
            self.assertNotIn('terra_replay',context)
            replay.queue(core.state,'boss-9')
            replay.select_random(core.state)
            core.state.state['stats']['messages_since_last_fight']=8
            plugin.before_chat('Noch ein Schritt auf Terra.',{'test':True})
            self.assertEqual(core.run_fight.call_args.args[0],'normal')
            self.assertIsNone(replay.pending(core.state.state))


class ReplayWorkerTests(unittest.TestCase):
    def test_random_button_clears_saved_boss_and_respects_profile_and_unlock(self):
        state=complete();state['world']['terra_replay_pending']='final-5'
        state['stats']['messages_since_last_fight']=8
        worker=Worker(seed={'battle_state.json':state})
        try:
            worker.send(op='terra_random',profile_slot=2)
            events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            self.assertFalse(next(e['ok'] for e in events if e['event']=='terra_replay_result'))
            self.assertEqual(next(e['data']['journey']['replay_pending']['id'] for e in events if e['event']=='profile'),'final-5')
            worker.send(op='terra_random',profile_slot=1)
            events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            self.assertTrue(next(e['ok'] for e in events if e['event']=='terra_replay_result'))
            self.assertFalse(any(e['event']=='battle' for e in events))
            self.assertIsNone(next(e['data']['journey']['replay_pending'] for e in events if e['event']=='profile'))
            saved=json.loads((Path(worker.temp.name)/'state/battle_state.json').read_text())
            self.assertEqual(saved['stats']['messages_since_last_fight'],8)
            self.assertNotIn('terra_replay_pending',saved['world'])
        finally:worker.close()
        worker=Worker(seed={'battle_state.json':saved})
        try:
            self.assertIsNone(next(e['data']['journey']['replay_pending'] for e in worker.boot if e['event']=='profile'))
        finally:worker.close()
        state=complete();state['stats']['final_wins']=4
        worker=Worker(seed={'battle_state.json':state})
        try:
            worker.send(op='terra_random',profile_slot=1)
            events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            self.assertFalse(next(e['ok'] for e in events if e['event']=='terra_replay_result'))
        finally:worker.close()

    def test_queue_and_profile_gate_use_worker_and_survive_restart(self):
        worker=Worker(seed={'battle_state.json':complete()})
        try:
            worker.send(op='terra_replay',target='boss-21',profile_slot=1)
            events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            self.assertTrue(next(e['ok'] for e in events if e['event']=='terra_replay_result'))
            self.assertFalse(any(e['event']=='battle' for e in events))
            saved=json.loads((Path(worker.temp.name)/'state/battle_state.json').read_text())
            self.assertEqual(replay.pending(saved)['id'],'boss-21')
            worker.send(op='terra_replay',target='final-5',profile_slot=2)
            events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            self.assertFalse(next(e['ok'] for e in events if e['event']=='terra_replay_result'))
        finally:worker.close()
        worker=Worker(seed={'battle_state.json':saved})
        try:
            data=next(e['data']['journey'] for e in worker.boot if e['event']=='profile')
            self.assertEqual(data['replay_pending']['id'],'boss-21')
        finally:worker.close()
        worker=Worker(seed={'battle_state.json':{'world':{'combat_unlocked':True},'stats':{'final_wins':4}}})
        try:
            worker.send(op='terra_replay',target='boss-1',profile_slot=1)
            events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            self.assertFalse(next(e['ok'] for e in events if e['event']=='terra_replay_result'))
        finally:worker.close()


class ReplayUiTests(unittest.TestCase):
    spin=helpers.LiveWindowTest.spin
    def test_map_regions_click_busy_guards_and_profile_reset(self):
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            helpers.unlock_test_arena()
            w=LiveWindow(audio=helpers.SilentAudio())
            w.request_title_start()
            w.choose_profile(w.game._profile_slot())
            try:
                w.resize(1220,900);w.show();self.spin(lambda:w.game.ready)
                w.ki_dialog.hide();w.phase='playing';w.navigate(3)
                w.receive(dict(event='profile',data=dict(journey=journey.snapshot(complete()),hero_class='robo',combat_unlocked=True)))
                w.open_terra_map();w.update_controls();view=w.terra_view
                self.assertEqual(len(view.board.markers),6)
                view.region_choice.setCurrentIndex(4)
                self.assertEqual([m.target['id'] for m in view.board.markers],['boss-21','boss-22','boss-23','boss-24','boss-25','final-5'])
                with patch.object(w.game,'write') as write:
                    QTest.mouseClick(view.board.markers[-1],Qt.LeftButton)
                    self.assertEqual(write.call_args.args[0]['target'],'final-5')
                    self.assertTrue(w.game.busy)
                    w.select_terra_boss('boss-1');self.assertEqual(write.call_count,1)
                w.game.busy=False
                state=complete();state['world']['terra_replay_pending']='final-5'
                w.receive(dict(event='profile',data=dict(journey=journey.snapshot(state),hero_class='robo',combat_unlocked=True)))
                w.update_controls()
                self.assertTrue(view.board.markers[-1].isChecked())
                self.assertIn('Licht der MAAT',view.replay_note.text())
                self.assertFalse(view.random_encounters.isChecked())
                w.game.get_snapshot().language='en';w.apply_menu_language()
                self.assertEqual(view.random_encounters.text(),'Random encounters')
                self.assertIn('next random encounter',view.replay_note.text())
                with patch.object(w.game,'write') as write:
                    QTest.mouseClick(view.random_encounters,Qt.LeftButton)
                    self.assertEqual(write.call_args.args[0],dict(op='terra_random',profile_slot=w.game._profile_slot()))
                    self.assertTrue(w.game.busy)
                    self.assertFalse(view.random_encounters.isEnabled())
                    w.select_terra_random();self.assertEqual(write.call_count,1)
                w.game.busy=False
                state['world'].pop('terra_replay_pending')
                w.receive(dict(event='profile',data=dict(journey=journey.snapshot(state),hero_class='robo',combat_unlocked=True)))
                w.update_controls()
                self.assertTrue(view.random_encounters.isChecked())
                self.assertFalse(any(m.isChecked() for m in view.board.markers))
                self.assertIn('Random encounters active',view.replay_note.text())
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    out=Path(os.environ['MAAT_GUI_SCREENSHOTS']);out.mkdir(parents=True,exist_ok=True)
                    APP.processEvents();w.grab().save(str(out/'random-encounters-en.png'))
                w.game.get_snapshot().language='de';w.apply_menu_language()
                self.assertEqual(view.random_encounters.text(),'Zufallskämpfe')
                self.assertIn('Zufallskämpfe aktiv',view.replay_note.text())
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    out=Path(os.environ['MAAT_GUI_SCREENSHOTS']);out.mkdir(parents=True,exist_ok=True)
                    for region in (0,4):
                        view.region_choice.setCurrentIndex(region);APP.processEvents()
                        w.grab().save(str(out/f'replay-region-{region+1}.png'))
                        w.resize(880,650);APP.processEvents()
                        w.grab().save(str(out/f'replay-region-{region+1}-small.png'))
                        w.resize(1220,900)
                w.receive(dict(event='profile',data=dict(journey=journey.snapshot({}),hero_class='normal')))
                w.update_controls()
                self.assertEqual(view.board.markers,[])
                self.assertTrue(view.region_choice.isHidden())
                self.assertTrue(view.random_encounters.isHidden())
                self.assertFalse(view.random_encounters.isEnabled())
            finally:
                w.game.shutdown();w.close();w.deleteLater()
                QCoreApplication.sendPostedEvents(w,QEvent.DeferredDelete);APP.processEvents()


if __name__=='__main__':unittest.main()
