import os,unittest
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication,QEvent
from test_desktop import APP
from test_live_window import SilentAudio,LiveWindowTest
from apps.maat_rpg import session_shared
from gui.live_window import LiveWindow

class StartupModelTests(unittest.TestCase):
    spin=LiveWindowTest.spin
    def test_first_selection_saved_auto_load_failure_and_ready_gate(self):
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            w=LiveWindow(audio=SilentAudio())
            w.request_title_start()
            w.choose_profile(w.game._profile_slot())
            try:
                w.show();self.spin(lambda:w.game.ready)
                w.saved_model=None;w.model_ready=False;w.prepare_startup_model()
                self.assertTrue(w.ki_dialog.isVisible())
                self.assertEqual(w.title_screen.start_button.text(),'Modell auswählen')
                w.request_title_start();self.assertEqual(w.phase,'title')
                self.assertFalse(w.title_idle.isActive())
                w.ki_dialog.hide()
                w.model_combo.addItem('saved.gguf');w.saved_model='saved.gguf'
                def load(*args):w.game.busy=True
                with patch.object(w.game,'load_model',side_effect=load) as called:
                    w.prepare_startup_model();w.prepare_startup_model()
                    called.assert_called_once()
                self.assertFalse(w.title_screen.loading_bar.isHidden())
                self.assertEqual(w.title_screen.loading_bar.maximum(),0)
                w.request_title_start();self.assertEqual(w.phase,'title')
                w.start_title_demo();self.assertEqual(w.phase,'title')
                w.receive({'event':'model','status':'unloaded'})
                w.game.busy=False
                with patch.object(w.game,'load_model') as called:
                    w.prepare_startup_model();called.assert_not_called()
                self.assertTrue(w.ki_dialog.isVisible())
                self.assertIn('fehlgeschlagen',w.title_screen.start_button.text())
                w.receive({'event':'model','status':'ready','name':'saved.gguf'})
                self.assertTrue(w.title_screen.loading_bar.isHidden())
                self.assertFalse(w.ki_dialog.isVisible())
                self.assertEqual(w.title_screen.start_button.text(),'PRESS ENTER TO PLAY')
                self.assertTrue(w.title_idle.isActive())
                w.request_title_start();self.assertEqual(w.phase,'menu')
            finally:
                w.close();w.deleteLater();QCoreApplication.sendPostedEvents(w,QEvent.DeferredDelete);APP.processEvents()
