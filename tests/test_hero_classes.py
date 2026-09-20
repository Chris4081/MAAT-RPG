"""Class timing, durable selection, and shared portraits without a GGUF model."""
import json
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from test_desktop import APP
from test_live_rpg import Worker
from test_live_window import SilentAudio, unlock_test_arena
from PySide6.QtCore import QCoreApplication, QEvent
from apps.maat_rpg import session_shared
from shared.core.hero_classes import CLASSES, selected_class, choice_pending, finish_first_fight, choose_class
from gui.battle_arena import CombatStage
from gui.live_window import LiveWindow


class ClassStateTests(unittest.TestCase):
    def test_unlock_then_completed_fight_excludes_demo_and_keeps_stats(self):
        with tempfile.TemporaryDirectory() as root:
            store = SimpleNamespace(state={'player': {'hp': 1, 'xp': 123}, 'stats': {'fights_won': 1}},
                                    state_path=Path(root)/'battle_state.json')
            self.assertEqual(selected_class(store.state), 'normal')
            self.assertFalse(finish_first_fight(store, unlocked=False))
            self.assertFalse(finish_first_fight(store, unlocked=True, demo=True))
            self.assertFalse(Path(store.state_path).exists())
            with self.assertRaises(ValueError): choose_class(store, 'magier')
            self.assertTrue(finish_first_fight(store, unlocked=True))
            self.assertTrue(choice_pending(json.loads(Path(store.state_path).read_text())))
            choose_class(store, 'magier')
            self.assertFalse(finish_first_fight(store, unlocked=True))
            self.assertEqual(selected_class(store.state), 'magier')
            with self.assertRaises(ValueError): choose_class(store, 'puppy')
            with self.assertRaises(ValueError): choose_class(store, [])
            self.assertEqual(store.state['player'], {'hp': 1, 'xp': 123})
            self.assertEqual(store.state['stats'], {'fights_won': 1})
            self.assertEqual(selected_class(json.loads(Path(store.state_path).read_text())), 'magier')

    def test_failed_save_keeps_pending_and_does_not_acknowledge_class(self):
        with tempfile.TemporaryDirectory() as root:
            store = SimpleNamespace(state={}, state_path=Path(root)/'battle_state.json')
            finish_first_fight(store, unlocked=True)
            before = Path(store.state_path).read_bytes()
            with patch('shared.core.hero_classes.os.replace', side_effect=OSError('disk full')):
                with self.assertRaises(OSError): choose_class(store, 'priester')
            self.assertEqual(selected_class(store.state), 'normal')
            self.assertTrue(choice_pending(store.state))
            self.assertEqual(Path(store.state_path).read_bytes(), before)
            self.assertEqual(list(Path(root).glob('.hero-class-*')), [])


class ClassWorkerTests(unittest.TestCase):
    def finish_fight(self, worker):
        events = []
        for _ in range(80):
            batch = worker.until(lambda e: e['event'] in ('prompt', 'class_selection') or
                                 (e['event'] == 'busy' and not e['value']))
            events += batch
            if batch[-1]['event'] != 'prompt':
                return events
            worker.send(op='answer', id=batch[-1]['id'], value='1')
        self.fail('Fight did not finish')

    def test_real_first_arena_fight_selects_once_and_survives_restart(self):
        worker = Worker(seed={'battle_state.json': {'world': {'combat_unlocked': True},
                        'player': {'level': 15, 'hp': 9999, 'max_hp': 9999}}}, auto_classes=False)
        try:
            self.assertEqual(next(e['data']['hero_class'] for e in worker.boot if e['event']=='profile'), 'normal')
            worker.send(op='text', text='/fight')
            events = self.finish_fight(worker)
            request = events[-1]
            self.assertEqual(request['event'], 'class_selection')
            self.assertTrue(any(e['event']=='battle' and e.get('active') is False for e in events[:-1]))
            self.assertTrue(choice_pending(json.loads((Path(worker.temp.name)/'state/battle_state.json').read_text())))
            worker.send(op='class_select', id=request['id'], value='normal')
            worker.until(lambda e: e['event']=='class_error')
            worker.send(op='class_select', id='stale-request', value='puppy')
            worker.send(op='class_select', id=request['id'], value='magier')
            done = worker.until(lambda e: e['event']=='busy' and not e['value'])
            self.assertEqual(next(e['value'] for e in done if e['event']=='class_selected'), 'magier')
            worker.send(op='text', text='/fight')
            following = self.finish_fight(worker)
            self.assertFalse(any(e['event']=='class_selection' for e in following))
            saved = json.loads((Path(worker.temp.name)/'state/battle_state.json').read_text())
        finally: worker.close()
        worker = Worker(seed={'battle_state.json': saved}, auto_classes=False)
        try:
            self.assertEqual(next(e['data']['hero_class'] for e in worker.boot if e['event']=='profile'), 'magier')
            self.assertFalse(any(e['event']=='class_selection' for e in worker.boot))
        finally: worker.close()

    def test_pending_choice_resumes_without_loading_model_or_another_fight(self):
        worker = Worker(seed={'battle_state.json': {'hero_class': {'pending': True, 'first_fight_completed': True}}}, auto_classes=False)
        try:
            self.assertTrue(next(e['data']['class_choice_pending'] for e in worker.boot if e['event']=='profile'))
            worker.send(op='class_resume')
            request = worker.until(lambda e: e['event']=='class_selection')[-1]
            worker.send(op='class_select', id=request['id'], value='puppy')
            done = worker.until(lambda e: e['event']=='busy' and not e['value'])
            self.assertEqual(next(e['data']['hero_class'] for e in done if e['event']=='profile'), 'puppy')
            self.assertFalse(any(e['event']=='battle' for e in done))
        finally: worker.close()


