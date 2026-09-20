"""Encounter variety, save compatibility and real animated portrait integration."""
import json
import random
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
from test_desktop import APP
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtSvg import QSvgRenderer
from shared.core.monster_catalog import (ENEMY_KINDS, KIND_ART, ENEMY_EFFECTS, choose_enemy_name,
    enemy_display_name, regular_enemy_kind, entries)
from shared.core.dungeon_campaign import run, run_endless, room_enemy, NARRATIVE_KINDS, dungeon
from gui.battle_arena import BattleArena, ART, artwork_for
from gui.monster_catalog import MonsterCatalog


class VarietyTests(unittest.TestCase):
    def test_real_battle_save_retains_recent_types(self):
        import tempfile
        from apps.maat_rpg.plugins.battle import plugin_main as battle
        with tempfile.TemporaryDirectory(prefix='maat-monster-save-') as folder:
            with patch.object(battle,'state_file',return_value=str(Path(folder)/'battle_state.json')):
                saved=battle.BattleState(folder)
                for _ in range(12):battle.generate_enemy_name(saved.state)
                previous=list(saved.state['recent_enemy_kinds']);saved.save()
                loaded=battle.BattleState(folder)
                self.assertEqual(loaded.state['recent_enemy_kinds'],previous)
                self.assertNotIn(regular_enemy_kind(battle.generate_enemy_name(loaded.state)),previous)

    def test_no_last_five_silhouettes_and_save_reload(self):
        rng=random.Random(14);state={};seen=[]
        for i in range(600):
            if i%17==0:state=json.loads(json.dumps(state))
            name=choose_enemy_name(state,rng)
            kind=regular_enemy_kind(enemy_display_name(name,'en'))
            self.assertNotIn(kind,seen[-5:]);seen.append(kind)
            self.assertEqual(state['recent_enemy_kinds'],seen[-5:])
        self.assertEqual(set(seen),set(ENEMY_KINDS))
        self.assertEqual(len(ENEMY_KINDS),20)

    def test_legacy_corrupt_and_constrained_histories(self):
        for invalid in (None,'old data',{},[None,{},17,'modded']):
            state={'recent_enemy_kinds':invalid}
            self.assertIn(regular_enemy_kind(choose_enemy_name(state,random.Random(7))),ENEMY_KINDS)
            self.assertEqual(len(state['recent_enemy_kinds']),1)
        state={'recent_enemy_kinds':['Skarabäus','Wächter','Skarabäus','Wanderer','Qualle']}
        name=choose_enemy_name(state,random.Random(3),kinds=['Skarabäus','Wächter'])
        self.assertEqual(regular_enemy_kind(name),'Wächter')
        self.assertEqual(regular_enemy_kind(choose_enemy_name(state,kinds=['Wächter'])),'Wächter')
        with self.assertRaises(ValueError):choose_enemy_name({},kinds=[])
        # A demo/no-state call has no process-global history to alter another save.
        before=json.dumps(state);choose_enemy_name(rng=random.Random(2))
        self.assertEqual(json.dumps(state),before)

    def test_dungeon_story_constraints_and_fixed_guardians(self):
        for (index,room),allowed in NARRATIVE_KINDS.items():
            self.assertIn(regular_enemy_kind(room_enemy({},index,room,'en')),allowed)
        encountered=[]
        for index in range(9):
            core=Mock();state={'player':{'level':50,'hp':500},'stats':{'fights_won':0}}
            core.state.state=state;names=[]
            def win(kind,context):
                names.append(context['battle_profile']['boss_name'])
                state['stats']['fights_won']+=1
            core.run_fight.side_effect=win
            self.assertTrue(run(core,index,Mock(),Mock(),language='en'))
            self.assertEqual(len(names),5);self.assertEqual(names[-1],dungeon(index,'en')['guardian'])
            self.assertTrue(all(regular_enemy_kind(n) in ENEMY_KINDS for n in names[:4]))
            encountered.extend(regular_enemy_kind(n) for n in names[:4])
        self.assertTrue(set(encountered)&set(ENEMY_KINDS[8:]))

    def test_dungeon_plus_variety_keeps_rewards_progress_and_music(self):
        core=Mock();state={'player':{'level':50,'hp':500},'stats':{'fights_won':0,'boss_progress':7}}
        core.state.state=state;names=[];notify=Mock()
        def fight(kind,context):
            names.append(context['battle_profile']['boss_name'])
            if len(names)<=25:state['stats']['fights_won']+=1
        core.run_fight.side_effect=fight
        self.assertEqual(run_endless(core,Mock(),notify,language='en'),25)
        forms=[regular_enemy_kind(n) for n in names]
        for i,kind in enumerate(forms):self.assertNotIn(kind,forms[max(0,i-5):i])
        self.assertEqual(state['stats']['boss_progress'],7)
        self.assertEqual(state['dungeon_plus']['best_wave'],25)
        audio=[c.kwargs for c in notify.call_args_list if c.args==('audio',)]
        self.assertEqual([a['action'] for a in audio],['play','stop'])
        self.assertEqual(len(audio[0]['playlist']),3)


