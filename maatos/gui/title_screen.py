"""Native title screen and an isolated replay of the terminal attract-mode battle."""
import json
import re
import sys
import tempfile
from collections import deque
from pathlib import Path
from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget, QTextBrowser, QProgressBar
from gui.desktop import label, button
from gui.title_artwork import JourneyArtwork
from gui.runtime_diagnostics import event as diagnostic


class TitleDemo(QObject):
    presented = Signal(dict)
    completed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.temp = None
        self.queue = deque()
        self.buffer = b''
        self.ready = False
        self.finished = False
        self.stderr = b''
        self._completed = False
        self._generation = 0
        self._retired = {}
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.advance)

    def start(self, stage, profile_slot=None):
        self.stop()
        diagnostic('demo_start', stage=stage, profile=profile_slot)
        self.temp = tempfile.TemporaryDirectory(prefix='maat-title-demo-')
        if profile_slot is not None:
            self.seed_profile(profile_slot)
        process = QProcess(self)
        self.process = process
        env = QProcessEnvironment.systemEnvironment()
        for key in env.keys():
            if key.startswith('MAAT_') and key.endswith('_DIR'):
                env.remove(key)
        env.insert('MAAT_GUI_DATA_ROOT', self.temp.name)
        env.insert('PYTHONUNBUFFERED', '1')
        process.setProcessEnvironment(env)
        process.setWorkingDirectory(str(Path(__file__).resolve().parents[1]))
        process.readyReadStandardOutput.connect(lambda: self.read(process))
        process.readyReadStandardError.connect(lambda: self.read_stderr(process))
        process.finished.connect(lambda code, status: self.ended(process, code))
        process.errorOccurred.connect(lambda error: self.failed(process))
        process.start(sys.executable, ['-u', str(Path(__file__).with_name('game_worker.py')), '1', '--title-demo', str(stage)])

    def seed_profile(self, slot):
        """Snapshot only battle progression; the worker can write only its demo copy."""
        from apps.maat_rpg import session_shared
        from copy import deepcopy
        root = session_shared.profile_slot_root(slot)
        battle = session_shared.load_json_file(root / 'state' / 'battle_state.json')
        battle = deepcopy(battle)
        # A demo starts rested even if Maatis is injured in the actual save.
        player = battle.get('player')
        if isinstance(player, dict):
            player['hp'] = max(1, int(player.get('max_hp', player.get('hp', 120))))
        settings = session_shared.load_profile_settings(slot)
        story_name = 'companion_story_state.json' if settings.get('gui_perspective') == 'companion' else 'story_state.json'
        story = session_shared.load_json_file(root / 'state' / story_name)
        target = Path(self.temp.name) / 'state'
        target.mkdir(parents=True, exist_ok=True)
        (target / 'battle_state.json').write_text(json.dumps(battle, ensure_ascii=False), encoding='utf-8')
        (target / 'settings_state.json').write_text(json.dumps({'language': session_shared.profile_language(slot)}), encoding='utf-8')
        # Choices affect battle modifiers; no chat, model settings or memories needed.
        path_state = {key:story[key] for key in ('choices','choice_labels','consequences','path_profile') if key in story}
        (target / 'story_state.json').write_text(json.dumps(path_state, ensure_ascii=False), encoding='utf-8')

    def read(self, process):
        if process is not self.process:
            return
        self.buffer += bytes(process.readAllStandardOutput())
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get('event') == 'ready':
                self.ready = True
            elif self.ready:
                if event.get('event') == 'prompt':
                    process.write((json.dumps({'op':'answer', 'id':event['id'], 'value':'1' if event.get('choices') else ''})+'\n').encode())
                elif event.get('event') in {'battle', 'battle_effect', 'audio', 'output', 'error'}:
                    if event.get('event') == 'output':
                        # Present individual lines, so large worker batches do not
                        # skip over the arena's three-line reading area.
                        for line in event.get('text', '').splitlines(keepends=True):
                            self.queue.append(dict(event, text=line))
                    else:
                        self.queue.append(event)
        if not self.timer.isActive():
            self.timer.start(1)

    def advance(self):
        if self.queue:
            generation = self._generation
            event = self.queue.popleft()
            self.presented.emit(event)
            if generation == self._generation:
                self.timer.start(self.presentation_delay(event))
        elif self.finished and not self._completed:
            self._completed = True
            diagnostic('demo_playback_finished')
            self.completed.emit()

    def read_stderr(self, process):
        chunk = bytes(process.readAllStandardError())
        if process is self.process:
            self.stderr = (self.stderr + chunk)[-8192:]

    @staticmethod
    def presentation_delay(event):
        # 2.25× original playback speed; combat sprite duration is controlled separately.
        return round(TitleDemo._base_presentation_delay(event) / 2.25)

    @staticmethod
    def _base_presentation_delay(event):
        if event.get('event') == 'battle_effect':
            return 1400
        if event.get('event') == 'battle' and 'enemy_hp' in event:
            return 3500
        if event.get('event') in ('output', 'error'):
            text = event.get('text', '').strip()
            # Hidden terminal HUD and action lists need no artificial reading pause.
            if text and not re.match(r'^(?:[-─]{3,}|[1-6][).]|.*HP:|Resonanz:|Schwäche:|Schwaeche:|Aktion:)', text):
                return max(2400, min(10000, 1200 + len(text)*55))
        return 60

    def ended(self, process, code):
        if process in self._retired:
            self.release_retired(process)
            return
        if process is self.process:
            self.read(process)
            self.read_stderr(process)
            diagnostic('demo_worker_finished', code=code, exit_status=process.exitStatus().name,
                       stderr=self.stderr.decode('utf-8', 'replace') if code else '')
            if code:
                self.queue.append({'event':'error', 'text':f'Demo beendet (Fehler {code}). Rückkehr zum Titelbildschirm.\n'})
            self.finished = True
            if not self.timer.isActive():
                self.timer.start(1)

    def failed(self, process):
        if process is self.process and process.state() == QProcess.NotRunning:
            diagnostic('demo_worker_error', error=process.errorString())
            self.queue.append({'event':'error','text':process.errorString()})
            self.finished = True
            self.timer.start(1)

    def stop(self):
        self._generation += 1
        self.timer.stop()
        process, self.process = self.process, None
        temp, self.temp = self.temp, None
        if process:
            # Keep the process and its private files until it really exits. No
            # nested wait/event loop while the arena is being hidden or repainted.
            self._retired[process] = temp
            if process.state() == QProcess.NotRunning:
                self.release_retired(process)
            else:
                process.kill()
        elif temp:
            temp.cleanup()
        self.queue.clear()
        self.buffer = b''
        self.stderr = b''
        self._completed = False
        self.ready = self.finished = False

    def release_retired(self, process):
        temp = self._retired.pop(process, None)
        process.deleteLater()
        if temp:
            temp.cleanup()

    def close(self):
        self.stop()
        # Only application shutdown waits; ordinary demo transitions never do.
        for process in list(self._retired):
            process.waitForFinished(1000)


