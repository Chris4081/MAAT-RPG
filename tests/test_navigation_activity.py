"""Navigation, unread chat/logs, and stream-safe attention without a GGUF."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from test_desktop import APP
import test_live_window as helpers
from apps.maat_rpg import session_shared
from gui.live_window import LiveWindow


class NavigationActivityTests(unittest.TestCase):
    spin = helpers.LiveWindowTest.spin

    def setUp(self):
        self.env = patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)})
        self.env.start()
        helpers.unlock_test_arena()
        self.w = LiveWindow(audio=helpers.SilentAudio())
        self.w.request_title_start()
        self.w.choose_profile(self.w.game._profile_slot())
        self.w.resize(1220,900); self.w.show()
        self.spin(lambda:self.w.game.ready)
        self.w.ki_dialog.hide()
        self.w.phase='playing'; self.w._started=True
        self.w.navigate(3)
        self.w.text_stream.finish(); APP.processEvents()
        self.chat=self.w.nav_buttons[3]
        self.w.chat_activity.reset()

    def tearDown(self):
        self.w.game.shutdown();self.w.close();self.w.deleteLater()
        QCoreApplication.sendPostedEvents(self.w,QEvent.DeferredDelete)
        APP.processEvents();self.env.stop()

    def test_visual_order_keeps_routes_and_unlocks_and_fits_small_screen(self):
        w=self.w
        expected=[w.nav_buttons[3],w.nav_buttons[5],w.memories_button,w.nav_buttons[1],
                  w.talent_button,w.nav_buttons[2],w.dungeon_button,w.game_hall_button,
                  w.guide_button,w.nav_buttons[4],w.nav_buttons[0]]
        layout=w.navigation_scroll.widget().layout()
        actual=[layout.itemAt(i).widget() for i in range(layout.count()) if layout.itemAt(i).widget() in expected]
        self.assertEqual(actual,expected)
        self.assertEqual(len(set(actual)),11)
        w._guide_messages=0;w._talent_data={'unlocked':False};w._combat_unlocked=False
        w.update_controls()
        for btn in (w.memories_button,w.talent_button,w.guide_button,w.nav_buttons[2]):
            self.assertFalse(btn.isEnabled())
        for btn,index in ((w.nav_buttons[5],5),(w.nav_buttons[1],1),(w.nav_buttons[3],3),(w.nav_buttons[4],4)):
            btn.click()
            self.assertEqual(w.stack.currentIndex(),index)
            self.assertTrue(btn.isChecked())
        w.resize(880,650);APP.processEvents()
        self.assertEqual(w.navigation_scroll.width(),218)
        self.assertLessEqual(w.navigation_scroll.height(),650)
        w.navigation_scroll.ensureWidgetVisible(w.nav_buttons[0])
        APP.processEvents()
        viewport=w.navigation_scroll.viewport()
        bottom=w.nav_buttons[0].mapTo(viewport,w.nav_buttons[0].rect().bottomRight())
        self.assertLessEqual(bottom.y(),viewport.height())
        w.nav_buttons[0].click()
        self.assertEqual(w.phase,'menu')
        self.assertEqual(w.stack.currentIndex(),0)

    def test_stream_marks_unread_once_and_opening_chat_acknowledges(self):
        w=self.w
        w.navigate(1)
        w.receive(dict(event='chat_generation'))
        self.assertFalse(self.chat.unread)  # Generation alone is not a new message.
        for text in ('Hallo ', 'Maatis. ', 'Die Reise geht weiter.'):
            w.receive(dict(event='output',text=text))
            w.text_stream.finish()
            self.assertTrue(self.chat.unread)
            self.assertTrue(self.chat.pulse_timer.isActive())
        self.assertEqual(w.stack.currentIndex(),1)  # No forced jump away from a task.
        QTest.qWait(100)
        elapsed=self.chat.pulse_clock.elapsed()
        w.present_text(' Noch ein Token.')
        self.assertGreaterEqual(self.chat.pulse_clock.elapsed(),elapsed)
        self.assertIn('Neue Chatnachrichten',self.chat.accessibleDescription())
        self.chat.click()
        self.assertEqual(w.stack.currentIndex(),3)
        self.assertFalse(self.chat.unread)
        self.assertFalse(self.chat.pulse_timer.isActive())
        w.present_text(' Sichtbar im geöffneten Chat.')
        self.assertFalse(self.chat.unread)

    def test_reward_logs_mark_chat_but_formatting_deletion_and_diagnostics_do_not(self):
        w=self.w
        w.present_text('Bisheriger Verlauf.\n')
        w.navigate(5)
        w.receive(dict(event='diagnostic',text='ggml: internal detail'))
        w.receive(dict(event='level_progress',level=15,xp=6386,next_xp=6685,gain=12))
        w.apply_text_size('large')
        self.assertFalse(self.chat.unread)
        w.receive(dict(event='minigame_result',text='Gewonnen! Du erhältst Gold.'))
        self.assertTrue(self.chat.unread)
        w.navigate(3);w.navigate(1)
        cursor=QTextCursor(w.journal.document())
        cursor.select(QTextCursor.Document)
        fmt=cursor.charFormat();fmt.setFontItalic(True);cursor.mergeCharFormat(fmt)
        self.assertFalse(self.chat.unread)
        w.journal.clear()
        self.assertFalse(self.chat.unread)
        w.journal.append('📜 Neue Quest abgeschlossen!')
        self.assertTrue(self.chat.unread)
        w.journal.clear()
        self.assertFalse(self.chat.unread)

    def test_bounded_log_keeps_notifying_and_hidden_indicator_does_not_run(self):
        w=self.w
        w.journal.document().setMaximumBlockCount(2)
        w.journal.append('Eintrag 1');w.journal.append('Eintrag 2')
        w.navigate(1)
        w.journal.append('Eintrag 3')
        self.assertTrue(self.chat.unread)
        self.assertNotIn('Eintrag 1',w.journal.toPlainText())
        w.navigation_scroll.hide();APP.processEvents()
        self.assertFalse(self.chat.pulse_timer.isActive())
        self.assertTrue(self.chat.unread)
        w.navigation_scroll.show();APP.processEvents()
        self.assertTrue(self.chat.pulse_timer.isActive())
        w.navigate(3)
        self.assertFalse(self.chat.unread)

    def test_profile_switch_resets_unread_without_changing_old_log(self):
        w=self.w
        w.navigate(1);w.journal.append('Nur im bisherigen Profil neu.')
        self.assertTrue(self.chat.unread)
        other=(w.game._profile_index+1)%session_shared.PROFILE_SLOT_COUNT
        w.change_profile(other)
        if w.phase == 'language': w.select_profile_language('de')
        self.spin(lambda:w.game.ready)
        self.assertFalse(self.chat.unread)
        self.assertFalse(self.chat.pulse_timer.isActive())
        self.assertNotIn('Nur im bisherigen Profil neu.',w.journal.toPlainText())

    def test_render_sidebar_with_unread_chat(self):
        w=self.w
        w._guide_messages=20
        w.guide_button.setText('✦   MAAT-Guide')
        w.update_controls();w.navigate(1)
        w.receive(dict(event='minigame_result',text='Neuer Logeintrag · Minispiel gewonnen.'))
        QTest.qWait(150)
        self.assertTrue(self.chat.unread)
        image=w.navigation_scroll.grab()
        self.assertFalse(image.isNull())
        if os.environ.get('MAAT_GUI_SCREENSHOTS'):
            out=Path(os.environ['MAAT_GUI_SCREENSHOTS']);out.mkdir(parents=True,exist_ok=True)
            image.save(str(out/'sidebar-unread.png'))
            w.grab().save(str(out/'navigation-unread.png'))
            w.resize(880,650);APP.processEvents()
            w.grab().save(str(out/'navigation-small.png'))


if __name__=='__main__':unittest.main()
