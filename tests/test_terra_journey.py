"""Real campaign counters, retry saves and native map presentation; no GGUF."""
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
from apps.maat_rpg.plugins.battle.plugin_main import BattleCore
from shared.core import terra_journey as journey
from gui.live_window import LiveWindow
from PySide6.QtCore import QCoreApplication,QEvent,Qt
from PySide6.QtTest import QTest


class JourneyRulesTests(unittest.TestCase):
    def test_intro_uses_story_count_and_actual_unlock_not_a_second_counter(self):
        end,checkpoints=journey.intro_milestones()
        self.assertEqual(end,30)
        state={'stats':{'messages_total':4},'world':{}}
        for n in (0,1,10,29,30,31):
            data=journey.snapshot(state,{'messages_total':n})
            self.assertEqual(data['kind'],'intro')
            self.assertEqual(data['position'],min(30,n))
        self.assertEqual(checkpoints,(0,1,10,30))
        state['world']['combat_unlocked']=True
        self.assertEqual(journey.snapshot(state)['id'],'boss-1')
        self.assertEqual(journey.snapshot(state)['position'],0)

    def core(self,folder):
        core=BattleCore(folder)
        core.state.state=core.state._default()
        core.state.state['world']['combat_unlocked']=True
        core.state.save=Mock()
        core.state.add_xp=lambda amount:(1,1)
        core._load_story_state=lambda:{}
        core._save_story_state=Mock()
        return core

    def test_actual_rewards_drive_all_twenty_five_bosses_and_five_finales(self):
        with tempfile.TemporaryDirectory() as folder,redirect_stdout(io.StringIO()):
            core=self.core(folder)
            state=core.state.state
            seen={'awakening'}
            for boss in range(1,26):
                self.assertEqual(journey.snapshot(state)['id'],f'boss-{boss}')
                seen.add(journey.snapshot(state)['id'])
                # Mix both sources: eight random victories + four arena = ten fields.
                for i,source in enumerate(['random']*8+['arena']*4):
                    self.assertEqual(core._auto_fight_type(),'normal')
                    core._reward_on_victory('normal',1,{'combat_source':source})
                    expected=min(8,i+1)+max(0,i-7)/2
                    self.assertEqual(journey.snapshot(state)['position'],expected)
                self.assertEqual(core._auto_fight_type(),'boss')
                core._reward_on_victory('boss',1,{'combat_source':'random'})
                self.assertEqual(state['world']['last_boss_checkpoint'],boss)
                self.assertEqual(state['stats']['boss_progress'],0)
                if boss%5==0:
                    final=boss//5
                    self.assertEqual(core._auto_fight_type(),'final')
                    data=journey.snapshot(state)
                    self.assertEqual(data['id'],f'final-{final}')
                    self.assertEqual(data['region'],final-1)
                    seen.add(data['id'])
                    # First final is available immediately after five boss victories.
                    self.assertEqual(data['position'],10)
                    core._reward_on_victory('final',1,{'combat_source':'random'})
            self.assertEqual(len(seen),31)
            self.assertEqual(journey.snapshot(state)['kind'],'complete')
            self.assertEqual(journey.snapshot(state)['finals'],5)

    def test_final_retries_need_ten_random_wins_each_time_and_consume_progress(self):
        with tempfile.TemporaryDirectory() as folder,redirect_stdout(io.StringIO()):
            core=self.core(folder);state=core.state.state
            state['stats'].update(boss_wins=5,final_wins=0)
            for attempt in range(2):
                self.assertEqual(core._auto_fight_type(),'final')
                self.assertTrue(journey.reset_after_defeat(state,'final',{'combat_source':'arena'}))
                self.assertEqual(journey.snapshot(state)['position'],0)
                for step in range(10):
                    self.assertEqual(core._auto_fight_type(),'normal')
                    core._reward_on_victory('normal',1,{'combat_source':'random'})
                    self.assertEqual(journey.snapshot(state)['position'],step+1)
            core._reward_on_victory('final',1,{'combat_source':'random'})
            self.assertNotIn('final_retry',state['world'])
            self.assertEqual(state['stats']['boss_progress'],0)
            self.assertEqual(core._auto_fight_type(),'normal')
            self.assertEqual(journey.snapshot(state)['id'],'boss-6')

    def test_boss_retries_keep_five_fields_with_random_arena_and_mixed_wins(self):
        with tempfile.TemporaryDirectory() as folder,redirect_stdout(io.StringIO()):
            core=self.core(folder);state=core.state.state
            state['stats'].update(boss_wins=7,final_wins=1,boss_progress=20)
            for sources in (['random']*5, ['arena']*10, ['random']*3+['arena']*4):
                self.assertEqual(core._auto_fight_type(),'boss')
                self.assertTrue(journey.reset_after_defeat(state,'boss',{'combat_source':'random'}))
                data=journey.snapshot(state)
                self.assertEqual((data['id'],data['position']),('boss-8',5))
                self.assertEqual(data['checkpoints'],[0,5,10])
                for source in sources:
                    self.assertEqual(core._auto_fight_type(),'normal')
                    core._reward_on_victory('normal',1,{'combat_source':source})
                self.assertEqual(journey.snapshot(state)['position'],10)
            core._reward_on_victory('boss',1,{'combat_source':'arena'})
            self.assertEqual(journey.snapshot(state)['id'],'boss-9')
            self.assertEqual(state['stats']['boss_progress'],0)

    def test_forced_boss_loss_never_grants_progress_or_keeps_overflow(self):
        for progress,expected in [(0,0),(9,0),(20,10),(100,10)]:
            state={'stats':{'boss_progress':progress}}
            journey.reset_after_defeat(state,'boss',{'combat_source':'arena'})
            self.assertEqual(state['stats']['boss_progress'],expected)

    def test_map_retry_hints_are_available_in_both_languages(self):
        from gui.ui_i18n import tr
        state={'world':{'combat_unlocked':True},'stats':{'boss_progress':10}}
        hint=journey.snapshot(state)['hint']
        self.assertIn('5 Felder zurück',tr(hint,'de'))
        self.assertIn('back 5 spaces',tr(hint,'en'))
        state['stats'].update(boss_wins=5)
        journey.reset_after_defeat(state,'final',{'combat_source':'random'})
        self.assertIn('10 random encounters',tr(journey.snapshot(state)['hint'],'en'))

    def test_dungeon_demo_guide_and_normal_defeat_do_not_reset_the_campaign(self):
        state={'stats':{'boss_progress':13,'boss_wins':4},'world':{'combat_unlocked':True}}
        before=deepcopy(state)
        for kind,context in [('boss',{'combat_source':'dungeon'}),('final',{'combat_source':'demo'}),
                             ('boss',{'combat_source':'random','guide_mode':True}),
                             ('final',{'combat_source':'arena','title_demo_mode':True}),
                             ('normal',{'combat_source':'random'})]:
            self.assertFalse(journey.reset_after_defeat(state,kind,context))
            self.assertEqual(state,before)


