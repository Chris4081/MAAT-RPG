import json
import unittest
from pathlib import Path
from test_desktop import APP
from gui.character_sidebar import CharacterSidebar
from shared.core.achievement_history import enrich
from test_live_rpg import Worker

class SidebarStatisticsTests(unittest.TestCase):
    def test_history_migration_new_order_reload_and_no_duplicates(self):
        def snapshot(keys):return {'groups':{'Kampf':[dict(id=k,name=k,unlocked=True) for k in keys]},'total':4,'unlocked':len(keys)}
        state={};self.assertEqual(enrich(state,snapshot(['old']))['recent'],[])
        data=enrich(state,snapshot(['old','first']));self.assertEqual([e['id'] for e in data['recent']],['first'])
        state=json.loads(json.dumps(state));data=enrich(state,snapshot(['old','first','second']))
        self.assertEqual([e['id'] for e in data['recent']],['second','first'])
        enrich(state,snapshot(['old','first','second']));self.assertEqual(len(state['achievement_history']['events']),2)
    def test_sidebar_totals_scroll_collapse_and_reset(self):
        w=CharacterSidebar()
        try:
            w.update_achievements({'total':94,'unlocked':24,'groups':{'Kampf':[{'unlocked':True},{'unlocked':False}]},'recent':[{'name':'Ein neuer Erfolg','at':'2026-09-08T20:00:00+00:00'}]})
            w.update_dungeons({'0':{'attempts':4,'completed':2,'best_room':5},'1':{'attempts':1,'completed':0,'best_room':3}})
            self.assertIn('24 / 94',w.achievement_summary.text());self.assertEqual(w.achievement_progress.value(),24)
            self.assertIn('40 %',w.dungeon_summary.text());self.assertIn('Orte gemeistert: 1',w.dungeon_summary.text())
            self.assertIn('Ein neuer Erfolg',w.recent_achievements.text())
            w.resize(240,400);w.show();APP.processEvents()
            self.assertGreater(w.scroll.verticalScrollBar().maximum(),0)
            w.toggle_expanded();self.assertTrue(w.scroll.isHidden());w.toggle_expanded();self.assertFalse(w.scroll.isHidden())
            w.reset_statistics();self.assertNotIn('Ein neuer Erfolg',w.recent_achievements.text());self.assertIn('Durchläufe: 0',w.dungeon_summary.text())
        finally:w.close();w.deleteLater();APP.processEvents()
    def test_worker_persists_observed_unlocks(self):
        w=Worker()
        try:
            path=Path(w.temp.name)/'state/achievements_state.json'
            path.write_text(json.dumps({'unlocked':['hallo']}))
            events=w.command('/quests');data=next(e['data'] for e in events if e['event']=='achievements')
            self.assertEqual(data['recent'][0]['id'],'word:hallo')
            saved=json.loads((Path(w.temp.name)/'state/battle_state.json').read_text())
            self.assertEqual(saved['achievement_history']['events'][0]['id'],'word:hallo')
            events=w.command('/quests');data2=next(e['data'] for e in events if e['event']=='achievements')
            self.assertEqual(data2['recent'],data['recent'])
        finally:w.close()

    def test_quest_limit_live_progress_completion_and_clear(self):
        w=CharacterSidebar()
        try:
            quests=[dict(id=str(i),name=f'Aufgabe {i}',target=10,progress=3,completed=False) for i in range(7)]
            w.update_quests({'groups':{'active':quests,'available':[{'name':'Nicht angenommen'}]}})
            self.assertEqual(sum(not r.isHidden() for r,n,b in w.quest_rows),5)
            self.assertEqual(w.quest_rows[0][2].format(),'3/10')
            self.assertIn('2 weitere',w.quest_hint.text())
            quests[0]['completed']=True;quests[1]['progress']=7
            w.update_quests({'groups':{'active':quests}})
            self.assertEqual(w.quest_rows[0][1].text(),'Aufgabe 1')
            self.assertEqual(w.quest_rows[0][2].format(),'7/10')
            w.update_quests({'groups':{'active':[dict(name='Beobachten',target=None,progress_text='Noch offen')]}})
            self.assertTrue(w.quest_rows[0][2].isHidden());self.assertIn('Noch offen',w.quest_rows[0][1].text())
            w.reset_statistics();self.assertTrue(all(r.isHidden() for r,n,b in w.quest_rows))
        finally:w.close();w.deleteLater();APP.processEvents()
