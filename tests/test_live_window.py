from PySide6.QtCore import QCoreApplication, QEvent
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch
# Reuse the offscreen QApplication and private Path.home established by UI tests.
from test_desktop import APP
from PySide6.QtCore import QObject, Signal
from apps.maat_rpg import session_shared
from gui.live_window import LiveWindow


class SilentAudio(QObject):
    status = Signal(str)
    music_enabled = False
    def __init__(self):
        super().__init__()
        self.events = []
    def location(self, *args): pass
    def set_volume(self, *args): pass
    def set_enabled(self, *args): pass
    def close(self): pass
    def handle_event(self, e): self.events.append(e)


def unlock_test_arena():
    if not session_shared.profile_has_explicit_language(session_shared.active_profile_slot()):
        session_shared.write_profile_settings(session_shared.active_profile_slot(), {'language': 'de'})
    import json
    path=session_shared.profile_slot_root(session_shared.active_profile_slot())/'state/battle_state.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    data=json.loads(path.read_text()) if path.exists() else {}
    data.setdefault('world',{})['combat_unlocked']=True
    data.setdefault('player',{}).update(hp=1000,max_hp=1000,level=5)
    # Existing combat tests use a profile whose first class choice is complete.
    data['hero_class'] = {'selected': 'robo', 'pending': False}
    path.write_text(json.dumps(data))


