"""Profile gate, ten-slot persistence and bilingual in-window navigation."""
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from test_desktop import APP
from test_live_window import SilentAudio
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QMessageBox
from apps.maat_rpg import session_shared as shared
from gui.live_window import LiveWindow


class ProfileSelectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='maat-profile-selection-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        paths = patch.multiple(shared, BASE_APP_SUPPORT_DIR=self.root,
            PROFILES_DIR=self.root/'profiles',
            PROFILE_MANAGER_STATE_PATH=self.root/'state/profile_manager_state.json')
        paths.start(); self.addCleanup(paths.stop)
        env = patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT': str(self.root)})
        env.start(); self.addCleanup(env.stop)
        shared.write_application_language('de')
        self.windows = []
        self.addCleanup(self.close_windows)

    def close_windows(self):
        for w in self.windows:
            w.game.shutdown(); w.close(); w.deleteLater()
            QCoreApplication.sendPostedEvents(w, QEvent.DeferredDelete)
        APP.processEvents()

    def window(self, audio=None):
        w = LiveWindow(audio=audio or SilentAudio())
        self.windows.append(w)
        w.show(); APP.processEvents()
        return w

    def ready(self, w):
        until = time.monotonic() + 12
        while not w.game.ready and time.monotonic() < until:
            APP.processEvents(); time.sleep(.01)
        self.assertTrue(w.game.ready)
        APP.processEvents(); w.ki_dialog.hide()

    def test_title_then_ten_profiles_then_language_and_worker(self):
        shared.write_application_language('en')
        w = self.window()
        self.assertEqual(w.phase, 'title')
        self.assertIsNone(w.game.process)
        self.assertTrue(w.title_idle.isActive())
        self.assertFalse(w.navigation_scroll.isVisible())
        self.assertEqual(w.title_screen.start_button.text(), 'PRESS ENTER TO PLAY')
        with patch.object(w.game, 'load_model') as load:
            w.prepare_startup_model()
            w.request_title_start()
            self.assertEqual(w.phase, 'profiles')
            self.assertEqual(len(w.profile_screen.cards), 0)
            self.assertFalse(w.title_idle.isActive())
            self.assertIsNone(w.game.process)
            self.assertFalse(shared.profile_slot_root(10).exists())
            self.assertFalse(hasattr(w.profile_screen, 'language_buttons'))
            self.assertEqual(w.profile_screen.heading.text(), 'Choose your profile')
            self.assertEqual(w.profile_screen.create_button.text(), '+ New profile')
            with patch('gui.live_window.QInputDialog.getText', return_value=('My Llama adventure', True)):
                w.profile_screen.create_button.click()
            self.assertEqual(w.phase, 'title')
            self.ready(w)
            self.assertEqual(shared.active_profile_slot(), 1)
            self.assertEqual(w.game.get_snapshot().language, 'en')
            self.assertEqual(w.game.get_snapshot().profile_name, 'My Llama adventure')
            self.assertEqual(w.profile_choice_button.text(), 'Choose profile')
            load.assert_not_called()

    def test_overview_reads_class_and_statistics_without_changing_saves(self):
        shared.write_application_language('en')
        shared.write_profile_settings(4, {'language':'de'})
        shared.write_profile_settings(10, {'language':'en'})
        shared.write_profile_manager_state({'active_profile':10})
        state = shared.profile_slot_root(4)/'state/battle_state.json'
        state.write_text(json.dumps(dict(player={'level':42}, hero_class={'selected':'magier'},
            stats={'fights_total':137,'fights_won':123,'boss_wins':4},
            dungeon_runs={'0':{'attempts':7,'completed':5}, '1':{'attempts':2,'completed':1}},
            dungeon_plus={'best_wave':18})))
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        w = self.window(); w.request_title_start()
        row = w.profile_screen.cards[4]
        self.assertEqual(set(w.profile_screen.cards), {4, 10})
        for index in range(w.profile_screen.grid.count()):
            self.assertEqual(w.profile_screen.grid.getItemPosition(index)[1], 0)
        self.assertIn('Level 42', row['klass'].text())
        self.assertIn('Mage', row['klass'].text())
        self.assertIn('123', row['stats'].text())
        self.assertIn('137', row['stats'].text())
        self.assertIn('6/9', row['stats'].text())
        self.assertIn('18', row['stats'].text())
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        w.profile_screen.set_language('de')
        self.assertIn('Magier', w.profile_screen.cards[4]['klass'].text())
        w.cancel_profile_choice()
        self.assertEqual(w.phase, 'title')
        w.request_title_start()
        self.assertEqual(w.phase, 'profiles')

    def test_settings_same_profile_keeps_worker_later_title_skips_choice(self):
        shared.write_profile_settings(1, {'language':'de'})
        w = self.window(); w.request_title_start(); w.choose_profile(1)
        self.ready(w)
        w.model_ready = True; w.prepare_startup_model()
        self.assertEqual(w.phase, 'menu')
        process = w.game.process
        w.navigate(4)
        self.assertFalse(hasattr(w, 'profiles'))
        self.assertFalse(hasattr(w, 'delete_profile_button'))
        w.profile_choice_button.click()
        self.assertEqual(w.phase, 'profiles')
        w.choose_profile(1)
        self.assertEqual(w.stack.currentIndex(), 4)
        self.assertIs(w.game.process, process)
        self.assertTrue(w.model_ready)
        w.show_title(); w.request_title_start()
        self.assertEqual(w.phase, 'menu')
        w.navigate(4); w.show_profile_choice()
        shared.write_profile_settings(9, {'language':'en'})
        w._startup_model_attempted = w._startup_model_failed = True
        w.choose_profile(9)
        self.ready(w)
        self.assertEqual(w.game._profile_slot(), 9)
        self.assertEqual(w.game.get_snapshot().language, 'de')
        self.assertFalse(w._startup_model_failed)
        self.assertFalse(w.model_ready)
        w.model_ready = True; w.prepare_startup_model()
        self.assertEqual(w.phase, 'menu')

    def test_profile_switch_is_blocked_during_combat_prompt_and_stream(self):
        w = self.window()
        for field, value in [('busy', True), ('prompt_id', 'choice-1')]:
            with patch.object(w.game, field, value):
                w.show_profile_choice()
                self.assertEqual(w.phase, 'title')
        for field in ('_battle_active', '_encounter_intro', '_active_minigame'):
            with patch.object(w, field, True):
                w.show_profile_choice()
                self.assertEqual(w.phase, 'title')
        w.text_stream.append('Eine laufende Nachricht')
        w.show_profile_choice()
        self.assertEqual(w.phase, 'title')

    def test_delete_on_startup_requires_confirmation_and_preserves_other_slots(self):
        shared.write_profile_settings(10, {'language':'en'})
        shared.write_profile_settings(3, {'language':'de'})
        shared.write_profile_manager_state({'active_profile':10})
        w = self.window(); w.request_title_start()
        with patch('gui.live_window.QMessageBox.question', return_value=QMessageBox.No):
            w.delete_profile(10)
        self.assertTrue(shared.profile_slot_root(10).exists())
        with patch('gui.live_window.QMessageBox.question', return_value=QMessageBox.Yes):
            w.delete_profile(10)
        self.assertFalse(shared.profile_slot_root(10).exists())
        self.assertTrue(shared.profile_slot_root(3).exists())
        self.assertEqual(shared.active_profile_slot(), 1)
        self.assertEqual(w.phase, 'profiles')
        self.assertIsNone(w.game.process)
        self.assertEqual(set(w.profile_screen.cards), {3})
        self.assertTrue(w.profile_screen.create_button.isEnabled())
        self.assertEqual(len(shared.profile_labels('de')), 10)
        self.assertIn('1-10', shared.profile_text('en')['prompt'])

    def test_rename_keeps_settings_model_and_save_and_survives_a_new_session(self):
        from test_gui_language import ObservedAudio
        audio = ObservedAudio()
        shared.write_profile_settings(1, {'language':'de', 'gui_volume':35})
        root = shared.profile_slot_root(1)
        (root/'data').mkdir()
        model = root/'data/model_override.txt'
        model.write_text('/Models/Meta-Llama-3.1-8B-Q4_K_M.gguf')
        state = root/'state/battle_state.json'
        state.write_text(json.dumps({'player':{'level':23}}))
        before = {p:p.read_bytes() for p in (shared.profile_settings_path(1), state, model)}
        w = self.window(audio); w.request_title_start(); w.choose_profile(1); self.ready(w)
        w.model_ready = True; w.prepare_startup_model(); w.navigate(4); w.show_profile_choice()
        process = w.game.process
        self.assertEqual(audio.playing, 'de')
        starts = list(audio.starts)
        before = {p:p.read_bytes() for p in before}
        with patch('gui.live_window.QInputDialog.getText', return_value=('Äon & Llama <3', True)):
            w.profile_screen.cards[1]['rename'].click()
        self.assertEqual(w.game.get_snapshot().profile_name, 'Äon & Llama <3')
        self.assertEqual(audio.playing, 'de')
        self.assertEqual(audio.starts, starts)
        self.assertIs(w.game.process, process)
        self.assertTrue(w.model_ready)
        self.assertEqual(before, {p:p.read_bytes() for p in before})
        w.profile_screen.set_language('en')
        self.assertEqual(w.profile_screen.cards[1]['name'].text(), 'Äon & Llama <3')
        self.assertEqual(w.profile_screen.cards[1]['model'].text(), 'Model: Meta-Llama-3.1-8B-Q4_K_M.gguf')
        from apps.maat_rpg.session_controller import MaatRpgSession
        self.assertEqual(MaatRpgSession().get_snapshot().profile_name, 'Äon & Llama <3')

    def test_startup_rename_and_profile_refresh_keep_menu_music_without_restarting(self):
        from test_gui_language import ObservedAudio
        for language in ('de', 'en'):
            with self.subTest(language=language):
                shared.write_application_language(language)
                shared.set_profile_name(1, 'First journey')
                shared.set_profile_name(2, 'Second journey')
                audio = ObservedAudio()
                w = self.window(audio); w.request_title_start()
                self.assertEqual(audio.playing, language)
                starts = list(audio.starts)
                for slot in (1, 2):
                    def rename_dialog(*args, **kwargs):
                        # A modal dialog still processes background UI updates.
                        w.game._emit_snapshot()
                        APP.processEvents()
                        self.assertEqual(audio.playing, language)
                        return f'Renamed {slot}', True
                    with patch('gui.live_window.QInputDialog.getText', side_effect=rename_dialog):
                        w.rename_profile(slot)
                    self.assertEqual(w.profile_screen.cards[slot]['name'].text(), f'Renamed {slot}')
                    self.assertEqual(audio.playing, language)
                    self.assertEqual(audio.starts, starts)
                w.apply_audio_settings()
                self.assertEqual(audio.playing, language)
                self.assertEqual(audio.starts, starts)
                self.assertEqual(w.phase, 'profiles')
                self.assertIsNone(w.game.process)
                w.close()

    def test_music_continues_from_pyramid_through_profile_launch_and_later_switch(self):
        from test_gui_language import ObservedAudio
        for language in ('de', 'en'):
            with self.subTest(language=language):
                shared.write_application_language(language)
                shared.set_profile_name(1, 'First journey')
                shared.set_profile_name(2, 'Second journey')
                audio = ObservedAudio()
                w = self.window(audio)
                self.assertEqual(audio.playing, language)
                starts = list(audio.starts)
                w.request_title_start()
                self.assertEqual(w.phase, 'profiles')
                self.assertEqual(audio.starts, starts)
                w.choose_profile(1); self.ready(w)
                self.assertEqual(audio.playing, language)
                self.assertEqual(audio.starts, starts)
                # Finish the model-loading gate without loading a GGUF in tests.
                w.ki_dialog.hide(); w.model_ready = True; w.prepare_startup_model()
                self.assertEqual(w.phase, 'menu')
                self.assertEqual(audio.starts, starts)
                w.navigate(4); w.profile_choice_button.click()
                self.assertEqual(w.phase, 'profiles')
                self.assertEqual(audio.starts, starts)
                w.choose_profile(1)  # The current journey keeps its worker.
                self.assertEqual(audio.starts, starts)
                w.profile_choice_button.click(); w.choose_profile(2); self.ready(w)
                w.ki_dialog.hide(); w.model_ready = True; w.prepare_startup_model()
                self.assertEqual(w.phase, 'menu')
                self.assertEqual(audio.playing, language)
                self.assertEqual(audio.starts, starts)
                w.close()

    def test_model_names_are_profile_specific_and_refresh_after_change(self):
        for slot, path in [(2, '/Models/My Llama.gguf'), (7, 'C:\\Models\\Qwen3-14B.gguf')]:
            shared.write_profile_settings(slot, {'language':'en'})
            folder=shared.profile_slot_root(slot)/'data'; folder.mkdir()
            (folder/'model_override.txt').write_text(path)
        w=self.window(); w.request_title_start(); w.profile_screen.set_language('en')
        self.assertEqual(w.profile_screen.cards[2]['model'].text(), 'Model: My Llama.gguf')
        self.assertEqual(w.profile_screen.cards[7]['model'].text(), 'Model: Qwen3-14B.gguf')
        (shared.profile_slot_root(7)/'data/model_override.txt').write_text('/Models/Gemma.gguf')
        w.profile_screen.refresh()
        self.assertEqual(w.profile_screen.cards[7]['model'].text(), 'Model: Gemma.gguf')

    def test_cancel_invalid_names_and_full_capacity_do_not_overwrite_profiles(self):
        w=self.window(); w.request_title_start()
        with patch('gui.live_window.QInputDialog.getText', return_value=('Cancelled', False)):
            w.create_profile()
        self.assertEqual(shared.existing_profile_slots(), [])
        for bad in ('', '   ', 'x'*49, 'two\nlines'):
            with self.assertRaises(ValueError): shared.create_profile(bad)
        self.assertEqual(shared.existing_profile_slots(), [])
        for slot in range(1,11):
            self.assertEqual(shared.create_profile(f'Adventure {slot}'), slot)
        before = {p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with self.assertRaises(ValueError): shared.create_profile('Too many')
        self.assertEqual(before, {p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        w.profile_screen.refresh()
        self.assertEqual(len(w.profile_screen.cards),10)
        self.assertFalse(w.profile_screen.create_button.isEnabled())
        self.assertEqual(w.profile_screen.grid.columnCount(),1)
        w.choose_profile(10)
        self.assertEqual(w.phase,'title')
        self.ready(w)
        self.assertEqual(w.game.get_snapshot().profile_name,'Adventure 10')
        self.assertEqual(shared.active_profile_slot(),10)

    def test_shared_models_and_manager_file_do_not_create_a_phantom_profile(self):
        (self.root/'models').mkdir()
        (self.root/'models/shared.gguf').write_bytes(b'placeholder')
        shared.write_profile_manager_state({'active_profile':1})
        self.assertEqual(shared.existing_profile_slots(), [])
        self.assertEqual(shared.create_profile('First journey'),1)
        self.assertEqual(shared.existing_profile_slots(), [1])
