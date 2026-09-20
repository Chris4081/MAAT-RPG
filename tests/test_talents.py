import io
import json
import os
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from test_desktop import APP
from test_live_rpg import Worker
from test_live_window import SilentAudio, unlock_test_arena
from test_combat_quests import quest_plugin
from apps.maat_rpg import session_shared
from apps.maat_rpg.plugins.quests.combat_quests import COMBAT_QUESTS
from apps.maat_rpg.plugins.battle.plugin_main import BattleCore
from shared.core import talents
from gui.live_window import LiveWindow
from PySide6.QtCore import QCoreApplication, QEvent


def saved(class_id='robo', level=50, completed=True):
    return dict(player=dict(level=level, hp=500, max_hp=500, xp=0, skills=['Licht'], gold=50),
                hero_class=dict(selected=class_id), world=dict(combat_unlocked=True), stats={},
                quests=dict(completed=deepcopy(COMBAT_QUESTS) if completed else []))


class TalentStateTests(unittest.TestCase):
    def test_points_from_existing_levels_and_unique_permanent_combat_quests(self):
        state = saved(level=10, completed=False)
        quest = dict(id='first_win', type='counter', counter_key='battle_wins')
        state['quests']['completed'] = [quest, quest.copy(), dict(id='chat',type='chat_keyword'),
            dict(quest,id='daily',daily_reset=True), dict(quest,id='repeat',repeatable=True)]
        before = deepcopy(state)
        self.assertEqual(talents.snapshot(state)['earned'], 11)
        self.assertEqual(state, before)
        state['player']['level'] = 12
        self.assertEqual(talents.snapshot(state)['earned'], 13)
        self.assertEqual(talents.snapshot(state)['earned'], 13)
        state['hero_class'] = None
        self.assertFalse(talents.snapshot(state)['unlocked'])
        self.assertEqual(talents.snapshot(state)['earned'], 0)
        self.assertEqual(talents.combat_bonuses(state), {})

    def test_buy_gates_points_ranks_and_save_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            store = SimpleNamespace(state=saved(level=1,completed=False), state_path=Path(folder)/'battle_state.json')
            buy = lambda key, rank: talents.buy(store,key,expected_rank=rank,class_id='robo')
            with self.assertRaises(ValueError): buy('magier:0:0',0)
            with self.assertRaises(ValueError): buy('robo:0:1',0)
            buy('robo:0:0',0)
            before = store.state_path.read_bytes()
            with self.assertRaises(ValueError): buy('robo:0:0',0)  # duplicate transport
            with self.assertRaises(ValueError): buy('robo:1:0',0)  # no points
            store.state['player']['level']=10
            store.state['quests']['completed']=[deepcopy(COMBAT_QUESTS[0])]
            with self.assertRaises(ValueError): buy('robo:0:1',0)  # prerequisite rank
            buy('robo:0:0',1)
            disk_before = store.state_path.read_bytes(); memory_before=deepcopy(store.state)
            with patch('shared.core.hero_classes.os.replace',side_effect=OSError('disk full')):
                with self.assertRaises(OSError): buy('robo:0:1',0)
            self.assertEqual(store.state_path.read_bytes(),disk_before)
            self.assertEqual(store.state,memory_before)
            self.assertEqual(list(Path(folder).glob('.hero-class-*')),[])
            buy('robo:0:1',0)
            self.assertEqual(talents.snapshot(json.loads(store.state_path.read_text()))['ranks']['robo:0:1'],1)

    def test_all_five_complete_trees_use_ninety_points_and_only_their_own_class(self):
        with tempfile.TemporaryDirectory() as folder:
            for class_id in talents.TREES:
                with self.subTest(class_id=class_id):
                    store=SimpleNamespace(state=saved(class_id),state_path=Path(folder)/'battle_state.json')
                    original=deepcopy(store.state['player'])
                    for node in talents.catalog(class_id):
                        for rank in range(3):
                            talents.buy(store,node['id'],expected_rank=rank,class_id=class_id)
                    data=talents.snapshot(store.state)
                    self.assertEqual(len(data['nodes']),12)
                    self.assertEqual(data['spent'],90)
                    self.assertTrue(all(n['rank']==3 for n in data['nodes']))
                    self.assertEqual(store.state['player'],original)
                    with self.assertRaises(ValueError):
                        talents.buy(store,data['nodes'][0]['id'],expected_rank=3,class_id=class_id)
                    for context in ({'guide_mode':True},{'title_demo_mode':True},{'combat_source':'demo'}):
                        turn={'guard':0,'resonance':0}
                        self.assertEqual(talents.begin_fight(store.state,turn,context),{})
                        self.assertEqual(turn['guard'],0)

    def test_real_quest_completion_grants_one_point_and_never_for_chat(self):
        plugin, core=quest_plugin()
        core.state.state['hero_class']={'selected':'puppy'}
        q=deepcopy(COMBAT_QUESTS[0]);q['progress']=0
        plugin.qstate.update(active=[q], completed=[])
        old=talents.snapshot(core.state.state)['earned']
        messages=[];plugin._complete_quest(q,messages)
        self.assertEqual(talents.snapshot(core.state.state)['earned'],old+1)
        self.assertTrue(any('Talentpunkt' in m for m in messages))
        plugin._complete_quest(q,[])
        self.assertEqual(talents.snapshot(core.state.state)['earned'],old+1)


