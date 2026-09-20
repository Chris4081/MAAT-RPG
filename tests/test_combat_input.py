"""Battle narration shortcuts must never choose an attack or eat a draft."""
import unittest
from unittest.mock import patch
from test_desktop import APP
import test_gui_language as helpers
from apps.maat_rpg import session_shared as shared
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog
from gui.combat_input import advance_state


class CombatInputTests(unittest.TestCase):
    setUp = helpers.LanguageTests.setUp
    close_windows = helpers.LanguageTests.close_windows
    window = helpers.LanguageTests.window

    def battle(self, language='de'):
        shared.write_application_language(language)
        window = self.window()
        window.title_idle.stop()
        window.phase = 'playing'
        window._combat_unlocked = True
        window.navigate(2)
        window.game._handle(dict(event='battle', active=True, enemy_name='Schattenwächter',
            enemy_hp=100, enemy_max_hp=100, player_hp=100, combat_source='arena'))
        APP.processEvents()
        self.assertEqual(window.stack.currentIndex(), 2)
        return window

    def narrate(self, window):
        window.game._handle(dict(event='output', text='Maatis trifft den Gegner. ' * 6, combat=True))
        window.text_stream.timer.stop()
        self.assertTrue(window.text_stream.running)
        self.assertTrue(window.reveal_button.isHidden())
        self.assertFalse(window.arena.advance_hint.isHidden())

    def prompt(self, window, choices=None, text='Weiter mit ENTER …'):
        window.game._handle(dict(event='prompt', id='turn', text=text, choices=choices or []))

    def test_click_space_and_both_enter_keys_reveal_without_selecting_an_action(self):
        window = self.battle()
        for gesture in ('scene', 'text', Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            with self.subTest(gesture=gesture), patch.object(window.game, 'write') as write:
                self.narrate(window)
                self.prompt(window, [{'value':'1', 'label':'Harmonie'}, {'value':'2', 'label':'Balance'}], 'Wähle deinen Angriff')
                if gesture in ('scene', 'text'):
                    target = window.arena.stage if gesture == 'scene' else window.arena.log.viewport()
                    QTest.mouseClick(target, Qt.LeftButton)
                else:
                    QTest.keyClick(window.arena.log, gesture)
                self.assertFalse(window.text_stream.running)
                self.assertTrue(window.arena.advance_hint.isHidden())
                self.assertEqual(window.game.prompt_id, 'turn')
                self.assertIn('Maatis trifft den Gegner.', window.arena.log.toPlainText())
                write.assert_not_called()
                QTest.keyClick(window.arena.log, Qt.Key_Return)
                write.assert_not_called()
                window.game._handle(dict(event='prompt_closed'))

    def test_confirmation_is_a_separate_press_and_key_repeat_cannot_confirm(self):
        window = self.battle('en')
        self.narrate(window)
        self.assertIn('Space', window.arena.advance_hint.text())
        self.assertIn('reveal', window.arena.advance_hint.text())
        self.prompt(window, text='Press ENTER to continue …')
        with patch.object(window.game, 'write') as write:
            QCoreApplication.sendEvent(window.arena.log, QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))
            self.assertEqual(advance_state(window), 'confirm')
            self.assertIn('continue', window.arena.advance_hint.text())
            self.assertEqual(window.game.prompt_id, 'turn')
            # Qt moves focus to the confirmation field when streaming ends.
            for _ in range(3):
                QCoreApplication.sendEvent(window.answer, QKeyEvent(QEvent.KeyRelease, Qt.Key_Return, Qt.NoModifier, '', True))
                QCoreApplication.sendEvent(window.answer, QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier, '', True))
            QCoreApplication.sendEvent(window.answer, QKeyEvent(QEvent.KeyRelease, Qt.Key_Return, Qt.NoModifier))
            write.assert_not_called()
            QTest.keyClick(window.answer, Qt.Key_Space)
            write.assert_called_once_with({'op':'answer', 'id':'turn', 'value':''})
            self.assertIsNone(window.game.prompt_id)
            self.assertEqual(window.answer.text(), '')
            self.assertTrue(window.arena.advance_hint.isHidden())

    def test_mouse_confirmation_and_existing_choice_buttons(self):
        window = self.battle()
        with patch.object(window.game, 'write') as write:
            self.narrate(window)
            self.prompt(window)
            QTest.mouseClick(window.arena.log.viewport(), Qt.LeftButton)
            write.assert_not_called()
            QTest.mouseClick(window.arena.stage, Qt.LeftButton)
            write.assert_called_once_with({'op':'answer', 'id':'turn', 'value':''})
            write.reset_mock()
            self.prompt(window, [{'value':'2', 'label':'Heilen'}], text='Wähle eine Aktion')
            button = window.choice_layout.itemAt(0).widget()
            QTest.mouseClick(button, Qt.LeftButton)
            write.assert_called_once_with({'op':'answer', 'id':'turn', 'value':'2'})

    def test_keyboard_reveal_works_after_clicking_an_attack_without_an_extra_focus_click(self):
        window = self.battle()
        window.game.ready = True
        choices = [{'value':str(i), 'label':label} for i, label in enumerate(
            ('Harmonie', 'Balance', 'Schöpfungskraft', 'Verbundenheit', 'Respekt', 'Zurück'), 1)]
        self.prompt(window, choices, 'Wähle [1-6]:')
        window.arena.actions['h'].setFocus()
        with patch.object(window.game, 'write') as write:
            QTest.mouseClick(window.arena.actions['h'], Qt.LeftButton)
            write.assert_called_once_with({'op':'answer', 'id':'turn', 'value':'1'})
            write.reset_mock()
            self.narrate(window)
            self.prompt(window, choices, 'Wähle [1-6]:')
            self.assertIs(APP.focusWidget(), window.arena.log)
            QTest.keyClick(APP.focusWidget(), Qt.Key_Space)
            self.assertFalse(window.text_stream.running)
            write.assert_not_called()

    def test_text_fields_navigation_and_modal_dialogs_keep_their_input(self):
        window = self.battle()
        window.tactical_input.show()
        window.tactical_input.setText('Fokus')
        window.tactical_input.setFocus()
        self.narrate(window)
        # Typing in the editable tactical advice field must remain normal.
        self.assertIs(APP.focusWidget(), window.tactical_input)
        QTest.keyClick(window.tactical_input, Qt.Key_Space)
        self.assertEqual(window.tactical_input.text(), 'Fokus ')
        self.assertTrue(window.text_stream.running)
        # Clicking a normal button must not reveal combat text.
        QTest.mouseClick(window.arena.actions['h'], Qt.LeftButton)
        self.assertTrue(window.text_stream.running)
        dialog = QDialog(window)
        dialog.setModal(True); dialog.show(); APP.processEvents()
        self.assertFalse(window.combat_input.handle(window, window.arena.log,
            QKeyEvent(QEvent.KeyPress, Qt.Key_Space, Qt.NoModifier)))
        dialog.close(); dialog.deleteLater()
        self.assertTrue(window.text_stream.running)
        window.navigate(3)
        self.assertFalse(window.reveal_button.isHidden())
        QTest.keyClick(window.journal, Qt.Key_Space)
        self.assertTrue(window.text_stream.running)
        window.reveal_button.click()
        self.assertFalse(window.text_stream.running)

    def test_free_text_and_drafts_are_never_empty_confirmations(self):
        window = self.battle()
        self.prompt(window, text='Wie lautet dein Rat?')
        with patch.object(window.game, 'write') as write:
            QTest.mouseClick(window.arena.stage, Qt.LeftButton)
            QTest.keyClick(window.arena.log, Qt.Key_Space)
            write.assert_not_called()
            self.prompt(window)
            window.answer.setText('Bitte heilen')
            self.assertIsNone(advance_state(window))
            QTest.mouseClick(window.arena.stage, Qt.LeftButton)
            write.assert_not_called()
            QTest.keyClick(window.answer, Qt.Key_Return)
            write.assert_called_once_with({'op':'answer', 'id':'turn', 'value':'Bitte heilen'})

    def test_boss_phase_and_final_scene_follow_the_revealed_text(self):
        window = self.battle()
        send = window.game._handle
        for fight_type in ('boss', 'final'):
            with self.subTest(fight_type=fight_type):
                send(dict(event='battle', active=True, enemy_name='Pharao', phase=1, fight_type=fight_type))
                self.narrate(window)
                send(dict(event='battle', active=True, phase=2))
                self.assertEqual(window.game.get_snapshot().battle.phase, 1)
                QTest.keyClick(window.arena.log, Qt.Key_Space)
                self.assertEqual(window.game.get_snapshot().battle.phase, 2)
                self.narrate(window)
                send(dict(event='battle', active=False, enemy_hp=0))
                send(dict(event='story_scene', id='ending', lines=['Das Licht kehrt zurück.'], module='credits', name='Finale', music=None))
                self.assertEqual(window.phase, 'playing')
                QTest.keyClick(window.arena.log, Qt.Key_Return)
                self.assertEqual(window.phase, 'story')
                self.assertFalse(window.combat_input.keys_down)
                self.assertTrue(window.reveal_button.isHidden())
                window.finish_story_scene()
                window.navigate(2)


if __name__ == '__main__':
    unittest.main()
