"""UI-language defaults and a translation follow-up keep the actual MAAT task."""
from copy import deepcopy
import unittest
from unittest.mock import Mock,patch
from test_desktop import ROOT
from apps.maat_rpg.session_bootstrap import load_yaml_profile,build_systemprompt,bootstrap_rpg_session
from shared.core.reply_language import requested_language,language_followup,MARKER
from shared.core.thinking_mode import prepare_generation_messages
from shared.core.maat_reference import generation_reference
from shared.core.gguf_chat import prepare_messages

GAME=ROOT/'maatos'


class ReplyLanguageTests(unittest.TestCase):
    def setUp(self):
        self.profiles={lang:load_yaml_profile(str(GAME),lang)[0] for lang in ('de','en')}
        self.context={'profile':self.profiles['en'],'profile_variants':self.profiles}
        self.history=[{'role':'system','content':build_systemprompt(self.profiles['en'])},
                      {'role':'user','content':'maat wert von licht'},
                      {'role':'assistant','content':'My assessment: Harmony: 7 out of 10.'}]

    def prepare(self,messages,language='en'):
        with patch('shared.core.thinking_mode._load_settings',return_value={}), \
             patch('shared.core.rpg_generation_context._load_settings',return_value={}):
            return prepare_generation_messages(messages,language=language,runtime_context=self.context)

    def test_game_language_is_default_even_for_a_german_question(self):
        messages=self.prepare(self.history[:2])
        self.assertEqual(messages[0]['content'],build_systemprompt(self.profiles['en']))
        system='\n'.join(m['content'] for m in messages if m['role']=='system')
        self.assertIn('Harmony: 5 out of 10',system)
        self.assertNotIn('Harmonie: 5 von 10',system)
        self.assertNotIn(MARKER,system)

    def test_translation_keeps_topic_reference_and_only_changes_generation_language(self):
        previous=deepcopy(self.context)
        for request in ('bitte auf deutsch','Bitte Deutsch','Kannst du das bitte auf Deutsch schreiben?',
                        'Please in German','German please'):
            original=self.history+[{'role':'user','content':request}]
            messages=self.prepare(original)
            with self.subTest(request=request):
                self.assertTrue(language_followup(request))
                self.assertEqual(messages[0]['content'],build_systemprompt(self.profiles['de']))
                system='\n'.join(m['content'] for m in messages if m['role']=='system')
                self.assertIn('Harmonie: 5 von 10',system)
                self.assertIn('Übersetze die vorherige Antwort zum gleichen Thema',system)
                self.assertIn('keine neue Selbstdarstellung',system)
                self.assertIn('Einzelbewertungen',system)
                self.assertNotIn('Harmony: 5 out of 10',system)
                self.assertEqual([m for m in messages if m['role']!='system'],original[1:])
                for architecture in ('llama','qwen3','gemma3','gemma4'):
                    wire=prepare_messages(messages,architecture)
                    self.assertEqual(str(wire).count(MARKER),1)
                    self.assertIn('Harmonie: 5 von 10',str(wire))
        self.assertEqual(self.context,previous)

    def test_next_regular_question_returns_to_game_language_and_removes_stale_overrides(self):
        german=self.prepare(self.history+[{'role':'user','content':'bitte auf Deutsch'}])
        german += [{'role':'assistant','content':'Meine Einschätzung: Harmonie: 7 von 10.'},
                   {'role':'user','content':'maat wert von Berlin'}]
        english=self.prepare(german)
        system='\n'.join(m['content'] for m in english if m['role']=='system')
        self.assertEqual(english[0]['content'],build_systemprompt(self.profiles['en']))
        self.assertNotIn(MARKER,system)
        self.assertNotIn('Harmonie: 5 von 10',system)
        self.assertIn('Harmony: 5 out of 10',system)

    def test_repeated_translation_retains_formula_but_translation_of_smalltalk_does_not_add_it(self):
        for question in ('MAAT-Wert von Licht','Calculate PLP'):
            history=[{'role':'user','content':question},{'role':'assistant','content':'An answer'},
                     {'role':'user','content':'bitte auf Deutsch'},{'role':'assistant','content':'Eine Antwort'},
                     {'role':'user','content':'English please'}]
            block=generation_reference(history,self.context)
            self.assertIn('PLP=P*K/(O+ΔE)' if 'PLP' in question else '[MAAT]',block)
        self.assertIsNone(generation_reference([{'role':'user','content':'Hallo'},
            {'role':'assistant','content':'Hello'},{'role':'user','content':'bitte auf Deutsch'}],self.context))
        self.assertFalse(language_followup('Bitte auf Deutsch über Berlin schreiben'))
        self.assertIsNone(requested_language('The phrase "in German" appears in this quote.'))
        self.assertIsNone(requested_language('Ich lerne Deutsch.'))

    def test_bootstrap_supplies_both_variants_without_changing_selected_profile(self):
        with patch('apps.maat_rpg.session_bootstrap.load_plugin_manager',return_value=(None,[])):
            boot=bootstrap_rpg_session(root=str(GAME),language='en',mods_plugins_dir='',
                system_prompt_rpg_appendix='',rpg_mode=False)
        self.assertEqual(boot.language,'en')
        self.assertIs(boot.profile,boot.context['profile_variants']['en'])
        self.assertIn('Harmonie: 5 von 10',boot.context['profile_variants']['de']['maat_reference'])