class ClassUiTests(unittest.TestCase):
    def dispose(self, widget):
        widget.close(); widget.deleteLater()
        QCoreApplication.sendPostedEvents(widget, QEvent.DeferredDelete)

    def spin(self, condition, seconds=15):
        end = time.monotonic()+seconds
        while not condition() and time.monotonic()<end:
            APP.processEvents(); time.sleep(.01)
        self.assertTrue(condition())

    def test_each_class_uses_its_own_action_poses_and_returns_to_standard(self):
        stage = CombatStage()
        try:
            stage.resize(960,460); stage.set_enemy('Schattenwächter')
            for value in ['normal', *CLASSES]:
                stage.set_hero_class(value)
                self.assertTrue(stage.hero.isValid())
                original = stage.hero.pixmap.cacheKey()
                for action in ('Harmonie', 'Balance', 'Schöpfungskraft', 'Verbundenheit', 'Respekt', 'skill', 'impulse', 'focus', 'heal'):
                    stage.clear_effects()
                    stage.show_effect(dict(attacker='player', attack=action, damage=4))
                    self.assertEqual(stage.attack_asset.parent.name, value)
                    self.assertEqual(stage.attack_asset.stem, stage.effect_kind)
                    self.assertNotEqual(stage.hero.pixmap.cacheKey(), original)
                    self.assertFalse(stage.grab().isNull())
                    stage.clear_effects()
                    self.assertEqual(stage.hero.pose_id, 'standard')
                    self.assertEqual(stage.hero.pixmap.cacheKey(), original)
                stage.clear_effects()
                stage.show_effect(dict(attacker='enemy', damage=14))
                self.assertEqual(stage.hero.class_id, value)
                self.assertFalse(stage.grab().isNull())
                self.assertEqual(stage.hero.pose_id, 'hurt')
        finally: self.dispose(stage)

    def test_window_defers_choice_then_updates_all_portraits_after_save_ack(self):
        with patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            unlock_test_arena()
            path=session_shared.profile_slot_root(session_shared.active_profile_slot())/'state/battle_state.json'
            saved=json.loads(path.read_text()); saved.pop('hero_class',None); path.write_text(json.dumps(saved))
            window=LiveWindow(audio=SilentAudio())
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
            try:
                window.resize(1220,900); window.show()
                self.spin(lambda:window.game.ready)
                self.assertEqual(window._hero_class,'normal')
                window.phase='playing';window._started=True;window.navigate(2)
                window.arena.stage.show_effect(dict(attacker='player',attack='Harmonie',damage=4))
                window.text_stream.append('Dein erster Kampf ist beendet.\n')
                window.receive(dict(event='class_selection',id='test-choice'))
                self.assertEqual(window.phase,'playing')
                window.text_stream.finish()
                window.present_class_selection()
                self.assertEqual(window.phase,'playing')
                window.arena.stage.clear_effects()
                window.present_class_selection()
                self.assertEqual(window.phase,'class_selection')
                self.assertTrue(window.character_sidebar.isHidden())
                window.navigate(0)
                self.assertIs(window.stack.currentWidget(),window.class_selection)
                screen=window.class_selection
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    out=Path(os.environ['MAAT_GUI_SCREENSHOTS']);out.mkdir(parents=True,exist_ok=True)
                    APP.processEvents();window.grab().save(str(out/'class-selection.png'))
                    window.resize(880,650);APP.processEvents()
                    self.assertLessEqual(window.minimumSizeHint().width(),880)
                    window.grab().save(str(out/'class-selection-small.png'))
                self.assertEqual(set(screen.cards),set(CLASSES))
                self.assertFalse(screen.confirm.isEnabled())
                screen.cards['engelchen'].click()
                self.assertTrue(screen.confirm.isEnabled())
                with patch.object(window.game,'write') as write:
                    screen.confirm.click()
                    write.assert_called_once_with(dict(op='class_select',id='test-choice',value='engelchen'))
                self.assertEqual(window._hero_class,'normal')
                window.receive(dict(event='class_error',id='test-choice',text='Speicher nicht erreichbar'))
                self.assertTrue(screen.confirm.isEnabled())
                screen.select('magier')
                window.receive(dict(event='class_selected',id='test-choice',value='magier'))
                self.assertEqual(window.phase,'playing')
                for portrait in (window.character_sidebar.portrait,window.character_portrait,
                                 window.companion_panel.hero_portrait,window.arena.stage.hero,
                                 window.title_screen.arena.stage.hero):
                    self.assertEqual(portrait.class_id,'magier')
                window.perspective.setCurrentIndex(window.perspective.findData('companion'))
                self.assertEqual(window.character_sidebar.portrait.class_id,'magier')
                window.apply_hero_class('normal')
                self.assertEqual(window.arena.stage.hero.class_id,'normal')
            finally:
                window.game.shutdown();self.dispose(window)

    def test_real_pending_selection_and_profile_switch_keep_the_saved_class(self):
        with patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            unlock_test_arena()
            slot=session_shared.active_profile_slot()
            path=session_shared.profile_slot_root(slot)/'state/battle_state.json'
            saved=json.loads(path.read_text())
            saved['hero_class']={'pending':True,'first_fight_completed':True}
            path.write_text(json.dumps(saved))
            session_shared.write_profile_settings(slot,{'gui_perspective':'adventure'})
            window=LiveWindow(audio=SilentAudio())
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
            try:
                window.show();self.spin(lambda:window.game.ready)
                window.phase='playing';window._started=True;window.navigate(3)
                self.assertTrue(window.resume_class_selection())
                self.spin(lambda:window.phase=='class_selection')
                window.class_selection.cards['puppy'].click()
                window.class_selection.confirm.click()
                self.spin(lambda:not window.game.busy and window.phase=='playing')
                self.assertEqual(selected_class(json.loads(path.read_text())),'puppy')
                self.assertEqual(window.character_sidebar.portrait.class_id,'puppy')
                old=window.game._profile_index;other=(old+1)%session_shared.PROFILE_SLOT_COUNT
                other_path=session_shared.profile_slot_root(other+1)/'state/battle_state.json'
                other_path.parent.mkdir(parents=True,exist_ok=True)
                other_path.write_text('{}')
                # This test switches between configured profiles; language onboarding
                # is exercised separately in test_gui_language.
                session_shared.write_profile_settings(other+1,{'language':'de'})
                window.change_profile(other)
                if window.phase == 'language': window.select_profile_language('de')
                self.spin(lambda:window.game.ready and not window.game.busy)
                self.assertEqual(window._hero_class,'normal')
                window.change_profile(old)
                if window.phase == 'language': window.select_profile_language('de')
                self.spin(lambda:window.game.ready and not window.game.busy)
                self.assertEqual(window._hero_class,'puppy')
                self.assertFalse(window._class_choice_pending)
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    Path(os.environ['MAAT_GUI_SCREENSHOTS']).mkdir(parents=True,exist_ok=True)
                    window.phase='playing';window.navigate(2)
                    window.arena.update_state(dict(active=True,enemy_name='Schattenwächter',enemy_hp=48,
                        enemy_max_hp=80,player_hp=100,player_max_hp=100,player_level=5))
                    APP.processEvents()
                    window.grab().save(str(Path(os.environ['MAAT_GUI_SCREENSHOTS'])/'class-puppy-battle.png'))
            finally:
                window.game.shutdown();self.dispose(window)


if __name__ == '__main__': unittest.main()
