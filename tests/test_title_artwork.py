"""Terra title art at real campaign boundaries, cold startup and profile/demo transitions."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_desktop import APP, ROOT
import test_gui_language as helpers
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QColor
from gui.desktop import STYLE
from gui.title_artwork import ART, REGION_KEYS, REGIONS_EN, JourneyArtwork, artwork_key, landscape, saved_journey
from gui.title_screen import TitleScreen
from apps.maat_rpg import session_shared as shared
from shared.core.terra_journey import snapshot, reset_after_defeat


def campaign(bosses=0, finals=0):
    return {'world': {'combat_unlocked': True},
            'stats': {'boss_wins': bosses, 'final_wins': finals, 'boss_progress': 12}}


class ArtworkRulesTests(unittest.TestCase):
    def test_actual_unlock_all_regions_final_gates_and_retries(self):
        for messages in (0, 5, 29, 30, 31):
            self.assertEqual(artwork_key(snapshot({}, {'messages_total': messages})), 'pyramid')
        # Completing the introduction, not merely having 30 messages, opens map two.
        self.assertEqual(artwork_key(snapshot(campaign())), 'desert')
        for region, key in enumerate(REGION_KEYS):
            for local_boss in range(5):
                state = campaign(region*5+local_boss, region)
                before = deepcopy(state)
                self.assertEqual(artwork_key(snapshot(state)), key)
                self.assertEqual(state, before)
            # Fifth boss won: remain in this region until its final is also won.
            state = campaign((region+1)*5, region)
            self.assertEqual(snapshot(state)['kind'], 'final')
            self.assertEqual(artwork_key(snapshot(state)), key)
            self.assertTrue(reset_after_defeat(state, 'final', {'combat_source':'random'}))
            self.assertEqual(artwork_key(snapshot(state)), key)
            state['stats']['final_wins'] += 1
            self.assertEqual(artwork_key(snapshot(state)), REGION_KEYS[min(4, region+1)])
        self.assertEqual(snapshot(campaign(25,5))['kind'], 'complete')
        for invalid in (None, {}, {'kind':'battle','region':-1}, {'kind':'battle','region':99},
                        {'kind':'battle','region':'1'}, {'kind':'other','region':0}):
            self.assertEqual(artwork_key(invalid), 'pyramid')

    def test_render_all_art_languages_sizes_and_missing_asset_fallback(self):
        screen = TitleScreen(); screen.setStyleSheet(STYLE)
        self.addCleanup(screen.deleteLater)
        screen.set_model_state('ready'); screen.blink.stop()
        screen.show()
        preview = os.environ.get('MAAT_TITLE_ART_PREVIEW')
        scenes = [('pyramid', snapshot({}))] + [(key, snapshot(campaign(i*5, i)))
                                               for i,key in enumerate(REGION_KEYS)]
        for key, data in scenes:
            screen.landscape.set_journey(data)
            for language in ('de', 'en'):
                screen.landscape.set_language(language)
                for width,height in ((880,650), (1440,840), (2310,893)):
                    screen.resize(width,height); APP.processEvents()
                    rendered = screen.landscape.grab().toImage()
                    self.assertFalse(rendered.isNull())
                    if key != 'pyramid':
                        self.assertFalse(screen.landscape.image.isNull(), str(ART/(key+'.png')))
                        self.assertEqual(rendered.pixelColor(0,0), QColor('#080f23'))
                        self.assertEqual(rendered.pixelColor(rendered.width()-1,0), QColor('#080f23'))
                        if language == 'en':
                            self.assertEqual(screen.landscape.caption(), REGIONS_EN[REGION_KEYS.index(key)])
                    if preview and language == 'de' and width == 1440:
                        folder = Path(preview); folder.mkdir(parents=True, exist_ok=True)
                        self.assertTrue(screen.grab().save(str(folder/(key+'.png'))))
        # Corrupt/missing installation asset must keep a usable title and Enter button.
        with tempfile.TemporaryDirectory() as empty, patch('gui.title_artwork.ART', Path(empty)):
            landscape.cache_clear()
            screen.landscape.set_journey(snapshot({}))
            screen.landscape.set_journey(snapshot(campaign()))
            self.assertTrue(screen.landscape.image.isNull())
            self.assertFalse(screen.landscape.grab().isNull())
            self.assertTrue(screen.start_button.isEnabled())
        landscape.cache_clear()
        screen.close()


class ProfileArtworkTests(unittest.TestCase):
    setUp = helpers.LanguageTests.setUp
    close_windows = helpers.LanguageTests.close_windows
    window = helpers.LanguageTests.window
    ready = helpers.LanguageTests.ready

    def test_missing_or_damaged_save_and_companion_intro_count(self):
        self.assertEqual(artwork_key(saved_journey(6)), 'pyramid')
        self.assertFalse(shared.profile_slot_root(6).exists())
        shared.write_profile_settings(6, {'gui_perspective':'companion'})
        root = shared.profile_slot_root(6)/'state'
        shared.save_json_file(root/'battle_state.json', {'stats':None, 'world':[]})
        shared.save_json_file(root/'story_state.json', {'messages_total':1})
        shared.save_json_file(root/'companion_story_state.json', {'messages_total':29})
        self.assertEqual(saved_journey(6)['position'], 29)
        self.assertEqual(artwork_key(saved_journey(6)), 'pyramid')
        (root/'battle_state.json').write_text('{broken', encoding='utf-8')
        self.assertEqual(artwork_key(saved_journey(6)), 'pyramid')

    def test_cold_start_uses_saved_profile_and_switch_to_new_profile_clears_old_art(self):
        shared.write_application_language('en')
        shared.set_profile_name(4, 'Crystal traveller')
        shared.write_profile_settings(4, {'gui_perspective':'companion'})
        root = shared.profile_slot_root(4)/'state'
        shared.save_json_file(root/'battle_state.json', campaign(10,2))
        shared.save_json_file(root/'companion_story_state.json', {'messages_total':47})
        shared.save_json_file(root/'story_state.json', {'messages_total':2})
        shared.write_profile_manager_state({'active_profile':4})
        before = {p.name:p.read_bytes() for p in root.iterdir()}
        self.assertEqual(saved_journey(4)['region'], 2)
        self.assertEqual(before, {p.name:p.read_bytes() for p in root.iterdir()})
        window = self.window()
        self.assertIsNone(window.game.process)
        self.assertEqual(window.phase, 'title')
        self.assertEqual(window.title_screen.landscape.key, 'coast')
        self.assertEqual(window.menu_pyramid.key, 'coast')
        self.assertEqual(window.title_screen.landscape.caption(), 'Crystal Coast of Resonance')
        self.assertEqual(window.title_screen.landscape.image.cacheKey(), window.menu_pyramid.image.cacheKey())
        shared.set_profile_name(1, 'New traveller')
        window.request_title_start(); window.choose_profile(1)
        self.assertEqual(window.title_screen.landscape.key, 'pyramid')
        self.assertEqual(window.menu_pyramid.key, 'pyramid')
        self.ready(window)
        self.assertEqual(window.title_screen.landscape.key, 'pyramid')

    def test_real_profile_event_changes_art_and_demo_does_not_advance_it(self):
        shared.write_application_language('de')
        window = self.window()
        self.assertEqual(window.title_screen.landscape.key, 'pyramid')
        for region,key in enumerate(REGION_KEYS):
            journey = snapshot(campaign(region*5,region))
            window.receive({'event':'profile', 'data':{'chat_messages':30, 'combat_unlocked':True,
                                                       'journey':journey}})
            self.assertEqual(window.title_screen.landscape.key, key)
            self.assertEqual(window.menu_pyramid.key, key)
        window.phase = 'title_demo'; window.title_screen.show_demo()
        window.present_demo({'event':'profile', 'data':{'journey':snapshot(campaign())}})
        window.demo_finished(); APP.processEvents()
        self.assertEqual(window.phase, 'title')
        self.assertEqual(window.title_screen.views.currentIndex(), 0)
        self.assertEqual(window.title_screen.landscape.key, 'terra')
        self.assertEqual(window.title_idle.interval(), 20000)
        self.assertTrue(window.isVisible())
        window.game.get_snapshot().language = 'en'; window.apply_menu_language()
        self.assertEqual(window.title_screen.landscape.caption(), 'The Light of Terra')
        self.assertEqual(window.menu_pyramid.caption(), 'The Light of Terra')


if __name__ == '__main__':
    unittest.main()