class TalentCombatTests(unittest.TestCase):
    def test_focus_resonance_weakness_impulse_and_all_boss_specials(self):
        core=BattleCore.__new__(BattleCore)
        plain={'guard':0,'resonance':0,'weakness':'Harmonie'}
        learned=dict(plain,talents=dict(focus_heal=50,focus_guard=50,resonance=3,weakness=10,impulse=30,reduction=20))
        hp,_=core._use_focus(100,500,learned)
        self.assertEqual(hp,160)
        self.assertEqual(learned['guard'],50)
        self.assertEqual(learned['resonance'],33)
        self.assertEqual(core._apply_enemy_weakness('Harmonie',100,learned)[0],135)
        with patch('random.randint',return_value=5):
            plain['resonance']=100; learned['resonance']=100
            self.assertGreater(core._use_ult(20,500,learned)[0],core._use_ult(20,500,plain)[0])
        for special in ('Fraktur der Harmonie','Spiegel des Gegengewichts','Nova der Möglichkeiten',
                        'Vakuum-Ruf','Urteil der Grenze','Achsenbruch','Genesis-Sturm','Other'):
            profile={'special':special}
            vanilla=500-core._boss_special_attack(profile,dict(plain),500,500)[0]
            talented=500-core._boss_special_attack(profile,dict(learned),500,500)[0]
            self.assertEqual(talented,round(vanilla*.8))

    def test_real_fight_principle_skill_and_incoming_damage_use_saved_talents(self):
        def fight(trained, action):
            with tempfile.TemporaryDirectory() as folder:
                core=BattleCore(folder)
                core.state.state=core.state._default()
                for key, value in saved().items():
                    core.state.state.setdefault(key, {}).update(value)
                if trained:
                    core.state.state['hero_class']['talents']={'ranks':{n['id']:3 for n in talents.catalog('robo')}}
                core.state.save=Mock()
                core._enemy_stats=lambda kind:(10000,100,100)
                core._choose_music=lambda *args:(None,None)
                core._load_story_state=lambda:{}
                core._choose_enemy_weakness=lambda:'Respekt'
                core._register_boss_codex_entry=Mock()
                core._slow_line=lambda *args,**kwargs:None
                core._prompt=Mock(side_effect=[action,'1','6'])
                events=[]
                with patch('shared.core.gui_bridge.emit',side_effect=lambda event,**kw:events.append(dict(event=event,**kw))), \
                     patch('random.random',return_value=0),patch('random.randint',return_value=0), \
                     patch('apps.maat_rpg.plugins.battle.plugin_main.BattleMusicManager'),redirect_stdout(io.StringIO()):
                    core.run_fight('normal',{'combat_source':'arena'})
                return [e for e in events if e['event']=='battle_effect']
        for action in ('1','2'):
            baseline, trained=fight(False,action),fight(True,action)
            self.assertGreater(trained[0]['damage'],baseline[0]['damage'])
            self.assertLess(trained[1]['damage'],baseline[1]['damage'])


