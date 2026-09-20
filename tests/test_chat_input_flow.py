"""Compose the next turn while streaming; keep draft/focus and follow new text."""
import os
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt, QCoreApplication, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QLineEdit, QVBoxLayout
from test_desktop import APP
from test_live_window import SilentAudio
import test_live_window as window_helpers
from apps.maat_rpg import session_shared
from gui.live_window import LiveWindow


class ChatInputFlowTests(unittest.TestCase):
    spin = window_helpers.LiveWindowTest.spin

    def setUp(self):
        self.env = patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)})
        self.env.start()
        self.w = LiveWindow(audio=SilentAudio())
        self.w.request_title_start()
        self.w.choose_profile(self.w.game._profile_slot())
        self.w.show(); self.spin(lambda:self.w.game.ready)
        self.w.ki_dialog.hide()
        self.w.model_ready = True
        self.w.phase = 'playing'
        self.w.perspective.setCurrentIndex(self.w.perspective.findData('adventure'))
        self.w.navigate(3)
        self.w.activateWindow()
        APP.processEvents()
        self.w.request_chat_focus()
        self.spin(lambda:self.w.input.hasFocus())

    def tearDown(self):
        self.w.game.shutdown(); self.w.close(); self.w.deleteLater()
        QCoreApplication.sendPostedEvents(self.w, QEvent.DeferredDelete)
        APP.processEvents(); self.env.stop()

    def begin_reply(self, text='Die KI antwortet gerade. ' * 12):
        self.w.game._handle({'event':'chat_generation'})
        self.w.game._handle({'event':'output','text':text})
        self.w.text_stream.timer.stop()

    def finish_reply(self):
        self.w.game._handle({'event':'busy','value':False})
        self.w.text_stream.finish()
        APP.processEvents()

    def test_draft_survives_stream_and_can_be_sent_without_mouse(self):
        sent=[]
        def accept(text):
            sent.append(text)
            self.w.game._handle({'event':'busy','value':True})
        with patch.object(self.w.game,'send_text',side_effect=accept):
            self.w.input.setText('Hallo Maatis')
            self.w.send_button.setFocus()
            self.w.send_button.click()
            self.spin(lambda:self.w.input.hasFocus())
            self.assertTrue(self.w.input.isEnabled())  # Already editable before token 1.
            self.assertFalse(self.w.send_button.isEnabled())
            self.begin_reply()
            QTest.keyClicks(self.w.input,'Meine zweite Frage')
            self.w.input.setCursorPosition(6)
            QTest.keyClick(self.w.input, Qt.Key_Return)
            self.assertEqual(sent,['Hallo Maatis'])
            self.assertEqual(self.w.input.text(),'Meine zweite Frage')
            self.finish_reply()
            self.assertTrue(self.w.input.hasFocus())
            self.assertEqual(self.w.input.cursorPosition(),6)
            self.assertEqual(self.w.input.text(),'Meine zweite Frage')
            self.assertTrue(self.w.send_button.isEnabled())
            QTest.keyClick(self.w.input, Qt.Key_Return)
            self.assertEqual(sent,['Hallo Maatis','Meine zweite Frage'])
            self.assertEqual(self.w.input.text(),'')
            self.w.game._handle({'event':'busy','value':False})

    def test_escape_discards_pending_tokens_and_keeps_next_draft(self):
        self.w._chat_turn_active=True
        self.w.game.chat_turn_id='cancel-me'
        self.w.game._handle({'event':'busy','value':True})
        self.begin_reply()
        self.w.input.setText('Mein nächster Entwurf')
        with patch.object(self.w.game,'write') as send:
            QTest.keyClick(self.w.input,Qt.Key_Escape)
            send.assert_called_with({'op':'cancel_chat','turn_id':'cancel-me'})
            self.assertFalse(self.w.text_stream.running)
            self.w.game._handle({'event':'output','text':'late tokens must vanish'})
            self.w.game._handle({'event':'chat_generated','turn_id':'cancel-me'})
            self.assertFalse(self.w.text_stream.running)
            self.w.game._handle({'event':'chat_cancelled','turn_id':'cancel-me'})
            self.w.game._handle({'event':'busy','value':False})
        self.assertNotIn('late tokens',self.w.journal.toPlainText())
        self.assertIn('zählt nicht zum Fortschritt',self.w.journal.toPlainText())
        self.assertEqual(self.w.input.text(),'Mein nächster Entwurf')
        self.assertTrue(self.w.send_button.isEnabled())

    def test_progress_ack_waits_until_last_visible_character(self):
        self.w.game.chat_turn_id='delivered'
        self.w.game._handle({'event':'busy','value':True})
        self.begin_reply('Eine vollständige Antwort.')
        with patch.object(self.w.game,'write') as send:
            self.w.game._handle({'event':'chat_generated','turn_id':'delivered'})
            send.assert_not_called()
            self.w.text_stream.finish()
            send.assert_called_once_with({'op':'chat_presented','turn_id':'delivered'})
        self.w.game._handle({'event':'busy','value':False})

    def test_free_companion_uses_the_same_draft_and_focus_flow(self):
        self.w.perspective.setCurrentIndex(self.w.perspective.findData('companion'))
        self.w.companion_panel.data={'scene':None}
        def accept(*args): self.w.game._handle({'event':'busy','value':True})
        with patch.object(self.w.game,'answer_companion',side_effect=accept) as send:
            self.w.input.setText('Ich bin deine Begleiter-KI und helfe dir dabei, gemeinsam einen sicheren Weg durch die Bibliothek zu finden.')
            self.w.send()
            send.assert_called_once()
            self.begin_reply()
            self.assertTrue(self.w.input.isEnabled())
            self.w.input.setText('Mein neuer Entwurf bleibt hier stehen.')
            self.finish_reply()
            self.assertTrue(self.w.input.hasFocus())
            self.assertEqual(self.w.input.text(),'Mein neuer Entwurf bleibt hier stehen.')

    def test_prompt_modal_and_other_page_keep_their_focus(self):
        self.w._chat_turn_active=True
        self.w.game._handle({'event':'busy','value':True})
        self.begin_reply('Wähle deinen Weg.\n')
        self.w.game._handle({'event':'prompt','id':'choice','text':'Deine Entscheidung?', 'choices':[]})
        self.w.text_stream.finish(); APP.processEvents()
        self.assertFalse(self.w.input.isEnabled())
        self.w.request_chat_focus(); APP.processEvents()
        self.assertTrue(self.w.answer.hasFocus())
        # The real submit path clears prompt_id before announcing prompt_closed.
        with patch.object(self.w.game, 'write'):
            self.w.game.submit_choice('1')
        self.finish_reply()
        dialog=QDialog(self.w); dialog.setModal(True)
        edit=QLineEdit(); QVBoxLayout(dialog).addWidget(edit)
        try:
            dialog.show(); edit.setFocus(); APP.processEvents()
            self.w.request_chat_focus(); APP.processEvents()
            self.assertTrue(edit.hasFocus())
        finally:
            dialog.close(); dialog.deleteLater(); APP.processEvents()
        # Offscreen Qt leaves activeWindow() empty after a modal closes; emulate
        # the user returning to the main window without forcing this in production.
        self.w.activateWindow(); APP.processEvents()
        self.w.navigate(5)
        self.w.world_tabs.setCurrentIndex(1)
        self.w.command_filter.setFocus()
        self.w._chat_turn_active=True
        self.finish_reply()
        self.assertEqual(self.w.stack.currentIndex(),5)
        self.assertFalse(self.w.input.hasFocus())
        self.w.navigate(3)
        self.spin(lambda:self.w.input.hasFocus())

    def test_new_text_scrolls_to_bottom_after_wrapping_and_keeps_input_cursor(self):
        self.w.resize(1000,700)
        self.w.input.setText('Noch nicht gesendet')
        self.w.input.setCursorPosition(5)
        self.w.journal.setPlainText('\n'.join(f'Zeile {i}: Eine lange Reise durch Terra.' for i in range(100)))
        bar=self.w.journal.verticalScrollBar()
        self.spin(lambda:bar.maximum()>0 and bar.value()==bar.maximum())
        bar.setValue(0); APP.processEvents()
        self.assertEqual(bar.value(),0)  # Reading older text still works between messages.
        self.w.journal.append('Du · Meine neue Eingabe')
        self.spin(lambda:bar.value()==bar.maximum())
        bar.setValue(0)
        self.w.present_text('\n'+'Eine neue Antwort mit langen umgebrochenen Sätzen. '*60)
        self.w.resize(780,700)
        self.spin(lambda:bar.value()==bar.maximum())
        self.assertEqual(self.w.input.text(),'Noch nicht gesendet')
        self.assertEqual(self.w.input.cursorPosition(),5)
        self.assertTrue(self.w.input.hasFocus())
        self.w.receive({'event':'minigame_result','text':'Minispiel beendet: Du erhältst Gold.'})
        self.spin(lambda:bar.value()==bar.maximum())
        self.w.navigate(5); self.w.world_tabs.setCurrentIndex(2)
        self.w.world_output.setPlainText('\n'.join('Ereignis '+str(i) for i in range(100)))
        world_bar=self.w.world_output.verticalScrollBar()
        self.spin(lambda:world_bar.maximum()>0 and world_bar.value()==world_bar.maximum())
        world_bar.setValue(0)
        self.w.world_output.append('Neues Ereignis')
        self.spin(lambda:world_bar.value()==world_bar.maximum())
