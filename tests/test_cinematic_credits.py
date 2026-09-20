import unittest
from pathlib import Path
from test_desktop import APP
from gui.credits_screen import CreditsScreen
from gui.cutscenes import cutscene_payload

class CreditsTests(unittest.TestCase):
    def test_original_credits_content_music_pause_finish(self):
        root=Path(__file__).resolve().parents[1]/'maatos'
        payload=cutscene_payload(root/'apps/maat_rpg/plugins/battle/credits.py')
        self.assertTrue(Path(payload['music']).is_file())
        screen=CreditsScreen();audio=[];done=[];screen.audio_requested.connect(audio.append);screen.completed.connect(lambda:done.append(True))
        try:
            screen.resize(1000,740);screen.show();screen.start_scene(dict(id='finale',lines=payload['lines'],music=payload['music']))
            self.assertIn('Konzept & Universum:       Christof Krieg',screen.canvas.lines)
            self.assertTrue(audio[-1]['loop']);screen.toggle_pause();old=screen.canvas.offset;screen.tick();self.assertEqual(old,screen.canvas.offset)
            screen.toggle_pause();screen.canvas.time=30;screen.canvas.offset=700;APP.processEvents();screen.grab().save('/tmp/maat-cinema.png')
            screen.canvas.offset=screen.canvas.height()+screen.canvas.content_height+200;screen.tick()
            self.assertEqual(done,[True]);self.assertEqual(audio[-1]['action'],'stop');self.assertFalse(screen.timer.isActive())
            screen.finish();self.assertEqual(done,[True])
        finally:screen.cancel();screen.close();screen.deleteLater();APP.processEvents()
