import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from test_desktop import APP
from gui.live_window import LiveWindow
from gui.audio_manager import AudioManager
from audio_fixtures import music_fixture

class DemoAudioTests(unittest.TestCase):
    def test_terminal_cleanup_cannot_stop_visible_demo_music(self):
        from PySide6.QtCore import QCoreApplication,QEvent
        a=AudioManager(backend='qt')
        a.root=music_fixture(self)
        a.music_enabled=True
        # Inspect ownership without opening an audio device/decoder.
        a.player.setSource=Mock();a.player.play=Mock()
        screen=Mock()
        fake=SimpleNamespace(phase='title_demo',audio=a,title_screen=screen,game=Mock())
        fake.game.get_snapshot.return_value.language='de'
        source_root=Path(__file__).resolve().parents[1]/'maatos/apps/maat_rpg/plugins'
        path=source_root/'battle/music/battle_normal.mp3'
        handle=a.handle_event
        def fixture_event(event):
            if event.get('path'):
                event=dict(event,path=str(a.root/Path(event['path']).relative_to(source_root)))
            handle(event)
        a.handle_event=fixture_event
        try:
            a.location(True)
            LiveWindow.present_demo(fake,{'event':'audio','action':'play','owner':'worker','path':str(path),'loop':True})
            self.assertEqual(a.current[0],'native-title-demo')
            for event in [{'event':'audio','action':'stop','owner':'worker'}, {'event':'audio','action':'clear'}, {'event':'audio','action':'play','owner':'menu','path':str(source_root/'game_menu/menu_theme.mp3')}]:
                LiveWindow.present_demo(fake,event)
                self.assertEqual(a.current[0],'native-title-demo')
            LiveWindow.present_demo(fake,{'event':'output','text':'Letzte sichtbare Kampfrunde'})
            screen.present.assert_called_once()
            fake.title_demo=Mock();fake.demo_stage=0;fake.show_title=Mock()
            fake._demo_return_pending=False;fake._demo_return_timer=Mock();fake.isVisible=lambda:True
            LiveWindow.demo_finished(fake)
            self.assertEqual(a.current[0],'native-title-demo')
            fake._demo_return_timer.start.assert_called_once_with(0)
            LiveWindow.finish_demo_return(fake)
            self.assertEqual(a.current[0],'menu')
            self.assertNotIn('native-title-demo',a.requests)
        finally:
            a.close();a.deleteLater();QCoreApplication.sendPostedEvents(a,QEvent.DeferredDelete)
