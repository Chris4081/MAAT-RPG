import unittest
from copy import deepcopy
from test_desktop import APP
from apps.maat_rpg.plugins.quests.plugin_main import Plugin,_ALL_QUEST_DEFINITIONS
from shared.core.story_campaign import set_companion_story

class CompanionQuestTests(unittest.TestCase):
    def setUp(self):
        self.plugin=Plugin.__new__(Plugin);self.plugin._lang=lambda:'de'
        self.quests={q['id']:deepcopy(q) for q in _ALL_QUEST_DEFINITIONS}
    def tearDown(self):set_companion_story(False)
    def test_all_quests_change_perspective_without_changing_rules_or_saves(self):
        before=deepcopy(self.quests)
        self.assertEqual(len(self.quests),188)
        for q in self.quests.values():
            set_companion_story(False);self.assertEqual(self.plugin._quest_display(q),q)
            set_companion_story(True);display=self.plugin._quest_display(q)
            self.assertNotIn('MAAT-KI',display['desc']);self.assertNotIn('mit der KI',display['desc'])
            self.assertEqual({k:v for k,v in display.items() if k not in ('name','desc')},{k:v for k,v in q.items() if k not in ('name','desc')})
        self.assertEqual(self.quests,before)
    def test_reversed_starter_and_trigger_examples(self):
        set_companion_story(True)
        self.assertEqual(self.plugin._quest_name(self.quests['know_maat_ki']),'Lerne Maatis kennen')
        for qid in ('maat_first_calc','maat_self','maat_person','maat_consciousness','maat_manifest'):
            q=self.quests[qid];d=self.plugin._quest_display(q)
            token=q['keywords'][0]
            self.assertIn(token,d['desc'])
            self.assertTrue(self.plugin._matches_chat_keyword_quest(q,f'Maatis, meine Erklärung zu {token}: Wir betrachten das gemeinsam.'))
        q=self.quests['know_maat_ki'];q['progress']=7
        self.assertIs(self.plugin._find_quest_in_list([q],'Lerne Maatis kennen'),q)
        self.assertIs(self.plugin._find_quest_in_list([q],'know_maat_ki'),q)
        self.assertEqual(q['progress'],7)
        set_companion_story(False)
        self.assertEqual(self.plugin._quest_name(q),'Lerne die MAAT-KI kennen')
    def test_late_chronicles_dailies_and_contract_board(self):
        set_companion_story(True)
        self.assertIn('du als KI gelernt hast',self.plugin._quest_display(self.quests['journey_50_journal'])['desc'])
        self.assertIn('gegenüber Maatis',self.plugin._quest_display(self.quests['daily50_respect'])['desc'])
        q=self.quests['contract50_21']
        self.plugin.qstate={'locked':[q]}
        self.plugin._quest_xp_effective=lambda q:q['reward_xp'];self.plugin._quest_path_bonus_preview=lambda q:0
        display=self.plugin.contract_board()[0]
        self.assertIn('Berate Maatis',display['desc'])
        self.assertEqual(display['purchase_price'],q['purchase_price'])
