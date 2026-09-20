import tempfile
from pathlib import Path
import unittest
from test_desktop import APP
from gui.ai_companion import CompanionCampaign, SCENES, estimate_reply_tokens, validate_reply_length
from test_live_rpg import Worker

LONG_REPLY = ' Ich erkläre dir meine Entscheidung und prüfe die Angaben zuerst sorgfältig, bevor wir gemeinsam den nächsten Schritt unternehmen.'

class CompanionTests(unittest.TestCase):
    def tearDown(self):
        from shared.core.story_campaign import set_companion_story
        set_companion_story(False)

    def test_reply_token_boundary(self):
        self.assertEqual(estimate_reply_tokens('  \n  '), 0)
        self.assertEqual(estimate_reply_tokens('a ' * 19), 19)
        with self.assertRaises(ValueError): validate_reply_length('a ' * 19)
        self.assertEqual(validate_reply_length('a ' * 20), 20)
        with tempfile.TemporaryDirectory() as folder:
            game = CompanionCampaign(Path(folder)/'ai.json')
            with self.assertRaises(ValueError): game.answer('zu kurz', 0)
            self.assertEqual(game.state['xp'], 0)
            self.assertEqual(game.state['chapter'], 0)
            self.assertFalse(game.path.exists())

    def test_verification_persistence_and_no_repeated_reward(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'ai.json'
            game = CompanionCampaign(path)
            with self.assertRaises(ValueError): game.answer('Ein Rat', -1)
            self.assertEqual(game.state['chapter'], 0)
            result = game.answer('Ganz sicher sieben Sekunden.' + LONG_REPLY, 1)
            self.assertFalse(result['verified'])
            self.assertEqual(game.state['trust'], 42)
            game = CompanionCampaign(path)
            self.assertEqual(game.state['chapter'], 1)
            while game.view()['scene']:
                scene = game.view()['scene']
                game.answer('Wir prüfen die Angaben gemeinsam.' + LONG_REPLY, scene['correct'] if scene['correct'] is not None else 0)
            earned = game.state['xp']
            self.assertIsNone(game.answer('Noch einmal bitte.' + LONG_REPLY, 0))
            self.assertEqual(game.state['xp'], earned)
            self.assertEqual(len(game.state['memories']), 6)
            self.assertTrue(game.view()['skills'])

    def test_worker_campaign_without_model(self):
        worker = Worker()
        try:
            events = worker.command('/ai-start')
            self.assertTrue(any(e['event']=='companion' for e in events))
            worker.send(op='companion_answer', text='Ich bin deine Begleiter-KI.' + LONG_REPLY, choice=-1)
            worker.until(lambda e:e['event']=='busy' and not e['value'])
            for scene in SCENES:
                worker.send(op='companion_answer', text='Ich prüfe das mit dir, Maatis.' + LONG_REPLY, choice=scene['correct'] if scene['correct'] is not None else 0)
                events = worker.until(lambda e:e['event']=='busy' and not e['value'])
            state = next(e['data'] for e in events if e['event']=='companion')
            self.assertEqual(state['chapter'],6)
            self.assertIsNone(state['scene'])
            self.assertEqual(state['xp'],192)
            self.assertTrue(any(e['event']=='profile' for e in events))
            events=worker.command('/ai-start')
            self.assertEqual(next(e['data']['xp'] for e in events if e['event']=='companion'),192)
        finally: worker.close()

    def test_gui_perspective_answer_and_tactics(self):
        import os, time
        from unittest.mock import patch
        from PySide6.QtCore import QCoreApplication, QEvent
        from gui.live_window import LiveWindow
        from apps.maat_rpg import session_shared
        from test_live_window import SilentAudio
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'MAAT_GUI_DATA_ROOT':folder}):
            previous_manager = session_shared.read_profile_manager_state()
            session_shared.write_profile_manager_state({'active_profile':1})
            previous = session_shared.load_profile_settings(1).get('gui_perspective','adventure')
            import json
            arena_seed=Path(folder)/'state/battle_state.json'
            arena_seed.parent.mkdir(parents=True,exist_ok=True)
            arena_seed.write_text(json.dumps({'world':{'combat_unlocked':True},'player':{'hp':1000,'max_hp':1000}}))
            w = LiveWindow(audio=SilentAudio())
            w.request_title_start()
            w.choose_profile(w.game._profile_slot())
            def wait(predicate):
                end=time.monotonic()+12
                while not predicate() and time.monotonic()<end:
                    APP.processEvents(); w.text_stream.finish()
                    if w.phase == 'story': w.story_screen.finish()
                    if w.game.prompt_id and not w.text_stream.running and not w._battle_active: w.game.submit_choice('1')
                    time.sleep(.01)
                self.assertTrue(predicate())
            try:
                w.show()
                wait(lambda:w.game.ready)
                w.enter_menu()
                w.begin_game()
                w.intro.finish()
                self.assertEqual(w.phase, 'perspective')
                self.assertFalse(w.title_idle.isActive())
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    w.grab().save(str(Path(os.environ['MAAT_GUI_SCREENSHOTS'])/'perspective-selection.png'))
                w.perspective_screen.cards['companion'].click()
                self.assertEqual(w.perspective.currentData(), 'companion')
                wait(lambda:bool(w.companion_panel.data) and w.phase == 'playing' and not w.game.busy and not w.text_stream.running and not w._deferred)
                w.text_stream.finish()
                self.assertTrue(w.companion_panel.isVisible())
                self.assertTrue(w.tactical_input.isVisibleTo(w.arena))
                self.assertIn('Wer bist du?', w.journal.toPlainText())
                w.input.setText('Ich bin deine Begleiter-KI.' + LONG_REPLY)
                w.send()
                wait(lambda:w.companion_panel.data.get('identity_answered') and not w.game.busy and not w.text_stream.running and not w._deferred)
                w.companion_panel.choice.setCurrentIndex(1)
                w.input.setText('Zu kurz.')
                w.send()
                self.assertEqual(w.input.text(), 'Zu kurz.')
                self.assertEqual(w.companion_panel.data['chapter'], 0)
                self.assertIn('mindestens 20', w.footer.text())
                w.input.setText('Zwölf Sekunden, Maatis: drei mal vier.' + LONG_REPLY)
                w.send()
                wait(lambda:w.companion_panel.data.get('chapter')==1 and not w.game.busy)
                self.assertEqual(w.companion_panel.data['xp'],32)
                self.assertIn('Zwölf Sekunden',w.journal.toPlainText())
                w.resize(1450,1050)
                APP.processEvents()
                if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                    w.grab().save(str(Path(os.environ['MAAT_GUI_SCREENSHOTS'])/'ai-companion.png'))
                w.companion_panel.fight.click()
                wait(lambda:bool(w.game.prompt_id))
                w.text_stream.finish()
                self.assertEqual(w.stack.currentIndex(),2)
                w.tactical_input.setText('H: Prüfe den Wächter mit Harmonie.')
                w.tactical_advice()
                wait(lambda:bool(w.game.prompt_id) and w._pending_principle is None)
                self.assertIn('Taktischer Rat',w.journal.toPlainText())
            finally:
                session_shared.write_profile_settings(1, {'gui_perspective':previous})
                session_shared.write_profile_manager_state(previous_manager)
                w.game.shutdown(); w.close(); w.deleteLater()
                QCoreApplication.sendPostedEvents(w,QEvent.DeferredDelete)
                APP.processEvents()

    def test_model_plays_maatis_and_keeps_dialogue_without_awarding_xp(self):
        from unittest.mock import patch
        from contextlib import redirect_stdout
        import io
        from gui.game_worker import Runtime
        with tempfile.TemporaryDirectory() as folder:
            runtime = Runtime.__new__(Runtime)
            runtime.companion = CompanionCampaign(Path(folder)/'ai.json')
            runtime.companion.state['identity_answered'] = True
            runtime.llm = object()
            runtime.perf = {}
            runtime.core = None
            runtime.context = {}
            runtime.pm = None
            from types import SimpleNamespace
            runtime.boot = SimpleNamespace(conversation=[])
            calls = []
            def generate(llm, messages, perf, plugins, runtime_context):
                self.assertEqual(runtime_context['memory_perspective'], 'companion')
                calls.append(messages)
                return iter(['Ich stehe vor einem Tor. Wie soll ich vorgehen?'])
            with patch('gui.game_worker.emit'), patch('shared.core.streaming.stream_chat_completion', side_effect=generate), patch('shared.core.streaming.stream_to_console', side_effect=lambda chunks,echo,**kwargs: ''.join(chunks)), redirect_stdout(io.StringIO()):
                runtime.companion_start()
                self.assertIsNone(runtime.companion_view()['scene'])
                self.assertEqual(runtime.companion_view()['playstyle'], 'free')
                runtime.companion_answer(LONG_REPLY, -1)
            self.assertIn('Du bist Maatis', calls[0][0]['content'])
            self.assertIn('genau eine passende offene Frage', calls[0][0]['content'])
            self.assertTrue(any(m['role']=='assistant' for m in calls[1]))
            self.assertEqual(calls[1][-1]['content'], LONG_REPLY)
            self.assertEqual(runtime.companion.state['xp'],0)
            self.assertEqual(len(CompanionCampaign(runtime.companion.path).state['dialogue']),4)

    def test_gui_stream_failure_raises_without_spinner_or_memory(self):
        from unittest.mock import patch
        from contextlib import redirect_stdout
        import io
        from shared.core.streaming import stream_chat_completion, stream_to_console
        def failing(*args, **kwargs):
            raise RuntimeError('llama_decode returned -3')
        output = io.StringIO()
        with patch('shared.core.streaming.backend_stream_chat', side_effect=failing), patch('shared.core.streaming.threading.Thread') as thread, patch('shared.core.streaming.FIRST_RUN_DONE', False), redirect_stdout(output):
            with self.assertRaisesRegex(RuntimeError, 'llama_decode'):
                stream_to_console(stream_chat_completion({'backend':'llama'}, [], {'gui_mode':True,'raise_errors':True}), raise_errors=True)
            thread.assert_not_called()
        self.assertNotIn('STREAM ERROR', output.getvalue())
        self.assertNotIn('Lade Modell', output.getvalue())
        from gui.game_worker import Runtime
        with tempfile.TemporaryDirectory() as folder:
            runtime = Runtime.__new__(Runtime)
            runtime.companion = CompanionCampaign(Path(folder)/'ai.json')
            runtime.companion.state['identity_answered'] = True
            runtime.llm = object(); runtime.perf = {}; runtime.core = None; runtime.pm = None
            runtime.context = {}
            with patch('gui.game_worker.emit'), patch('shared.core.streaming.stream_to_console', side_effect=failing), redirect_stdout(output):
                with self.assertRaises(RuntimeError): runtime.companion_start()
            self.assertNotIn('dialogue', runtime.companion.state)
            self.assertFalse(runtime.companion.path.exists())
