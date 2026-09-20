import os
import time
import unittest
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtSvg import QSvgRenderer
from test_desktop import APP
from test_live_window import SilentAudio, unlock_test_arena
from gui.battle_arena import ART, artwork_for, BattleArena
from gui.live_window import LiveWindow
from apps.maat_rpg import session_shared

class ArenaTests(unittest.TestCase):
    def test_art_catalog_and_compact_demo(self):
        files = list(ART.glob('*.svg'))
        from shared.core.monster_catalog import ENEMY_KINDS, CAMPAIGN_BOSS_COUNT, FINAL_NAMES
        self.assertEqual(len(files), len(ENEMY_KINDS)+CAMPAIGN_BOSS_COUNT+len(FINAL_NAMES)+1)
        for path in files:
            self.assertTrue(QSvgRenderer(str(path)).isValid(), str(path))
        for word, expected in [('Bestie','beast'),('Phantom','phantom'),('Beobachter','watcher'),('Idol','idol'),('Konstrukt','construct'),('Funke','spark'),('Wächter','guardian'),('Wanderer','wanderer'),('Pharao','pharaoh'),('Avatar','avatar'),('Herz der Schöpfung','heart')]:
            self.assertEqual(artwork_for(word), expected)
        arena = BattleArena(demo=True)
        try:
            arena.update_state({'enemy_name':'Pharao der Dissonanz #1','enemy_hp':64,'enemy_max_hp':100,'player_hp':80,'player_max_hp':120,'player_level':23,'resonance':72})
            self.assertEqual(arena.log.font().pixelSize(), 18)
            self.assertEqual(arena.resonance.value(),72)
            self.assertEqual(arena.hero_hp.value(),80)
            self.assertIn('23', arena.hero_name.text())
            self.assertTrue(all(not b.isEnabled() for b in arena.actions.values()))
        finally:
            arena.deleteLater()
            QCoreApplication.sendPostedEvents(arena,QEvent.DeferredDelete)

    def test_difficulty_badge_and_reset(self):
        from shared.core.arena_difficulty import TIERS
        arena=BattleArena()
        try:
            for key,tier in TIERS.items():
                arena.update_state({'arena_difficulty':key,'enemy_name':'Schattenwächter'})
                self.assertFalse(arena.difficulty_badge.isHidden())
                self.assertIn(tier['label'].upper(),arena.difficulty_badge.text())
                self.assertIn(tier['color'],arena.enemy_name.styleSheet())
                self.assertEqual(arena.enemy_name.text(),'● Schattenwächter')
                arena.update_state({'arena_difficulty':key,'combat_source':'random'})
                self.assertIn('Zufallskampf-EP',arena.difficulty_badge.text())
            arena.update_state({'arena_difficulty':None})
            self.assertTrue(arena.difficulty_badge.isHidden())
            self.assertEqual(arena.enemy_name.text(),'Schattenwächter')
        finally:
            arena.deleteLater()
            QCoreApplication.sendPostedEvents(arena,QEvent.DeferredDelete)

    def test_attack_sprites_and_return_to_idle(self):
        from gui.battle_arena import CombatStage
        from gui.ascii_effects import FRAMES
        for character in ART.glob('*.svg'):
            for kind in FRAMES:
                path=ART/'attacks'/f'{character.stem}-{kind}.svg'
                self.assertTrue(QSvgRenderer(str(path)).isValid(), str(path))
        stage=CombatStage()
        try:
            stage.show_effect({'attacker':'player','attack':'Harmonie','damage':4})
            self.assertEqual(stage.attack_asset.name, 'wave.png')
            self.assertEqual(stage.hero.class_id, 'normal')
            stage.show_effect({'attacker':'enemy','enemy_name':'Bestie','attack':'normal','damage':2})
            for _ in range(7):stage.advance_effect()
            self.assertEqual(stage.attack_asset.name,'beast-claw.svg')
            for _ in range(7):stage.advance_effect()
            self.assertIsNone(stage.attack_asset)
            self.assertIsNone(stage.effect)
            self.assertFalse(stage.effect_timer.isActive())
            stage.show_effect({'attacker':'player','attack':'skill','damage':9})
            stage.clear_effects()
            self.assertIsNone(stage.attack_asset)
        finally:
            stage.deleteLater()
            QCoreApplication.sendPostedEvents(stage,QEvent.DeferredDelete)

    def test_sway_only_runs_while_visible(self):
        from gui.battle_arena import CombatStage
        stage=CombatStage()
        try:
            self.assertFalse(stage.sway_timer.isActive())
            stage.show()
            APP.processEvents()
            self.assertTrue(stage.sway_timer.isActive())
            self.assertTrue(stage.hero.isValid())
            self.assertFalse(hasattr(stage,'maatis_portrait'))
            stage.show_effect({'attacker':'player','attack':'skill','damage':3})
            self.assertEqual(stage.attack_asset.name, 'spark.png')
            self.assertEqual(stage.hero.class_id, 'normal')
            stage.hide()
            self.assertFalse(stage.sway_timer.isActive())
            self.assertIsNone(stage.attack_asset)
        finally:
            stage.deleteLater()
            QCoreApplication.sendPostedEvents(stage,QEvent.DeferredDelete)

    def test_principle_button_runs_real_attack(self):
        with patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            unlock_test_arena()
            window = LiveWindow(audio=SilentAudio())
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
            def wait_for(predicate):
                end = time.monotonic()+12
                while not predicate() and time.monotonic()<end:
                    APP.processEvents()
                    window.text_stream.finish()
                    time.sleep(.01)
                self.assertTrue(predicate())
            try:
                wait_for(lambda: window.game.ready)
                window.enter_menu()
                window.begin_game()
                window.intro.finish()
                window.perspective_screen.cards['adventure'].click()
                window.text_stream.finish()
                window.start_battle.click()
                wait_for(lambda: window.arena.actions['h'].isEnabled())
                self.assertTrue(window.arena.enemy_name.text().startswith('● '))
                self.assertIsNotNone(window.game.get_snapshot().battle.arena_difficulty)
                effects = []
                window.game.on_transport(lambda event: effects.append(event) if event.get('event') == 'battle_effect' else None)
                before = window.arena.enemy_hp.value()
                window.arena.actions['h'].click()
                wait_for(lambda: window.arena.enemy_hp.value() < before and window.arena.actions['h'].isEnabled())
                self.assertIsNone(window._pending_principle)
                self.assertEqual({e['attacker'] for e in effects}, {'player','enemy'})
                self.assertTrue(all(e['damage'] >= 0 for e in effects))
                self.assertEqual(window.journal.font().pixelSize(),26)
                self.assertTrue(window._return_to_chat)
                deadline = time.monotonic()+12
                while window.game.busy and time.monotonic()<deadline:
                    APP.processEvents()
                    window.text_stream.finish()
                    if window.game.prompt_id:
                        window.game.submit_choice('1' if window._arena_choices else '')
                    time.sleep(.01)
                window.text_stream.finish()
                self.assertFalse(window.game.busy)
                self.assertEqual(window.stack.currentIndex(), 2)
                wait_for(lambda: window.stack.currentIndex() == 3)
                self.assertFalse(window._return_to_chat)
            finally:
                window.game.shutdown()
                window.close()
                window.deleteLater()
                QCoreApplication.sendPostedEvents(window,QEvent.DeferredDelete)
                APP.processEvents()

    def test_ascii_animation_direction_order_and_stop(self):
        from gui.ascii_effects import effect_kind, directional_frame
        from gui.battle_arena import CombatStage
        self.assertEqual(effect_kind({'attacker':'enemy'}, 'beast'), 'claw')
        self.assertEqual(effect_kind({'attacker':'enemy'}, 'pharaoh'), 'sand')
        self.assertEqual(directional_frame('-->', 'enemy'), '<--')
        stage = CombatStage()
        try:
            started = []
            stage.effect_started.connect(lambda e: started.append(e['attacker']))
            stage.show_effect({'attacker':'player','attack':'Harmonie','damage':12})
            stage.show_effect({'attacker':'enemy','damage':4})
            self.assertEqual(started,['player'])
            for _ in range(7):
                stage.advance_effect()
            self.assertEqual(started,['player','enemy'])
            stage.clear_effects()
            self.assertIsNone(stage.effect)
            self.assertFalse(stage.effects)
            self.assertFalse(stage.effect_timer.isActive())
        finally:
            stage.deleteLater()
            QCoreApplication.sendPostedEvents(stage,QEvent.DeferredDelete)
