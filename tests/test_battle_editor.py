"""Editor storage, endgame gates, bilingual actions and real battle isolation."""
import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_desktop import APP
from PySide6.QtCore import Qt, QBuffer, QIODevice
from PySide6.QtGui import QImage
from shared.core import battle_editor as core
from shared.core.command_i18n import tr
from shared.core.mod_support import create_battle_mod_template, load_battle_profile_mods
from gui.battle_editor import BattleEditor
from gui.command_menu import CommandMenu
from gui.battle_arena import BattleArena
from test_live_rpg import Worker

STATE = {'stats': {'final_wins': 5}}
DRAFT = dict(name='Aurora Sentinel', art='dragon', effect='spark', weakness='Balance',
             hp_mult=.5, damage_mult=.1, fight_type='normal', intro='Aurora wakes.', victory='The light rests.')


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='maat-editor-')
        self.env = patch.dict(os.environ, MAAT_MODS_DIR=self.temp.name)
        self.env.start()

    def tearDown(self):
        self.env.stop(); self.temp.cleanup()

    def test_save_reload_terminal_compatibility_and_conflict(self):
        item = core.save(STATE, DRAFT)
        self.assertTrue(item['editable'])
        self.assertEqual(core.catalog(STATE), [item])
        terminal = load_battle_profile_mods()[item['id']]
        self.assertEqual(terminal['battle_profile']['visual']['art'], 'dragon')
        self.assertFalse(terminal['persistent_rewards'])
        changed = core.save(STATE, dict(DRAFT, name='Aurora II'), mod_id=item['id'], revision=item['revision'])
        self.assertEqual(changed['id'], item['id'])
        self.assertEqual(changed['name'], 'Aurora II')
        with self.assertRaisesRegex(ValueError, 'editor_changed'):
            core.save(STATE, DRAFT, mod_id=item['id'], revision=item['revision'])
        external = create_battle_mod_template('terminal-dragon')
        original = Path(external['path']).read_bytes()
        legacy = next(x for x in core.catalog(STATE) if x['id']=='terminal-dragon')
        self.assertFalse(legacy['editable'])
        with self.assertRaisesRegex(ValueError, 'editor_copy'):
            core.playable(STATE, legacy['id'])
        clone = core.save(STATE, legacy)
        self.assertTrue(clone['editable'])
        self.assertEqual(Path(external['path']).read_bytes(), original)

    def test_unlock_validation_and_paths(self):
        for state in ({}, {'stats': {'boss_wins':100, 'final_wins':4}}, {'stats':{'final_wins':'bad'}}):
            self.assertFalse(core.unlocked(state))
            with self.assertRaisesRegex(ValueError, 'editor_locked'): core.save(state, DRAFT)
        for update in ({'name':''}, {'hp_mult':float('nan')}, {'damage_mult':20}, {'art':'../x'},
                       {'weakness':'invalid'}, {'image':'../save.json'}, {'intro':'x'*1001}):
            with self.subTest(update=update), self.assertRaises(ValueError): core.save(STATE, dict(DRAFT, **update))
        self.assertEqual(core.catalog(STATE), [])

    def test_imported_png_stays_after_original_disappears_and_uses_effect(self):
        img=QImage(24,24,QImage.Format_ARGB32); img.fill(Qt.red)
        buf=QBuffer(); buf.open(QIODevice.WriteOnly); img.save(buf,'PNG')
        item=core.save(STATE, dict(DRAFT, portrait_png=base64.b64encode(bytes(buf.data())).decode()))
        self.assertTrue(core.portrait_path(item['image']).is_file())
        arena=BattleArena()
        try:
            arena.update_state(dict(active=True, enemy_name=item['name'], enemy_visual={k:item[k] for k in ('art','effect','image')}, enemy_hp=40, enemy_max_hp=40))
            self.assertTrue(arena.stage.custom_portrait)
            self.assertTrue(arena.stage.enemy.isValid())
            arena.stage.show_effect(dict(attacker='enemy', attack='normal', damage=14))
            self.assertEqual(arena.stage.effect_kind, 'spark')
            self.assertIsNone(arena.stage.attack_asset)
            arena.stage.clear_effects()
            arena.update_state(dict(enemy_name='Wächter', enemy_visual={}))
            self.assertFalse(arena.stage.custom_portrait)
        finally: arena.close()

    def test_ui_language_preserves_custom_text_and_selects_attack_art(self):
        item=core.save(STATE,DRAFT)
        view=BattleEditor()
        try:
            view.set_ready(True); view.set_entries([item],item['id']);view.set_language('en')
            self.assertEqual(view.name.text(),DRAFT['name'])
            self.assertEqual(view.weakness.currentText(),'Balance')
            self.assertEqual(view.play_button.text(),'Start test battle →')
            self.assertTrue(view.play_button.isEnabled())
            view.preview_attack()
            self.assertEqual(view.preview.effect_kind,'spark')
            self.assertEqual(view.preview.attack_asset.name,'dragon-spark.svg')
            view.name.setText('A new name');self.assertFalse(view.play_button.isEnabled())
            view.set_language('de');self.assertEqual(view.name.text(),'A new name')
            self.assertEqual(view.play_button.text(),'Testkampf starten →')
        finally: view.close()


