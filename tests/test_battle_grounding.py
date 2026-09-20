"""Actual arena paint geometry stays registered across padded class sprites."""
import unittest
from unittest.mock import Mock, patch
from PIL import Image
from PySide6.QtCore import QCoreApplication, QEvent, QPointF, QRectF
from PySide6.QtGui import QTransform
from test_desktop import APP
from gui.battle_arena import CombatStage
from gui.hero_portrait import POSES, portrait_path


class BattleGroundingTests(unittest.TestCase):
    def setUp(self):
        self.stage = CombatStage()
        self.stage.set_enemy('Gefallener Wanderer')
        self.stage.resize(960, 460)
        self.stage.show()
        APP.processEvents()
        self.stage.sway_timer.stop()
        self.clock = Mock()
        self.clock.isValid.return_value = True
        self.clock.elapsed.return_value = 0
        self.stage.sway_clock = self.clock

    def tearDown(self):
        self.stage.close()
        self.stage.deleteLater()
        QCoreApplication.sendPostedEvents(self.stage, QEvent.DeferredDelete)

    def paint_registration(self):
        hero, effects = [], []
        render, paint = self.stage.hero.render, self.stage.presence.paint

        def record_hero(painter, rect):
            hero.append((QTransform(painter.worldTransform()), QRectF(rect)))
            render(painter, rect)

        def record_effect(painter, rect, *args, **kwargs):
            effects.append((QTransform(painter.worldTransform()), QRectF(rect)))
            paint(painter, rect, *args, **kwargs)

        with patch.object(self.stage.hero, 'render', side_effect=record_hero), \
                patch.object(self.stage.presence, 'paint', side_effect=record_effect):
            self.assertFalse(self.stage.grab().isNull())
        self.assertEqual(len(hero), 1)
        self.assertEqual(len(effects), 2)  # Aura behind the body and the front effects.
        return hero[0], effects

    def projected_feet(self, registration):
        transform, rect = registration
        with Image.open(portrait_path(self.stage.hero.class_id)) as image:
            foot = image.getchannel('A').getbbox()[3] / image.height
        if self.stage.hero.pose_id != 'standard':
            # The unchanged extraction pipeline registers a 320px body inside
            # a 416px canvas with 48px margins. No per-pose alpha crop is valid:
            # particles or lifted arms could change those bounds.
            foot = (48 + foot*320) / 416
        return transform.map(QPointF(rect.center().x(), rect.top()+rect.height()*foot))

    def assert_effects_follow_feet(self, hero, effects):
        feet = self.projected_feet(hero)
        for transform, rect in effects:
            effect_feet = transform.map(QPointF(rect.center().x(), rect.top()+rect.height()*225/240))
            self.assertAlmostEqual(effect_feet.x(), feet.x(), places=6)
            self.assertAlmostEqual(effect_feet.y(), feet.y(), places=6)
        return feet

    def test_all_classes_and_poses_stand_on_floor_at_different_aspect_ratios(self):
        for cls in ('normal', 'robo', 'engelchen', 'magier', 'priester', 'puppy'):
            self.stage.set_hero_class(cls)
            for width, height in ((1320, 540), (420, 210), (700, 760)):
                self.stage.resize(width, height)
                for pose in ('standard', *sorted(POSES)):
                    with self.subTest(cls=cls, size=(width, height), pose=pose), \
                            patch.object(self.stage.presence, 'pose', return_value=pose):
                        hero, effects = self.paint_registration()
                        feet = self.assert_effects_follow_feet(hero, effects)
                        self.assertAlmostEqual(feet.x(), width*.25, places=6)
                        self.assertAlmostEqual(feet.y(), height*.92, places=6)

    def test_attack_and_support_share_sway_lunge_and_lift_with_effects(self):
        self.stage.set_hero_class('engelchen')
        self.clock.elapsed.return_value = 650
        for action in ('h', 'focus', 'impulse'):
            with self.subTest(action=action):
                self.stage.show_effect(dict(attacker='player', attack=action, damage=14, heal=8))
                self.stage.effect_timer.stop()
                self.stage.hit_timer.stop()
                self.stage.effect_clock = self.clock
                hero, effects = self.paint_registration()
                feet = self.assert_effects_follow_feet(hero, effects)
                if action == 'h':
                    self.assertAlmostEqual(feet.y(), self.stage.height()*.92, places=6)
                    self.assertGreater(feet.x(), self.stage.width()*.25)
                else:
                    self.assertLess(feet.y(), self.stage.height()*.92)
                self.stage.clear_effects()
