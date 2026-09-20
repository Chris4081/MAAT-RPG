"""Qt-side process adapter preserving the original snapshot callback API."""
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import uuid
from PySide6.QtCore import QProcess, QProcessEnvironment, QTimer
from apps.maat_rpg.session_controller import MaatRpgSession
from apps.maat_rpg.session_models import BattleSnapshot
from apps.maat_rpg import session_shared
from gui.runtime_diagnostics import event as diagnostic


class LiveSession(MaatRpgSession):
    live = True

    def __init__(self):
        super().__init__()
        self.transport_callbacks = []
        self.process = None
        self.ready = False
        self.busy = True
        self.prompt_id = None
        self._buffer = b''
        self._stderr_buffer = b''
        self._closing = False
        self.chat_turn_id = None
        self._loading_model = None
        self._active_model = None
        self._memory_stop = None
        self._low_memory_samples = 0
        self._memory_timer = QTimer()
        self._memory_timer.setInterval(500)
        self._memory_timer.timeout.connect(self._check_model_memory)
        self._encounter_queue = None
        self._releasing_encounter = False
        self._battle_presentation_queue = None
        self._releasing_battle_presentation = False

    def on_transport(self, callback):
        self.transport_callbacks.append(callback)

    def transport(self, event):
        if event.get('event') == 'diagnostic':
            from shared.core.native_diagnostics import visible_diagnostics
            event = dict(event, text=visible_diagnostics(event.get('text', '')))
            if not event['text']:
                return
        for cb in self.transport_callbacks:
            cb(event)

    def start(self):
        self._snapshot = self._build_snapshot()
        self._snapshot.model_status = 'Kein KI-Modell geladen'
        self._emit_snapshot()
        self._start_process()

    @property
    def needs_language_choice(self):
        return session_shared.application_language() is None

    def set_language(self, language, *, start_worker=True):
        if language not in ('de', 'en') or self.busy or self.prompt_id:
            return False
        super().set_language(language)
        self.shutdown()
        if start_worker:
            self._start_process()
        else:
            self.ready = self.busy = False
        return True

    def _start_process(self):
        # Ask once for the application, before any profile worker can start.
        if self.needs_language_choice:
            self.ready = self.busy = False
            self.transport({'event': 'language_required'})
            return
        self._encounter_queue=None
        self._battle_presentation_queue=None
        self._closing = False
        self.ready = False
        self.busy = True
        self.prompt_id = None
        self._buffer = b''
        self._stderr_buffer = b''
        process = QProcess()
        self.process = process
        process.setWorkingDirectory(str(Path(__file__).resolve().parents[1]))
        env = QProcessEnvironment.systemEnvironment()
        env.insert('PYTHONUNBUFFERED', '1')
        env.insert('PYTHONIOENCODING', 'utf-8')
        process.setProcessEnvironment(env)
        process.readyReadStandardOutput.connect(lambda: self._read(process))
        process.readyReadStandardError.connect(lambda: self._read_stderr(process))
        process.errorOccurred.connect(lambda err: self._process_error(process))
        process.finished.connect(lambda code, status: self._finished(process, code))
        process.start(sys.executable, ['-u', str(Path(__file__).with_name('game_worker.py')), str(self._profile_slot())])
        self.transport({'event': 'busy', 'value': True})

    def _read_stderr(self, process, final=False):
        if process is not self.process:
            return
        self._stderr_buffer += bytes(process.readAllStandardError())
        while b'\n' in self._stderr_buffer:
            line, self._stderr_buffer = self._stderr_buffer.split(b'\n', 1)
            self.transport({'event':'diagnostic', 'text':line.decode('utf-8', 'replace') + '\n'})
        if final and self._stderr_buffer:
            self.transport({'event':'diagnostic', 'text':self._stderr_buffer.decode('utf-8', 'replace')})
            self._stderr_buffer = b''

    def _process_error(self, process):
        if process is not self.process or self._closing or self._memory_stop:
            return
        self.busy = False
        self.transport({'event': 'error', 'text': process.errorString()})

    def _finished(self, process, code):
        if process is not self.process:
            return
        self._memory_timer.stop()
        self.chat_turn_id = None
        self._encounter_queue=None
        self._battle_presentation_queue=None
        self._read_stderr(process, final=True)
        self.ready = False
        self.busy = False
        self.prompt_id = None
        self._battle_state.active = False
        self._snapshot = self._build_snapshot()
        self._emit_snapshot()
        failed_model=(self._loading_model or (self._active_model if self._memory_stop else None)) if not self._closing else None
        diagnostic('worker_finished', code=code, expected=self._closing,
                   model_loading=bool(self._loading_model), memory_guard=bool(self._memory_stop))
        memory_stop=self._memory_stop
        self._active_model=None
        self._memory_stop=None
        self._loading_model=None
        self.transport({'event': 'stopped', 'code': code, 'expected': self._closing, 'model_load_failed': bool(failed_model)})
        if failed_model:
            from gui.model_errors import process_exit_error
            from shared.core.model_safety import safety_message
            message=safety_message(memory_stop,self.get_snapshot().language) if memory_stop else process_exit_error(self.get_snapshot().language)
            self.transport({'event':'model_error', 'text':message, 'detail':f'Model: {failed_model}; process exit: {code}'})
            QTimer.singleShot(0, lambda:self._recover_model_process(process))

    def _check_model_memory(self):
        process=self.process
        if self._closing or self._memory_stop or process is None or process.state()==QProcess.NotRunning or not (self._loading_model or self._active_model):
            self._memory_timer.stop()
            return
        from shared.core.model_safety import system_memory, critical_memory, ModelSafetyError
        memory=system_memory()
        self._low_memory_samples=self._low_memory_samples+1 if critical_memory(memory) else 0
        if self._low_memory_samples>=2:
            diagnostic('model_memory_guard_stop', **memory)
            self._memory_stop=ModelSafetyError('pressure',memory)
            self._memory_timer.stop()
            # Only our own worker; no global process-killing command or UI wait.
            process.kill()

    def _recover_model_process(self, process):
        if self._closing or self.process is not process:return
        self.process=None
        process.deleteLater()
        self._start_process()

    def _read(self, process):
        if process is not self.process:
            return
        self._buffer += bytes(process.readAllStandardOutput())
        while b'\n' in self._buffer:
            line, self._buffer = self._buffer.split(b'\n', 1)
            try:
                event = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                self.transport({'event': 'diagnostic', 'text': line.decode('utf-8', 'replace')})
                continue
            self._handle(event)

    def release_encounter(self):
        queued,self._encounter_queue=self._encounter_queue,None
        if queued is None:return
        self._releasing_encounter=True
        try:
            for event in queued:self._handle(event)
        finally:self._releasing_encounter=False

    def release_battle_presentation(self):
        queued, self._battle_presentation_queue = self._battle_presentation_queue, None
        if queued is None:
            return
        # Bypass only this boundary: later phase/end events may need their own wait.
        self._releasing_battle_presentation = True
        try:
            self._handle(queued[0])
        finally:
            self._releasing_battle_presentation = False
        for event in queued[1:]:
            self._handle(event)

    def _handle(self, e):
        kind = e.get('event')
        if self._encounter_queue is not None:
            self._encounter_queue.append(e)
            return
        if (not self._releasing_encounter and kind=='battle' and e.get('active')
                and e.get('combat_source')=='random' and not self._battle_state.active):
            self._encounter_queue=[e]
            self.transport({'event':'encounter_intro'})
            return
        if self._battle_presentation_queue is not None:
            self._battle_presentation_queue.append(e)
            return
        b = self._battle_state
        first_opponent = e.get('active') and e.get('enemy_name') and (not b.active or not b.enemy_name)
        phase_change = e.get('active') and b.active and 'phase' in e and e['phase'] != b.phase
        battle_end = kind == 'battle' and not e.get('active') and b.active
        if (kind == 'battle' and not self._releasing_battle_presentation
                and (first_opponent or phase_change or battle_end)):
            self._battle_presentation_queue = [e]
            self.transport({'event': 'battle_presentation'})
            return
        if kind == 'model' and e.get('status') in ('ready','unloaded'):
            self._active_model=(e.get('name') or self._loading_model or self._active_model) if e['status']=='ready' else None
            self._loading_model=None
            if self._active_model:
                self._memory_timer.start()
            else:
                self._memory_timer.stop()
        if kind == 'ready':
            self.ready, self.busy = True, False
        elif kind == 'busy':
            self.busy = bool(e['value'])
            if not self.busy:
                self.chat_turn_id = None
        elif kind == 'prompt':
            self.prompt_id = e['id']
        elif kind == 'prompt_closed':
            self.prompt_id = None
        elif kind == 'profile':
            d = e['data']
            p = self._player_state
            for attr, key in [('hp','hp'), ('max_hp','max_hp'), ('level','level'), ('xp','xp'), ('next_xp','next_xp'), ('gold','gold'), ('potions','potions'), ('boss_victories','boss_wins'), ('principles_restored','principles')]:
                if key in d:
                    setattr(p, attr, int(d[key]))
            self._apply_localized_profile_fields()
            self._snapshot = self._build_snapshot()
            self._emit_snapshot()
        elif kind == 'battle':
            if e.get('active') and not self._battle_state.active:
                self._battle_state=BattleSnapshot()
            b = self._battle_state
            for attr in BattleSnapshot.__dataclass_fields__:
                if attr in e:
                    setattr(b, attr, e[attr])
            if 'player_hp' in e:
                self._player_state.hp = int(e['player_hp'])
            if 'player_potions' in e:
                self._player_state.potions = int(e['player_potions'])
            self._snapshot = self._build_snapshot()
            self._emit_snapshot()
        elif kind == 'battle_effect' and 'player_potions' in e:
            # Refresh the inventory as soon as a potion is consumed, without
            # waiting for the full profile refresh after the battle ends.
            self._player_state.potions = int(e['player_potions'])
            self._snapshot = self._build_snapshot()
            self._emit_snapshot()
        self.transport(e)

    def write(self, message):
        if self.process and self.process.state() == QProcess.Running:
            self.process.write((json.dumps(message, ensure_ascii=False) + '\n').encode('utf-8'))

    def stop_speech(self):
        # Control message: never a chat turn, command, or answer to a choice.
        self.write({'op': 'stop_speech'})

    def cancel_chat(self):
        if not self.chat_turn_id:
            return False
        self.write({'op': 'cancel_chat', 'turn_id': self.chat_turn_id})
        return True

    def chat_presented(self, identifier):
        if identifier == self.chat_turn_id:
            self.write({'op': 'chat_presented', 'turn_id': identifier})
            self.chat_turn_id = None

    def send_text(self, text):
        if self.prompt_id:
            self.submit_choice(text)
        elif self.ready and not self.busy:
            self.busy = True
            self.transport({'event': 'busy', 'value': True})
            self.chat_turn_id = None if text.strip().startswith('/') else uuid.uuid4().hex
            self.write({'op': 'text', 'text': text, 'turn_id': self.chat_turn_id})

    def answer_companion(self, text, choice):
        if self.ready and not self.busy and not self.prompt_id:
            self.busy = True
            self.transport({'event': 'busy', 'value': True})
            self.chat_turn_id = uuid.uuid4().hex
            self.write({'op': 'companion_answer', 'text': text, 'choice': choice, 'turn_id': self.chat_turn_id})

    send_command = send_text

    def submit_choice(self, value):
        if self.prompt_id:
            identifier = self.prompt_id
            self.prompt_id = None
            self.transport({'event': 'prompt_closed', 'id': identifier})
            self.write({'op': 'answer', 'id': identifier, 'value': value})

    def handle_battle_action(self, action):
        # Real choices are rendered from the current plugin prompt instead.
        return

    def load_model(self, name, backend='llama', n_ctx=20000, temperature=.8, tuning=None):
        if self.ready and not self.busy:
            self._loading_model=name
            self._low_memory_samples=0
            self._memory_stop=None
            self._memory_timer.start()
            self.busy = True
            self.transport({'event': 'busy', 'value': True})
            self.transport({'event':'model_load_started','name':name,'backend':backend,'n_ctx':n_ctx,'tuning':tuning})
            self.write({'op': 'load_model', 'name': name, 'backend': backend, 'n_ctx': n_ctx, 'temperature': temperature, 'tuning': tuning})

    def set_profile_index(self, index):
        if self.busy or self.prompt_id:
            return
        self.shutdown()
        super().set_profile_index(index)
        self._start_process()

    def shutdown(self):
        self._closing = True
        self._memory_timer.stop()
        self._memory_stop=None
        self._active_model=None
        if self.process and self.process.state() != QProcess.NotRunning:
            self.write({'op': 'shutdown'})
            # Graceful EOF/input exit first; bounded fallback for a stuck model.
            self.process.closeWriteChannel()
            if not self.process.waitForFinished(1000):
                self.process.terminate()
                if not self.process.waitForFinished(1000):
                    self.process.kill()
                    self.process.waitForFinished(1000)