class PortraitTests(unittest.TestCase):
    def test_new_forms_in_real_and_demo_arena_animate_and_return(self):
        for demo in (False,True):
            arena=BattleArena(demo=demo);arena.resize(1000,690);arena.show();APP.processEvents()
            try:
                for kind in ENEMY_KINDS:
                    name='Schatten '+kind;art=KIND_ART[kind]
                    arena.set_language('en')
                    arena.update_state(dict(active=True,enemy_name=name,enemy_hp=90,enemy_max_hp=100,
                        player_hp=85,player_max_hp=100,player_level=25,resonance=20,arena_difficulty='normal'))
                    stage=arena.stage
                    self.assertEqual(artwork_for(enemy_display_name(name,'en')),art)
                    self.assertIn(enemy_display_name(name,'en'),arena.enemy_name.text())
                    self.assertTrue(stage.enemy.isValid());self.assertTrue(stage.sway_timer.isActive())
                    for attack,effect in [('normal',ENEMY_EFFECTS.get(art,'slash')),('special','impulse')]:
                        stage.show_effect(dict(attacker='enemy',enemy_name=name,attack=attack,damage=14))
                        self.assertEqual(stage.effect_kind,effect)
                        self.assertEqual(stage.attack_asset.name,f'{art}-{effect}.svg')
                        self.assertTrue(stage.attack_sprite.isValid())
                        self.assertEqual(stage.hit_target,'player');self.assertEqual(stage.hit_damage,14)
                        APP.processEvents();self.assertFalse(arena.grab().isNull())
                        for _ in range(7):stage.advance_effect()
                        self.assertIsNone(stage.attack_asset);self.assertIsNone(stage.effect)
                        self.assertFalse(stage.effect_timer.isActive())
                    stage.show_effect(dict(attacker='player',enemy_name=name,attack='h',damage=9))
                    self.assertEqual(stage.hit_target,'enemy')
                    self.assertFalse(arena.grab().isNull());stage.clear_effects()
                arena.hide();self.assertFalse(arena.stage.sway_timer.isActive())
            finally:
                arena.close();arena.deleteLater();QCoreApplication.sendPostedEvents(arena,QEvent.DeferredDelete)

    def test_catalog_lists_all_forms_with_localized_attack_details(self):
        w=MonsterCatalog()
        try:
            w.set_level(49);self.assertEqual(w.list.count(),0)
            w.set_level(50);self.assertEqual(w.list.count(),50)
            for language,search,expected in [('de','Skarabäus','Funkenstoß'),('en','Scarab','Spark discharge')]:
                w.set_language(language);w.search.setText(search)
                self.assertEqual(w.list.count(),1);self.assertIn(expected,w.description.text())
                self.assertTrue(w.art.renderer().isValid())
                self.assertEqual(w.art.renderer().aspectRatioMode(),Qt.KeepAspectRatio)
                self.assertIn('20',w.note.text())
            for row in entries('en'):
                self.assertTrue(QSvgRenderer(str(ART/(artwork_for(row['art_name'])+'.svg'))).isValid())
        finally:
            w.close();w.deleteLater();QCoreApplication.sendPostedEvents(w,QEvent.DeferredDelete)
