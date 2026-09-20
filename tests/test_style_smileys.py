"""Independent emoji/ASCII preferences through profile UI and generation hooks."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
from PySide6.QtCore import QCoreApplication, QEvent
from apps.maat_rpg import session_shared as shared
from gui.plugin_settings import PluginSettingsPanel
from gui.desktop import STYLE
from shared.core.ai_plugin_settings import DEFAULTS, STYLE_DEFAULTS, begin_turn
from shared.core.maat_style import build_style_prompt
from shared.core.thinking_mode import prepare_generation_messages
import test_ai_plugins as helpers
from test_settings_scroll import wheel


class StyleSmileyTests(unittest.TestCase):
    def test_bilingual_modes_are_independent_and_off_does_not_inject_them(self):
        for language in ('de','en'):
            emoji_phrases = (('keine Emojis', 'höchstens ein passendes Emoji', 'mehrere passende Emojis')
                             if language=='de' else ('Do not use emojis', 'at most one fitting emoji', 'several fitting emojis'))
            classic_phrases = (('keine klassischen ASCII-Smileys', 'höchstens einen passenden klassischen ASCII-Smiley', 'ASCII-Smileys in lockeren oder spielerischen Antworten häufiger')
                               if language=='de' else ('Do not use ASCII smileys', 'at most one fitting ASCII smiley', 'ASCII smileys more freely'))
            for i, emoji in enumerate(('none','few','many')):
                for j, classic in enumerate(('none','few','many')):
                    settings = dict(DEFAULTS, maat_style_enabled=True, style_emoji_mode=emoji, style_old_smiley_mode=classic)
                    prompt,state = build_style_prompt(settings,'Hallo :D',language=language)
                    self.assertEqual((state['emoji_mode'],state['old_smiley_mode']),(emoji,classic))
                    self.assertIn(emoji_phrases[i],prompt);self.assertIn(classic_phrases[j],prompt)
                    self.assertIn('^^',prompt)
                    for k, phrase in enumerate(emoji_phrases):
                        if k != i:self.assertNotIn(phrase,prompt)
                    self.assertIn('Code und Zitate' if language=='de' else 'code and quotations',prompt)
                    settings['maat_style_enabled'] = False
                    self.assertEqual(build_style_prompt(settings,'Hi!',language=language)[0],'')

    def test_updated_preferences_reach_next_turn_without_stacking_old_instructions(self):
        settings = dict(DEFAULTS, **STYLE_DEFAULTS, maat_style_enabled=True)
        context={'pm':helpers.manager()}
        with patch('shared.core.ai_plugin_settings.load_settings',side_effect=lambda:dict(settings)):
            begin_turn(context,'Hallo')
            messages=prepare_generation_messages([{'role':'user','content':'Hallo'}],language='de',runtime_context=context)
            self.assertIn('höchstens ein passendes Emoji',str(messages))
            settings.update(style_emoji_mode='none',style_old_smiley_mode='many')
            old=prepare_generation_messages(messages,language='de',runtime_context=context)
            self.assertIn('höchstens ein passendes Emoji',str(old))
            begin_turn(context,'Weiter')
            new=prepare_generation_messages(messages,language='de',runtime_context=context)
            self.assertEqual(str(new).count('[MAAT_STYLE]'),1)
            self.assertIn('Verwende keine Emojis',str(new));self.assertIn('Antworten häufiger',str(new))
            self.assertNotIn('höchstens ein passendes Emoji',str(new))

    def test_dialog_profile_persistence_language_and_wheel_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            paths={i:Path(directory)/f'profile{i}.json' for i in (1,2)}
            slot=[1]
            with patch.object(shared,'profile_settings_path',side_effect=paths.get):
                save=Mock(side_effect=lambda update:shared.write_profile_settings(slot[0],update))
                dialog=PluginSettingsPanel(lambda:shared.load_profile_settings(slot[0]),save)
                dialog.setStyleSheet(STYLE)
                try:
                    dialog.show();APP.processEvents()
                    self.assertFalse(dialog.style_options.isEnabled())
                    self.assertEqual({key:combo.currentData() for key,combo in dialog.style_combos.items()},
                                     {key:STYLE_DEFAULTS[key] for key in dialog.style_combos})
                    save.assert_not_called()
                    dialog.boxes['maat_style_enabled'].click()
                    self.assertTrue(dialog.style_options.isEnabled())
                    emoji=dialog.style_combos['style_emoji_mode'];classic=dialog.style_combos['style_old_smiley_mode']
                    emoji.setCurrentIndex(emoji.findData('none'));classic.setCurrentIndex(classic.findData('many'))
                    self.assertEqual(shared.load_profile_settings(1)['style_emoji_mode'],'none')
                    self.assertEqual(shared.load_profile_settings(1)['style_old_smiley_mode'],'many')
                    calls=save.call_count
                    for language in ('en','de'):
                        dialog.set_language(language);dialog.refresh();APP.processEvents()
                        self.assertEqual(classic.currentText(),'Many' if language=='en' else 'Viele')
                        self.assertEqual(emoji.currentData(),'none')
                        for control in (emoji,classic):
                            dialog.scroll.ensureWidgetVisible(control);control.setFocus()
                            wheel(control);wheel(control,trackpad=True)
                        self.assertEqual(classic.currentData(),'many');self.assertEqual(emoji.currentData(),'none')
                    self.assertEqual(save.call_count,calls)
                    slot[0]=2;dialog.refresh()
                    self.assertFalse(dialog.style_options.isEnabled())
                    self.assertEqual({key:combo.currentData() for key,combo in dialog.style_combos.items()},
                                     {key:STYLE_DEFAULTS[key] for key in dialog.style_combos})
                    slot[0]=1;dialog.refresh()
                    self.assertTrue(dialog.style_options.isEnabled());self.assertEqual(classic.currentData(),'many')
                    self.assertEqual(save.call_count,calls)
                    # Persist across dialog reopen, not just within the controls.
                    dialog.close()
                    again=PluginSettingsPanel(lambda:shared.load_profile_settings(1),save)
                    self.assertEqual(again.style_combos['style_old_smiley_mode'].currentData(),'many')
                    again.close();again.deleteLater()
                    if os.environ.get('MAAT_STYLE_SCREENSHOTS'):
                        target=Path(os.environ['MAAT_STYLE_SCREENSHOTS']);target.mkdir(parents=True,exist_ok=True)
                        dialog.resize(700,850);dialog.show();APP.processEvents()
                        for language in ('de','en'):
                            dialog.set_language(language);APP.processEvents()
                            tile=dialog.style_options.parentWidget()
                            dialog.scroll.verticalScrollBar().setValue(tile.y())
                            APP.processEvents()
                            self.assertTrue(dialog.grab().save(str(target/f'style-smileys-{language}.png')))
                finally:
                    dialog.close();dialog.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)


if __name__=='__main__':unittest.main()