class ActionTests(unittest.TestCase):
    def test_english_categories_search_and_description_keep_command_ids(self):
        menu=CommandMenu()
        try:
            items=[dict(command='/fight',description='Startet einen Arenakampf mit halben Kampf-EP (nach Freischaltung).'),
                   dict(command='/mem search',description='Erinnerungen suchen.')]
            menu.populate(items);menu.set_language('en');menu.populate(items,'memories')
            root=menu.topLevelItem(0)
            self.assertIn('AI & Memories',root.text(0))
            leaf=root.child(0).child(0)
            self.assertEqual(leaf.data(0,Qt.UserRole)['command'],'/mem search')
            self.assertEqual(leaf.toolTip(0),'Search memories.')
            menu.populate(items,'arena')
            self.assertIn('Enter the arena',menu.topLevelItem(0).child(0).text(0))
            menu.populate(items);menu.set_language('de')
            self.assertIn('Kämpfe',menu.topLevelItem(0).text(0))
        finally: menu.close()

    def test_entire_actual_command_catalog_has_english_descriptions(self):
        worker=Worker()
        try:
            items=next(e['items'] for e in worker.boot if e['event']=='commands')
            missing=[x for x in items if x['description'] and tr(x['description'],'en')==x['description']]
            self.assertEqual(missing,[])
        finally: worker.close()


class EditorWorkerTests(unittest.TestCase):
    def test_defeat_does_not_move_the_map_or_use_resources(self):
        worker=Worker(seed={'battle_state.json':{'stats':{'final_wins':5,'boss_wins':5,'boss_progress':20},
            'world':{'combat_unlocked':True},'player':{'level':50,'hp':1,'max_hp':1,'potions':10}}})
        try:
            worker.send(op='battle_editor_save',profile_slot=1,data=dict(DRAFT,hp_mult=10,damage_mult=5,fight_type='boss'))
            saved=worker.until(lambda e:e['event']=='busy' and not e['value'])
            mod_id=next(e['selected'] for e in saved if e['event']=='battle_editor_result')
            path=Path(worker.temp.name)/'state/battle_state.json';before=json.loads(path.read_text())
            worker.send(op='battle_editor_play',profile_slot=1,mod_id=mod_id)
            events=[]
            for _ in range(10):
                batch=worker.until(lambda e:e['event']=='prompt' or (e['event']=='busy' and not e['value']))
                events.extend(batch)
                if batch[-1]['event']=='busy':break
                worker.send(op='answer',id=batch[-1]['id'],value='1')
            else:self.fail('expected defeat')
            self.assertTrue(next(e for e in events if e['event']=='battle_editor_result')['ok'])
            self.assertFalse(any(e['event']=='battle' and e.get('enemy_hp')==0 and e.get('enemy_name') for e in events))
            self.assertNotIn('Zurück zum Speicherpunkt',str(events))
            self.assertEqual(json.loads(path.read_text()),before)
        finally:worker.close()

    def test_locked_and_wrong_profile_requests_do_not_create_files(self):
        worker=Worker(seed={'battle_state.json':{'stats':{'final_wins':4}}})
        try:
            for slot,error in [(1,'editor_locked'),(2,'editor_profile')]:
                worker.send(op='battle_editor_save',profile_slot=slot,data=DRAFT)
                events=worker.until(lambda e:e['event']=='busy' and not e['value'])
                result=next(e for e in events if e['event']=='battle_editor_result')
                self.assertFalse(result['ok']);self.assertEqual(result['error'],error)
            self.assertEqual(list(Path(worker.temp.name).glob('mods/battle_profiles/*.json')),[])
        finally: worker.close()


