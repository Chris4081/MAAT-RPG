"""Every campaign boss retains its identity across language, replay and attacks."""
import hashlib
import json
import unittest
from test_desktop import APP
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QWidget
from apps.maat_rpg.plugins.battle.plugin_main import generate_boss_name, generate_final_name
from shared.core.boss_art import BOSS_ART, EGYPTIAN_BOSSES
from shared.core.monster_catalog import boss_artwork, enemy_display_name, entries, ENEMY_EFFECTS
from shared.core.terra_replay import targets
from gui.ascii_effects import FRAMES
from gui.battle_arena import ART, artwork_for, BattleArena
from gui.terra_map import BossMarker


class BossArtTests(unittest.TestCase):
    def dispose(self, widget):
        widget.close(); widget.deleteLater()
        QCoreApplication.sendPostedEvents(widget, QEvent.DeferredDelete)

    def test_all_25_numbers_are_distinct_in_both_languages_and_preserve_old_art(self):
        self.assertEqual([BOSS_ART[i] for i in range(1,6)],
                         ['pharaoh','broken_harmony','archon','time','sun'])
        hashes = set()
        for i in range(1,26):
            name = generate_boss_name(i)
            for language in ('de', 'en'):
                self.assertEqual(artwork_for(enemy_display_name(name, language)), BOSS_ART[i])
            hashes.add(hashlib.sha256((ART/(BOSS_ART[i]+'.svg')).read_bytes()).hexdigest())
        self.assertEqual(len(hashes), 25)
        self.assertEqual([artwork_for(generate_final_name(i)) for i in range(1,6)],
                         ['avatar','heart','crown','axis','light'])
        for name in ('Custom Pharaoh #6', 'Schatten Wächter #6', 'Pharao der Dissonanz #0',
                     'Pharao der Dissonanz #26', 'Pharao der Dissonanz #7', 'Avatar der Balance (Final 1)'):
            self.assertIsNone(boss_artwork(name))
        self.assertEqual(artwork_for('Pharao der Dissonanz'), 'pharaoh')

    def test_every_new_boss_has_all_ten_valid_attack_sprites_with_its_own_body(self):
        manifest = json.loads((ART/'attacks/manifest.json').read_text())
        for _, asset, *_ in EGYPTIAN_BOSSES:
            original = (ART/(asset+'.svg')).read_text()
            body = original[original.index('>')+1:original.rindex('</svg>')]
            self.assertTrue(QSvgRenderer(original.encode()).isValid())
            self.assertEqual(set(manifest[asset]), set(FRAMES))
            for effect in FRAMES:
                path = ART/'attacks'/manifest[asset][effect]
                self.assertIn(body, path.read_text())
                self.assertTrue(QSvgRenderer(str(path)).isValid(), path)

    def test_live_and_demo_bosses_animate_without_switching_to_old_silhouette(self):
        for demo in (False, True):
            arena = BattleArena(demo=demo)
            arena.resize(1050,720);arena.show();APP.processEvents()
            try:
                for i in range(1,26):
                    name, asset = generate_boss_name(i), BOSS_ART[i]
                    for language in ('en', 'de'):
                        arena.set_language(language)
                        arena.update_state(dict(active=True,enemy_name=name,enemy_hp=200,enemy_max_hp=250,
                                                player_hp=100,player_max_hp=150,fight_type='boss',phase=1))
                        stage = arena.stage
                        self.assertEqual(stage.enemy_art, asset)
                        self.assertTrue(stage.enemy.isValid())
                        self.assertTrue(stage.sway_timer.isActive())
                        for attack, effect in [('normal', ENEMY_EFFECTS.get(asset,'slash')), ('special','impulse')]:
                            stage.show_effect(dict(attacker='enemy',attack=attack,damage=14))
                            self.assertEqual(stage.attack_asset.name, f'{asset}-{effect}.svg')
                            self.assertTrue(stage.attack_sprite.isValid())
                            self.assertEqual(stage.hit_target,'player')
                            self.assertFalse(arena.grab().isNull())
                            for _ in range(7):stage.advance_effect()
                            self.assertIsNone(stage.attack_asset)
                            self.assertIsNone(stage.effect)
                            self.assertEqual(stage.enemy_art,asset)
                        stage.show_effect(dict(attacker='player',attack='h',damage=21))
                        self.assertEqual(stage.hit_target,'enemy')
                        self.assertFalse(arena.grab().isNull())
                        stage.clear_effects()
                # An explicitly selected editor portrait still wins over a boss name.
                arena.stage.set_enemy(generate_boss_name(8), {'art':'beast'})
                self.assertEqual(arena.stage.enemy_art, 'beast')
            finally:
                self.dispose(arena)

    def test_catalog_and_replay_map_use_every_boss_identity(self):
        for language in ('de','en'):
            rows = entries(language)
            bosses = [row for row in rows if row['category']=='Bosse']
            self.assertEqual(len(rows),50)
            self.assertEqual(len(bosses),25)
            self.assertEqual({artwork_for(row['art_name']) for row in bosses},set(BOSS_ART.values()))
            for row in bosses[5:]:
                self.assertIn('Egyptian motif:' if language=='en' else 'Ägyptisches Motiv:',row['details'])
        parent = QWidget()
        try:
            for target in targets():
                marker = BossMarker(target,parent)
                art = marker.findChild(QSvgWidget)
                self.assertTrue(art.renderer().isValid())
                marker.set_language('en')
                self.assertIn(enemy_display_name(target['name'],'en'),marker.toolTip())
                self.dispose(marker)
        finally:
            self.dispose(parent)


if __name__ == '__main__':unittest.main()