class TitleScreen(QWidget):
    start_requested = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label('MAAT RPG', 'eyebrow'))
        layout.addWidget(label('Die Rückkehr der Prinzipien', 'title'))
        layout.addWidget(label('Eine Reise durch Erinnerung, Resonanz und die fünf Prinzipien.', 'muted'))
        self.views = QStackedWidget()
        self.landscape = JourneyArtwork()
        self.views.addWidget(self.landscape)
        from gui.battle_arena import BattleArena
        self.arena = BattleArena(demo=True)
        self.arena.stage.effect_started.connect(self.apply_attack_hp)
        self.enemy = self.arena.enemy_name
        self.health = self.arena.enemy_hp
        self.player = self.arena.hero_name
        self.log = self.arena.log
        self.views.addWidget(self.arena)
        layout.addWidget(self.views, 1)
        self.start_button = button('PRESS ENTER TO PLAY', self.start_requested.emit, True)
        self.start_button.setMinimumHeight(56)
        self.start_button.setStyleSheet('text-align: center; font-size: 22px; letter-spacing: 5px; border: none; background: transparent; color: #e5c981;')
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setFixedHeight(12)
        self.loading_bar.setStyleSheet("QProgressBar {background:#172e4a;border:0;border-radius:5px;} QProgressBar::chunk {background:#d5b56c;}")
        layout.addWidget(self.loading_bar)
        self.loading_bar.hide()
        self.can_start = True
        self.lit = True
        layout.addWidget(self.start_button)
        self.blink = QTimer(self)
        self.blink.setInterval(650)
        self.blink.timeout.connect(self.flash)

    def set_model_state(self, state):
        from gui.ui_i18n import translate_widgets
        self.can_start = state == 'ready'
        self.blink.stop()
        self.loading_bar.setVisible(state == 'loading')
        self.start_button.setText({'loading':'Modell wird geladen …', 'choose':'Modell auswählen', 'error':'Laden fehlgeschlagen · Modell auswählen', 'ready':'PRESS ENTER TO PLAY'}[state])
        translate_widgets(self.start_button, getattr(self, 'language', 'de'))
        self.start_button.setEnabled(state != 'loading')
        self.lit=False
        self.flash()
        if self.can_start:self.blink.start()

    def flash(self):
        self.lit = not self.lit
        color = '#e5c981' if self.lit else '#28334a'
        self.start_button.setStyleSheet(f'text-align: center; font-size: 22px; letter-spacing: 5px; border: none; background: transparent; color: {color};')

    def show_title(self):
        self.views.setCurrentIndex(0)
        self.lit = False
        self.flash()
        if self.can_start:self.blink.start()

    def show_demo(self):
        self.arena.clear_opponent()
        self.views.setCurrentIndex(1)
        self.log.clear()
        self.arena.pending = ''
        self.enemy.setText('Eine Begegnung erwacht …')
        self.health.setRange(0, 1)
        self.health.setValue(0)
        self.player.clear()

    def apply_attack_hp(self, event):
        # Apply authoritative HP at the visible attack, including queued effects.
        self.arena.update_state({key:event[key] for key in ('enemy_hp','player_hp') if key in event})

    def present(self, event):
        kind = event.get('event')
        if kind == 'battle' and 'enemy_hp' in event:
            self.arena.update_state(event)
        elif kind == 'battle_effect':
            self.arena.stage.show_effect(event)
        elif kind in {'output', 'error'}:
            self.arena.append_text(event.get('text', ''))
