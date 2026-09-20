import unittest
from unittest.mock import Mock, patch
from test_desktop import APP
from shared.plugins.say_tts.plugin_main import Plugin
from shared.core.streaming import StreamingPluginInterface, stream_chat_completion

class SpeechInterruptTests(unittest.TestCase):
    def make_plugin(self):
        with patch.object(Plugin,'_detect_tts_backend',return_value='say'),patch('shared.plugins.say_tts.plugin_main.threading.Thread.start'):
            p=Plugin()
        p.enabled=True
        p._tts_enabled_setting=lambda:True
        return p

    def test_first_token_cancels_process_and_old_queue_not_input(self):
        p=self.make_plugin();proc=Mock();proc.poll.return_value=None
        p._speech_process=proc
        p._speak('Alter Satz.');p._speak('Noch ein alter Satz.')
        p.before_stream('')
        proc.terminate.assert_not_called()
        self.assertEqual(p.tts_queue.qsize(),2)
        p.on_token('Neue ')
        proc.terminate.assert_called_once()
        self.assertTrue(p.tts_queue.empty())
        p.on_token('Antwort.')
        generation,text=p.tts_queue.get_nowait()
        self.assertEqual(text,'Neue Antwort.')
        self.assertEqual(generation,p._speech_generation)
        proc.terminate.assert_called_once()

    def test_stream_and_final_hook_do_not_speak_same_reply_twice(self):
        p=self.make_plugin();p.before_stream('')
        p.on_token('Hallo Maatis.')
        p.after_stream('Hallo Maatis.')
        p.after_final_response('Hallo Maatis.')
        self.assertEqual(p.tts_queue.qsize(),1)
        p.begin_response_speech()
        p.after_final_response('Die neue Antwort.')
        self.assertEqual(p.tts_queue.qsize(),1)
        self.assertEqual(p.tts_queue.get()[1],'Die neue Antwort.')

    def test_stale_dequeued_sentence_cannot_start(self):
        p=self.make_plugin()
        p.begin_response_speech()
        p.tts_queue.put((0,'Alter, bereits entnommener Satz.'))
        p.tts_queue.put((p._speech_generation,'Neue Antwort.'))
        proc=Mock();proc.wait.side_effect=lambda:p.stop_event.set()
        with patch('shared.plugins.say_tts.plugin_main.subprocess.Popen',return_value=proc) as launch:
            p._tts_worker()
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[0][-1],'Neue Antwort.')

    def test_callback_runs_on_first_token_even_without_stream_plugins(self):
        callback=Mock()
        api=StreamingPluginInterface([],on_first_token=callback)
        api.call_before('');api.call_token('')
        callback.assert_not_called()
        api.call_token('Hallo');api.call_token(' Welt')
        callback.assert_called_once()
        callback.reset_mock()
        def chunks(*args, **kwargs):
            callback.assert_not_called()
            yield 'Erster'
            callback.assert_called_once()
            yield ' Token'
        with patch('shared.core.streaming.backend_stream_chat',side_effect=chunks):
            tokens=list(stream_chat_completion({'backend':'llama'},[],{'gui_mode':True,'raise_errors':True},[],runtime_context={'on_first_response_token':callback}))
        self.assertEqual(''.join(tokens),'Erster Token')
        callback.assert_called_once()

    def test_stop_escalates_only_owned_process(self):
        import subprocess
        p=self.make_plugin();proc=Mock();proc.poll.return_value=None
        proc.wait.side_effect=[subprocess.TimeoutExpired('say',.5),0]
        p._speech_process=proc
        p.begin_response_speech()
        proc.terminate.assert_called_once();proc.kill.assert_called_once()
        self.assertIsNone(p._speech_process)

    def test_event_cancellation_rejects_late_tokens_and_final_hook(self):
        p = self.make_plugin()
        p.before_stream('')
        p.on_token('Erster Satz.')
        p.on_token('Noch nicht fertig')
        p.cancel_speech()
        p.on_token(' und jetzt fertig.')
        p.after_stream('Erster Satz. Noch nicht fertig und jetzt fertig.')
        p.after_final_response('Erster Satz. Noch nicht fertig und jetzt fertig.')
        self.assertTrue(p.tts_queue.empty())
        self.assertEqual(p.buffer, '')
        p.before_stream('')
        p.on_token('Die nächste Chatantwort.')
        self.assertEqual(p.tts_queue.get_nowait()[1], 'Die nächste Chatantwort.')

    def test_all_battle_types_stop_before_any_presentation(self):
        from types import SimpleNamespace
        from gui.game_worker import Runtime
        for source, kind in [('arena', 'normal'), ('random', 'normal'),
                             ('random', 'boss'), ('random', 'final'),
                             ('dungeon', 'normal'), ('dungeon_plus', 'boss'), ('demo', 'boss')]:
            with self.subTest(source=source, kind=kind):
                plugin = self.make_plugin()
                process = Mock()
                process.poll.return_value = None
                plugin._speech_process = process
                plugin._speak('Vorherige Antwort.')
                runtime = Runtime.__new__(Runtime)
                runtime.pm = SimpleNamespace(iter_all_plugins=lambda: [plugin])
                def boundary(event, **data):
                    self.assertIsNone(plugin._speech_process)
                    self.assertTrue(plugin.tts_queue.empty())
                with patch('gui.game_worker.emit', side_effect=boundary):
                    runtime.begin_battle(kind, {'combat_source': source})
                process.terminate.assert_called_once()

    def test_story_stops_owned_process_before_text_or_scene_is_sent(self):
        import io
        import json
        import subprocess
        import sys
        from types import SimpleNamespace
        from gui import game_worker as worker
        p = self.make_plugin()
        runtime = worker.Runtime.__new__(worker.Runtime)
        runtime.pm = SimpleNamespace(iter_all_plugins=lambda: [p])
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'])
        try:
            p._speech_process = process
            p._speak('Ein wartender Satz.')
            source = io.StringIO()
            output = worker.Output()
            output.pending = 'Eine Geschichte beginnt.\n'
            sent = []
            def wire(event, **data):
                self.assertIsNotNone(process.poll())
                self.assertTrue(p.tts_queue.empty())
                sent.append(event)
                if event == 'story_scene':
                    source.write(json.dumps({'op':'story_done', 'id':data['id']}) + '\n')
                    source.seek(0)
            with patch.object(worker, 'OUT', output), patch.object(worker, 'INPUT', source), \
                    patch.object(worker, 'receive', side_effect=lambda: json.loads(source.readline())), \
                    patch.object(worker, 'emit', side_effect=wire), \
                    patch('shared.core.story_campaign.companion_story_active', return_value=False):
                runtime.present_story(['Ein Ereignis.'], None, {'module':'story1'})
            self.assertEqual(sent, ['speech_stopped', 'output', 'story_scene'])
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()

    def test_status_text_and_silent_hooks_keep_reading(self):
        from contextlib import redirect_stdout
        from types import SimpleNamespace
        from gui import game_worker as worker
        p = self.make_plugin()
        runtime = worker.Runtime.__new__(worker.Runtime)
        runtime.pm = SimpleNamespace(iter_all_plugins=lambda: [p])
        output = worker.Output()
        with patch.object(worker, 'OUT', output), patch.object(worker, 'emit') as wire:
            with runtime.game_event_output():
                pass
            wire.assert_not_called()
            p.before_stream('')
            p.on_token('Eine lange Antwort.')
            p.after_stream('Eine lange Antwort.')
            process = Mock()
            process.poll.return_value = None
            p._speech_process = process
            with redirect_stdout(output), runtime.game_event_output():
                print('Erfolg freigeschaltet!')
                with runtime.game_event_output():
                    print('Daily progress: 3/5 · AI development: +50 XP')
            self.assertEqual([c.args[0] for c in wire.call_args_list],
                             ['output', 'output'])
            p.after_final_response('Eine lange Antwort.')
            process.terminate.assert_not_called()
            self.assertEqual(p.tts_queue.get_nowait()[1], 'Eine lange Antwort.')
            self.assertTrue(p.tts_queue.empty())

    def test_status_command_keeps_reading_but_menu_still_stops(self):
        from contextlib import redirect_stdout
        import io
        from types import SimpleNamespace
        from gui.game_worker import Runtime
        runtime = Runtime.__new__(Runtime)
        runtime.context = {}
        runtime.boot = SimpleNamespace(command_router=SimpleNamespace(execute=Mock(return_value='Level 20 · 50 XP')))
        runtime.stop_speech = Mock()
        with redirect_stdout(io.StringIO()) as output, patch('gui.game_worker.emit'):
            runtime.text('/xp')
            runtime.stop_speech.assert_not_called()
            self.assertIn('50 XP', output.getvalue())
            runtime.text('/menu')
        runtime.stop_speech.assert_called_once_with('menu')

    def test_real_owned_process_stops_on_first_token(self):
        import subprocess
        import sys
        p=self.make_plugin()
        process=subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)'])
        try:
            p._speech_process=process
            p.before_stream('')
            self.assertIsNone(process.poll())
            p.on_token('Neue Antwort.')
            self.assertIsNotNone(process.poll())
            self.assertEqual(p.tts_queue.get_nowait()[1],'Neue Antwort.')
        finally:
            if process.poll() is None:process.kill()
            process.wait()

    def test_random_encounter_stops_voice_before_battle_announcement(self):
        from types import SimpleNamespace
        from gui.game_worker import Runtime
        plugin=self.make_plugin();proc=Mock();proc.poll.return_value=None
        plugin._speech_process=proc;plugin._speak('Alter Satz in der Warteschlange.')
        plugin.buffer='Ein noch nicht fertig gesprochener Satz'
        runtime=Runtime.__new__(Runtime)
        runtime.pm=SimpleNamespace(iter_all_plugins=lambda:[plugin])
        def check_boundary(kind,**data):
            self.assertIsNone(plugin._speech_process)
            self.assertTrue(plugin.tts_queue.empty())
            self.assertEqual(plugin.buffer,'')
        with patch('gui.game_worker.emit',side_effect=check_boundary) as notify:
            runtime.begin_battle('normal',{'combat_source':'random','arena_difficulty':'hard'})
        self.assertEqual([c.args[0] for c in notify.call_args_list],['speech_stopped','battle'])
        proc.terminate.assert_called_once()
        self.assertEqual(notify.call_args.kwargs['combat_source'],'random')
        self.assertEqual(notify.call_args.kwargs['enemy_name'],'')
        # Stopping this speech does not disable reading the next chat answer.
        plugin.before_stream('');plugin.on_token('Eine neue Antwort.')
        self.assertEqual(plugin.tts_queue.get_nowait()[1],'Eine neue Antwort.')

    def test_menu_control_message_does_not_create_chat_turn(self):
        from test_live_rpg import Worker
        worker=Worker()
        try:
            worker.send(op='stop_speech')
            events=worker.until(lambda e:e['event']=='speech_stopped')
            self.assertEqual(events[-1]['reason'],'menu')
            self.assertFalse(any(e['event'] in ('busy','chat_generation','output') for e in events))
            events=worker.command('/wiki status')
            self.assertTrue(any('Offline-Wikipedia' in e.get('text','') for e in events))
        finally:worker.close()

    def test_control_is_processed_while_real_story_and_battle_wait(self):
        from test_live_rpg import Worker
        worker = Worker(seed={'battle_state.json': {
            'world': {'combat_unlocked': True},
            'player': {'level': 50, 'hp': 1000, 'max_hp': 1000}}}, auto_stories=False)
        try:
            worker.send(op='text', text='/dungeon-enter 0')
            events = worker.until(lambda e: e['event'] == 'story_scene')
            story = events[-1]
            self.assertTrue(any(e['event'] == 'speech_stopped' for e in events))
            worker.send(op='stop_speech', reason='story_test')
            events = worker.until(lambda e: e['event'] == 'speech_stopped')
            self.assertEqual(events[-1]['reason'], 'story_test')
            self.assertFalse(any(e['event'] == 'prompt_closed' for e in events))
            worker.send(op='story_done', id=story['id'])
            worker.until(lambda e: e['event'] == 'prompt')
            worker.send(op='stop_speech', reason='battle_test')
            events = worker.until(lambda e: e['event'] == 'speech_stopped')
            self.assertEqual(events[-1]['reason'], 'battle_test')
            self.assertFalse(any(e['event'] in ('busy', 'prompt_closed', 'output') for e in events))
        finally:
            worker.close()

    def test_menu_and_title_navigation_stop_speech(self):
        import os
        from apps.maat_rpg import session_shared
        from gui.live_window import LiveWindow
        from test_live_window import SilentAudio,LiveWindowTest
        with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':str(session_shared.BASE_APP_SUPPORT_DIR)}):
            window=LiveWindow(audio=SilentAudio())
            window.request_title_start()
            window.choose_profile(window.game._profile_slot())
            try:
                LiveWindowTest.spin(self,lambda:window.game.ready)
                window.phase='playing';window.navigate(3);window.text_stream.clear()
                with patch.object(window.game,'stop_speech') as stop:
                    window.navigate(0)
                    stop.assert_called_once()
                    self.assertEqual(window.phase,'menu')
                    window.show_title()
                    self.assertEqual(stop.call_count,2)
            finally:window.close();APP.processEvents()
