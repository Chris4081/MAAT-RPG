"""English and German coverage for complete authored campaigns, not just menus."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_desktop import APP
from PySide6.QtCore import QCoreApplication, QEvent
from gui.cutscenes import cutscene_payload, TITLES
from gui.companion_stories import SCENES, CHOICES, REFLECTIONS, scene_payload, CompanionStory
from gui import companion_stories_en as en
from gui.story_screen import StoryScreen
from gui.credits_screen import CreditsScreen

ROOT=Path(__file__).resolve().parents[1]
BATTLE=ROOT/'maatos/apps/maat_rpg/plugins/battle'

class StoryLanguageTests(unittest.TestCase):
    def test_every_cutscene_has_full_english_narration(self):
        from gui.cutscenes_en import TEXT, TITLES as EN_TITLES
        self.assertEqual(set(TITLES),set(TEXT))
        self.assertEqual(set(TITLES),set(EN_TITLES))
        for name in TITLES:
            de=cutscene_payload(BATTLE/(name+'.py'),'de')
            english=cutscene_payload(BATTLE/(name+'.py'),'en')
            self.assertEqual(sum(bool(s.strip()) for s in de['lines']),sum(bool(s.strip()) for s in english['lines']),name)
            self.assertNotEqual(de['entry']['name'],english['entry']['name'])
            if name == 'credits':
                self.assertEqual(Path(de['music']).name, 'credits_theme.mp3')
                self.assertEqual(Path(english['music']).name, 'credits_en.mp3')
            else:
                self.assertEqual(de['music'],english['music'])
            self.assertTrue(Path(english['music']).is_file())
            self.assertFalse(any('Drücke ENTER' in line for line in english['lines']))
            # No untranslated full German sentences; names/separators may match.
            for line in set(de['lines']) & set(english['lines']):
                if line in ('✨ MAAT-RPG — Credits ✨','🌌 MAAT-RPG — Finale'):continue
                self.assertLess(len(line.split()),4,(name,line))

    def test_companion_translations_preserve_every_scene_and_decision(self):
        self.assertEqual(set(SCENES),set(en.SCENES))
        self.assertEqual(set(CHOICES),set(en.CHOICES))
        self.assertEqual(set(REFLECTIONS),set(en.REFLECTIONS))
        for name in SCENES:
            de=scene_payload(name,'de');english=scene_payload(name,'en')
            self.assertEqual(len(de['lines']),len(english['lines']))
            self.assertEqual(de['module'],english['module'])
            self.assertEqual(de['image'],english['image'])
            self.assertNotEqual(de['lines'],english['lines'])
        for name in CHOICES:
            de=CompanionStory(name,'de').run()['choice']
            english=CompanionStory(name,'en').run()['choice']
            self.assertEqual(de['id'],english['id'])
            self.assertEqual([o['value'] for o in de['options']],[o['value'] for o in english['options']])
            self.assertNotEqual(de['prompt'],english['prompt'])
            english['options'][0]['label']='Changed in caller'
            self.assertNotEqual(CompanionStory(name,'en').run()['choice']['options'][0]['label'],'Changed in caller')

    def test_campaigns_in_real_private_runtime(self):
        for language in ('de','en'):
            for perspective in ('adventure','companion'):
                with self.subTest(language=language,perspective=perspective), tempfile.TemporaryDirectory(prefix='maat-story-language-') as folder:
                    result=subprocess.run([sys.executable,str(Path(__file__).with_name('story_language_probe.py')),folder,language,perspective],
                        capture_output=True,text=True,timeout=45)
                    self.assertEqual(result.returncode,0,result.stdout[-2000:]+result.stderr[-4000:])

    def test_english_boss_view_and_credits_controls(self):
        payload=cutscene_payload(BATTLE/'boss_scene_2.py','en')
        screen=StoryScreen();audio=[]
        from gui.desktop import STYLE
        screen.setStyleSheet(STYLE)
        screen.audio_requested.connect(audio.append)
        credits=CreditsScreen()
        try:
            screen.resize(1000,800);screen.show()
            screen.start_scene(dict(id='boss2',language='en',module='boss_scene_2',name=payload['entry']['name'],
                                    lines=payload['lines'],music=payload['music']))
            APP.processEvents()
            self.assertEqual(screen.skip_button.text(),'Skip scene')
            self.assertIn('The second shadow falls',screen.segments[0])
            self.assertFalse(screen.artwork.pixmap.isNull())
            self.assertTrue(audio[-1]['loop'])
            screen.advance()
            self.assertIn('The second shadow falls',screen.text.toPlainText())
            if os.environ.get('MAAT_STORY_PREVIEW'):
                screen.grab().save(str(Path(os.environ['MAAT_STORY_PREVIEW'])/'story-boss-2-en-20260912.png'))
            while screen.running:screen.advance()
            self.assertEqual(audio[-1]['action'],'stop')
            for language in ('en','de','en'):
                data=cutscene_payload(BATTLE/'credits.py',language)
                credits.start_scene(dict(id='credits',language=language,name=data['entry']['name'],lines=data['lines'],music=data['music']))
                self.assertEqual(credits.skip_button.text(),'Back to game' if language=='en' else 'Zurück ins Spiel')
                credits.toggle_pause()
                self.assertEqual(credits.pause_button.text(),'Resume' if language=='en' else 'Fortsetzen')
                credits.toggle_pause()
                self.assertEqual(credits.pause_button.text(),'Pause')
        finally:
            for widget in (screen,credits):
                widget.cancel();widget.close();widget.deleteLater()
                QCoreApplication.sendPostedEvents(widget,QEvent.DeferredDelete)
            APP.processEvents()
