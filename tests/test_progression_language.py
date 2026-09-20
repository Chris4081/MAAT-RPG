"""Bilingual quest completion and talent purchases with private test profiles."""
from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
import test_gui_language as language_helpers
from test_combat_quests import quest_plugin
from test_live_rpg import Worker
from test_talents import saved
from apps.maat_rpg import session_shared
from apps.maat_rpg.plugins.quests.plugin_main import Plugin, _ALL_QUEST_DEFINITIONS
from apps.maat_rpg.plugins.quests.english_content import keyword_aliases, COMPANION
from shared.core.story_campaign import set_companion_story
from shared.core import talents
from gui.quest_log import QuestLog
from gui.talent_tree import TalentTree
from PySide6.QtCore import Qt, QCoreApplication, QEvent


class ProgressionContentTests(unittest.TestCase):
    def tearDown(self):
        set_companion_story(False)

    def test_all_188_quests_in_both_perspectives_preserve_rules_and_saves(self):
        plugin=Plugin.__new__(Plugin);plugin._lang=lambda:'en'
        definitions=deepcopy(_ALL_QUEST_DEFINITIONS)
        self.assertEqual(len(definitions),188)
        for companion in (False,True):
            set_companion_story(companion)
            for q in definitions:
                with self.subTest(quest=q['id'],companion=companion):
                    shown=plugin._quest_display(q)
                    self.assertNotEqual(shown['name'],q['name'])
                    self.assertNotEqual(shown['desc'],q['desc'])
                    for key in q.keys()-{'name','desc','contract_category'}:
                        self.assertEqual(shown[key],q[key])
                    self.assertNotRegex(shown['desc'],r'\b(Gewinne|Sprich|Schreibe|Nenne|Heiltränke|Schutz-Siegel|Belohnung)\b')
                    if companion:
                        self.assertNotIn('MAAT-AI',shown['desc'])
                        self.assertNotIn('with the AI',shown['desc'])
                        if q['id'] in COMPANION:
                            self.assertEqual(shown['name'],COMPANION[q['id']][0])
                            for hint in re.findall('Mention “([^”]+)”',shown['desc']):
                                self.assertTrue(plugin._matches_chat_keyword_quest(q,hint))
        self.assertEqual(definitions,_ALL_QUEST_DEFINITIONS)

    def test_every_new_english_keyword_completes_once_and_german_still_matches(self):
        for definition in _ALL_QUEST_DEFINITIONS:
            aliases=keyword_aliases(definition)
            if not aliases:continue
            with self.subTest(quest=definition['id']):
                plugin,core=quest_plugin();plugin._lang=lambda:'en'
                q=deepcopy(definition)
                plugin.qstate.update(active=[q],completed=[],locked=[],available=[])
                expected=plugin._quest_xp_effective(q)
                messages=[]
                if q['type']=='chat_keyword':
                    self.assertTrue(plugin._matches_chat_keyword_quest(q,q['keywords'][0]))
                    plugin._check_keyword_quests('An unrelated conversation.',messages)
                    self.assertFalse(plugin.qstate['completed'])
                    plugin._check_keyword_quests('Let us discuss '+aliases[0]+'.',messages)
                    plugin._check_keyword_quests(aliases[0],messages)
                else:
                    self.assertTrue(plugin._matches_daily_quest(q,q['keyword']))
                    for day in range(q['days']):
                        clock=Mock(wraps=datetime)
                        clock.now.return_value=datetime(2026,9,1)+timedelta(days=day)
                        with patch.dict(plugin._check_daily_quests.__func__.__globals__,datetime=clock):
                            plugin._check_daily_quests(aliases[0],messages)
                            plugin._check_daily_quests(q['keyword'],messages)
                    self.assertEqual(q['progress'],q['days'])
                self.assertEqual(len(plugin.qstate['completed']),1)
                self.assertEqual(core.state.state['player']['xp'],expected)
                self.assertTrue(any('Quest completed:' in message for message in messages))

    def test_english_daily_reopens_next_day_and_contract_progress_starts_at_purchase(self):
        plugin,core=quest_plugin();plugin._lang=lambda:'en'
        q=deepcopy(next(q for q in _ALL_QUEST_DEFINITIONS if q['id']=='daily50_respect'))
        plugin.qstate.update(active=[q],completed=[],locked=[],available=[])
        keyword=keyword_aliases(q)[0];messages=[]
        reward=plugin._quest_xp_effective(q)
        for day in (1,2):
            clock=Mock(wraps=datetime);clock.now.return_value=datetime(2026,9,day)
            with patch.dict(plugin._check_daily_quests.__func__.__globals__,datetime=clock):
                plugin._refresh_daily_quests()
                plugin._check_daily_quests(keyword,messages)
                plugin._refresh_daily_quests()
                plugin._check_daily_quests(keyword,messages)
            self.assertEqual(q['completions'],day)
            self.assertEqual(core.state.state['player']['xp'],day*reward)
        contract=deepcopy(next(q for q in _ALL_QUEST_DEFINITIONS if q['id']=='contract50_21'))
        plugin.qstate.update(active=[],completed=[],locked=[contract])
        core.state.state['player']['gold']=10000
        core.state.state['stats']['fights_won']=100
        receipt=plugin.buy_contract(contract['id'])
        self.assertIn('Expedition to the First Horizon',receipt)
        self.assertEqual(plugin.qstate['active'][0]['counter_start'],100)
        plugin._check_battle_quests(messages,paid_only=True)
        self.assertFalse(plugin.qstate['completed'])
        core.state.state['stats']['fights_won']+=contract['target']
        plugin._check_battle_quests(messages,paid_only=True)
        self.assertIn('Horizon Guardian','\n'.join(messages))
        self.assertIn('Horizontwächter',core.state.state['player']['earned_titles'])
        self.assertEqual(core.state.state['player']['gold'],8000)

    def test_all_60_talents_have_same_costs_gates_bonuses_and_saved_ranks(self):
        with tempfile.TemporaryDirectory() as folder:
            for class_id in talents.TREES:
                state=saved(class_id)
                before=deepcopy(state)
                de,en=talents.snapshot(state),talents.snapshot(state,'en')
                self.assertEqual(state,before)
                for key in de.keys()-{'class_name','nodes','bonus_text'}:
                    self.assertEqual(de[key],en[key])
                for a,b in zip(de['nodes'],en['nodes']):
                    self.assertNotEqual(a['name'],b['name'])
                    self.assertIn('per rank',b['description'])
                    for key in a.keys()-{'name','branch_name','description','reason'}:
                        self.assertEqual(a[key],b[key])
                saved_states=[]
                for language in ('de','en'):
                    store=SimpleNamespace(state=deepcopy(state),state_path=Path(folder)/f'{class_id}-{language}.json')
                    for node in talents.catalog(class_id):
                        for rank in range(3):
                            receipt=talents.buy(store,node['id'],expected_rank=rank,class_id=class_id,language=language)
                            if language=='en':self.assertIn('learned',receipt)
                    saved_states.append(json.loads(store.state_path.read_text()))
                    self.assertEqual(talents.snapshot(store.state,language)['spent'],90)
                self.assertEqual(*saved_states)

    def test_real_english_worker_quest_details_and_talent_purchase_restart(self):
        state=saved('magier',level=50,completed=False)
        state['quests']['meta']={'messages_total':40,'quest_intro_shown':True}
        worker=Worker(seed={'settings_state.json':{'language':'en'},'battle_state.json':state})
        try:
            data=next(e['data'] for e in worker.boot if e['event']=='quests')
            active={q['id']:q for q in data['groups']['active']}
            self.assertEqual(active['journey_50_insight']['name'],'Living World')
            self.assertEqual(active['daily50_respect']['status_label'],'Repeatable daily · Level 50')
            events=worker.command('/quest info journey_22_insight')
            self.assertIn('Star Paths',''.join(e.get('text','') for e in events))
            events=worker.command('/questcheck Star Paths')
            self.assertIn('Active: Star Paths',''.join(e.get('text','') for e in events))
            for rank,ok in ((0,True),(0,False)):
                worker.send(op='talent_buy',profile_slot=1,talent='magier:0:0',rank=rank,class_id='magier')
                events=worker.until(lambda e:e['event']=='busy' and not e['value'])
                result=next(e for e in events if e['event']=='talent_result')
                self.assertEqual(result['ok'],ok)
                self.assertIn('Rune Lore' if ok else 'rank has changed',result['text'])
            state=json.loads((Path(worker.temp.name)/'state/battle_state.json').read_text())
        finally:worker.close()
        worker=Worker(seed={'settings_state.json':{'language':'en','gui_perspective':'companion'},'battle_state.json':state})
        try:
            data=next(e['data'] for e in worker.boot if e['event']=='talents')
            self.assertEqual(data['ranks']['magier:0:0'],1)
            self.assertEqual(data['class_name'],'Mage')
            self.assertIn('skill damage',data['bonus_text'])
            quest_data=next(e['data'] for e in worker.boot if e['event']=='quests')
            quests={q['id']:q for group in quest_data['groups'].values() for q in group}
            self.assertEqual(quests['know_maat_ki']['name'],'Get to Know Maatis')
            self.assertIn('you will respect with Maatis',quests['daily50_respect']['desc'])
        finally:worker.close()


