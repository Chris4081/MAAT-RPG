"""Combat defaults to the arena and is mirrored into the visible chat only."""
from contextlib import nullcontext, redirect_stdout
from copy import deepcopy
import io
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
import test_live_window as helpers
from apps.maat_rpg import session_shared
from apps.maat_rpg.plugins.battle import plugin_main as battle
from gui.live_window import LiveWindow


class CombatChatOutputTests(unittest.TestCase):
    def plugin(self):
        plugin = battle.Plugin.__new__(battle.Plugin)
        plugin.state = SimpleNamespace(state={
            'stats': {'messages_total': 4, 'messages_since_last_fight': 9},
            'world': {'combat_unlocked': True}}, save=Mock())
        plugin.core = SimpleNamespace(state=plugin.state,
            _load_story_state=lambda: {'played': [1, 2, 3]},
            _auto_fight_type=Mock(return_value='normal'),
            run_fight=Mock(return_value='Victory · XP 100 · Gold 50'))
        plugin._credit_chat_message = Mock()
        plugin._slow_print_lines = lambda lines: print('\n'.join(lines))
        plugin._build_hud = Mock(return_value='HP 100 · Level 20')
        return plugin

    def test_gui_discards_old_queued_reports_terminal_keeps_them(self):
        for gui in (True, False):
            plugin = self.plugin()
            context = {'gui_mode': gui, 'battle_log': ['Victory · XP 100 · Gold 50']}
            with redirect_stdout(io.StringIO()) as output:
                reply = plugin.after_response('Our conversation continues.', context)
            self.assertEqual(reply, 'Our conversation continues.')
            self.assertNotIn('battle_log', context)
            if gui:
                self.assertEqual(output.getvalue(), '')
                plugin._build_hud.assert_not_called()
            else:
                self.assertIn('Victory · XP 100', output.getvalue())
                self.assertIn('HP 100', output.getvalue())

    def test_random_encounter_does_not_queue_a_gui_replay(self):
        for gui in (True, False):
            plugin = self.plugin()
            context = {'gui_mode': gui}
            with patch('shared.core.terra_replay.take_pending', return_value=None):
                self.assertEqual(plugin.before_chat('Hello Terra!', context), (False, 'Hello Terra!'))
            plugin.core.run_fight.assert_called_once()
            if gui:
                self.assertNotIn('battle_log', context)
            else:
                self.assertEqual(context['battle_log'], ['Victory · XP 100 · Gold 50'])

    def test_arena_and_mod_results_are_not_returned_to_gui_chat(self):
        for gui in (True, False):
            for command, kind in (('/fight', 'normal'), ('/fightboss', 'boss'),
                                  ('/fightfinal', 'final'), ('/fightmod test', 'boss')):
                with self.subTest(gui=gui, command=command):
                    plugin = self.plugin()
                    plugin.core._auto_fight_type.return_value = kind
                    context = {'gui_mode': gui}
                    with patch.object(battle, 'load_battle_profile_mods', return_value={'test': {'fight_type': kind}}):
                        handled, reply = plugin.command(command, context)
                    self.assertTrue(handled)
                    self.assertEqual(reply, '' if gui else 'Victory · XP 100 · Gold 50')
                    self.assertTrue(context['reset_conversation_after_battle'])
                    plugin.core.run_fight.assert_called_once()

    def test_live_chat_mirrors_combat_once_without_changing_default_arena(self):
        with patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT': str(session_shared.BASE_APP_SUPPORT_DIR)}):
            helpers.unlock_test_arena()
            window = LiveWindow(audio=helpers.SilentAudio())
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
            try:
                helpers.LiveWindowTest.spin(self, lambda: window.game.ready)
                window.phase = 'playing'
                window._combat_unlocked = True
                window.navigate(3)
                window.text_stream.clear()
                window.journal.clear()
                window.world_output.clear()
                window.append_encounter_text('Ein Wesen erscheint …\n')
                send = window.game._handle
                with patch.object(window.arena, 'append_text', wraps=window.arena.append_text) as arena:
                    send({'event': 'output', 'text': 'Vorherige Antwort.\n'})
                    send({'event': 'battle', 'active': True, 'enemy_name': '', 'combat_source': 'arena'})
                    self.assertEqual(window.stack.currentIndex(), 2)
                    window.navigate(3)
                    send({'event': 'output', 'text': 'Kampftreffer: 14 Schaden.\n', 'combat': True})
                    window.text_stream.finish()
                    self.assertIn('Kampftreffer: 14 Schaden.', window.journal.toPlainText())
                    send({'event': 'battle', 'active': False})
                    # The core finishes the HP display before reward text.
                    send({'event': 'output', 'text': 'Sieg: 100 XP, 50 Gold.\n', 'combat': True})
                    send({'event': 'output', 'text': 'Erfolg freigeschaltet!\n'})
                    send({'event': 'chat_response', 'action': 'begin', 'id': 'after-battle'})
                    send({'event': 'output', 'text': 'Die neue KI-Antwort.\n'})
                    send({'event': 'chat_response', 'action': 'end', 'id': 'after-battle'})
                    send({'event': 'chat_response', 'action': 'replace', 'id': 'after-battle',
                          'original': 'Die neue KI-Antwort.', 'text': 'Die korrigierte KI-Antwort.'})
                    while window.text_stream.running:
                        window.text_stream.finish()
                    combat_text = ''.join(call.args[0] for call in arena.call_args_list)
                self.assertEqual(combat_text, 'Kampftreffer: 14 Schaden.\nSieg: 100 XP, 50 Gold.\n')
                self.assertEqual(window.journal.toPlainText(),
                    'Ein Wesen erscheint …\nVorherige Antwort.\nKampftreffer: 14 Schaden.\n'
                    'Sieg: 100 XP, 50 Gold.\nErfolg freigeschaltet!\nDie korrigierte KI-Antwort.\n')
                self.assertEqual(window.world_output.toPlainText(),
                    'Vorherige Antwort.\nErfolg freigeschaltet!\nDie korrigierte KI-Antwort.\n')
            finally:
                window.game.shutdown()
                window.close()
                window.deleteLater()
                APP.processEvents()

    def test_worker_tags_delayed_results_and_resets_even_after_failure(self):
        from gui import game_worker as worker
        runtime = worker.Runtime.__new__(worker.Runtime)
        output = worker.Output()
        with patch.object(worker, 'OUT', output), patch.object(worker, 'emit') as emit, redirect_stdout(output):
            print('Before')
            with self.assertRaises(ValueError), runtime.combat_output():
                print('Hit')
                worker.emit('battle', active=False)
                print('Reward: 100 XP')
                raise ValueError('test failure')
            print('Next reply')
        events = [call.kwargs for call in emit.call_args_list if call.args[0] == 'output']
        self.assertEqual([(e['text'].strip(), e.get('combat', False)) for e in events],
                         [('Before', False), ('Hit', True), ('Reward: 100 XP', True), ('Next reply', False)])

    def test_live_combat_never_enters_model_archive_memory_or_speech(self):
        from gui import game_worker as worker
        from shared.core import streaming
        for backend in ('llama', 'llama_intel'):
            with self.subTest(backend=backend):
                runtime = worker.Runtime.__new__(worker.Runtime)
                runtime.boot = SimpleNamespace(conversation=[{'role': 'system', 'content': 'MAAT-RPG'}])
                runtime.llm = {'backend': backend}
                runtime.perf = {'gui_mode': True}
                runtime.language = 'de'
                memory = SimpleNamespace(
                    engine=SimpleNamespace(_iter_save_spans=lambda raw: []),
                    code_spans=lambda raw: [], extract_model_saves=lambda raw: (raw, []),
                    finish_turn=Mock())
                runtime.context = {'gui_mode': True, 'super_memory': memory,
                                   'super_memory_query': 'Hallo Terra!'}
                for name in ('archive_chat', 'select_story_campaign', 'ensure_maatis_chat_opening',
                             'restore_chat_prompt', 'complete_chat_turn'):
                    setattr(runtime, name, Mock())
                runtime.game_event_output = nullcontext
                plugin = self.plugin()
                def fight(*args, **kwargs):
                    with runtime.combat_output():
                        print('KAMPF_NUR_ANZEIGE: 14 Schaden, Sieg, 50 Gold.')
                    return 'KAMPF_NUR_ANZEIGE'
                plugin.core.run_fight.side_effect = fight
                speech = Mock()
                runtime.pm = Mock()
                runtime.pm.handle_before_chat.side_effect = plugin.before_chat
                runtime.pm.has_before_final_response.return_value = False
                runtime.pm.get_streaming_plugins.return_value = [speech]
                runtime.pm.generation_system_messages.return_value = []
                runtime.pm.handle_after_response.side_effect = plugin.after_response
                prompts = []
                def generate(llm, messages, **kwargs):
                    prompts.append(deepcopy(messages))
                    return iter(['Unsere Unterhaltung geht weiter.'])
                output = worker.Output()
                with patch.object(worker, 'OUT', output), patch.object(worker, 'emit') as emit, \
                     patch.object(streaming, 'backend_stream_chat', side_effect=generate), \
                     patch('shared.core.terra_replay.take_pending', return_value=None), \
                     redirect_stdout(output):
                    runtime.text('Hallo Terra!')
                plugin.core.run_fight.assert_called_once()
                self.assertTrue(any(c.kwargs.get('combat') and 'KAMPF_NUR_ANZEIGE' in c.kwargs.get('text', '')
                                    for c in emit.call_args_list))
                self.assertEqual(len(prompts), 1)
                self.assertNotIn('KAMPF_NUR_ANZEIGE', repr(prompts) + repr(runtime.boot.conversation))
                self.assertEqual([c.args for c in runtime.archive_chat.call_args_list],
                                 [('user', 'Hallo Terra!'), ('assistant', 'Unsere Unterhaltung geht weiter.')])
                memory.finish_turn.assert_called_once()
                self.assertEqual(memory.finish_turn.call_args.args[:2],
                                 ('Hallo Terra!', 'Unsere Unterhaltung geht weiter.'))
                self.assertEqual(''.join(c.args[0] for c in speech.on_token.call_args_list),
                                 'Unsere Unterhaltung geht weiter.')

    def test_real_victory_reports_rewards_once_in_the_arena_channel(self):
        from test_live_rpg import Worker
        worker = Worker(seed={'battle_state.json': {
            'world': {'combat_unlocked': True},
            'hero_class': {'selected': 'robo'},
            'player': {'level': 50, 'hp': 99999, 'max_hp': 99999}}})
        try:
            worker.send(op='text', text='/fight')
            events = []
            for _ in range(60):
                batch = worker.until(lambda e: e['event'] == 'prompt' or (e['event'] == 'busy' and not e['value']))
                events.extend(batch)
                if batch[-1]['event'] == 'busy':
                    break
                worker.send(op='answer', id=batch[-1]['id'], value='1')
            else:
                self.fail('Battle did not end')
            results = [e for e in events if e['event'] == 'output' and 'Gold erhalten:' in e.get('text', '')]
            self.assertEqual(len(results), 1)
            self.assertTrue(results[0]['combat'])
            self.assertIn('XP erhalten:', results[0]['text'])
            self.assertFalse(any('Verlauf des Kampfes' in e.get('text', '') for e in events))
            end = next(i for i, e in enumerate(events) if e['event'] == 'battle' and not e.get('active'))
            self.assertTrue(any(e.get('combat') and 'Gold erhalten:' in e.get('text', '') for e in events[end+1:]))
        finally:
            worker.close()
