"""Verify real alpha compositing in the views affected by the navy rectangles."""
import json
import hashlib
import unittest
from test_desktop import APP
from PySide6.QtCore import QRectF, QCoreApplication, QEvent
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QWidget
from gui.hero_portrait import ART, HeroPortrait, portrait_path
from gui.battle_arena import CombatStage
from gui.story_screen import StoryScreen
from gui.desktop import STYLE


class ClassPortraitTests(unittest.TestCase):
    def dispose(self, widget):
        widget.close()
        widget.deleteLater()
        QCoreApplication.sendPostedEvents(widget, QEvent.DeferredDelete)

    def test_assets_have_real_alpha_and_preserve_original_interior_colors(self):
        dark_points = {'normal': (620, 300), 'robo': (620, 435),
                       'engelchen': (620, 300), 'magier': (630, 915),
                       'priester': (620, 300), 'puppy': (600, 400)}
        manifest = json.loads((ART/'manifest.json').read_text())
        self.assertEqual({a['name'] for a in manifest['assets']}, set(dark_points))
        for item in manifest['assets']:
            with self.subTest(name=item['name']):
                source = ART/item['source']
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), item['source_sha256'])
                target = portrait_path(item['name'])
                self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), item['sha256'])
                before, after = QImage(str(source)), QImage(str(target))
                self.assertTrue(after.hasAlphaChannel())
                self.assertEqual(after.size(), before.size())
                for point in ((0, 0), (1253, 0), (0, 1253), (1253, 1253), (627, 115)):
                    # The tall wizard hat reaches above y=115; its corners remain clear.
                    if point == (627, 115) and item['name'] == 'magier': continue
                    self.assertEqual(after.pixelColor(*point).alpha(), 0)
                for point in (dark_points[item['name']], (625, 750)):
                    self.assertEqual(after.pixelColor(*point), before.pixelColor(*point))
                self.assertGreater(item['partial_alpha_pixels'], 0)
        for name, point in (('magier', (270, 600)), ('priester', (312, 340))):
            self.assertEqual(QImage(str(portrait_path(name))).pixelColor(*point).alpha(), 0)

    def test_portrait_and_hit_flash_leave_background_visible(self):
        stage = CombatStage()
        try:
            for name in ('normal', 'robo', 'engelchen', 'magier', 'priester', 'puppy'):
                with self.subTest(name=name):
                    stage.set_hero_class(name)
                    flash = stage.hit_mask(stage.hero, 300).toImage()
                    self.assertEqual(flash.pixelColor(0, 0).alpha(), 0)
                    self.assertEqual(flash.pixelColor(150, 179), QColor('#ff354d'))
                    canvas = QPixmap(300, 300)
                    background = QColor('#46739a')
                    canvas.fill(background)
                    painter = QPainter(canvas)
                    stage.hero.render(painter, QRectF(0, 0, 300, 300))
                    painter.end()
                    rendered = canvas.toImage()
                    self.assertEqual(rendered.pixelColor(0, 0), background)
                    self.assertNotEqual(rendered.pixelColor(150, 179), background)
        finally: self.dispose(stage)

    def test_portrait_widget_uses_its_parent_background_despite_global_theme(self):
        parent = QWidget()
        parent.setObjectName('portraitTest')
        parent.setStyleSheet(STYLE+'\nQWidget#portraitTest {background: #264c72;}')
        parent.resize(180, 180)
        portrait = HeroPortrait(110, parent)
        portrait.move(30, 30)
        try:
            parent.show(); APP.processEvents()
            rendered = parent.grab().toImage()
            self.assertEqual(rendered.pixelColor(31, 31), rendered.pixelColor(10, 10))
            self.assertEqual(rendered.pixelColor(31, 31), QColor('#264c72'))
        finally: self.dispose(parent)

    def test_story_portrait_uses_navy_but_cinematic_scenes_keep_letterboxing(self):
        screen = StoryScreen()
        try:
            screen.hero_class = 'puppy'
            screen.start_scene(dict(id='portrait', module='companion', image='maatis-human.png', lines=['Maatis.']))
            screen.artwork.resize(600, 300)
            self.assertEqual(screen.artwork.grab().toImage().pixelColor(0, 0), QColor('#080f23'))
            screen.start_scene(dict(id='scene', module='story1', lines=['Das Erwachen.']))
            self.assertEqual(screen.artwork.background, QColor('#000000'))
        finally:
            screen.cancel(); self.dispose(screen)