class JourneyWorkerTests(unittest.TestCase):
    def finish_loss(self,worker,command):
        worker.send(op='text',text=command)
        events=[]
        for _ in range(15):
            batch=worker.until(lambda e:e['event']=='prompt' or (e['event']=='busy' and not e['value']))
            events+=batch
            if batch[-1]['event']=='busy':return events
            worker.send(op='answer',id=batch[-1]['id'],value='1')
        self.fail('Defeat did not finish')

    def test_boss_and_final_loss_persist_and_cannot_be_bypassed_with_commands(self):
        for kind,bosses,progress in [('boss',0,20),('final',5,0)]:
            with self.subTest(kind=kind):
                expected_position=5 if kind=='boss' else 0
                worker=Worker(seed={'battle_state.json':{'player':{'hp':1,'max_hp':100,'level':1},
                    'stats':{'boss_wins':bosses,'boss_progress':progress,'fights_won':37},
                    'hero_class':{'selected':'robo'},'world':{'combat_unlocked':True,'last_boss_checkpoint':bosses}}})
                try:
                    boot=next(e['data']['journey'] for e in worker.boot if e['event']=='profile')
                    self.assertEqual(boot['position'],10)
                    events=self.finish_loss(worker,'/fight'+kind)
                    data=[e['data']['journey'] for e in events if e['event']=='profile'][-1]
                    self.assertEqual(data['position'],expected_position)
                    saved=json.loads((Path(worker.temp.name)/'state/battle_state.json').read_text())
                    self.assertEqual(saved['player']['hp'],1)
                    self.assertEqual(saved['stats']['boss_progress'],expected_position*2)
                    self.assertEqual(saved['stats']['fights_won'],37)
                    self.assertEqual(saved['stats']['boss_wins'],bosses)
                    self.assertTrue(any('Speicherpunkt' in e.get('text','') for e in events))
                    needed=5 if kind=='boss' else 10
                    self.assertTrue(any(f'{needed} Zufallssiege oder {needed*2} Arenasiege' in e.get('text','') for e in events))
                finally:worker.close()
                worker=Worker(seed={'battle_state.json':saved})
                try:
                    boot=next(e['data']['journey'] for e in worker.boot if e['event']=='profile')
                    self.assertEqual(boot['position'],expected_position)
                    events=worker.command('/fight'+kind)
                    self.assertFalse(any(e['event']=='battle' and e.get('active') for e in events))
                    self.assertTrue(any('noch nicht an der Reihe' in e.get('text','') for e in events))
                finally:worker.close()


