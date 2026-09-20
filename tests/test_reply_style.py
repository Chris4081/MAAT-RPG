"""Reply preferences through profile controls and the actual shared stream path."""
import contextlib
from copy import deepcopy
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
from PySide6.QtCore import QCoreApplication, QEvent
from apps.maat_rpg import session_shared as shared
from gui.desktop import STYLE
from gui.plugin_settings import PluginSettingsPanel
from shared.core.ai_plugin_settings import DEFAULTS, begin_turn
from shared.core.reply_style import DEFAULTS as REPLY_DEFAULTS, PRESETS, OPTIONS, build_reply_style_prompt, normalize_settings
from shared.core.maat_style import build_style_prompt
from shared.core.thinking_mode import prepare_generation_messages
from shared.core import streaming
from test_settings_scroll import wheel
import test_ai_plugins as helpers


class ReplyStyleTests(unittest.TestCase):
    def test_modes_language_switches_and_invalid_saved_values(self):
        for language in ('de', 'en'):
            for mode, (low, high) in PRESETS.items():
                settings = {'reply_style_mode': mode}
                prompt = build_reply_style_prompt(settings, language)
                self.assertIn(f'{low}–{high}', prompt)
                self.assertIn('End every conversational reply' if language == 'en' else 'Beende jede Gesprächsantwort', prompt)
                settings.update({key: False for key, _ in OPTIONS})
                prompt = build_reply_style_prompt(settings, language)
                self.assertNotIn('End every conversational reply' if language == 'en' else 'Beende jede Gesprächsantwort', prompt)
                self.assertNotIn('Respond to the user’s concrete' if language == 'en' else 'Gehe konkret auf', prompt)
                self.assertIn('no optional elaboration' if language == 'en' else 'keine zusätzlichen Ausführungen', prompt)
                self.assertIn('no optional tangents' if language == 'en' else 'keine zusätzlichen Abschweifungen', prompt)
                settings['reply_style_enabled'] = False
                self.assertEqual(build_reply_style_prompt(settings, language), '')
        normalized = normalize_settings({'reply_style_mode': 'invalid', 'reply_style_min_tokens': 'broken',
                                         'reply_style_max_tokens': float('inf')})
        self.assertEqual(normalized, REPLY_DEFAULTS)
        normalized = normalize_settings({'reply_style_min_tokens': 8000, 'reply_style_max_tokens': -10})
        self.assertEqual((normalized['reply_style_min_tokens'], normalized['reply_style_max_tokens']), (2000, 2000))

    def test_maat_style_keeps_smileys_without_competing_word_limits(self):
        settings = dict(DEFAULTS, maat_style_enabled=True, style_old_smiley_mode='many')
        for language in ('de', 'en'):
            prompt, _ = build_style_prompt(settings, 'Hallo', language=language)
            self.assertNotIn('höchstens zwei' if language == 'de' else 'at most two', prompt)
            self.assertNotIn('Wörtern' if language == 'de' else 'words unless', prompt)
            self.assertIn('^^', prompt)
            settings['reply_style_enabled'] = False
            prompt, _ = build_style_prompt(settings, 'Hallo', language=language)
            self.assertIn('Wörtern' if language == 'de' else 'words unless', prompt)
            settings['reply_style_enabled'] = True

    def test_snapshot_deduplication_disable_role_and_explicit_reply_language(self):
        settings = dict(DEFAULTS, **REPLY_DEFAULTS, rpg_context_enabled=False)
        for perspective in ('adventure', 'companion'):
            context = {'pm': helpers.manager(), 'memory_perspective': perspective}
            original = [{'role': 'system', 'content': 'You are Maatis on Terra.'},
                        {'role': 'user', 'content': 'Please reply in English.'}]
            before = deepcopy(original)
            with patch('shared.core.ai_plugin_settings.load_settings', side_effect=lambda: dict(settings)):
                begin_turn(context, original[-1]['content'])
                messages = prepare_generation_messages(original, language='de', runtime_context=context)
                self.assertEqual(original, before)
                self.assertIn('Reply style: Normal.', str(messages))
                self.assertIn('80–180', str(messages))
                settings.update(reply_style_mode='chatty', reply_style_min_tokens=150, reply_style_max_tokens=300)
                same_turn = prepare_generation_messages(messages, language='de', runtime_context=context)
                self.assertIn('80–180', str(same_turn))
                begin_turn(context, original[-1]['content'])
                next_turn = prepare_generation_messages(messages, language='de', runtime_context=context)
                self.assertEqual(str(next_turn).count('[MAAT_REPLY_STYLE]'), 1)
                self.assertIn('150–300', str(next_turn)); self.assertNotIn('80–180', str(next_turn))
                self.assertIn(original[0], next_turn)
                settings['reply_style_enabled'] = False
                begin_turn(context, original[-1]['content'])
                off = prepare_generation_messages(next_turn, language='de', runtime_context=context)
                self.assertNotIn('[MAAT_REPLY_STYLE]', str(off))
            settings = dict(DEFAULTS, **REPLY_DEFAULTS, rpg_context_enabled=False)

    def test_both_gguf_adapters_receive_style_without_buffering_or_mutating_history(self):
        settings = dict(DEFAULTS, **REPLY_DEFAULTS)
        for backend in ('llama', 'llama_intel'):
            for language in ('de', 'en'):
                context = {'pm': helpers.manager()}
                history = [{'role': 'user', 'content': 'Hallo' if language == 'de' else 'Hello'}]
                saved = deepcopy(history)
                emitted = []
                def chunks(llm, messages, perf):
                    self.assertEqual(llm['backend'], backend)
                    self.assertIn('80–180', str(messages))
                    self.assertIn('Antwortstil: Normal' if language == 'de' else 'Reply style: Normal', str(messages))
                    self.assertEqual(perf['max_tokens'], 450)
                    yield 'Hello'
                    self.assertEqual(emitted, ['Hello'])
                    yield ' Terra!'
                with patch('shared.core.ai_plugin_settings.load_settings', return_value=settings), \
                     patch.object(streaming, 'backend_stream_chat', side_effect=chunks), \
                     patch.object(streaming, '_stream_lang', return_value=language), \
                     patch.object(streaming, 'key_pressed', return_value=False), contextlib.redirect_stdout(io.StringIO()):
                    begin_turn(context, history[-1]['content'])
                    emitted.extend(streaming.stream_chat_completion({'backend': backend}, history,
                                   {'gui_mode': True, 'max_tokens': 450, 'raise_errors': True}, runtime_context=context))
                self.assertEqual(history, saved)
                self.assertEqual(emitted, ['Hello', ' Terra!'])

    def test_ui_profile_storage_range_limits_language_and_scrolling(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = {slot: Path(directory)/f'{slot}.json' for slot in (1, 2)}
            slot = [1]
            with patch.object(shared, 'profile_settings_path', side_effect=paths.get):
                save = Mock(side_effect=lambda update: shared.write_profile_settings(slot[0], update))
                panel = PluginSettingsPanel(lambda: shared.load_profile_settings(slot[0]), save)
                panel.setStyleSheet(STYLE); panel.resize(680, 900); panel.show(); APP.processEvents()
                try:
                    self.assertTrue(panel.reply_modes['normal'].isChecked())
                    self.assertTrue(panel.reply_options.isEnabled())
                    self.assertFalse(panel.reply_force.isChecked())
                    self.assertTrue(all(box.isChecked() for box in panel.reply_checks.values()))
                    self.assertEqual((panel.reply_min.value(), panel.reply_max.value()), (80, 180))
                    save.assert_not_called()
                    panel.reply_force.click()
                    self.assertTrue(shared.load_profile_settings(1)['reply_style_force_length'])
                    for mode, bounds in PRESETS.items():
                        panel.reply_modes[mode].click()
                        self.assertEqual((panel.reply_min.value(), panel.reply_max.value()), bounds)
                        self.assertEqual(shared.load_profile_settings(1)['reply_style_mode'], mode)
                    panel.reply_min.setValue(700)
                    self.assertEqual(panel.reply_max.value(), 700)
                    panel.reply_max.setValue(250)
                    self.assertEqual(panel.reply_min.value(), 250)
                    for box in panel.reply_checks.values(): box.click()
                    calls = save.call_count
                    for language in ('en', 'de'):
                        panel.set_language(language); panel.refresh(); APP.processEvents()
                        self.assertEqual(panel.reply_modes['short'].text(), 'Short' if language == 'en' else 'Kurz')
                        self.assertIn('250–250', panel.reply_target.text())
                        self.assertIn('Target length' if language=='en' else 'Zielumfang', panel.reply_target.text())
                        self.assertEqual(panel.reply_force.text(), 'Develop substantive answers' if language=='en' else 'Inhaltliche Antworten vertiefen')
                        for spin in (panel.reply_min, panel.reply_max):
                            panel.scroll.ensureWidgetVisible(spin); spin.setFocus()
                            wheel(spin); wheel(spin, trackpad=True); wheel(spin.lineEdit())
                        self.assertEqual((panel.reply_min.value(), panel.reply_max.value()), (250, 250))
                    self.assertEqual(save.call_count, calls)
                    slot[0] = 2; panel.refresh()
                    self.assertTrue(panel.reply_modes['normal'].isChecked())
                    self.assertFalse(panel.reply_force.isChecked())
                    self.assertTrue(all(box.isChecked() for box in panel.reply_checks.values()))
                    slot[0] = 1; panel.refresh()
                    self.assertTrue(panel.reply_modes['very_chatty'].isChecked())
                    self.assertTrue(panel.reply_force.isChecked())
                    self.assertFalse(any(box.isChecked() for box in panel.reply_checks.values()))
                    self.assertEqual(save.call_count, calls)
                    panel.boxes['reply_style_enabled'].click()
                    self.assertFalse(panel.reply_options.isEnabled())
                    panel.close()
                    again = PluginSettingsPanel(lambda: shared.load_profile_settings(1), save)
                    self.assertFalse(again.reply_options.isEnabled())
                    self.assertTrue(again.reply_force.isChecked())
                    self.assertEqual(again.reply_min.value(), 250)
                    again.close(); again.deleteLater()
                    if os.environ.get('MAAT_REPLY_STYLE_SCREENSHOTS'):
                        panel.boxes['reply_style_enabled'].click()
                        panel.reply_modes['chatty'].click()
                        for box in panel.reply_checks.values(): box.setChecked(True)
                        panel.show()
                        target = Path(os.environ['MAAT_REPLY_STYLE_SCREENSHOTS']); target.mkdir(parents=True, exist_ok=True)
                        for language in ('de', 'en'):
                            panel.set_language(language); APP.processEvents()
                            panel.scroll.verticalScrollBar().setValue(0); APP.processEvents()
                            self.assertTrue(panel.grab().save(str(target/f'reply-style-{language}.png')))
                finally:
                    panel.close(); panel.deleteLater(); QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


if __name__ == '__main__': unittest.main()
