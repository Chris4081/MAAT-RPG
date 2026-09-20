"""Random identity flavour must precede, never replace, the model reply."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP  # Isolates profile paths before importing game code.
from apps.maat_rpg.plugins.rpg_identity import plugin_main as identity
from shared.plugins.plugin_loader import PluginManager
from shared.core import streaming
from gui import game_worker as worker


class IdentityChatTests(unittest.TestCase):
    def test_every_flavour_line_is_visible_but_keeps_the_original_input(self):
        for language in ('de', 'en'):
            strings = identity.IDENTITY_TEXT[language]
            for tone, prefix in (('tone_trust', 'hint_trust_'), ('tone_awe', 'hint_awe_'),
                                 ('tone_distance', 'hint_neutral_')):
                for index in (1, 2):
                    with self.subTest(language=language, tone=tone, index=index), \
                         patch.object(identity, '_identity_language', return_value=language), \
                         patch.object(identity, 'companion_story_active', return_value=False), \
                         patch('random.randint', return_value=1), \
                         patch('random.choice', side_effect=lambda options, i=index: options[i-1]):
                        plugin = identity.Plugin()
                        plugin._relationship_state = lambda: {'tone': strings[tone]}
                        context = {'last_user_input':'Wie geht es dir?'}
                        before = deepcopy(context)
                        with redirect_stdout(io.StringIO()) as output:
                            result = plugin.before_chat('Wie geht es dir?', context)
                        self.assertEqual(result, (False, 'Wie geht es dir?'))
                        self.assertEqual(output.getvalue().strip(), strings[prefix + str(index)])
                        self.assertEqual(context, before)

    def test_no_random_hint_for_commands_companion_or_an_ordinary_turn(self):
        plugin = identity.Plugin()
        for companion, text, roll in ((True, 'Hallo', 1), (False, '/lore', 1),
                                       (False, 'Hallo', 2)):
            with self.subTest(companion=companion, text=text, roll=roll), \
                 patch.object(identity, 'companion_story_active', return_value=companion), \
                 patch('random.randint', return_value=roll), \
                 patch.object(plugin, '_relationship_state') as relationship, \
                 redirect_stdout(io.StringIO()) as output:
                self.assertEqual(plugin.before_chat(text, {}), (False, text))
                relationship.assert_not_called()
                self.assertEqual(output.getvalue(), '')

    def test_explicit_lore_commands_still_return_their_own_response(self):
        for language in ('de', 'en'):
            with patch.object(identity, '_identity_language', return_value=language):
                plugin = identity.Plugin()
                for command, key in (('/whoismaat', 'identity_full'), ('/origin', 'origin_full'),
                                      ('/lore', 'lore_full')):
                    handled, result = plugin.command(command)
                    self.assertTrue(handled)
                    self.assertEqual(result, identity.IDENTITY_TEXT[language][key].strip())

    def test_real_worker_chain_streams_and_archives_the_model_reply_after_the_hint(self):
        for language in ('de', 'en'):
            for backend in ('llama', 'llama_intel'):
                with self.subTest(language=language, backend=backend):
                    query = 'Wie geht es dir?' if language == 'de' else 'How are you?'
                    reply = 'Ich höre dir zu. Was beschäftigt dich?' if language == 'de' else 'I am listening. What is on your mind?'
                    hint = identity.IDENTITY_TEXT[language]['hint_neutral_1']
                    runtime = worker.Runtime.__new__(worker.Runtime)
                    runtime.boot = SimpleNamespace(conversation=[{'role':'system', 'content':'MAAT-RPG'}])
                    runtime.llm = {'backend':backend}
                    runtime.perf = {'gui_mode':True}
                    runtime.language = language
                    memory = SimpleNamespace(engine=SimpleNamespace(_iter_save_spans=lambda raw: []),
                        code_spans=lambda raw: [], extract_model_saves=lambda raw: (raw, []), finish_turn=Mock())
                    runtime.context = {'gui_mode':True, 'super_memory':memory, 'super_memory_query':query}
                    for name in ('archive_chat', 'select_story_campaign', 'ensure_maatis_chat_opening',
                                 'restore_chat_prompt', 'complete_chat_turn'):
                        setattr(runtime, name, Mock())
                    flavour = identity.Plugin()
                    flavour._relationship_state = lambda: {'tone':'neutral'}
                    downstream = SimpleNamespace(before_chat=Mock(return_value=(False, query)),
                        after_response=Mock(side_effect=lambda reply, context: reply))
                    speech = SimpleNamespace(on_token=Mock(), begin_response_speech=Mock())
                    runtime.pm = PluginManager([])
                    runtime.pm.plugins_chat = [flavour, downstream]
                    runtime.pm.plugins_stream = [speech]
                    runtime.context['pm'] = runtime.pm
                    runtime.context['on_first_response_token'] = runtime.stop_previous_speech
                    prompts = []
                    def generate(llm, messages, **kwargs):
                        prompts.append(deepcopy(messages))
                        speech.begin_response_speech.assert_not_called()
                        return iter([reply[:12], reply[12:]])
                    output = worker.Output()
                    with patch.object(identity, '_identity_language', return_value=language), \
                         patch.object(identity, 'companion_story_active', return_value=False), \
                         patch('random.randint', return_value=1), \
                         patch('random.choice', side_effect=lambda options: options[0]), \
                         patch.object(streaming, 'backend_stream_chat', side_effect=generate), \
                         patch.object(streaming, '_stream_lang', return_value=language), \
                         patch.object(worker, 'OUT', output), patch.object(worker, 'emit') as emit, \
                         redirect_stdout(output):
                        runtime.text(query)
                    downstream.before_chat.assert_called_once_with(query, runtime.context)
                    downstream.after_response.assert_called_once_with(reply, runtime.context)
                    runtime.complete_chat_turn.assert_called_once()
                    self.assertEqual(len(prompts), 1)
                    self.assertTrue(any(m['role']=='user' and m['content']==query for m in prompts[0]))
                    self.assertNotIn(hint, repr(prompts) + repr(runtime.boot.conversation))
                    self.assertEqual([c.args for c in runtime.archive_chat.call_args_list],
                                     [('user', query), ('assistant', reply)])
                    memory.finish_turn.assert_called_once()
                    self.assertEqual(memory.finish_turn.call_args.args[:2], (query, reply))
                    self.assertEqual(''.join(c.args[0] for c in speech.on_token.call_args_list), reply)
                    speech.begin_response_speech.assert_called_once()
                    events = emit.call_args_list
                    hints = [i for i,c in enumerate(events) if c.args[0]=='output' and hint in c.kwargs.get('text','')]
                    self.assertEqual(len(hints), 1)
                    begins = [i for i,c in enumerate(events) if c.args[0]=='chat_response' and c.kwargs['action']=='begin']
                    ends = [i for i,c in enumerate(events) if c.args[0]=='chat_response' and c.kwargs['action']=='end']
                    self.assertEqual(len(begins), 1)
                    self.assertEqual(len(ends), 1)
                    self.assertLess(hints[0], begins[0])
                    self.assertLess(begins[0], ends[0])
                    visible = ''.join(c.kwargs.get('text','') for c in events if c.args[0]=='output')
                    self.assertEqual(visible.count(reply), 1)


if __name__ == '__main__':
    unittest.main()