class ProgressionWindowTests(unittest.TestCase):
    setUp=language_helpers.LanguageTests.setUp
    close_windows=language_helpers.LanguageTests.close_windows
    window=language_helpers.LanguageTests.window
    ready=language_helpers.LanguageTests.ready

    def test_embedded_english_quest_filters_sidebar_and_talent_buttons(self):
        session_shared.write_application_language('en')
        session_shared.write_profile_settings(1,{'language':'en'})
        state=saved('puppy',level=50,completed=False)
        state['quests']['meta']={'messages_total':40,'quest_intro_shown':True}
        target=session_shared.profile_slot_root(1)/'state/battle_state.json'
        target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(state))
        window=self.window();self.ready(window)
        window.phase='playing';window._started=True;window.text_stream.finish();window.navigate(5)
        log=window.quest_log
        self.assertEqual(window.world_tabs.tabText(0),'📜 Quest log')
        self.assertIn('YOUR QUEST LOG',log.summary.text())
        log.select_quest('journey_22_insight')
        self.assertIn('Star Paths',log.detail.toPlainText())
        self.assertIn('Reward at your current level:',log.detail.toPlainText())
        self.assertIn('Active',log.filter.currentText())
        log.category.setCurrentIndex(log.category.findData('dungeon'))
        self.assertTrue(log.list.count())
        self.assertIn('talent point on completion',log.detail.toPlainText())
        commands=[];log.command_requested.connect(commands.append)
        self.assertFalse(commands)
        window.open_talents();tree=window.talent_tree
        self.assertIn('Talents',window.talent_button.text())
        self.assertEqual(tree.title.text(),'Puppy · Talent tree')
        tree.select('puppy:0:0')
        self.assertIn('Playful Bite',tree.detail.text())
        self.assertEqual(tree.learn.text(),'Learn rank 1 · 1 TP')
        self.assertIn('combat quests',tree.cards['puppy:0:0'].requirement.text())
        requests=[];tree.purchase_requested.connect(requests.append)
        with patch.object(window,'purchase_talent'):
            # Avoid a real purchase here; the real worker test above covers it.
            tree.purchase_requested.disconnect()
            tree.purchase_requested.connect(requests.append)
            tree.learn.click()
        self.assertEqual(requests,[dict(talent='puppy:0:0',rank=0,class_id='puppy')])
        self.assertEqual(tree.learn.text(),'Saving …')
        window.resize(880,720);APP.processEvents()
        self.assertEqual(window.width(),880)
        self.assertLessEqual(tree.minimumSizeHint().width(),tree.width())
        self.assertLessEqual(tree.tree.minimumSizeHint().width(),tree.scroll.viewport().width())
        tree.result('Preview finished',True)
        window.enter_menu()
        window.game.set_language('de');self.ready(window)
        window.apply_menu_language()
        self.assertEqual(tree.title.text(),'Puppy · Talentbaum')
        self.assertEqual(tree.cards['puppy:0:0'].name.text(),'Spielbiss')
        self.assertIn('DEIN QUESTLOG',log.summary.text())
        log.select_quest('journey_22_insight')
        self.assertIn('Sternenpfade',log.detail.toPlainText())
        self.assertEqual(window.world_tabs.tabText(0),'📜 Questlog')


if __name__=='__main__':unittest.main()
