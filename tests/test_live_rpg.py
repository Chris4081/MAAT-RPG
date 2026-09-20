"""Real plugin/GUI integration with private profiles and no model download."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / 'maatos/gui/game_worker.py'


class Worker:
    def __init__(self, seed=None, auto_stories=True, auto_classes=True):
        self.auto_stories = auto_stories
        self.auto_classes = auto_classes
        self.temp = tempfile.TemporaryDirectory(prefix='maat-worker-test-')
        if seed:
            for name, content in seed.items():
                target = Path(self.temp.name) / 'state' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(content))
        env = dict(os.environ, MAAT_GUI_DATA_ROOT=self.temp.name)
        for key in list(env):
            if key.startswith('MAAT_') and key.endswith('_DIR'):
                env.pop(key)
        self.p = subprocess.Popen([sys.executable, '-u', str(WORKER), '1'], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        self.q = queue.Queue()
        def read():
            for line in self.p.stdout:
                try:
                    self.q.put(json.loads(line))
                except ValueError:
                    self.q.put({'event':'raw', 'text':line})
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()
        self.boot = self.until(lambda e: e['event'] == 'ready')

    def send(self, **data):
        self.p.stdin.write(json.dumps(data)+'\n')
        self.p.stdin.flush()

    def until(self, predicate, timeout=12):
        result = []
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            e = self.q.get(timeout=max(.01, deadline-time.monotonic()))
            result.append(e)
            if e['event'] == 'story_scene' and self.auto_stories:
                self.send(op='story_done', id=e['id'])
            if e['event'] == 'class_selection' and self.auto_classes:
                self.send(op='class_select', id=e['id'], value='robo')
            if e['event'] == 'error':
                raise AssertionError(e)
            if predicate(e):
                return result
        raise AssertionError('worker timeout')

    def command(self, text):
        self.send(op='text', text=text)
        return self.until(lambda e: e['event']=='busy' and not e['value'])

    def close(self):
        if self.p.poll() is None:
            self.send(op='shutdown')
            try:
                self.p.wait(timeout=4)
            except subprocess.TimeoutExpired:
                self.p.kill()
                self.p.wait()
        self.reader.join(timeout=1)
        self.p.stdin.close()
        self.p.stdout.close()
        self.p.stderr.close()
        self.temp.cleanup()


class RealRpgTests(unittest.TestCase):
    def setUp(self):
        self.worker = Worker(seed={"battle_state.json":{"world":{"combat_unlocked":True},"player":{"level":5,"hp":1000,"max_hp":1000}}})

    def tearDown(self):
        self.worker.close()

    def test_invalid_external_gguf_keeps_worker_usable(self):
        bad = Path(self.worker.temp.name) / 'invalid.GGUF'
        bad.write_text('not a model')
        self.worker.send(op='load_model', name=str(bad), backend='llama', n_ctx=1024)
        events = []
        while True:
            event = self.worker.q.get(timeout=12)
            events.append(event)
            if event['event'] == 'busy' and not event['value']:
                break
        self.assertTrue(any(e['event'] == 'model_error' and 'GGUF' in e['text'] for e in events))
        self.assertTrue(any(e['event'] == 'output' for e in self.worker.command('/quests')))

    def test_plugin_catalog_and_world_commands(self):
        commands = next(e['items'] for e in self.worker.boot if e['event']=='commands')
        names = {c['command'] for c in commands}
        self.assertTrue({'/shop','/quests','/d1000','/d500','/dungeon60','/journal','/intro','/models'} <= names)
        for command in ['/shop', '/quests', '/journal', '/erfolge', '/dungeon60 status', '/d500 status', '/d1000 status']:
            events = self.worker.command(command)
            self.assertTrue(any(e['event']=='output' for e in events), command)

    def test_battle_decisions_hud_audio_and_shutdown(self):
        self.worker.send(op='text', text='/fight')
        events = self.worker.until(lambda e: e['event']=='prompt')
        self.assertTrue(any(e['event']=='battle' and 'enemy_hp' in e for e in events))
        self.assertTrue(any(e['event']=='audio' and e.get('loop') for e in events))
        prompt = events[-1]
        self.assertTrue(any(c['value']=='1' for c in prompt['choices']))
        self.worker.send(op='answer', id=prompt['id'], value='1')
        events = self.worker.until(lambda e: e['event']=='prompt')
        self.assertIn('Harmonie', str(events[-1]))
        self.worker.send(op='answer', id=events[-1]['id'], value='1')
        events = self.worker.until(lambda e: e['event']=='prompt')
        self.assertTrue(any(e['event']=='battle' for e in events))
        self.worker.send(op='shutdown')
        self.worker.p.wait(timeout=4)
        self.assertEqual(self.worker.p.returncode, 0)

    def test_real_arena_victory_has_final_hud_and_reward(self):
        initial = next(e['data'] for e in self.worker.boot if e['event'] == 'profile')
        self.worker.send(op='text', text='/fight')
        events = []
        for _ in range(40):
            batch = self.worker.until(lambda e: e['event'] == 'prompt' or (e['event'] == 'busy' and not e['value']))
            events.extend(batch)
            if batch[-1]['event'] == 'busy':
                break
            self.worker.send(op='answer', id=batch[-1]['id'], value='1')
        else:
            self.fail('Arena battle did not complete')
        self.assertTrue(any(e['event'] == 'battle' and e.get('enemy_hp') == 0 for e in events))
        final = [e['data'] for e in events if e['event'] == 'profile'][-1]
        self.assertGreater(final['gold'], initial['gold'])
        self.assertGreater(final['xp'], initial['xp'])
        self.assertEqual(final['boss_progress'],1)

    def test_intro_uses_gui_input_and_audio(self):
        self.worker.send(op='text', text='/intro')
        events = self.worker.until(lambda e: e['event']=='prompt')
        self.assertTrue(any(e['event']=='scene' for e in events))
        self.assertTrue(any(e['event']=='audio' for e in events))
        self.worker.send(op='answer', id=events[-1]['id'], value='q')
        events = self.worker.until(lambda e: e['event']=='busy' and not e['value'])
        self.assertTrue(any(e['event']=='audio' and e.get('action')=='stop' for e in events))

    def test_legacy_dungeon_command_respects_current_level_gate(self):
        self.worker.close()
        self.worker = Worker(seed={'state.json': {'unlocked': True, 'msg': 60, 'runs': 0}})
        # The GUI now routes this old command to the level-10 five-room dungeon.
        with self.assertRaisesRegex(AssertionError, 'Level 10'):
            self.worker.command('/dungeon60')
        self.worker.until(lambda e: e['event']=='busy' and not e['value'])
        state = json.loads((Path(self.worker.temp.name) / 'state/state.json').read_text())
        self.assertEqual(state['runs'], 0)


if __name__ == '__main__':
    unittest.main()