class EditorWindowTests(unittest.TestCase):
    def test_menu_unlock_actual_editor_battle_and_return(self):
        import time
        from apps.maat_rpg import session_shared
        from gui.live_window import LiveWindow
        from test_live_window import SilentAudio, unlock_test_arena
        from PySide6.QtCore import QCoreApplication, QEvent, QPoint
        unlock_test_arena()
        previous_language=session_shared.application_language()
        session_shared.write_application_language('en')
        slot=session_shared.active_profile_slot()
        path=session_shared.profile_slot_root(slot)/'state/battle_state.json'
        old=path.read_bytes()
        state=json.loads(old);state.setdefault('stats',{}).update(final_wins=5,boss_wins=5)
        state['player'].update(level=50,hp=31,max_hp=10000)
        path.write_text(json.dumps(state))
        def spin(condition, seconds=20):
            deadline=time.monotonic()+seconds
            while not condition() and time.monotonic()<deadline:
                APP.processEvents();time.sleep(.01)
            self.assertTrue(condition())
        with patch.dict(os.environ, MAAT_GUI_DATA_ROOT=str(session_shared.BASE_APP_SUPPORT_DIR)):
            window=LiveWindow(audio=SilentAudio())
            try:
                window.show();window.request_title_start();window.choose_profile(slot)
                spin(lambda:window.game.ready)
                window.enter_menu();window.text_stream.finish();window.update_controls()
                self.assertFalse(window.editor_button.isHidden());self.assertTrue(window.editor_button.isEnabled())
                # A visible flag alone is insufficient: the editor must be on
                # screen without scrolling at the supported minimum size.
                for width,height in ((880,650),(1250,800)):
                    window.resize(width,height);APP.processEvents()
                    menu=window.stack.widget(0);menu.verticalScrollBar().setValue(0);APP.processEvents()
                    origin=window.editor_button.mapTo(menu.viewport(),QPoint(0,0))
                    self.assertGreaterEqual(origin.y(),0)
                    self.assertLessEqual(origin.y()+window.editor_button.height(),menu.viewport().height())
                    self.assertEqual(window.editor_button.text(),'⚒   Battle editor')
                window.editor_button.click();spin(lambda:not window.game.busy)
                self.assertEqual(window.stack.currentIndex(),window.editor_index)
                editor=window.battle_editor
                editor.name.setText('Window Test Dragon');editor.hp.setValue(.1)
                editor.art.setCurrentIndex(editor.art.findData('dragon'))
                editor.effect.setCurrentIndex(editor.effect.findData('spark'))
                editor.save_button.click();spin(lambda:bool(editor.current.get('id')) and not window.game.busy)
                self.assertTrue(editor.play_button.isEnabled())
                self.assertEqual(editor.play_button.text(),'Start test battle →')
                if os.environ.get('MAAT_EDITOR_SCREENSHOTS'):
                    target=Path(os.environ['MAAT_EDITOR_SCREENSHOTS']);target.mkdir(parents=True,exist_ok=True)
                    window.resize(1300,1080);APP.processEvents()
                    window.grab().save(str(target/'editor-en.png'))
                    editor.set_language('de');window.grab().save(str(target/'editor-de.png'));editor.set_language('en')
                editor.play_button.click()
                self.assertEqual(window.phase,'playing')
                deadline=time.monotonic()+30;answered=set();saw_monster=False
                while time.monotonic()<deadline:
                    APP.processEvents();window.text_stream.finish();APP.processEvents()
                    if window.arena.stage.name=='Window Test Dragon':
                        saw_monster=True
                        self.assertEqual(window.arena.stage.enemy_art,'dragon')
                    if window.game.prompt_id and window.game.prompt_id not in answered and not window._deferred:
                        answered.add(window.game.prompt_id)
                        window.game.submit_choice('1')
                    if not window.game.busy and window.can_return_to_chat():window.return_from_battle()
                    if window.stack.currentIndex()==window.editor_index and not window._editor_return:break
                    time.sleep(.01)
                self.assertTrue(saw_monster)
                self.assertEqual(window.stack.currentIndex(),window.editor_index)
                self.assertEqual(window.phase,'menu')
                self.assertEqual(json.loads(path.read_text())['player']['hp'],31)
                # Routine status updates cannot clear the selected action.
                window.phase='playing';window.navigate(5)
                window.command_filter.setText('d500 status')
                leaf=window.command_tree.topLevelItem(0).child(0).child(0)
                window.command_tree.setCurrentItem(leaf)
                window.update_controls()
                self.assertEqual(window.command_combo.currentData()['command'],'/d500 status')
                self.assertEqual(window.command_run.text(),'Run selected action')
                self.assertNotIn('anzeigen',window.command_help.text())
                if os.environ.get('MAAT_EDITOR_SCREENSHOTS'):
                    window.world_tabs.setCurrentIndex(1);window.command_filter.clear();window.command_tree.expandAll()
                    APP.processEvents();window.grab().save(str(target/'actions-en.png'))
                # Unlock belongs to the currently selected profile.
                window._receive_event({'event':'profile','data':{'final_wins':4}})
                self.assertTrue(window.editor_button.isHidden())
                window.phase='menu';window.navigate(0);window.open_battle_editor()
                self.assertEqual(window.stack.currentIndex(),0)
            finally:
                window.close();window.deleteLater()
                QCoreApplication.sendPostedEvents(window,QEvent.DeferredDelete);APP.processEvents()
                path.write_bytes(old)
                session_shared.write_application_language(previous_language or 'de')

    def test_editor_fight_real_engine_restores_state_and_animations(self):
        worker=Worker(seed={'battle_state.json':{'stats':{'final_wins':5,'boss_wins':5},
            'world':{'combat_unlocked':True},'player':{'level':50,'hp':23,'max_hp':10000,'potions':10}}})
        try:
            self.assertEqual(next(e['data']['final_wins'] for e in worker.boot if e['event']=='profile'),5)
            worker.send(op='battle_editor_save',profile_slot=1,data=DRAFT)
            saved=worker.until(lambda e:e['event']=='busy' and not e['value'])
            receipt=next(e for e in saved if e['event']=='battle_editor_result')
            self.assertTrue(receipt['ok'])
            mod_id=receipt['selected']
            path=Path(worker.temp.name)/'state/battle_state.json'
            before=json.loads(path.read_text())
            worker.send(op='battle_editor_play',profile_slot=1,mod_id=mod_id)
            events=[]
            for turn in range(60):
                batch=worker.until(lambda e:e['event']=='prompt' or (e['event']=='busy' and not e['value']))
                events.extend(batch)
                if batch[-1]['event']=='busy':break
                worker.send(op='answer',id=batch[-1]['id'],value='4' if turn==0 else '1')
            else:self.fail('editor fight did not end')
            battle=next(e for e in events if e['event']=='battle' and e.get('enemy_name'))
            self.assertEqual(battle['enemy_name'],DRAFT['name'])
            self.assertEqual(battle['enemy_visual']['art'],'dragon')
            self.assertEqual(battle['weakness'],'Balance')
            self.assertTrue(any(e['event']=='battle_effect' for e in events))
            self.assertTrue(any(e['event']=='battle' and e.get('enemy_hp')==0 for e in events))
            self.assertTrue(next(e for e in events if e['event']=='battle_editor_result')['ok'])
            self.assertEqual(json.loads(path.read_text()),before)
        finally: worker.close()
