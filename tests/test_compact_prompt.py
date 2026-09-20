"""Small-model prompt budget, formulas, roles and language actually sent to GGUF."""
import io
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from test_desktop import APP,ROOT
from apps.maat_rpg.session_bootstrap import load_yaml_profile,build_systemprompt
from shared.core.companion_prompt import build_companion_prompt
from shared.core.thinking_mode import prepare_generation_messages
from shared.core.gguf_chat import prepare_messages
from shared.plugins.maat_thinking.prompt import build_prompt_block
from shared.core.maat_reference import MARKER,needs_reference,generation_reference
from shared.core.wiki_maat_query import assessment_topics

GAME=ROOT/'maatos'


class CompactPromptTests(unittest.TestCase):
    def test_bilingual_profiles_keep_formulas_and_a_bounded_total(self):
        for language in ('de','en'):
            profile,_,_=load_yaml_profile(str(GAME),language)
            prompt=build_systemprompt(profile)
            self.assertLess(len(prompt),850)
            self.assertIn('MAAT-RPG',prompt);self.assertIn('Terra',prompt)
            self.assertNotIn('[MAAT]',prompt)
            reference=profile['maat_reference']
            formulas='\n'.join(profile['maat_formulas'].values())
            for formula in ('min(R,(H*B*S*V)^(1/4))',
                            'P=H*B*S*V*R','Maat_world=P/ΔE','PLP=P*K/(O+ΔE)',
                            'C(x)=P/(ΔE+ε)','AGI_proximity=P*C*M/(ΔI+ΔE+ΔD)',
                            'AI_CONSCIOUSNESS','MAAT_MASTER=P*K*C/(ΔE+ΔQ+ΔI+ΔD+ε)',
                            'B_universe=∫[P/(ΔE+ΔQ)]d⁴x'):
                self.assertIn(formula,formulas)
            self.assertIn('0.03125',formulas);self.assertIn('0.0625',formulas);self.assertIn('0.025',formulas)
            self.assertIn('(5+6+7+8+9)/5 = 7',reference)
            self.assertEqual(sum([5,6,7,8,9])/5,7)
            self.assertAlmostEqual(.5**5,.03125)
            self.assertAlmostEqual(.5**5/.5,.0625)
            self.assertAlmostEqual(.5**5*.8/(.5+.5),.025)
            manager=SimpleNamespace(generation_system_messages=lambda **kw:[build_prompt_block(100,language)])
            for architecture in ('llama','qwen3'):
                with patch('shared.core.thinking_mode._load_settings',return_value={}), \
                     patch('shared.core.rpg_generation_context._load_settings',return_value={}):
                    messages=prepare_generation_messages([{'role':'system','content':prompt},{'role':'user','content':'MAAT value?'}],
                        language=language,runtime_context={'pm':manager,'profile':profile},llm={'chat_state':{'architecture':architecture}})
                system=prepare_messages(messages,architecture)[0]['content']
                self.assertLess(len(system),3600)
                self.assertEqual(system.count('[MAAT]'),1)
                self.assertEqual(system.count('[MAAT_INTERNAL_QUALITY]'),1)
                self.assertNotIn('WORLD CONTEXT',system);self.assertNotIn('WELTZUSTAND',system)
                for unwanted in ('Maat_world','PLP=','Stability=','0.03125','0.5'):
                    self.assertNotIn(unwanted,system)

    def test_companion_role_gets_reference_only_on_request_in_selected_language(self):
        from gui.game_worker import Runtime
        from shared.core import streaming
        for language in ('de','en'):
            profile,_,_=load_yaml_profile(str(GAME),language)
            runtime=SimpleNamespace(language=language,boot=SimpleNamespace(profile=profile),context={'profile':profile},
                companion=SimpleNamespace(state={'dialogue':[]},save=Mock()),
                llm={'backend':'llama_intel'},perf={},stop_previous_speech=Mock(),
                complete_chat_turn=Mock(),archive_chat=Mock())
            with patch.object(streaming,'backend_stream_chat',return_value=iter(['Who are you?'])) as backend, \
                 patch.object(streaming,'key_pressed',return_value=False),patch('gui.game_worker.emit'),redirect_stdout(io.StringIO()):
                Runtime.maatis_dialogue(runtime,'Calculate PLP')
            sent=backend.call_args.args[1][0]['content']
            self.assertIn('You are Maatis' if language=='en' else 'Du bist Maatis',sent)
            self.assertIn('MAAT-RPG',sent);self.assertNotIn('PLP=P*K/(O+ΔE)',sent)
            self.assertIn('PLP=P*K/(O+ΔE)',str(backend.call_args.args[1]))
            self.assertNotIn('You are MAAT-KI',sent);self.assertNotIn('Du bist MAAT-KI',sent)

    def test_word_variants_share_wiki_topic_and_formula_intent(self):
        aliases=('maat wert','maatwert','MAAT-Wert','MAAT‑Wert','MAAT–Wert','MAAT_Wert',
                 'MAAT Werte','MAAT-Bewertung','MAAT Einschätzung','maatbeurteilung',
                 'MAAT value','maatvalue','MAAT values','maat score','maatscore','MAAT scores',
                 'MAAT rating','maat ratings','MAAT assessment','MAAT analysis',
                 "Ma'at value",'Ma’at score','M.A.A.T. Wert')
        for alias in aliases:
            query=f'Berechne {alias} von "Mona Lisa"'
            with self.subTest(alias=alias):
                self.assertTrue(needs_reference([{'role':'user','content':query}]))
                self.assertEqual(assessment_topics(query),[('Mona Lisa',True)])
        for query in ('Calculate the MAAT score of "Mona Lisa"',
                      'Evaluate Mona Lisa using MAAT','Bewerte Mona Lisa nach MAAT',
                      'maatweltformel','MAAT Welt-Formel','MAAT world formula','maatworldformula',
                      'Maat_world','MAAT–MASTER','Weltformel','PLP','Problemlösungspotenzial',
                      'Problemlösungspotential','problem-solving potential','Problem solving potential',
                      'Calculate Stability','Berechne Stabilität','Stability=','C(x)',
                      'AGI proximity','AI_CONSCIOUSNESS','B universe','H=0.6, B=0.5, S=0.4'):
            with self.subTest(query=query):
                self.assertTrue(needs_reference([{'role':'user','content':query}]))

    def test_user_examples_get_full_names_out_of_ten_and_no_advanced_maths(self):
        for language in ('de','en'):
            profile,_,_=load_yaml_profile(str(GAME),language)
            names=('Harmonie','Balance','Schöpfungskraft','Verbundenheit','Respekt') if language=='de' else (
                'Harmony','Balance','Creative Power','Connection','Respect')
            out_of='von 10' if language=='de' else 'out of 10'
            for query in ('was ist der maat wert von licht?','maat wert von sonnenlicht',
                          'maat wert da vinci','maat wert der mona lisa','maat wert von albert einstein',
                          'MAAT score of sunlight','MAAT value of the Mona Lisa',
                          'Harmonie 5 von 10, Balance 6 von 10','Harmony: 5 out of 10, Balance: 6 out of 10',
                          'H: 5/10, B: 6/10','MAAT value of World of Warcraft'):
                with self.subTest(language=language,query=query):
                    block=generation_reference([{'role':'user','content':query}],{'profile':profile})
                    self.assertIsNotNone(block)
                    for name,value in zip(names,range(5,10)):
                        self.assertIn(f'{name}: {value} {out_of}',block)
                    self.assertIn(f'(5+6+7+8+9)/5 = 7 {out_of}',block)
                    self.assertNotIn('PLP',block);self.assertNotIn('Maat_world',block)
                    self.assertNotIn('0.5',block);self.assertNotIn('Stability',block)

    def test_advanced_formulas_are_selected_individually_and_do_not_leak(self):
        requests={'Berechne Stability':'Stability=', 'MAAT world formula':'Maat_world=',
                  'Calculate PLP':'PLP=', 'C(x)':'C(x)=', 'AGI proximity':'AGI_proximity=',
                  'AI consciousness':'AI_CONSCIOUSNESS=', 'MAAT master':'MAAT_MASTER=',
                  'B universe':'B_universe='}
        for language in ('de','en'):
            profile,_,_=load_yaml_profile(str(GAME),language)
            for query,formula in requests.items():
                with self.subTest(language=language,query=query):
                    history=[{'role':'user','content':query}]
                    block=generation_reference(history,{'profile':profile})
                    self.assertIn(formula,block);self.assertIn('P=H*B*S*V*R',block)
                    self.assertLess(len(block),1800)
                    self.assertNotIn('[MAAT]\n',block)
                    for other in requests.values():
                        if other!=formula:self.assertNotIn(other,block)
                    for followup in ('Noch ein Beispiel bitte','Another example please',
                                     'Harmonie 5 von 10, Balance 6 von 10'):
                        continuation=generation_reference(history+[{'role':'user','content':followup}],{'profile':profile})
                        self.assertIn(formula,continuation)
                    # A new simple assessment sheds the prior normalized scale.
                    simpler=generation_reference(history+[{'role':'user','content':'maatwert von Licht'}],{'profile':profile})
                    self.assertIn('[MAAT]\n',simpler);self.assertNotIn(formula,simpler)

    def test_all_additional_formulas_have_short_steps_and_correct_worked_examples(self):
        from math import sqrt
        expected={'stability':('0.0625',0.5), 'world':('0.03125/0.5=0.0625',0.0625),
                  'plp':('0.025/1=0.025',0.025), 'coherence':('0.03125/0.5=0.0625',0.0625),
                  'agi':('0.0125/1=0.0125',0.0125),'consciousness':('0.0125/1=0.0125',0.0125),
                  'master':('0.0125/1=0.0125',0.0125),'universe':('0.0625*2=0.125',0.125)}
        p=(5/10)**5
        calculated={'stability':min(.5,sqrt(sqrt(.5**4))), 'world':p/.5,
                    'plp':p*.8/(.5+.5),'coherence':p/(.49+.01),
                    'agi':p*.8*.5/(.2+.5+.3),'consciousness':p*.8*.5/(.2+.5+.3),
                    'master':p*.8*.5/(.4+.2+.2+.19+.01),'universe':p/.5*2}
        for language in ('de','en'):
            profile,_,_=load_yaml_profile(str(GAME),language)
            for key,(example,result) in expected.items():
                block=profile['maat_formulas'][key]
                with self.subTest(language=language,key=key):
                    self.assertIn('1.',block);self.assertIn('2.',block)
                    self.assertIn('Beispiel:' if language=='de' else 'example:',block.casefold() if language=='en' else block)
                    self.assertIn(example,block)
                    self.assertAlmostEqual(calculated[key],result)
            for query,key in [('Weltformel','world'),('world formula','world'),
                              ('lokale Kohärenz','coherence'),('local coherence','coherence'),
                              ('KI-Bewusstsein','consciousness'),('AI consciousness','consciousness'),
                              ('AGI-Nähe','agi'),('AGI proximity','agi'),
                              ('Universumsformel','universe'),('universe formula','universe')]:
                reference=generation_reference([{'role':'user','content':query}],{'profile':profile})
                self.assertIn(profile['maat_formulas'][key],reference)

    def test_smalltalk_does_not_inherit_formula_reference_or_assistant_offers(self):
        for language in ('de','en'):
            profile,_,_=load_yaml_profile(str(GAME),language)
            for query in ('Hallo =)','wie geht es dir?','wer bist du jenseits der Programmierung?',
                          'Hello!','How are you?','Who are you?','What is MAAT?',
                          'Die Stabilität meines Tisches ist schlecht.'):
                history=[{'role':'system','content':build_systemprompt(profile)},
                         {'role':'system','content':MARKER+'\nSTALE FORMULA'},
                         {'role':'user','content':'Berechne den MAAT-Wert'},
                         {'role':'assistant','content':'Would you like a Stability calculation?'},
                         {'role':'user','content':query}]
                with self.subTest(language=language,query=query), \
                     patch('shared.core.thinking_mode._load_settings',return_value={}), \
                     patch('shared.core.rpg_generation_context._load_settings',return_value={}):
                    messages=prepare_generation_messages(history,language=language,runtime_context={'profile':profile})
                    system='\n'.join(m['content'] for m in messages if m['role']=='system')
                    self.assertNotIn(MARKER,system)
                    self.assertNotIn('PLP',system);self.assertNotIn('[MAAT]',system)
                    self.assertIn(query,messages[-1]['content'])
        for followup in ('Noch ein Beispiel bitte','Another example please','Setze die Werte ein'):
            history=[{'role':'user','content':'MAAT-Wert'},{'role':'user','content':followup}]
            self.assertTrue(needs_reference(history))
            history.insert(1,{'role':'user','content':'Hallo'})
            self.assertFalse(needs_reference(history))
