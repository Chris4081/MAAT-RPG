"""Translated achievements and postgame maps retain canonical progress and controls."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
import test_gui_language as language_helpers
from test_live_rpg import Worker
from apps.maat_rpg import session_shared
from apps.maat_rpg.plugins.achievements import plugin_main as words
from apps.maat_rpg.plugins.emotional_achievements import plugin_main as emotions
from shared.core.achievement_i18n import WORDS, EMOTIONS
from shared.core.achievement_catalog import snapshot, localize
from shared.core.achievement_history import enrich
from shared.core.minigames import CATALOG
from shared.core.terra_journey import snapshot as journey, localized_snapshot
from gui.achievements import Achievements
from gui.terra_map import TerraJourneyView, TerraMapCard
from gui.character_sidebar import CharacterSidebar
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QLabel


def completed():
    return {'world': {'combat_unlocked': True}, 'stats': {'boss_wins': 25, 'final_wins': 5},
            'player': {'level': 50, 'hp': 500, 'max_hp': 500}, 'hero_class': {'selected': 'robo'}}


class AchievementContentLanguageTests(unittest.TestCase):
    def test_complete_catalog_and_recent_history_preserve_every_saved_value(self):
        self.assertEqual(set(WORDS), set(words.TRIGGERS))
        self.assertEqual(set(EMOTIONS), set(emotions.ACHIEVEMENTS))
        state = completed()
        state.update(achievements={'combat': list(words.COMBAT_ACHIEVEMENTS)},
            minigames={'discovered': list(CATALOG), 'wins': dict.fromkeys(CATALOG, 5), 'first_try_wins': 5, 'chat_wins': 10})
        before = deepcopy(state)
        args = (state, {'unlocked': list(WORDS)}, {'achievements': dict.fromkeys(EMOTIONS, True)})
        de, en = snapshot(*args), snapshot(*args, language='en')
        self.assertEqual(state, before)
        self.assertEqual(en['total'], 48+10+4+len(CATALOG)+9)
        for category, rows in de['groups'].items():
            for a, b in zip(rows, en['groups'][category]):
                with self.subTest(achievement=a['id']):
                    self.assertNotEqual(a['name'], b['name'])
                    self.assertNotEqual(a['description'], b['description'])
                    self.assertEqual({k:v for k,v in a.items() if k not in ('name','description')},
                                     {k:v for k,v in b.items() if k not in ('name','description')})
        self.assertEqual(localize(en, 'de'), de)
        state['achievement_history']={'seen': [], 'events': []}
        enriched=enrich(state, en, 'en')
        history=deepcopy(state['achievement_history'])
        enrich(state, de, 'de')
        self.assertEqual(state['achievement_history'],history)
        self.assertEqual(len(enriched['recent']),5)
        self.assertIn('older achievements', enriched['history_note'])
        recent_de=localize(enriched,'de')['recent']
        self.assertEqual([r['at'] for r in recent_de], [r['at'] for r in enriched['recent']])

    def test_every_english_word_unlocks_the_same_id_once_with_original_xp(self):
        for key, (name, aliases) in WORDS.items():
            with self.subTest(key=key):
                plugin=words.Plugin.__new__(words.Plugin)
                plugin.state={'unlocked': [], 'count': 0};plugin._save=Mock();plugin._lang=lambda:'en'
                context={}
                plugin.before_chat('Topic: '+aliases[0].upper()+'.', context)
                self.assertIn(key, plugin.state['unlocked'])
                self.assertEqual(context['maat_xp_bonus'],sum(words.TRIGGERS[k][1] for k in plugin.state['unlocked']))
                with patch.object(words, 'get_language', return_value='en'),redirect_stdout(io.StringIO()) as output:
                    plugin.after_response('An AI reply.', context)
                self.assertIn(name, output.getvalue())
                self.assertIn('New achievement unlocked', output.getvalue())
                saved=deepcopy(plugin.state);bonus=context['maat_xp_bonus']
                for alias in aliases:plugin.before_chat(alias, context)
                self.assertEqual(plugin.state,saved)
                self.assertEqual(context['maat_xp_bonus'],bonus)
        plugin.state={'unlocked': [], 'count': 0}
        plugin.before_chat('Thinking about skiing, kindness and a crisis.', {})
        self.assertEqual(plugin.state['unlocked'],[])
        plugin.before_chat('harmony', {})
        plugin._lang=lambda:'de'
        plugin.before_chat('harmonie', {})
        self.assertEqual(plugin.state['unlocked'],['harmonie'])

    def test_all_emotional_unlocks_and_commands_use_english_without_duplicate_rewards(self):
        with tempfile.TemporaryDirectory() as folder:
            for key,(name,quote,aliases) in EMOTIONS.items():
                with self.subTest(key=key):
                    plugin=emotions.Plugin.__new__(emotions.Plugin)
                    plugin._lang=lambda:'en'
                    plugin.state_path=str(Path(folder)/(key+'.json'))
                    plugin.state={'achievements': dict.fromkeys(EMOTIONS,False)}
                    context={}
                    with redirect_stdout(io.StringIO()) as output:
                        plugin.before_chat(aliases[0].replace("'",'’').upper(),context)
                    self.assertTrue(plugin.state['achievements'][key])
                    self.assertIn('Achievement unlocked: '+name,output.getvalue())
                    self.assertIn(quote,output.getvalue())
                    self.assertIn(name,plugin.command('/ach')[1])
                    self.assertEqual(context['maat_xp_bonus'],sum(emotions.ACHIEVEMENTS[k]['xp'] for k,v in plugin.state['achievements'].items() if v))
                    saved=Path(plugin.state_path).read_bytes();bonus=context['maat_xp_bonus']
                    with redirect_stdout(io.StringIO()):plugin.before_chat(aliases[0],context)
                    self.assertEqual(Path(plugin.state_path).read_bytes(),saved)
                    self.assertEqual(context['maat_xp_bonus'],bonus)
                    plugin._lang=lambda:'de'
                    self.assertIn(emotions.ACHIEVEMENTS[key]['name'],plugin.command('/ach')[1])


class AchievementMapWidgetTests(unittest.TestCase):
    def cleanup(self,*widgets):
        for w in widgets:
            w.close();w.deleteLater();QCoreApplication.sendPostedEvents(w,QEvent.DeferredDelete)
        APP.processEvents()

    def test_search_filters_recent_links_and_language_switch_do_not_reset_progress(self):
        page=Achievements();sidebar=CharacterSidebar()
        self.addCleanup(self.cleanup,page,sidebar)
        page.update_data(snapshot({}))
        state={};enriched=enrich(state,snapshot({}))
        data=enrich(state,snapshot({}, {'unlocked':['ägypten']}, {'achievements':{'grateful':True}}))
        before=deepcopy(data)
        page.update_data(data);sidebar.update_achievements(data)
        old_cards={key:row[0] for key,row in page.rows.items()}
        page.select_category('Worte & Entdeckungen');page.status.setCurrentIndex(1)
        for lang in ('en','de','en'):
            page.set_language(lang);sidebar.set_language(lang)
            self.assertEqual(page.category.currentData(),'Worte & Entdeckungen')
            self.assertEqual(page.status.currentIndex(),1)
            self.assertEqual(page.progress.value(),2)
            self.assertEqual(old_cards,{key:row[0] for key,row in page.rows.items()})
        page.search.setText('pyramids')
        self.assertFalse(page.rows['word:ägypten'][0].isHidden())
        self.assertTrue(page.rows['word:hallo'][0].isHidden())
        self.assertEqual(page.rows['word:ägypten'][3].format(),'Unlocked')
        self.assertIn('Newly unlocked:',page.notice.text())
        self.assertIn('Heir of the Pyramids',sidebar.recent_achievements.text())
        self.assertIn('achievement:word%3A%C3%A4gypten',sidebar.recent_achievements.text())
        self.assertIn('older achievements',sidebar.recent_achievements.toolTip())
        self.assertEqual(data,before)

    def test_all_route_phases_and_world_end_translate_without_changing_map_state(self):
        page=TerraJourneyView();card=TerraMapCard()
        self.addCleanup(self.cleanup,page,card)
        states=[{}, {'stats':{'messages_total':30}}]
        for bosses,finals,progress,retry in ((0,0,7,0),(2,0,20,0),(5,0,0,0),(5,0,4,1),(25,5,0,0)):
            states.append({'world':{'combat_unlocked':True,'final_retry':retry},
                           'stats':{'boss_wins':bosses,'final_wins':finals,'boss_progress':progress}})
        for state in states:
            data=journey(state);before=deepcopy(data)
            shown=localized_snapshot(data,'en')
            for field in data.keys()-{'title','subtitle','hint','progress','regions','goal'}:
                self.assertEqual(shown[field],data[field])
            page.update_data(data);card.update_data(data)
            for language in ('en','de','en'):
                page.set_language(language);card.set_language(language)
            self.assertEqual(page.title.text(),shown['title'])
            self.assertIn(shown['progress'],page.progress.text())
            self.assertIn(shown['progress'],card.progress.text())
            text='\n'.join(label.text() for label in page.findChildren(QLabel))
            self.assertNotRegex(text,r'\b(Nachrichten|Felder|Bosse|besiegt|Erwachen|Speicherpunkt|Ziel|Finaletor)\b')
            self.assertNotIn('Karte vergrößern',card.board.toolTip())
            self.assertEqual(data,before)
        page.set_replay_ready(True)
        page.region_choice.setCurrentIndex(4)
        self.assertEqual(page.region_choice.currentText(),'The Light of Terra')
        self.assertEqual(page.back.text(),'← Back')
        self.assertEqual(page.board.end_button.text(),'✦ End of the World\nWatch credits')
        self.assertFalse(page.board.end_button.isHidden())
        self.assertIn('Journey complete',page.progress.text())
        self.assertIn('Light of MAAT',page.progress.text())
        self.assertIn('Watch credits',page.board.end_button.accessibleName())
        self.assertTrue(any('Light of MAAT' in m.name_label.text() for m in page.board.markers))
        page.update_data(journey(completed()))
        self.assertEqual(page.region_choice.currentIndex(),4)
        page.set_language('de')
        self.assertEqual(page.region_choice.currentIndex(),4)
        self.assertIn('Abspann ansehen',page.board.end_button.text())

    def test_worker_english_catalog_and_credits_error_preserve_saved_keys(self):
        worker=Worker(seed={'settings_state.json':{'language':'en'},'battle_state.json':completed(),
                            'achievements_state.json':{'unlocked':['ägypten'],'count':1},
                            'achievements.json':{'achievements':{'grateful':True}}})
        try:
            data=next(e['data'] for e in worker.boot if e['event']=='achievements')
            self.assertEqual(data['groups']['Worte & Entdeckungen'][0]['name'],'🌍 Heir of the Pyramids')
            self.assertIn('I Am Grateful',[r['name'] for r in data['groups']['Emotionale Erfolge']])
            worker.send(op='terra_credits',profile_slot=2)
            events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            error=next(e['text'] for e in events if e['event']=='terra_credits_error')
            self.assertIn('Credits could not be opened:',error)
            self.assertIn('profile has changed',error)
            saved=json.loads((Path(worker.temp.name)/'state/achievements_state.json').read_text())
            self.assertEqual(saved['unlocked'],['ägypten'])
        finally:worker.close()


class AchievementMapLiveLanguageTests(unittest.TestCase):
    setUp=language_helpers.LanguageTests.setUp
    close_windows=language_helpers.LanguageTests.close_windows
    window=language_helpers.LanguageTests.window
    ready=language_helpers.LanguageTests.ready

    def test_live_commands_sidebar_links_and_endgame_previews(self):
        session_shared.write_application_language('en')
        session_shared.set_profile_name(1,'Terra language test')
        path=session_shared.profile_slot_root(1)/'state/battle_state.json'
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(completed()))
        w=self.window();self.ready(w)
        w.phase='playing';w.navigate(3)
        data=snapshot({}, {'unlocked':['ägypten','hallo']}, {'achievements':{'grateful':True}})
        w.receive({'event':'achievements','data':data})
        w.execute('/ach')
        self.assertEqual(w.achievements.category.currentText(),'Emotional achievements')
        self.assertFalse(w.achievements.rows['emotion:grateful'][0].isHidden())
        w.open_sidebar_link('category','Worte & Entdeckungen')
        self.assertEqual(w.achievements.category.currentText(),'Words & discoveries')
        self.assertIn('Heir of the Pyramids',w.achievements.rows['word:ägypten'][1].text())
        out=Path(os.environ['MAAT_LANGUAGE_PREVIEWS']) if os.environ.get('MAAT_LANGUAGE_PREVIEWS') else None
        w.resize(1440,960);APP.processEvents()
        if out:
            out.mkdir(parents=True,exist_ok=True)
            self.assertTrue(w.grab().save(str(out/'achievements-en.png')))
        w.open_terra_map();w.terra_view.region_choice.setCurrentIndex(4);APP.processEvents()
        self.assertEqual(w.terra_view.board.end_button.text(),'✦ End of the World\nWatch credits')
        self.assertEqual(w.terra_view.back.text(),'← Back')
        self.assertIn('25/25 bosses',w.terra_view.leg.text())
        if out:self.assertTrue(w.grab().save(str(out/'world-end-en.png')))
