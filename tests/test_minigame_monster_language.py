"""English offers and enemy names preserve game IDs, portraits and rewards."""
from copy import deepcopy
from itertools import product
import unittest
from unittest.mock import patch
from test_desktop import APP
from PySide6.QtCore import QCoreApplication,QEvent
import test_gui_language as language_helpers
from apps.maat_rpg import session_shared as shared
from shared.core.minigames import CATALOG
from shared.core.minigame_i18n import EN_GAMES,game_info
from shared.core.monster_catalog import (ENEMY_PREFIXES,ENEMY_KINDS,ENEMY_SUFFIXES,
    BOSS_NAMES,FINAL_NAMES,enemy_display_name,canonical_enemy_name,entries)
from shared.core.dungeon_campaign import THEMES,NEW_GUARDIANS
from gui.battle_arena import BattleArena,artwork_for
from gui.game_hall import GameHall
from gui.monster_catalog import MonsterCatalog


class NameTests(unittest.TestCase):
    def test_all_random_names_bosses_and_dungeon_guardians_translate(self):
        names=[p+' '+k+s for p,k,s in product(ENEMY_PREFIXES,ENEMY_KINDS,ENEMY_SUFFIXES)]
        self.assertEqual(len(names),1080)
        names += [n+f' #{i}' for i,n in enumerate(BOSS_NAMES,1)]
        names += [n+f' (Final {i})' for i,n in enumerate(FINAL_NAMES,1)]
        names += [t[4] for t in THEMES]+NEW_GUARDIANS
        for name in names:
            translated=enemy_display_name(name,'en')
            if translated==name:
                self.assertIn(name,('Echo Wanderer','Echo Phantom','Echo Idol','Echo Golem'))
            self.assertEqual(enemy_display_name(translated,'de'),name)
            self.assertEqual(artwork_for(translated),artwork_for(name))
        self.assertEqual(enemy_display_name('Gefallener Wanderer','en'),'Fallen Wanderer')
        self.assertEqual(enemy_display_name('Pharao der Dissonanz #6','en'),'Pharaoh of Dissonance #6')
        self.assertEqual(enemy_display_name('Achse des Äons (Final 4)','en'),'Axis of the Aeon (Final 4)')
        self.assertEqual(enemy_display_name('A Modded Name','en'),'A Modded Name')
        de,en=entries(),entries('en')
        self.assertEqual([r['art_name'] for r in de],[r['art_name'] for r in en])

    def test_shared_battle_demo_names_badges_hp_and_portrait_survive_translation(self):
        for demo in (False,True):
            arena=BattleArena(demo=demo)
            try:
                data=dict(active=True,enemy_name='Schatten Funke der Leere',enemy_level=12,
                    arena_difficulty='hard',fight_type='normal',enemy_hp=100,enemy_max_hp=120)
                arena.update_state(data);original=deepcopy(data)
                for language in ('en','de','en'):
                    arena.set_language(language)
                    self.assertTrue(arena.enemy_name.text().startswith('● '))
                    self.assertIn('Shadow Spark of the Void' if language=='en' else 'Schatten Funke der Leere',arena.enemy_name.text())
                    self.assertEqual(arena.stage.name,'Schatten Funke der Leere')
                    self.assertEqual(arena.enemy_hp.value(),100)
                    self.assertEqual(data,original)
            finally:
                arena.close();arena.deleteLater();QCoreApplication.sendPostedEvents(arena,QEvent.DeferredDelete)

    def test_catalog_filter_translates_and_unlock_stays_level_50(self):
        catalog=MonsterCatalog()
        try:
            catalog.set_language('en');catalog.set_level(49)
            self.assertIn('level 50',catalog.lock.text())
            self.assertEqual(catalog.list.count(),0)
            catalog.set_level(50)
            catalog.category.setCurrentIndex(catalog.category.findData('Finalgegner'))
            self.assertEqual(catalog.list.count(),5)
            catalog.search.setText('Aeon')
            self.assertEqual(catalog.list.count(),1)
            self.assertEqual(catalog.name.text(),'Axis of the Aeon')
            catalog.search.clear();catalog.set_language('de')
            self.assertEqual(catalog.category.currentData(),'Finalgegner')
            self.assertEqual(catalog.list.count(),5)
        finally:catalog.close();catalog.deleteLater();APP.processEvents()

    def test_hall_names_records_discovery_and_canonical_play_ids(self):
        chosen=[];hall=GameHall(['maat_coil'],lambda kind,view:chosen.append(kind))
        try:
            hall.update_discoveries(['maat_coil','maat_respect'],{'maat_coil':{'value':23}})
            hall.set_language('en')
            self.assertIn('THE ARCADE',hall.title.text())
            self.assertIn('2 / 23 games discovered',hall.summary.text())
            self.assertIn('Guardian of Respect',hall.names['maat_respect'].text())
            self.assertIn('23 covenants',hall.records['maat_coil'].text())
            self.assertIn('higher is better',hall.records['maat_coil'].text())
            self.assertIn('Not discovered',hall.buttons['temple_circles'].text())
            hall.buttons['maat_coil'].click();self.assertEqual(chosen,['maat_coil'])
            hall.set_language('de');self.assertIn('23 Bünde',hall.records['maat_coil'].text())
            self.assertFalse(hall.buttons['temple_circles'].isEnabled())
        finally:hall.close();hall.deleteLater();APP.processEvents()


class OfferTests(unittest.TestCase):
    setUp=language_helpers.LanguageTests.setUp
    close_windows=language_helpers.LanguageTests.close_windows
    window=language_helpers.LanguageTests.window
    ready=language_helpers.LanguageTests.ready

    def test_all_23_chat_offers_translate_on_arrival_and_language_change(self):
        shared.write_application_language('en');shared.set_profile_name(1,'Language test')
        window=self.window();self.ready(window)
        self.assertEqual(set(CATALOG),set(EN_GAMES))
        for kind in CATALOG:
            offer={'id':7,'game':kind,'seed':42,'attempts':1}
            event={'event':'minigame','data':{'pending':offer,'discovered':[kind]}}
            original=deepcopy(event)
            window.receive(event)
            self.assertIn('Minigame',window.minigame_title.text())
            self.assertIn(game_info(kind,'en')[0],window.minigame_title.text())
            self.assertIn(' XP + ',window.minigame_reward.text())
            self.assertIn('One-time reward',window.minigame_reward.text())
            self.assertEqual(window.minigame_play.text(),'Play · 1/2 attempts left')
            self.assertEqual(window.minigame_skip.text(),'Continue journey')
            self.assertEqual(event,original)
            self.assertEqual(game_info(kind,'en')[2:],CATALOG[kind][2:])
        # The exact offer from the reported screenshot, with no new worker event.
        window.receive({'event':'minigame','data':{'pending':{'id':7,'game':'maat_respect','attempts':1}}})
        snapshot=window.game.get_snapshot()
        with patch.object(window.game,'get_snapshot',return_value=__import__('dataclasses').replace(snapshot,language='de')):
            window.apply_menu_language()
            self.assertIn('Hüter des Respekts',window.minigame_title.text())
        window.apply_menu_language()
        self.assertIn('Guardian of Respect',window.minigame_title.text())