class TalentWorkerTests(unittest.TestCase):
    def test_worker_saves_purchase_rejects_duplicate_wrong_profile_and_restores(self):
        worker=Worker(seed={'battle_state.json':saved(level=10,completed=False)})
        try:
            data=next(e['data'] for e in worker.boot if e['event']=='talents')
            self.assertTrue(data['unlocked'])
            for slot,ok in ((2,False),(1,True),(1,False)):
                worker.send(op='talent_buy',profile_slot=slot,talent='robo:0:0',rank=0,class_id='robo')
                events=worker.until(lambda e:e['event']=='busy' and not e['value'])
                self.assertEqual(next(e['ok'] for e in events if e['event']=='talent_result'),ok)
            state=json.loads((Path(worker.temp.name)/'state/battle_state.json').read_text())
        finally:worker.close()
        worker=Worker(seed={'battle_state.json':state})
        try:
            data=next(e['data'] for e in worker.boot if e['event']=='talents')
            self.assertEqual(data['ranks']['robo:0:0'],1)
            self.assertEqual(data['available'],data['earned']-1)
        finally:worker.close()


class TalentUiTests(unittest.TestCase):
    def spin(self, condition):
        end=time.monotonic()+15
        while not condition() and time.monotonic()<end:
            APP.processEvents();time.sleep(.01)
        self.assertTrue(condition())

    def test_embedded_tree_purchase_profile_change_and_small_window(self):
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            unlock_test_arena()
            path=session_shared.profile_slot_root(session_shared.active_profile_slot())/'state/battle_state.json'
            state=json.loads(path.read_text());state['hero_class']={'selected':'magier'}
            path.write_text(json.dumps(state))
            window=LiveWindow(audio=SilentAudio())
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
            try:
                window.resize(1280,960);window.show();self.spin(lambda:window.game.ready)
                window.phase='playing';window._started=True;window.navigate(3);window.update_controls()
                self.assertTrue(window.talent_button.isEnabled())
                window.talent_button.click()
                self.assertIs(window.stack.currentWidget(),window.talent_tree)
                self.assertTrue(window.character_sidebar.isHidden())
                tree=window.talent_tree;self.assertEqual(len(tree.cards),12)
                tree.cards['magier:0:0'].click();tree.learn.click()
                self.assertFalse(tree.learn.isEnabled())
                self.spin(lambda:not window.game.busy)
                self.assertEqual(tree.data['ranks']['magier:0:0'],1)
                self.assertIn('gelernt',tree.receipt.text())
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    out=Path(os.environ['MAAT_GUI_SCREENSHOTS']);out.mkdir(parents=True,exist_ok=True)
                    APP.processEvents();window.grab().save(str(out/'talentbaum-magier.png'))
                    window.resize(880,720);APP.processEvents()
                    window.grab().save(str(out/'talentbaum-klein.png'))
                tree.quests_requested.emit()
                self.assertEqual(window.stack.currentIndex(),5)
                self.assertEqual(window.quest_log.category.currentData(),'combat')
                window.receive(dict(event='profile',data={'hero_class':'normal'}))
                window.receive(dict(event='talents',data=talents.snapshot({})))
                self.assertFalse(window.talent_button.isEnabled())
                self.assertEqual(window.talent_tree.cards,{})
            finally:
                window.game.shutdown();window.close();window.deleteLater()
                QCoreApplication.sendPostedEvents(window,QEvent.DeferredDelete)
