"""Class artwork and event timing in the actual shared Qt stage; no model load."""
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from test_desktop import APP
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QImage
from gui.hero_portrait import ACTION_ART, POSES, pose_path, portrait_path, pose_pixmap
from gui.battle_arena import CombatStage
from gui.title_screen import TitleScreen

CLASSES = ('normal','robo','engelchen','magier','priester','puppy')


class ClassActionTests(unittest.TestCase):
    def dispose(self, widget):
        widget.close(); widget.deleteLater()
        QCoreApplication.sendPostedEvents(widget, QEvent.DeferredDelete)

    def test_all_existing_sheets_produce_transparent_distinct_poses(self):
        manifest = json.loads((ACTION_ART/'manifest.json').read_text())
        self.assertEqual(len(manifest['assets']),120)
        source = Path(__file__).resolve().parents[1]/manifest['source_set']
        # The file index retains the hash of every unmodified source board.
        for entry in manifest['assets']:
            with self.subTest(cls=entry['class_id'], pose=entry['pose']):
                path = ACTION_ART/entry['file']
                self.assertEqual(sha256(path.read_bytes()).hexdigest(),entry['sha256'])
                self.assertEqual(sha256((source/entry['source']).read_bytes()).hexdigest(),entry['source_sha256'])
                image = QImage(str(path))
                self.assertTrue(image.hasAlphaChannel())
                self.assertEqual((image.width(),image.height()),(416,416))
                for x,y in ((0,0),(415,0),(0,415),(415,415)):
                    self.assertEqual(image.pixelColor(x,y).alpha(),0)
        for cls in CLASSES:
            self.assertEqual(len({sha256(pose_path(cls,p).read_bytes()).hexdigest() for p in POSES}),len(POSES))
        self.assertLessEqual(pose_pixmap.cache_info().maxsize,24)

    def test_principles_support_and_skill_use_class_poses_with_original_queue_timing(self):
        stage = CombatStage()
        try:
            stage.resize(960,460); stage.show(); APP.processEvents()
            stage.set_enemy('Schattenwächter')
            started = []
            stage.effect_started.connect(lambda event: started.append((event['attack'],stage.hero.pose_id)))
            actions = {'h':'wave','b':'balance','s':'creation','v':'connection','r':'respect',
                       'skill':'spark','focus':'focus','potion':'heal','special':'impulse'}
            for cls in CLASSES:
                stage.set_hero_class(cls)
                for attack,pose in actions.items():
                    stage.show_effect(dict(attacker='player',attack=attack,damage=10,heal=5))
                self.assertEqual(stage.hero.pose_id,'wave')
                for attack,pose in actions.items():
                    self.assertEqual(stage.hero.pose_id,pose)
                    self.assertEqual(stage.hero.asset,pose_path(cls,pose))
                    self.assertEqual(started[-1],(attack,pose))
                    self.assertFalse(stage.grab().isNull())
                    for _ in range(7):stage.advance_effect()
                self.assertEqual(stage.hero.asset,portrait_path(cls))
                self.assertEqual(stage.hero.pose_id,'standard')
                self.assertIsNone(stage.effect)
            self.assertEqual(stage.effect_timer.interval(),225)
        finally:self.dispose(stage)

    def test_hit_masks_track_pose_changes_and_missing_pose_falls_back_to_own_class(self):
        stage = CombatStage()
        try:
            stage.set_hero_class('magier')
            stage.hero.set_pose('hurt')
            hurt = stage.hit_mask(stage.hero,320).toImage()
            stage.hero.set_pose('guard')
            guard = stage.hit_mask(stage.hero,320).toImage()
            self.assertNotEqual(hurt,guard)
            self.assertEqual(hurt.pixelColor(0,0).alpha(),0)
            with patch('gui.hero_portrait.pose_pixmap',return_value=type(stage.hero.pixmap)()):
                stage.hero.set_pose('wave')
                self.assertEqual(stage.hero.asset,portrait_path('magier'))
                self.assertTrue(stage.hero.isValid())
        finally:self.dispose(stage)

    def test_demo_reactions_and_return_to_pyramid_clear_pose_and_timers(self):
        screen = TitleScreen()
        try:
            screen.resize(1080,820); screen.show(); APP.processEvents()
            stage = screen.arena.stage
            for cls in CLASSES:
                screen.show_demo()
                stage.set_hero_class(cls)
                screen.arena.update_state(dict(active=True,enemy_name='Pharao',enemy_hp=80,
                    enemy_max_hp=80,player_hp=100,player_max_hp=100,resonance=0))
                stage.show_effect(dict(attacker='enemy',damage=14))
                stage.grab()
                self.assertEqual(stage.hero.pose_id,'hurt')
                stage.clear_effects()
                stage.show_effect(dict(attacker='enemy',damage=0))
                stage.grab()
                self.assertEqual(stage.hero.pose_id,'guard')
                stage.clear_effects()
                stage.presence.resonance=100
                stage.grab()
                self.assertEqual(stage.hero.pose_id,'charged')
                screen.arena.update_state(dict(active=False,enemy_hp=0))
                stage.grab()
                self.assertEqual(stage.hero.pose_id,'victory')
                screen.show_title()
                self.assertIsNone(stage.effect)
                self.assertEqual(stage.hero.pose_id,'standard')
                self.assertFalse(stage.effect_timer.isActive())
                self.assertFalse(stage.hit_timer.isActive())
                self.assertTrue(screen.isVisible())
                self.assertFalse(stage.sway_timer.isActive())
                screen.show_demo()
                self.assertFalse(stage.presence.victory)
        finally:self.dispose(screen)


if __name__ == '__main__':unittest.main()
