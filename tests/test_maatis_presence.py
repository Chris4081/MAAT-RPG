"""Visual actions follow actual outcomes and retain the shared demo timing."""
import unittest
from unittest.mock import Mock
from test_desktop import APP
from PySide6.QtCore import QCoreApplication, QEvent
from gui.battle_arena import BattleArena, CombatStage
from gui.title_screen import TitleScreen
from gui.hero_portrait import portrait_path
from test_live_rpg import Worker


class MaatisPresenceTests(unittest.TestCase):
    def dispose(self, widget):
        widget.close()
        widget.deleteLater()
        QCoreApplication.sendPostedEvents(widget, QEvent.DeferredDelete)

    def test_support_queue_applies_demo_hp_at_action_and_never_hits_enemy(self):
        screen = TitleScreen()
        try:
            arena = screen.arena
            arena.update_state(dict(active=True, enemy_name='Wächter', enemy_hp=100, enemy_max_hp=100,
                                    player_hp=50, player_max_hp=100))
            screen.present(dict(event='battle_effect', attacker='player', attack='Harmonie', damage=10, enemy_hp=90, player_hp=50))
            screen.present(dict(event='battle_effect', attacker='player', attack='heal', damage=0, heal=24, enemy_hp=90, player_hp=74))
            self.assertEqual((arena.hero_hp.value(), arena.enemy_hp.value()), (50, 90))
            for _ in range(7): arena.stage.advance_effect()
            self.assertEqual((arena.hero_hp.value(), arena.enemy_hp.value()), (74, 90))
            self.assertEqual(arena.stage.hit_target, 'player')
            self.assertEqual(arena.stage.hit_damage, 0)
            self.assertEqual(arena.stage.hit_label, '+24 KP')
            self.assertEqual(arena.stage.attack_asset.name, 'heal.png')
            self.assertEqual(arena.stage.hero.class_id, 'normal')
            for _ in range(7): arena.stage.advance_effect()
            self.assertIsNone(arena.stage.attack_asset)
            self.assertFalse(arena.stage.effect_timer.isActive())
            self.assertEqual(arena.stage.effect_timer.interval(), 225)
        finally: self.dispose(screen)

    def test_victory_waits_for_attacks_and_new_encounter_resets_all_poses(self):
        arena = BattleArena()
        try:
            arena.update_state(dict(active=True, enemy_name='Wächter', enemy_hp=10, enemy_max_hp=10,
                                    player_hp=100, player_max_hp=100))
            stage = arena.stage
            stage.show_effect(dict(attacker='player', attack='impulse', damage=10))
            arena.update_state(dict(enemy_hp=0))
            self.assertFalse(stage.presence.victory)
            arena.update_state(dict(active=False, enemy_hp=0))
            self.assertNotEqual(stage.presence.pose(0, stage.effect, stage.hit_target, stage.hit_damage), 'victory')
            for _ in range(7): stage.advance_effect()
            self.assertEqual(stage.presence.pose(0, stage.effect, stage.hit_target, stage.hit_damage), 'victory')
            arena.clear_opponent()
            self.assertFalse(stage.presence.victory)
            self.assertEqual(stage.presence.resonance, 0)
            arena.update_state(dict(active=True, enemy_name='Wächter', enemy_hp=100, enemy_max_hp=100, player_hp=1))
            self.assertEqual(stage.presence.pose(0, None, None, 0), 'tired')
            arena.update_state(dict(active=False, enemy_hp=100))
            self.assertFalse(stage.presence.victory)
        finally: self.dispose(arena)

    def test_render_pose_reactions_and_stop_on_hide(self):
        stage = CombatStage()
        try:
            stage.resize(960, 460); stage.show(); APP.processEvents()
            stage.set_enemy('Schattenwächter')
            self.assertTrue(all(svg.isValid() for svg in stage.presence.poses.values()))
            for attack in ('Harmonie', 'Balance', 'Schöpfungskraft', 'Verbundenheit', 'Respekt', 'skill', 'impulse', 'focus', 'heal'):
                stage.clear_effects()
                stage.show_effect(dict(attacker='player', attack=attack, damage=0, heal=8))
                self.assertFalse(stage.grab().isNull())
            for damage, pose in ((14, 'hurt'), (0, 'guard')):
                stage.clear_effects()
                stage.show_effect(dict(attacker='enemy', damage=damage))
                self.assertEqual(stage.presence.pose(0, stage.effect, stage.hit_target, stage.hit_damage), pose)
                self.assertFalse(stage.grab().isNull())
            stage.hide()
            self.assertFalse(stage.sway_timer.isActive())
            self.assertFalse(stage.hit_timer.isActive())
            self.assertFalse(stage.effect_timer.isActive())
            self.assertIsNone(stage.effect)
        finally: self.dispose(stage)

    def test_all_classes_keep_their_portrait_through_old_blink_windows(self):
        stage=CombatStage()
        demo=TitleScreen()
        try:
            stage.resize(720,360);stage.set_enemy('Schattenwächter')
            demo.resize(900,650)
            demo.arena.update_state(dict(active=True,enemy_name='Wächter',player_hp=100,
                player_max_hp=100,enemy_hp=100,enemy_max_hp=100))
            clock=Mock();clock.isValid.return_value=True
            for surface in (stage,demo.arena.stage):
                surface.sway_clock=clock
                for cls in ('normal','robo','engelchen','magier','priester','puppy'):
                    surface.set_hero_class(cls)
                    # Former open/closed boundaries and repeated cycles. Render the
                    # real widget to catch accidental pose reuse or asset fallback.
                    for ms in (4790,4810,4900,4970,5090,5110,5230,11600,18300):
                        clock.elapsed.return_value=ms
                        self.assertFalse(surface.grab().isNull())
                        self.assertEqual(surface.hero.pose_id,'standard',(cls,ms))
                        self.assertEqual(surface.hero.asset,portrait_path(cls))
                    clock.elapsed.return_value=2500
                    surface.grab()
                    self.assertEqual(surface.hero.pose_id,'ready')
                    self.assertEqual(surface.hero.class_id,cls)
        finally:
            self.dispose(stage);self.dispose(demo)

    def test_real_fight_emits_focus_and_only_successful_potion(self):
        worker = Worker(seed={'battle_state.json': {'world': {'combat_unlocked': True},
                        'player': {'level': 5, 'hp': 300, 'max_hp': 1000, 'potions': 1}}})
        try:
            worker.send(op='text', text='/fight')
            batch = worker.until(lambda e: e['event'] == 'prompt')
            for action, expected in [('3', 'focus'), ('4', 'heal'), ('4', None)]:
                worker.send(op='answer', id=batch[-1]['id'], value=action)
                batch = worker.until(lambda e: e['event'] == 'prompt')
                support = [e for e in batch if e['event'] == 'battle_effect' and e.get('attacker') == 'player']
                if expected:
                    self.assertEqual(len(support), 1)
                    self.assertEqual(support[0]['attack'], expected)
                    self.assertGreater(support[0]['heal'], 0)
                    self.assertEqual(support[0]['damage'], 0)
                else:
                    self.assertEqual(support, [])
        finally: worker.close()


if __name__ == '__main__': unittest.main()