class JourneyUiTests(unittest.TestCase):
    spin=helpers.LiveWindowTest.spin
    def test_embedded_map_class_progress_animation_and_profile_reset(self):
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            helpers.unlock_test_arena()
            w=LiveWindow(audio=helpers.SilentAudio())
            w.request_title_start()
            w.choose_profile(w.game._profile_slot())
            try:
                w.resize(1220,900);w.show();self.spin(lambda:w.game.ready)
                w.ki_dialog.hide();w.phase='playing';w.navigate(3)
                state={'world':{'combat_unlocked':True},'stats':{'boss_progress':20,'boss_wins':7,'final_wins':1}}
                data=journey.snapshot(state)
                w.receive(dict(event='profile',data=dict(journey=data,hero_class='magier',combat_unlocked=True)))
                mini=w.character_sidebar.terra_map
                w.character_sidebar.scroll.ensureWidgetVisible(mini)
                QTest.mouseClick(mini.open,Qt.LeftButton)
                self.assertEqual(w.stack.currentIndex(),w.terra_index)
                self.assertFalse(w.terra_view.isWindow())
                self.assertEqual(w.terra_view.board.hero.class_id,'magier')
                self.assertEqual(w.terra_view.board.data,data)
                self.assertTrue(w.character_sidebar.isHidden())
                journey.reset_after_defeat(state,'boss',{'combat_source':'random'})
                data=journey.snapshot(state)
                w.receive(dict(event='profile',data=dict(journey=data,hero_class='magier',combat_unlocked=True)))
                self.assertEqual(w.terra_view.board.target,5)
                self.assertEqual(mini.board.data['position'],5)
                self.assertIn(5,w.terra_view.board.data['checkpoints'])
                w.terra_view.set_language('en')
                self.assertIn('back 5 spaces',w.terra_view.hint.text())
                w.terra_view.set_language('de')
                self.assertIn('5 Felder zurück',w.terra_view.hint.text())
                self.assertTrue(w.terra_view.board.walk_clock.isValid())
                QTest.qWait(2000)
                self.assertEqual(w.terra_view.board.position,5)
                w.terra_view.back.click();self.assertEqual(w.stack.currentIndex(),3)
                self.assertFalse(w.terra_view.board.timer.isActive())
                w._battle_active=True;w.open_terra_map();self.assertEqual(w.stack.currentIndex(),3)
                w._battle_active=False
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    out=Path(os.environ['MAAT_GUI_SCREENSHOTS']);out.mkdir(parents=True,exist_ok=True)
                    for label,s in [('intro',{}),('boss',state),('final',{'world':{'combat_unlocked':True},'stats':{'boss_wins':20,'final_wins':3}}),
                                    ('complete',{'world':{'combat_unlocked':True},'stats':{'boss_wins':25,'final_wins':5}})]:
                        j=journey.snapshot(s,{'messages_total':12})
                        w.receive(dict(event='profile',data=dict(journey=j,hero_class='normal' if label=='intro' else 'magier',combat_unlocked=True)))
                        w.open_terra_map();APP.processEvents()
                        w.grab().save(str(out/f'terra-{label}.png'))
                        mini.grab().save(str(out/f'terra-mini-{label}.png'))
                        w.resize(880,650);APP.processEvents()
                        w.grab().save(str(out/f'terra-{label}-small.png'))
                        w.resize(1220,900);w.navigate(3)
                    state['stats']['boss_progress']=10
                    w.receive(dict(event='profile',data=dict(journey=journey.snapshot(state),hero_class='magier',combat_unlocked=True)))
                    w.character_sidebar.scroll.verticalScrollBar().setValue(0)
                    QTest.qWait(1700)
                    w.grab().save(str(out/'terra-in-chat.png'))
                w.change_profile((w.game._profile_index+1)%session_shared.PROFILE_SLOT_COUNT)
                if w.phase == 'language': w.select_profile_language('de')
                self.spin(lambda:w.game.ready)
                self.assertEqual(w.terra_view.board.data['id'],'awakening')
            finally:
                w.game.shutdown();w.close();w.deleteLater()
                QCoreApplication.sendPostedEvents(w,QEvent.DeferredDelete);APP.processEvents()


if __name__=='__main__':unittest.main()
