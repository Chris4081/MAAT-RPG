"""Full Web Core style controls: effective prompts, precedence and profile UI."""
import contextlib
from copy import deepcopy
import io
import logging
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
from PySide6.QtCore import QCoreApplication, QEvent
from apps.maat_rpg import session_shared as shared
from gui.desktop import STYLE
from gui.plugin_settings import PluginSettingsPanel, STYLE_MODES
from shared.core.ai_plugin_settings import DEFAULTS, SNAPSHOT, begin_turn
from shared.core.maat_style import (STYLE_DEFAULTS, STYLE_CHOICES, STYLE_CHECKS,
    build_style_prompt, style_state, detect_intent, diagnostic_text)
from shared.core.reply_style import build_reply_style_prompt
from shared.core.thinking_mode import prepare_generation_messages
from shared.core import streaming
from shared.plugins.maat_formatting.plugin_main import Plugin as Formatting
from shared.plugins.maat_style.plugin_main import Plugin as Style
from test_settings_scroll import wheel
import test_ai_plugins as helpers


class FullStyleTests(unittest.TestCase):
    def settings(self, **changes):
        return dict(DEFAULTS, **STYLE_DEFAULTS) | {'maat_style_enabled':True} | changes

    def test_every_choice_changes_the_prompt_in_both_languages(self):
        for language in ('de','en'):
            for key, choices in STYLE_CHOICES.items():
                prompts = set()
                for value, _ in choices:
                    settings = self.settings(style_tone_auto=False, **{key:value})
                    prompt, state = build_style_prompt(settings, 'Tell me about Terra.', language=language)
                    self.assertEqual(state[key.removeprefix('style_')], value)
                    self.assertIn('RPG', prompt)
                    self.assertIn('preserve code and quotations' if language=='en' else 'erhalte Code und Zitate', prompt)
                    self.assertNotIn('max_words=', prompt)
                    prompts.add(prompt)
                self.assertEqual(len(prompts), len(choices), (language,key))

    def test_fixed_tone_auto_tone_short_greeting_and_bad_saved_values(self):
        for query, kind, tone in [('Hallo','greeting','friendly'), ('Hello','greeting','friendly'),
            ('Hallo Python-Fehler','technical','scientific'), ('Hi, why?','analysis','friendly'),
            ('Write a story','creative','enthusiastic'), ('Ich bin traurig','emotional','mentor'),
            ('I am sad','emotional','mentor'), ('Explain consciousness','philosophical','philosophical')]:
            self.assertEqual(detect_intent(query),kind,query)
            self.assertEqual(style_state(self.settings(),query)['tone_mode'],tone,query)
            self.assertEqual(style_state(self.settings(style_tone_auto=False,style_tone_mode='neutral'),query)['tone_mode'],'neutral')
        for language in ('de','en'):
            on, _ = build_style_prompt(self.settings(), 'Hello', language=language)
            off, state = build_style_prompt(self.settings(style_greeting_override=False), 'Hello', language=language)
            phrase = 'A greeting-only reply may stay short' if language=='en' else 'Eine reine Begrüßung darf'
            self.assertIn(phrase, on); self.assertNotIn(phrase, off)
            self.assertFalse(state['rules']['skip_deep_regulators'])
        invalid = self.settings(**{key:'invalid' for key in STYLE_CHOICES})
        state = style_state(invalid)
        for key in STYLE_CHOICES:self.assertEqual(state[key.removeprefix('style_')], STYLE_DEFAULTS[key])

    def test_no_competing_length_question_or_heading_list_rules(self):
        for language in ('de','en'):
          for mode in ('short','normal','chatty','very_chatty'):
            settings = self.settings(reply_style_mode=mode, reply_style_min_tokens=300,reply_style_max_tokens=600,
                reply_style_force_length=True, reply_style_end_question=False,
                style_density_mode='airy', style_heading_mode='none', style_list_mode='none')
            style, _ = build_style_prompt(settings,'Explain the Python error.',language=language)
            reply = build_reply_style_prompt(settings,language)
            formatter = Formatting().generation_prompt(language=language,context={SNAPSHOT:settings})
            self.assertNotIn('Wörtern',style); self.assertNotIn('words unless',style)
            self.assertNotIn('End every conversational reply' if language=='en' else 'Beende jede Gesprächsantwort',style)
            self.assertIn('Do not routinely end with a question' if language=='en' else 'nicht routinemäßig mit einer Frage',reply)
            self.assertIn('300–600',reply)
            self.assertIn('weiche Untergrenze' if language=='de' else 'soft lower target',reply)
            self.assertNotIn('Markdown-Überschriften' if language=='de' else 'Markdown headings',formatter)
            self.assertNotIn('Listen' if language=='de' else 'lists',formatter)
            self.assertIn('MAAT Style',formatter)
            settings['reply_style_enabled']=False
            self.assertIn('Wörtern' if language=='de' else 'words unless',build_style_prompt(settings,'Explain Python',language=language)[0])
            settings['maat_style_enabled']=False
            self.assertEqual(build_style_prompt(settings,'Hi',language=language)[0],'')
            self.assertIn('Markdown-Überschriften' if language=='de' else 'Markdown headings',
                Formatting().generation_prompt(language=language,context={SNAPSHOT:settings}))

    def test_all_controls_reach_both_adapters_once_and_snapshot_next_turn(self):
        for backend in ('llama','llama_intel'):
          for language in ('de','en'):
            settings=self.settings(style_tone_auto=False, style_tone_mode='scientific',style_opening_mode='personal',
                style_density_mode='airy',style_heading_mode='none',style_list_mode='none')
            pm=helpers.manager();context={'pm':pm,'memory_perspective':'companion'}
            history=[{'role':'system','content':'You are Maatis on Terra.'},{'role':'user','content':'Explain Terra.'}]
            before=deepcopy(history);shown=[]
            def backend_tokens(llm,messages,perf):
                self.assertEqual(llm['backend'],backend)
                self.assertEqual(str(messages).count('[MAAT_STYLE]'),1)
                style = next(m['content'] for m in messages if m['content'].startswith('[MAAT_STYLE]'))
                self.assertIn('Persönliche Einstiege' if language=='de' else 'Personal openings',style)
                self.assertIn('Keine Überschriften' if language=='de' else 'Do not use headings',style)
                self.assertEqual(perf['max_tokens'],220)
                yield 'Hello '
                self.assertEqual(shown,['Hello '])
                yield 'Terra!'
            with patch('shared.core.ai_plugin_settings.load_settings',side_effect=lambda:dict(settings)), \
                 patch.object(streaming,'backend_stream_chat',side_effect=backend_tokens), \
                 patch.object(streaming,'key_pressed',return_value=False), \
                 patch.object(streaming,'_stream_lang',return_value=language),contextlib.redirect_stdout(io.StringIO()):
                begin_turn(context,history[-1]['content'])
                shown.extend(streaming.stream_chat_completion({'backend':backend},history,
                    {'max_tokens':220,'gui_mode':True,'raise_errors':True},runtime_context=context))
                settings['style_opening_mode']='direct'
                old=prepare_generation_messages(history,language=language,runtime_context=context)
                self.assertIn('personal',str(pm.plugins_chat[1].last_state))
                begin_turn(context,'Explain Terra.')
                new=prepare_generation_messages(old,language=language,runtime_context=context)
                self.assertEqual(pm.plugins_chat[1].last_state['opening_mode'],'direct')
                self.assertEqual(str(new).count('[MAAT_STYLE]'),1)
            self.assertEqual(history,before);self.assertEqual(''.join(shown),'Hello Terra!')

    def test_debug_is_local_and_does_not_inject_or_log_private_text(self):
        secret='Private test phrase xyz123. Explain Python.'
        plugin=Style();settings=self.settings(style_debug=True)
        context={SNAPSHOT:settings,'_ai_plugin_query':secret}
        with self.assertLogs('maat.gui.lifecycle',logging.INFO) as logs:
            prompt=plugin.generation_prompt(language='de',context=context)
        self.assertIn('Technik',' '.join(logs.output));self.assertNotIn(secret,' '.join(logs.output))
        self.assertNotIn('xyz123',prompt)
        for language in ('de','en'):
            self.assertNotIn(secret,diagnostic_text(settings,secret,language))
        with patch('logging.Logger.info') as log:
            plugin.generation_prompt(context={SNAPSHOT:self.settings(style_debug=False)})
            plugin.generation_prompt(context={SNAPSHOT:self.settings(style_debug=True,maat_style_enabled=False)})
            log.assert_not_called()

    def test_full_panel_persists_all_values_switches_profiles_and_translates(self):
        with tempfile.TemporaryDirectory() as directory:
            paths={i:Path(directory)/f'{i}.json' for i in (1,2)};slot=[1]
            with patch.object(shared,'profile_settings_path',side_effect=paths.get):
                save=Mock(side_effect=lambda data:shared.write_profile_settings(slot[0],data))
                panel=PluginSettingsPanel(lambda:shared.load_profile_settings(slot[0]),save)
                panel.setStyleSheet(STYLE);panel.resize(700,950);panel.show();APP.processEvents()
                try:
                    self.assertEqual(set(panel.style_combos)|set(panel.style_checks),set(STYLE_DEFAULTS))
                    save.assert_not_called()
                    panel.boxes['maat_style_enabled'].click()
                    for key,combo in panel.style_combos.items():
                        for value,_ in STYLE_CHOICES[key]:
                            combo.setCurrentIndex(combo.findData(value))
                            self.assertEqual(shared.load_profile_settings(1)[key],value)
                    for key,box in panel.style_checks.items():
                        box.setChecked(not STYLE_DEFAULTS[key])
                        self.assertEqual(shared.load_profile_settings(1)[key],not STYLE_DEFAULTS[key])
                    calls=save.call_count
                    panel.style_example.setText('Explain a Python error xyz123.')
                    self.assertEqual(save.call_count,calls)
                    self.assertNotIn('xyz123',paths[1].read_text())
                    for language in ('de','en'):
                        panel.set_language(language);APP.processEvents()
                        for key,combo in panel.style_combos.items():
                            self.assertEqual(combo.currentText(),STYLE_CHOICES[key][-1][1][language=='en'])
                            panel.scroll.ensureWidgetVisible(combo);combo.setFocus()
                            wheel(combo);wheel(combo,trackpad=True)
                            self.assertEqual(combo.currentData(),STYLE_CHOICES[key][-1][0])
                        self.assertIn('Technical' if language=='en' else 'Technik',panel.style_preview.text())
                    self.assertEqual(save.call_count,calls)
                    slot[0]=2;panel.refresh()
                    for key,combo in panel.style_combos.items():self.assertEqual(combo.currentData(),STYLE_DEFAULTS[key])
                    for key,box in panel.style_checks.items():self.assertEqual(box.isChecked(),STYLE_DEFAULTS[key])
                    self.assertTrue(panel.style_debug_panel.isHidden())
                    slot[0]=1;panel.refresh()
                    for key,combo in panel.style_combos.items():self.assertEqual(combo.currentData(),STYLE_CHOICES[key][-1][0])
                    self.assertEqual(save.call_count,calls)
                    panel.close()
                    again=PluginSettingsPanel(lambda:shared.load_profile_settings(1),save)
                    self.assertTrue(again.style_checks['style_debug'].isChecked())
                    self.assertEqual(again.style_combos['style_opening_mode'].currentData(),'personal')
                    again.close();again.deleteLater()
                    if os.environ.get('MAAT_STYLE_SCREENSHOTS'):
                        target=Path(os.environ['MAAT_STYLE_SCREENSHOTS']);target.mkdir(parents=True,exist_ok=True)
                        panel.show()
                        for language in ('de','en'):
                            panel.set_language(language);APP.processEvents()
                            panel.scroll.verticalScrollBar().setValue(panel.style_options.parentWidget().y())
                            APP.processEvents();panel.grab().save(str(target/f'style-full-{language}.png'))
                finally:
                    panel.close();panel.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)

if __name__=='__main__':unittest.main()