class LiveWindowTest(unittest.TestCase):
    def spin(self, condition, seconds=12):
        deadline = time.monotonic() + seconds
        while not condition() and time.monotonic() < deadline:
            APP.processEvents()
            time.sleep(.01)
        self.assertTrue(condition())

    def test_real_window_prompt_and_navigation(self):
        with patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT': str(session_shared.BASE_APP_SUPPORT_DIR)}):
            unlock_test_arena()
            audio = SilentAudio()
            window = LiveWindow(audio=audio)
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
            try:
                window.show()
                self.spin(lambda: window.game.ready)
                window.enter_menu()
                self.assertEqual(window.text_size_combo.currentData(), 'medium')
                previous = window.journal.toPlainText()
                for key, size in [('small',18), ('large',36), ('medium',26)]:
                    window.text_size_combo.setCurrentIndex(window.text_size_combo.findData(key))
                    self.assertEqual(window.journal.font().pixelSize(), size)
                    self.assertEqual(window.world_output.font().pixelSize(), size)
                    self.assertEqual(window.journal.toPlainText(), previous)
                    self.assertEqual(window.arena.log.font().pixelSize(),18)
                    self.assertEqual(session_shared.load_profile_settings(window.game._profile_slot())['gui_text_size'],key)
                window.apply_audio_settings()
                self.assertEqual(window.text_size_combo.currentData(), 'medium')
                self.assertEqual(window.phase, 'menu')
                self.assertFalse(window.start_battle.isEnabled())
                self.assertFalse(window.centralWidget().layout().itemAt(0).widget().isVisible())
                self.assertTrue(window.begin_button.isEnabled())
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    window.grab().save(str(Path(os.environ['MAAT_GUI_SCREENSHOTS'])/'blue-menu.png'))
                window.open_models()
                APP.processEvents()
                self.assertTrue(window.ki_dialog.isVisible())
                self.assertEqual(window.backend_combo.count(), 1)
                with patch('gui.live_window.QFileDialog.getOpenFileName', return_value=('/tmp/test-Qwen3.GGUF', '')):
                    window.pick_model()
                self.assertEqual(window.model_combo.currentText(), '/tmp/test-Qwen3.GGUF')
                self.assertTrue(window.load_button.isEnabled())
                self.assertTrue(window.dialog_settings['thinking_enabled'].isVisible())
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    window.ki_dialog.grab().save(str(Path(os.environ['MAAT_GUI_SCREENSHOTS'])/'ki-menu.png'))
                window.ki_dialog.accept()
                window.begin_button.click()
                self.assertEqual(window.phase, 'intro')
                self.assertEqual(window.stack.currentIndex(), 6)
                self.spin(lambda: len(window.intro.text.toPlainText()) > 3)
                self.assertTrue(any(e.get('owner') == 'native-intro' and e.get('action') == 'play' for e in audio.events))
                window.navigate(3)
                self.assertEqual(window.stack.currentIndex(), 6)
                window.intro.skip_button.click()
                window.perspective_screen.cards['adventure'].click()
                self.assertEqual(window.phase, 'playing')
                self.assertEqual(window.stack.currentIndex(), 3)
                self.assertTrue(any(e.get('owner') == 'native-intro' and e.get('action') == 'stop' for e in audio.events))
                window.text_stream.finish()
                self.assertTrue(window.start_battle.isEnabled())
                window._combat_unlocked=False
                window.update_controls()
                self.assertFalse(window.start_battle.isEnabled())
                self.assertFalse(window.nav_buttons[2].isEnabled())
                self.assertFalse(window.companion_panel.fight.isEnabled())
                window.navigate(2)
                self.assertEqual(window.stack.currentIndex(),3)
                window._combat_unlocked=True
                window.update_controls()
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    window.grab().save(str(Path(os.environ['MAAT_GUI_SCREENSHOTS'])/'blue-chat.png'))
                self.assertTrue(window.character_sidebar.isVisible())
                self.assertTrue(window.character_sidebar.expanded)
                self.assertIn('HP ', window.character_sidebar.hp.text())
                self.assertIn('Level ', window.character_sidebar.level.text())
                window.character_sidebar.toggle.click()
                self.assertTrue(window.character_sidebar.scroll.isHidden())
                self.assertEqual(window.character_sidebar.toggle.text(), '+')
                window.character_sidebar.toggle.click()
                self.assertFalse(window.character_sidebar.scroll.isHidden())
                self.assertEqual(window.character_sidebar.toggle.text(), '−')
                old_text = window.journal.toPlainText()
                window.receive({'event':'diagnostic','text':'llama_kv_cache: technical detail'})
                self.assertEqual(window.journal.toPlainText(), old_text)
                self.assertIn('llama_kv_cache',window.model_status.toolTip())
                window.receive({'event': 'level_progress', 'level': 15, 'xp': 6386, 'next_xp': 6685, 'gain': 12})
                self.assertIn('Level 15', window.chat_level_text.text())
                self.assertIn('95.5%', window.chat_level_text.text())
                self.assertIn('(+12 XP)', window.chat_level_text.text())
                self.assertEqual(window.chat_xp_bar.value(), 955)
                self.assertEqual(window.journal.toPlainText(), old_text)
                # Token gaps must not flash the reveal control back into view.
                window.receive({'event': 'chat_generation'})
                for chunk in ['Eine ', 'gestreamte ', 'Antwort.']:
                    window.receive({'event': 'output', 'text': chunk})
                    self.assertTrue(window.reveal_button.isHidden())
                    window.text_stream.finish()
                    self.assertTrue(window.reveal_button.isHidden())
                window.receive({'event': 'output', 'text': ' Letzter Teil.'})
                window.receive({'event': 'busy', 'value': False})
                self.assertTrue(window._ki_reply_streaming)
                window.text_stream.finish()
                self.assertFalse(window._ki_reply_streaming)
                window.receive({'event': 'output', 'text': 'Spieltext bleibt überspringbar.'})
                self.assertFalse(window.reveal_button.isHidden())
                window.text_stream.finish()
                self.assertGreater(window.command_combo.count(), 10)
                window.execute('/help')
                self.assertEqual(window.world_tabs.currentIndex(),1)
                self.assertFalse(window.command_run.isEnabled())
                window.command_filter.setText('d500 status')
                root=window.command_tree.topLevelItem(0).child(0)
                with patch.object(window.game,'send_command') as sent:
                    window.command_tree.setCurrentItem(root.child(0))
                    sent.assert_not_called()
                    window.command_run.click()
                    sent.assert_called_once_with('/d500 status')
                window.execute('/quests')
                self.assertEqual(window.world_tabs.currentIndex(),0)
                window.navigate(3)
                window.start_battle.click()
                self.spin(lambda: bool(window.game.prompt_id))
                self.assertFalse(window.decision.isVisible())
                window.text_stream.finish()
                self.assertEqual(window.stack.currentIndex(), 2)
                self.assertFalse(window.decision.isVisible())
                self.assertTrue(window.arena.actions["h"].isEnabled())
                self.assertTrue(window.arena.enemy_name.text().startswith('● '))
                # Random encounter metadata also survives the session snapshot.
                from dataclasses import replace
                snapshot=window.game.get_snapshot()
                changed=replace(snapshot,battle=replace(snapshot.battle,combat_source='random',arena_difficulty='hard'))
                window.apply_snapshot(changed)
                self.assertTrue(window.arena.enemy_name.text().startswith('● '))
                self.assertIn('Zufallskampf-EP',window.arena.difficulty_badge.text())
                window.apply_snapshot(snapshot)
                self.assertFalse(window.profile_choice_button.isEnabled())
                self.assertGreater(window.choice_layout.count(), 0)
                self.assertTrue(any(e.get('loop') for e in audio.events))
                window.resize(1220, 940)
                APP.processEvents()
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    target = Path(os.environ['MAAT_GUI_SCREENSHOTS'])
                    target.mkdir(parents=True, exist_ok=True)
                    window.grab().save(str(target/'blue-battle.png'))
                    window.navigate(5)
                    APP.processEvents()
                    window.grab().save(str(target/'blue-world.png'))
            finally:
                window.game.shutdown()
                window.close()
                window.deleteLater()
                QCoreApplication.sendPostedEvents(window, QEvent.DeferredDelete)
                APP.processEvents()
