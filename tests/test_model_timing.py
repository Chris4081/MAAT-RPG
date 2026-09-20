import io
from contextlib import redirect_stdout
from copy import deepcopy
import unittest
from unittest.mock import patch
from test_desktop import APP
from gui.model_timing import ModelTiming,timing_key


class ModelTimingTests(unittest.TestCase):
    def setUp(self):
        self.saved={};self.now=0.
        self.widget=ModelTiming(lambda:deepcopy(self.saved),self.saved.update,clock=lambda:self.now)
        self.event={'event':'model_load_started','name':'Llama-4B.gguf','backend':'llama_intel','n_ctx':20000,'tuning':{'mode':'auto'}}

    def tearDown(self):
        self.widget.timer.stop();self.widget.close();self.widget.deleteLater();APP.processEvents()

    def load(self):
        self.widget.handle(self.event);self.now+=12
        self.widget.handle({'event':'model','status':'ready','name':'Llama-4B.gguf'})

    def test_first_measurement_then_persisted_estimate_excludes_player_idle_time(self):
        self.widget.handle(self.event)
        self.assertIn('Erste Messung',self.widget.detail.text())
        self.now=12;self.widget.handle({'event':'model','status':'ready'})
        self.now=900;self.widget.handle({'event':'chat_generation'})
        self.now=908;self.widget.handle({'event':'chat_first_token'})
        row=self.saved['gui_model_timings'][self.widget.key]
        self.assertEqual(row,{'load':[12.0],'first_token':[8.0]})
        self.widget.handle({'event':'chat_first_token'})
        self.assertEqual(row['first_token'],[8.0])
        self.widget.reset();self.widget.handle(self.event);self.now+=2;self.widget.render()
        self.assertIn('Geschätzt noch ≈ 0:10',self.widget.detail.text())
        self.assertIn('0:08',self.widget.detail.text())
        self.now+=10;self.widget.handle({'event':'model','status':'ready'})
        self.widget.handle({'event':'chat_generation'});self.now+=10;self.widget.render()
        self.assertIn('Dauert länger',self.widget.detail.text())
        self.assertLess(self.widget.bar.value(),100)

    def test_cancel_error_and_second_reply_do_not_pollute_first_reply_estimate(self):
        self.load();self.widget.handle({'event':'chat_generation'});self.now+=4
        self.widget.handle({'event':'chat_cancelled'})
        self.assertEqual(self.widget.samples('first_token'),[])
        self.widget.handle({'event':'chat_generation'});self.now+=8
        self.widget.handle({'event':'chat_first_token'})
        self.widget.handle({'event':'chat_generation'});self.now+=2
        self.widget.handle({'event':'chat_first_token'})
        self.assertEqual(self.widget.samples('first_token'),[8.])
        self.assertEqual(self.widget.samples('reply_token'),[2.])
        self.widget.handle({'event':'chat_generation'});self.now+=100
        self.widget.handle({'event':'error'})
        self.assertEqual(self.widget.samples('reply_token'),[2.])
        self.assertFalse(self.widget.timer.isActive())

    def test_model_hardware_and_configuration_keys_and_language(self):
        initial=timing_key(self.event)
        for updates in ({'name':'Qwen-4B.gguf'},{'backend':'llama'},{'n_ctx':100000},
                        {'tuning':{'mode':'manual','manual':{'threads':2}}}):
            self.assertNotEqual(initial,timing_key(dict(self.event,**updates)))
        with patch('gui.model_timing.platform.machine',return_value='different'):
            self.assertNotEqual(initial,timing_key(self.event))
        self.widget.set_language('en');self.widget.handle(self.event)
        self.assertIn('Loading AI model',self.widget.title.text())
        self.assertIn('First measurement',self.widget.detail.text())
        self.assertIn('idle time',self.widget.toolTip())

    def test_first_visible_callback_excludes_hidden_thinking_and_fires_once(self):
        from shared.core.streaming import stream_to_console
        calls=[]
        with patch('shared.core.streaming.key_pressed',return_value=False), \
             patch('shared.core.streaming._show_thinking_enabled',return_value=False),redirect_stdout(io.StringIO()):
            source=iter(['<think>hidden analysis','</think>','Hello',' again!'])
            reply=stream_to_console(source,on_first_visible=lambda:calls.append(True))
        self.assertEqual(calls,[True]);self.assertNotIn('hidden analysis',reply)
        self.assertTrue(reply.endswith('Hello again!'))

    def test_timing_write_failure_does_not_fail_a_reply(self):
        def fail(_):raise OSError('read-only')
        self.widget.save_settings=fail
        self.load();self.widget.handle({'event':'chat_generation'});self.now+=1
        self.widget.handle({'event':'chat_first_token'})
        self.assertEqual(self.widget.phase,'streaming')
