import os
import unittest
from dataclasses import replace
from unittest.mock import patch
from test_desktop import APP
import test_live_window as helpers
from apps.maat_rpg import session_shared
from gui.live_window import LiveWindow
from gui.monster_catalog import MonsterCatalog
from gui.battle_arena import ART,artwork_for
from shared.core.monster_catalog import entries,ENEMY_KINDS,BOSS_NAMES,FINAL_NAMES

class MonsterTests(unittest.TestCase):
    def test_portraits_search_and_level_boundary(self):
        w=MonsterCatalog()
        try:
            w.set_level(49);self.assertEqual(w.pages.currentIndex(),0);self.assertEqual(w.list.count(),0)
            w.set_level(50);self.assertEqual(w.pages.currentIndex(),1);self.assertEqual(w.list.count(),len(ENEMY_KINDS)+30)
            for r in entries():self.assertTrue((ART/(artwork_for(r['art_name'])+'.svg')).is_file())
            w.category.setCurrentText('Bosse');self.assertEqual(w.list.count(),25)
            w.search.setText('pharao');self.assertEqual(w.list.count(),5);self.assertEqual(w.name.text(),BOSS_NAMES[0]+' #1')
            w.search.setText('nonexistent');self.assertEqual(w.list.count(),0);self.assertTrue(w.art.isHidden())
            w.search.clear();w.category.setCurrentText('Alle');w.resize(1050,740);w.show();APP.processEvents();w.grab().save('/tmp/maat-monster-catalog.png')
            w.set_level(1);self.assertEqual(w.pages.currentIndex(),0);self.assertEqual(w.list.count(),0);self.assertFalse(w.description.text())
        finally:w.close();w.deleteLater();APP.processEvents()
    def test_live_unlock_and_profile_downgrade(self):
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            w=LiveWindow(audio=helpers.SilentAudio())
            w.request_title_start()
            w.choose_profile(w.game._profile_slot())
            try:
                helpers.LiveWindowTest.spin(self,lambda:w.game.ready)
                w.phase='playing';w.navigate(3);snapshot=w.game.get_snapshot()
                for level in (49,50,51,1):
                    state=replace(snapshot,player=replace(snapshot.player,level=level))
                    with patch.object(w.game,'get_snapshot',return_value=state):
                        w.update_controls();self.assertFalse(hasattr(w,'monster_button'))
                        self.assertEqual(w.world_tabs.isTabEnabled(w.monster_tab),level>=50)
                        w.open_monster_catalog()
                        if level>=50:self.assertIs(w.world_tabs.currentWidget(),w.monster_catalog)
                        else:self.assertIsNot(w.world_tabs.currentWidget(),w.monster_catalog)
            finally:w.close();APP.processEvents()
