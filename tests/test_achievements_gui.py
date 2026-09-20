import unittest
from unittest.mock import Mock
from test_desktop import APP
from shared.core.achievement_catalog import snapshot,TRIGGERS,COMBAT_ACHIEVEMENTS,EMOTIONAL
from shared.core.minigames import CATALOG,begin_attempt,resolve,begin_practice,resolve_practice
from gui.achievements import Achievements
from test_temple_arcade import solution

class AchievementTests(unittest.TestCase):
    def test_terminal_catalog_and_saved_unlocks(self):
        data=snapshot({'achievements':{'combat':['boss_no_potion']}}, {'unlocked':['hallo']}, {'achievements':{'grateful':True}})
        groups=data['groups']
        self.assertEqual(len(groups['Worte & Entdeckungen']),len(TRIGGERS))
        self.assertEqual(len(groups['Emotionale Erfolge']),len(EMOTIONAL))
        self.assertEqual(len(groups['Kampf']),len(COMBAT_ACHIEVEMENTS))
        self.assertEqual(len(groups['Minispiele']),len(CATALOG)+9)
        self.assertEqual(data['unlocked'],3)
    def test_chat_and_practice_count_once_without_practice_xp(self):
        core=Mock(state={'player':{'gold':0},'minigames':{'discovered':['memory'],'pending':{'id':1,'game':'memory','seed':7}}})
        attempt=begin_attempt(core,1)
        resolve(core,1,solution('memory').moves,ticket=attempt['ticket'])
        resolve(core,1,solution('memory').moves,ticket=attempt['ticket'])
        self.assertEqual(core.state['minigames']['wins'],{'memory':1})
        self.assertEqual(core.state['minigames']['first_try_wins'],1)
        self.assertIsNone(begin_practice(core,'wheel'))
        practice=begin_practice(core,'memory')
        moves=solution('memory',practice['seed']).moves
        self.assertIn('gewonnen',resolve_practice(core,practice['ticket'],moves))
        resolve_practice(core,practice['ticket'],moves)
        self.assertEqual(core.state['minigames']['wins'],{'memory':2})
        core.add_xp.assert_called_once_with(55)
        self.assertEqual(core.state['player']['gold'],20)
        data=snapshot(core.state)
        unlocked={r['id'] for r in data['groups']['Minispiele'] if r['unlocked']}
        self.assertEqual(unlocked,{'arcade:discover:1','arcade:wins:1','arcade:game:memory'})
    def test_filters_updates_and_profile_reset(self):
        widget=Achievements()
        try:
            widget.update_data(snapshot({}))
            widget.update_data(snapshot({'minigames':{'discovered':['wheel'],'wins':{'wheel':1}}}))
            self.assertIn('Neu freigeschaltet',widget.notice.text())
            widget.category.setCurrentText('Minispiele');widget.status.setCurrentIndex(1)
            self.assertFalse(widget.rows['arcade:game:wheel'][0].isHidden())
            self.assertTrue(widget.rows['word:hallo'][0].isHidden())
            widget.search.setText('Nicht vorhanden')
            self.assertTrue(widget.rows['arcade:game:wheel'][0].isHidden())
            widget.reset();self.assertEqual(widget.notice.text(),'')
            widget.update_data(snapshot({}));self.assertEqual(widget.notice.text(),'')
        finally:widget.deleteLater();APP.processEvents()
    def test_worker_practice_reward_validation_and_persistence(self):
        import json
        from pathlib import Path
        from test_live_rpg import Worker
        state={'player':{'gold':25,'level':5,'xp':0},'minigames':{'serial':1,'last_offer':15,'pending':None,'discovered':['memory']}}
        worker=Worker(seed={'battle_state.json':state,'achievements_state.json':{'unlocked':['hallo']}})
        try:
            worker.send(op='hall_start',game='memory')
            events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            attempt=next(e['data'] for e in events if e['event']=='minigame_started')
            worker.send(op='hall_result',ticket=attempt['ticket'],moves=solution('memory',attempt['seed']).moves)
            events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            data=next(e['data'] for e in events if e['event']=='achievements')
            self.assertTrue(next(r for r in data['groups']['Minispiele'] if r['id']=='arcade:game:memory')['unlocked'])
            saved=json.loads((Path(worker.temp.name)/'state/battle_state.json').read_text())
            self.assertEqual(saved['minigames']['wins'],{'memory':1})
            self.assertEqual(saved['minigames']['highscores']['memory']['value'],8)
            self.assertEqual(saved['player']['gold'],25);self.assertEqual(saved['player']['xp'],0)
        finally:worker.close()
        worker=Worker(seed={'battle_state.json':saved})
        try:
            worker.send(op='models');events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            data=next(e['data'] for e in events if e['event']=='achievements')
            self.assertTrue(next(r for r in data['groups']['Minispiele'] if r['id']=='arcade:game:memory')['unlocked'])
            hall=next(e['data'] for e in events if e['event']=='minigame')
            self.assertEqual(hall['highscores']['memory']['value'],8)
        finally:worker.close()

    def test_live_window_commands_open_achievement_tab(self):
        import os
        from unittest.mock import patch
        from apps.maat_rpg import session_shared
        import test_live_window as helpers
        from gui.live_window import LiveWindow
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            window=LiveWindow(audio=helpers.SilentAudio())
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
            try:
                helpers.LiveWindowTest.spin(self,lambda:window.game.ready)
                window.phase='playing'
                window.execute('/erfolge')
                self.assertEqual(window.stack.currentIndex(),5)
                self.assertIs(window.world_tabs.currentWidget(),window.achievements)
                self.assertEqual(window.achievements.category.currentText(),'Alle Kategorien')
                self.assertEqual(window.achievements.data['total'],len(TRIGGERS)+len(EMOTIONAL)+len(COMBAT_ACHIEVEMENTS)+len(CATALOG)+9)
                window.execute('/ach')
                self.assertEqual(window.achievements.category.currentText(),'Emotionale Erfolge')
                self.assertIsNone(window.game.prompt_id)
            finally:window.close();APP.processEvents()
