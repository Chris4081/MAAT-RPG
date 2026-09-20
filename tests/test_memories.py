"""Native history browsing, deletion confirmation, navigation and profile reset."""
import os
import sqlite3
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import QUrl, QCoreApplication, QEvent
from PySide6.QtWidgets import QMessageBox
from test_desktop import APP
import test_live_window as helpers
from apps.maat_rpg import session_shared
from gui.live_window import LiveWindow
from gui.memories import Memories


class MemoriesTests(unittest.TestCase):
    def test_failed_delete_keeps_entry_and_never_claims_it_was_erased(self):
        with tempfile.TemporaryDirectory() as folder:
            w=Memories(); w.set_profile(folder)
            try:
                identifier=w.store.append('user','Noch nicht gelöscht','adventure','2026-09-09T12:00:00')
                w.set_count(5)
                with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes), patch.object(w.store,'delete_message',side_effect=sqlite3.OperationalError('database is locked')):
                    w.delete_link(QUrl(f'delete:{identifier}'))
                self.assertIsNotNone(w.store.get(identifier))
                self.assertIn('fehlgeschlagen',w.error.text()); self.assertEqual(w.receipt.text(),'')
                with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):
                    w.delete_link(QUrl(f'delete:{identifier}'))
                self.assertIsNone(w.store.get(identifier)); self.assertIn('überschrieben',w.receipt.text())
            finally: w.deleteLater(); APP.processEvents()

    def test_fifth_message_notice_waits_for_response_and_is_once_per_profile(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            w=LiveWindow(audio=helpers.SilentAudio())
            w.request_title_start()
            w.choose_profile(w.game._profile_slot())
            try:
                helpers.LiveWindowTest.spin(self,lambda:w.game.ready)
                root=Path(folder)/'first'; w.memories.set_profile(root)
                w._guide_messages=0; w._history_unlock_pending=False
                w.phase='playing'; w.navigate(3); w.journal.clear()
                w.receive({'event':'profile','data':{'chat_messages':4}})
                self.assertNotIn('Verlauf freigeschaltet',w.journal.toPlainText())
                w.game._handle({'event':'busy','value':True})
                w.game._handle({'event':'chat_generation'})
                w.game._handle({'event':'output','text':'Die fünfte Antwort ist jetzt vollständig.'})
                w.text_stream.timer.stop()
                w.receive({'event':'profile','data':{'chat_messages':5}})
                self.assertNotIn('Verlauf freigeschaltet',w.journal.toPlainText())
                w.game._handle({'event':'busy','value':False}); w.text_stream.finish(); APP.processEvents()
                text=w.journal.toPlainText()
                self.assertEqual(text.count('Verlauf freigeschaltet'),1)
                self.assertLess(text.index('vollständig.'),text.index('Verlauf freigeschaltet'))
                for count in (5,6,12):w.receive({'event':'profile','data':{'chat_messages':count}})
                self.assertEqual(w.journal.toPlainText().count('Verlauf freigeschaltet'),1)
                # Reopening the same archive in a later session preserves the claim.
                w.memories.set_profile(root); w._guide_messages=0; w.journal.clear()
                w.receive({'event':'profile','data':{'chat_messages':12}})
                self.assertNotIn('Verlauf freigeschaltet',w.journal.toPlainText())
                # Another profile gets its own hint, after leaving menu/intro.
                w.memories.set_profile(Path(folder)/'second'); w._guide_messages=0
                w.phase='menu'; w.receive({'event':'profile','data':{'chat_messages':5}})
                self.assertNotIn('Verlauf freigeschaltet',w.journal.toPlainText())
                w.phase='playing'; w.navigate(3)
                self.assertEqual(w.journal.toPlainText().count('Verlauf freigeschaltet'),1)
            finally:
                w.game.shutdown(); w.close(); w.deleteLater()
                QCoreApplication.sendPostedEvents(w,QEvent.DeferredDelete); APP.processEvents()

    def test_browser_filters_escaping_and_confirmed_deletion(self):
        with tempfile.TemporaryDirectory() as folder:
            w=Memories(); w.set_profile(folder)
            try:
                first=w.store.append('user','<b>Nur Text</b>','adventure','2026-09-09T14:00:00')
                w.store.append('assistant','Schön, dass du wieder da bist.','adventure','2026-09-09T14:00:01')
                w.store.append('user','Anderer Monat','adventure','2026-08-09T14:00:00')
                w.store.append('user','Anderes Jahr','adventure','2027-09-09T14:00:00')
                w.set_count(4); self.assertTrue(w.body.isHidden()); self.assertFalse(w.transcript.toPlainText())
                w.set_count(5); w.year.setCurrentIndex(w.year.findData('2026')); w.month.setCurrentIndex(9)
                self.assertEqual(w.days.count(),1); self.assertIn('<b>Nur Text</b>',w.transcript.toPlainText())
                self.assertIn('2 Nachrichten',w.summary.text())
                with patch.object(QMessageBox,'question',return_value=QMessageBox.No): w.delete_link(QUrl(f'delete:{first}'))
                self.assertIsNotNone(w.store.get(first))
                with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes): w.delete_link(QUrl(f'delete:{first}'))
                self.assertIsNone(w.store.get(first)); self.assertNotIn('<b>',w.transcript.toPlainText())
                with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes): w.confirm_delete_day()
                self.assertEqual(w.days.count(),0); self.assertIn('keine Gespräche',w.transcript.toPlainText())
                w.month.setCurrentIndex(0); self.assertEqual(w.days.count(),1)
                w.year.setCurrentIndex(0); self.assertEqual(w.days.count(),2)
                w.order.setCurrentIndex(1); self.assertEqual(w.selected_day(),'2026-08-09')
                w.set_profile(Path(folder)/'other'); w.set_count(5)
                self.assertEqual(w.days.count(),0); self.assertNotIn('Anderer Monat',w.transcript.toPlainText())
            finally: w.deleteLater(); APP.processEvents()

    def test_live_unlock_sidebar_replacement_and_profile_change(self):
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            w=LiveWindow(audio=helpers.SilentAudio())
            w.request_title_start()
            w.choose_profile(w.game._profile_slot())
            try:
                helpers.LiveWindowTest.spin(self,lambda:w.game.ready)
                w.phase='playing'; w.navigate(3)
                self.assertFalse(hasattr(w,'monster_button'))
                for count in (4,5,6):
                    w.receive({'event':'profile','data':{'chat_messages':count}})
                    self.assertEqual(w.memories_button.isEnabled(),count>=5)
                    w.navigate(w.memories_index)
                    self.assertEqual(w.stack.currentIndex(),w.memories_index if count>=5 else 3)
                w.memories.store.append('user','Gespräch im ersten Profil','adventure','2026-09-09T12:00:00')
                w.receive({'event':'chat_archived'})
                self.assertIn('Gespräch im ersten Profil',w.memories.transcript.toPlainText())
                w.change_profile(1)
                self.assertEqual(w._guide_messages,0); self.assertFalse(w.memories_button.isEnabled())
                self.assertEqual(w.memories.store.root, session_shared.profile_slot_root(w.game._profile_slot()))
                self.assertNotIn('Gespräch im ersten Profil',w.memories.transcript.toPlainText())
            finally:
                w.game.shutdown(); w.close(); w.deleteLater()
                QCoreApplication.sendPostedEvents(w,QEvent.DeferredDelete); APP.processEvents()
