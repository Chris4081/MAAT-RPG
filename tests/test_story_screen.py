import unittest
from pathlib import Path
from PySide6.QtCore import QCoreApplication, QEvent
from test_desktop import APP
from test_live_rpg import Worker
from gui.story_screen import StoryScreen

class StoryScreenTests(unittest.TestCase):
    def test_original_story_waits_for_matching_completion(self):
        worker=Worker(auto_stories=False)
        try:
            opening = worker.command('/ai-start')
            self.assertFalse(any(e['event']=='story_scene' for e in opening))
            self.assertTrue(any('Wer bist du?' in e.get('text','') for e in opening))
            worker.send(op='companion_answer', choice=-1, text='Ich bin deine Begleiter-KI und möchte mit dir gemeinsam die Welt erkunden, Fragen stellen und unsere Erinnerungen bewahren.')
            events=worker.until(lambda e:e['event']=='story_scene')
            scene=events[-1]
            self.assertEqual(scene['module'],'companion_story1')
            self.assertTrue(Path(scene['music']).is_file())
            self.assertTrue(any('Bibliothek' in line for line in scene['lines']))
            screen=StoryScreen();audio=[];screen.audio_requested.connect(audio.append)
            try:
                screen.start_scene(scene)
                self.assertFalse(screen.artwork.pixmap.isNull())
                self.assertTrue(screen.running)
                self.assertEqual(audio[-1]['owner'],'story-screen')
                self.assertTrue(audio[-1]['loop'])
                screen.advance()
                self.assertEqual(screen.text.toPlainText(),screen.segments[0])
                screen.finish()
                self.assertEqual(audio[-1]['action'],'stop')
                self.assertFalse(screen.timer.isActive())
            finally:
                screen.cancel();screen.deleteLater()
                QCoreApplication.sendPostedEvents(screen,QEvent.DeferredDelete)
            worker.send(op='story_done', id=scene['id'])
            events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            self.assertTrue(any(e['event']=='companion' for e in events))
        finally:worker.close()

    def test_all_boss_cutscenes_and_credits_use_story_transport(self):
        from unittest.mock import patch
        from gui.cutscenes import cutscene_payload, TITLES
        from gui.game_worker import Runtime
        root=Path(__file__).resolve().parents[1]/'maatos/apps/maat_rpg/plugins/battle'
        runtime=Runtime.__new__(Runtime)
        for name in TITLES:
            with self.subTest(scene=name):
                path=root/(name+'.py')
                payload=cutscene_payload(path)
                self.assertGreater(len(payload['lines']),30)
                self.assertTrue(Path(payload['music']).is_file())
                self.assertFalse(any(line.startswith('Drücke ENTER') for line in payload['lines']))
                with patch.object(runtime,'present_story') as present:
                    runtime.run_scene(path)
                    present.assert_called_once_with(**payload)
                screen=StoryScreen()
                finished=[]
                screen.completed.connect(lambda:finished.append(True))
                try:
                    screen.start_scene(dict(id=name,lines=payload['lines'],music=payload['music'],name=payload['entry']['name'],module=name))
                    self.assertFalse(screen.artwork.pixmap.isNull())
                    while screen.running:
                        screen.advance()
                    self.assertEqual(finished,[True])
                    self.assertFalse(screen.timer.isActive())
                finally:
                    screen.cancel();screen.deleteLater()
                    QCoreApplication.sendPostedEvents(screen,QEvent.DeferredDelete)
