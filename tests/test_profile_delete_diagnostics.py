import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from test_desktop import APP
from apps.maat_rpg import session_shared as shared
from shared.core.native_diagnostics import visible_diagnostics, quiet_metal_startup
from gui.live_window import LiveWindow
from PySide6.QtWidgets import QMessageBox

class ProfileDeleteTests(unittest.TestCase):
    def test_only_selected_slot_deleted(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(shared,'BASE_APP_SUPPORT_DIR',Path(folder)), patch.object(shared,'PROFILES_DIR',Path(folder)/'profiles'), patch.object(shared,'PROFILE_MANAGER_STATE_PATH',Path(folder)/'state/manager.json'):
            for name in ['models/keep.gguf','profiles/profile_2/state/save.json','profiles/profile_3/state/save.json']:
                p=Path(folder)/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('test')
            shared.write_profile_manager_state({'active_profile':2})
            self.assertTrue(shared.delete_profile_slot(2))
            self.assertFalse(shared.profile_slot_root(2).exists())
            self.assertTrue((Path(folder)/'models/keep.gguf').exists())
            self.assertTrue(shared.profile_slot_root(3).exists())
            self.assertEqual(shared.active_profile_slot(),1)
            for invalid in [1,0,-1,11,True,'2']:
                with self.assertRaises(ValueError):shared.delete_profile_slot(invalid)
            self.assertFalse(shared.delete_profile_slot(2))
            shared.profile_slot_root(4).symlink_to(shared.profile_slot_root(3),target_is_directory=True)
            with self.assertRaises(ValueError):shared.delete_profile_slot(4)

    def test_cancel_never_deletes_or_switches(self):
        from unittest.mock import Mock
        w=SimpleNamespace(ui=lambda text,**values:text.format(**values),game=SimpleNamespace(get_snapshot=lambda:SimpleNamespace(language='de'),busy=False,ready=True,prompt_id=None,_profile_slot=lambda:2),change_profile=Mock())
        with patch.object(shared,'profile_slot_used',side_effect=lambda s:s==2), patch.object(shared,'profile_summary',return_value={'level':12}), patch('gui.live_window.QInputDialog.getItem',side_effect=lambda *a:(a[3][0],True)), patch('gui.live_window.QMessageBox.question',return_value=QMessageBox.No), patch.object(shared,'delete_profile_slot') as delete:
            LiveWindow.delete_profile(w)
            delete.assert_not_called();w.change_profile.assert_not_called()

    def test_active_profile_switches_before_deletion(self):
        from unittest.mock import Mock
        from PySide6.QtCore import QProcess
        order=[]
        w=SimpleNamespace(ui=lambda text,**values:text.format(**values),game=SimpleNamespace(get_snapshot=lambda:SimpleNamespace(language='de'),busy=False,ready=True,prompt_id=None,_profile_slot=lambda:2,
            process=SimpleNamespace(state=lambda:QProcess.NotRunning)),
            change_profile=lambda index:order.append(('switch',index)),footer=Mock())
        with patch.object(shared,'profile_slot_used',side_effect=lambda s:s==2), patch.object(shared,'profile_summary',return_value={'level':12}), patch('gui.live_window.QInputDialog.getItem',side_effect=lambda *a:(a[3][0],True)), patch('gui.live_window.QMessageBox.question',return_value=QMessageBox.Yes), patch.object(shared,'delete_profile_slot',side_effect=lambda slot:order.append(('delete',slot))):
            LiveWindow.delete_profile(w)
        self.assertEqual(order,[('switch',0),('delete',2)])

class DiagnosticsTests(unittest.TestCase):
    def test_info_hidden_errors_preserved(self):
        for line in ['ggml_metal_device_init: tensor API disabled for pre-M5 and pre-A19 devices','ggml_metal_device_init: GPU name:   MTL0 (Apple M4)','ggml_metal_device_init: simdgroup matrix mul. = true','ggml_metal_library_init: loaded in 0.009 sec','ggml_metal_rsets_init: creating a residency set collection (keep_alive = 180 s)']:
            self.assertEqual(visible_diagnostics(line+'\n'),'')
        errors='ggml_metal_library_init: failed to load library\nllama_decode returned -3\nunknown diagnostic\n'
        self.assertEqual(visible_diagnostics(errors),errors)

    def test_native_writes_and_exception_are_preserved(self):
        import os
        @quiet_metal_startup
        def probe():
            os.write(2,b'ggml_metal_library_init: using embedded metal library\n')
            os.write(2,b'actual error\n')
            raise ValueError('test error')
        previous=os.dup(2)
        try:
            with tempfile.TemporaryFile() as output:
                os.dup2(output.fileno(),2)
                with self.assertRaisesRegex(ValueError,'test error'):probe()
                output.seek(0)
                self.assertEqual(output.read(),b'actual error\n')
        finally:os.dup2(previous,2);os.close(previous)
