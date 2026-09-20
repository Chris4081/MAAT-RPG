import os
import re
from html import unescape
from pathlib import Path
import unittest
from unittest.mock import patch
from test_desktop import APP
import test_live_window as helpers
from test_live_rpg import Worker
from apps.maat_rpg import session_shared
from gui.live_window import LiveWindow
from gui.maat_guide import MaatGuide,stability,maat_score
from gui.maat_guide_content import FORMULAS, COPY

class GuideTests(unittest.TestCase):
    def test_formulas_match_both_local_website_versions(self):
        website=Path(__file__).resolve().parents[1]/'gui-preview/maat-rpg-website'
        expected={'maat','stability','world','plp','coherence','agi','master','universe'}
        for language, filename in [('de','features.html'),('en','features-en.html')]:
            with self.subTest(language=language):
                source=(website/filename).read_text()
                section=re.search(r'<section\b[^>]*id="formeln"[^>]*>(.*?)</section>',source,re.S).group(1)
                website_cards=re.findall(r'<details><summary>(.*?)</summary><div class="detail-body"><code class="equation">(.*?)</code>(.*?)</div></details>',section,re.S)
                self.assertEqual({item['id'] for item in FORMULAS[language]},expected)
                self.assertEqual(len(website_cards),len(FORMULAS[language]))
                for item,(title,equation,body) in zip(FORMULAS[language],website_cards):
                    self.assertEqual(item['title'],unescape(title))
                    self.assertEqual(item['equation'],unescape(equation))
                    self.assertEqual(item['body'],body)

    def test_average_is_distinct_from_respect_capped_stability(self):
        values=[.8,.6,.7,.5,.4]
        self.assertAlmostEqual(maat_score(values),6)
        self.assertAlmostEqual(stability(values)*10,4)
        self.assertAlmostEqual(maat_score([.5,.6,.7,.8,.9]),7)
        self.assertEqual(maat_score([0]*5),0)
        self.assertEqual(maat_score([1]*5),10)
        with self.assertRaises(ValueError):maat_score([1,1,1,1,10])

    def test_language_switch_covers_all_pages_and_preserves_private_exercise(self):
        from PySide6.QtTest import QSignalSpy
        w=MaatGuide()
        try:
            w.set_count(19);w.set_language('en')
            self.assertIn('Unlocks after 20',w.status.text());self.assertTrue(w.tabs.isHidden())
            self.assertEqual(w.values[0].text(),'Open')
            w.set_count(20);w.tabs.setCurrentIndex(2)
            w.formula_select.setCurrentIndex(w.formula_select.findData('plp'))
            for value,rating in zip(w.values,[.8,.6,.7,.5,.4]):value.setValue(rating)
            w.situation.setPlainText('Mein privater Text')
            w.notes[0].setPlainText('Meine Beobachtung');w.next_step.setPlainText('Mein Schritt')
            spy=QSignalSpy(w.values[0].valueChanged)
            for language in ('de','en'):
                w.set_language(language)
                self.assertEqual(w.tabs.currentIndex(),2)
                self.assertEqual(w.formula_select.currentData(),'plp')
                self.assertEqual(w.situation.toPlainText(),'Mein privater Text')
                self.assertEqual(w.notes[0].toPlainText(),'Meine Beobachtung')
                self.assertEqual(w.next_step.toPlainText(),'Mein Schritt')
                self.assertEqual([v.value() for v in w.values],[.8,.6,.7,.5,.4])
            self.assertEqual(spy.count(),0)
            self.assertEqual([w.tabs.tabText(i) for i in range(w.tabs.count())],list(COPY['en']['tabs']))
            self.assertIn('What is MAAT?',w.introduction.toPlainText())
            self.assertIn('From an impression',w.method.toPlainText())
            self.assertIn('MAAT score: 6.00 out of 10',w.result.text())
            self.assertIn('Stability ≈ 0.40',w.result.text())
            self.assertEqual(w.reset_button.text(),'Clear exercise')
            self.assertIn('Observation',w.notes[0].placeholderText())
            for i, item in enumerate(FORMULAS['en']):
                w.formula_select.setCurrentIndex(i)
                self.assertIn(item['equation'],w.formula_browser.toPlainText())
                self.assertIn('What the result means',w.formula_browser.toPlainText())
                self.assertNotRegex(w.formula_browser.toPlainText(),r'\b(Beispiel|Unordnung|Schöpfungskraft|Unsicherheit)\b')
            w.reset_profile()
            self.assertEqual(w.language,'en');self.assertEqual(w.count,0)
            self.assertEqual(w.formula_select.currentData(),'maat')
            self.assertFalse(w.situation.toPlainText());self.assertFalse(w.notes[0].toPlainText())
            self.assertTrue(w.tabs.isHidden());self.assertIn('Still open',w.result.text())
        finally:w.deleteLater();APP.processEvents()

    def test_live_english_guide_uses_game_language(self):
        previous=session_shared.application_language()
        session_shared.write_application_language('en')
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            w=LiveWindow(audio=helpers.SilentAudio())
            try:
                w.request_title_start();w.choose_profile(w.game._profile_slot())
                helpers.LiveWindowTest.spin(self,lambda:w.game.ready)
                w.phase='playing';w.navigate(3)
                w.receive({'event':'profile','data':{'chat_messages':20}})
                w.guide_button.click()
                self.assertIs(w.stack.currentWidget(),w.maat_guide)
                guide=w.maat_guide
                self.assertEqual(guide.language,'en')
                self.assertIn('Understand yourself better',guide.title.text())
                guide.tabs.setCurrentIndex(2)
                guide.formula_select.setCurrentIndex(guide.formula_select.findData('world'))
                w.update_controls()
                self.assertEqual(guide.formula_select.currentData(),'world')
                self.assertIn('0.0625',guide.formula_browser.toPlainText())
                if os.environ.get('MAAT_GUIDE_SCREENSHOTS'):
                    target=Path(os.environ['MAAT_GUIDE_SCREENSHOTS']);target.mkdir(parents=True,exist_ok=True)
                    w.resize(1380,1000);w.show();APP.processEvents()
                    w.grab().save(str(target/'guide-game-en.png'))
            finally:
                w.game.shutdown();w.close();APP.processEvents()
                session_shared.write_application_language(previous or 'de')

    def test_formula_open_values_and_reset(self):
        self.assertEqual(stability([.8,.6,.7,.5,.4]),.4)
        self.assertEqual(stability([1,1,1,1,1]),1)
        self.assertEqual(stability([0,1,1,1,1]),0)
        with self.assertRaises(ValueError):stability([1,1,1,1,float('nan')])
        w=MaatGuide()
        try:
            self.assertTrue(w.tabs.isHidden());w.set_count(19);self.assertTrue(w.tabs.isHidden())
            w.set_count(20);self.assertFalse(w.tabs.isHidden());self.assertIn('Noch offen',w.result.text())
            w.situation.setPlainText('Ein privates Beispiel')
            for widget,v in zip(w.values,[.8,.6,.7,.5,.4]):widget.setValue(v)
            self.assertIn('0,40',w.result.text())
            self.assertIn('6,00 von 10',w.result.text())
            w.reset_profile();self.assertFalse(w.situation.toPlainText());self.assertTrue(w.tabs.isHidden())
            self.assertTrue(all(v.value()<0 for v in w.values))
        finally:w.deleteLater();APP.processEvents()
    def test_live_boundary_navigation_and_profile_reset(self):
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            w=LiveWindow(audio=helpers.SilentAudio())
            w.request_title_start()
            w.choose_profile(w.game._profile_slot())
            try:
                helpers.LiveWindowTest.spin(self,lambda:w.game.ready)
                w.phase='playing';w.navigate(3)
                for count in (19,20,21):
                    w.receive({'event':'profile','data':{'chat_messages':count}})
                    self.assertEqual(w.guide_button.isEnabled(),count>=20)
                    if count==19:
                        w.navigate(w.guide_index);self.assertEqual(w.stack.currentIndex(),3)
                    else:
                        w.guide_button.click();self.assertIs(w.stack.currentWidget(),w.maat_guide)
                w.resize(1250,900);w.show();APP.processEvents();w.grab().save('/tmp/maat-guide.png')
                w.maat_guide.situation.setPlainText('Privat')
                w.change_profile(0)
                self.assertFalse(w.maat_guide.situation.toPlainText());self.assertEqual(w._guide_messages,0)
                self.assertFalse(w.guide_button.isEnabled())
            finally:w.game.shutdown();w.close();APP.processEvents()
    def test_saved_message_count_available_without_model(self):
        for count in (19,20):
            w=Worker(seed={'battle_state.json':{'quests':{'meta':{'messages_total':count}}}})
            try:
                profile=next(e['data'] for e in w.boot if e['event']=='profile')
                self.assertEqual(profile['chat_messages'],count)
                events=w.command('/quests')
                profile=next(e['data'] for e in events if e['event']=='profile')
                self.assertEqual(profile['chat_messages'],count) # opening a menu isn't a chat message
            finally:w.close()
