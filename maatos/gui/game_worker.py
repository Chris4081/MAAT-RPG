"""Isolated RPG process. JSON-lines transport; never imports Qt.

Legacy plugin input/print is adapted only inside this dedicated process.
The RPG's rules, plugins and saves stay authoritative.
"""
from __future__ import annotations
import builtins
from contextlib import contextmanager, redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import threading
import traceback
import uuid
import queue
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shared.core.progression_i18n import tr as progression_text
from shared.core.chat_turn import ChatTurn, ChatCancelled
from shared.core.repetition_guard import RepetitionStopped
from gui.runtime_diagnostics import event as diagnostic, failure as diagnostic_failure
WIRE = sys.stdout
INPUT = sys.stdin
LOCK = threading.RLock()
SPEECH_CONTROL = None
COMMANDS = queue.Queue()
TURNS = {}
ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')


def emit(kind, **data):
    # Narrative fragments must precede the combat presentation boundary on the wire.
    if kind == 'battle':
        OUT.flush()
    if kind == 'level_up':
        diagnostic('level_up_emitted', level=data.get('level'))
    with LOCK:
        WIRE.write(json.dumps({'event': kind, **data}, ensure_ascii=False, default=str) + '\n')
        WIRE.flush()


class Output(io.TextIOBase):
    def __init__(self):
        self.tail = ''
        self.pending = ''
        self.combat = False

    def write(self, text):
        clean = ANSI.sub('', str(text)).replace('\r', '')
        self.tail = (self.tail + clean)[-16000:]
        self.pending += clean
        if '\n' in self.pending or len(self.pending) > 512:
            self.flush()
        return len(text)

    def flush(self, force=False):
        from shared.core.native_diagnostics import visible_diagnostics
        text, self.pending = self.pending, ''
        # llama.cpp's Python logger uses sys.stderr, which is this same adapter.
        # Keep split native lines together even when the logger flushes each piece.
        complete, separator, trailing = text.rpartition('\n')
        candidate = trailing.lstrip()
        if not force and candidate and (candidate.startswith('ggml_metal_') or 'ggml_metal_'.startswith(candidate)):
            self.pending = trailing
            text = complete + separator
        text = visible_diagnostics(text)
        if text:
            emit('output', text=text, **({'combat': True} if self.combat else {}))

    def isatty(self):
        return False


class WorkerStopped(BaseException):
    pass


def receive():
    message = COMMANDS.get()
    if message is None:
        raise WorkerStopped()
    return message


def read_controls():
    """Read controls even while llama_decode or a story prompt is busy."""
    try:
        for line in INPUT:
            try:
                message = json.loads(line)
            except (ValueError, TypeError):
                continue
            op = message.get('op')
            if op == 'stop_speech':
                if SPEECH_CONTROL: SPEECH_CONTROL(message.get('reason') or 'menu')
                continue
            if op in {'cancel_chat', 'chat_presented'}:
                turn = TURNS.get(message.get('turn_id'))
                if turn:
                    if op == 'cancel_chat':
                        if turn.cancel() and SPEECH_CONTROL: SPEECH_CONTROL('cancel')
                    else:
                        turn.presented.set()
                continue
            if message.get('turn_id') and op in {'text', 'companion_answer'}:
                TURNS[message['turn_id']] = ChatTurn(message['turn_id'])
            if op == 'shutdown':
                for turn in list(TURNS.values()): turn.cancel()
            COMMANDS.put(message)
    finally:
        for turn in list(TURNS.values()): turn.cancel()
        COMMANDS.put(None)


OUT = Output()


def prompt(text=''):
    if SPEECH_CONTROL is not None:
        SPEECH_CONTROL('decision')
    OUT.flush()
    # Preserve the original option identifiers. Never infer a destructive answer.
    choices = []
    seen = set()
    for line in OUT.tail.splitlines():
        m = re.match(r'^\s*(?:\[([0-9A-Za-z]{1,3})\]|([0-9]{1,3})[).])\s*(.+)', line)
        if m:
            key, title = (m.group(1) or m.group(2)), m.group(3).strip()
            if key in seen:
                choices = []
                seen = set()
            choices.append({'value': key, 'label': title})
            seen.add(key)
    request_id = uuid.uuid4().hex
    emit('prompt', id=request_id, text=ANSI.sub('', str(text)) or 'Weiter mit Enter', choices=choices[-30:])
    OUT.tail = ''
    while True:
        message = receive()
        if message.get('op') == 'shutdown':
            raise WorkerStopped()
        if message.get('op') == 'answer' and message.get('id') == request_id:
            emit('prompt_closed', id=request_id)
            return str(message.get('value', ''))


class RemoteAudio:
    def __init__(self, track_path=None):
        self.track_path = track_path
        self.owner = uuid.uuid4().hex
        self.active = False

    def is_available(self):
        return True

    def set_track(self, path):
        self.track_path = path

    def _play(self, path, loop):
        if path is not None:
            self.track_path = path
        if not self.track_path or not Path(self.track_path).is_file():
            return False
        self.active = True
        emit('audio', action='play', owner=self.owner, path=str(self.track_path), loop=loop)
        return True

    def start_loop(self, track_path=None):
        return self._play(track_path, True)

    def play_once(self, track_path=None):
        return self._play(track_path, False)

    def stop(self, *args, **kwargs):
        self.active = False
        emit('audio', action='stop', owner=self.owner)

    def poll(self):
        return None if self.active else 0

    def terminate(self):
        self.stop()

    kill = terminate


def install_audio():
    from shared.core import audio
    audio.ManagedAudioPlayer = RemoteAudio
    # The GUI owns mute state; still send track changes while muted.
    audio.music_enabled = lambda default=True: True
    def play(path):
        player = RemoteAudio(path)
        return player if player.play_once() else None
    audio.play_audio_process = play
    audio.stop_audio_process = lambda proc, **kw: proc.stop() if proc else None
    audio.stop_all_audio_backends = lambda: emit('audio', action='clear')
    audio.audio_available = lambda *args: True


class Runtime:
    def __init__(self, slot):
        from apps.maat_rpg import session_shared, session_bootstrap
        from shared.core import gui_bridge
        self.shared = session_shared
        self.slot = slot
        self.language = session_shared.profile_language(slot)
        session_shared.prepare_profile_runtime(slot, language_hint=self.language)
        session_shared.write_profile_manager_state({'active_profile': slot})
        self.chat_history = None
        self._pending_chat_archive = []
        self._archive_warning = False
        try:
            from shared.core.chat_history import ChatHistory
            self.chat_history = ChatHistory(session_shared.profile_slot_root(slot))
            self.chat_history.import_legacy()
        except (OSError, sqlite3.Error) as exc:
            emit('notice', text='Chatarchiv konnte nicht vollständig geöffnet werden. Das Spiel kann weiterlaufen.')
            emit('diagnostic', text=f'Chat archive: {exc}')
        from shared.core.story_campaign import set_companion_story
        set_companion_story(session_shared.load_profile_settings(slot).get('gui_perspective') == 'companion')
        gui_bridge.install(emit)
        install_audio()
        self.llm = None
        self.perf = None
        self.boot = session_bootstrap.bootstrap_rpg_session(
            root=str(ROOT), language=self.language,
            mods_plugins_dir=str(__import__('shared.core.maat_paths', fromlist=['get_mods_plugins_dir']).get_mods_plugins_dir()),
            system_prompt_rpg_appendix='',
        )
        self.context = self.boot.context
        self.context['memory_perspective'] = 'companion' if session_shared.load_profile_settings(slot).get('gui_perspective') == 'companion' else 'adventure'
        self.context.update(gui_mode=True, fast_output=True, run_scene=self.run_scene, on_first_response_token=self.stop_previous_speech)
        self.context['reality_last_activity'] = self.last_chat_activity
        try:
            from shared.core.self_evolution import SelfEvolutionEngine
            from shared.core.maat_paths import get_data_dir
            self.context['evo_engine'] = SelfEvolutionEngine(memory=None, alignment_kernel=None, identity_kernel=None, base_dir=str(get_data_dir()))
        except Exception as exc:
            self.context['evo_engine'] = None
            emit('notice', text=f'Self-Evolution nicht verfügbar: {exc}')
        self.core = self.boot.battle_core
        self.pm = self.boot.plugin_manager
        global SPEECH_CONTROL
        SPEECH_CONTROL = self.stop_speech
        from gui.ai_companion import CompanionCampaign
        self.companion = CompanionCampaign(self.shared.profile_slot_root(self.slot)/'state/ai_companion.json')
        if self.core:
            original = self.core.run_fight
            def fight(ftype, context=None):
                ctx = context if isinstance(context, dict) else self.context
                ctx.update(gui_mode=True, fast_output=True, run_scene=self.run_scene)
                if not ctx.get('title_demo_mode'):
                    ctx.pop('scripted_actions', None)
                wins_before = self.core.state.state.get('stats', {}).get('fights_won', 0)
                unlocked_before = bool(self.core.state.state.get('world', {}).get('combat_unlocked'))
                self.begin_battle(ftype, ctx)
                try:
                    with self.combat_output():
                        result = original(ftype, ctx)
                    if self.shared.load_profile_settings(self.slot).get('gui_perspective') == 'companion' and not ctx.get('title_demo_mode') and not ctx.get('editor_mode'):
                        won = self.core.state.state.get('stats', {}).get('fights_won', 0) > wins_before
                        self.companion.battle_result(won)
                        emit('companion', data=self.companion_view())
                finally:
                    emit('battle', active=False)
                    if not ctx.get('editor_mode'):
                        self.snapshot()
                from shared.core.hero_classes import finish_first_fight
                if not ctx.get('editor_mode') and isinstance(result, str) and result and finish_first_fight(
                        self.core.state, unlocked=unlocked_before,
                        demo=bool(ctx.get('title_demo_mode') or ctx.get('combat_source') == 'demo'
                                  or '--title-demo' in sys.argv)):
                    self.request_class_selection()
                return result
            self.core.run_fight = fight
        self.boot.command_router.register('/clear', lambda args: '')
        # Native menu and native introductory reading replace terminal title loops.
        if self.pm:
            for plugin in self.pm.iter_all_plugins():
                if getattr(plugin, 'plugin_id', '') == 'story_loader':
                    plugin.gui_present_story = self.present_story
                dungeon = getattr(plugin, 'dungeon', None)
                if dungeon is not None and self.core is not None:
                    dungeon.battle_core = self.core
                if getattr(plugin, 'plugin_id', '') in {'game_menu', 'rpg_intro', 'model_downloader'}:
                    continue
                hook = getattr(plugin, 'on_startup', None)
                if callable(hook):
                    try:
                        hook(self.context)
                    except Exception as exc:
                        emit('notice', text=f'{getattr(plugin, "plugin_id", "Plugin")}: {exc}')
        for notice in self.boot.notices:
            emit('notice', text=notice.message)
        router = self.boot.command_router
        commands = {**router.commands, **router.plugin_cmd_map, '/intro': {'desc': 'Einleitung lesen'}, '/models': {'desc': 'Modell-Downloader öffnen'}, '/evo': {'desc': 'Self-Evolution-Status'}}
        from shared.core.command_i18n import tr as command_text
        emit('commands', items=[{'command': k, 'description': command_text(router._resolve_desc(v.get('desc', '')), self.language)} for k, v in commands.items()])
        self.snapshot()
        self.models()
        emit('model', status='unloaded')

    def last_chat_activity(self):
        # The current turn is archived only after commit. This reads the previous
        # retained exchange, respects deletion and follows this profile's archive.
        return self.chat_history.last_activity() if self.chat_history is not None else None

    def archive_chat(self, role, text, mode='adventure'):
        """Archive final, visible dialogue, never prompts, diagnostics or demo text."""
        turn = self.context.get('gui_chat_turn')
        if turn and not turn.committed:
            turn.defer(lambda: self.archive_chat(role, text, mode))
            return
        if self.context.get('title_demo_mode'):
            return
        from datetime import datetime
        pending = getattr(self, '_pending_chat_archive', None)
        if pending is None:
            pending = self._pending_chat_archive = []
        pending.append(dict(role=role, content=text, mode=mode,
                            timestamp=datetime.now().astimezone().isoformat()))
        saved = 0
        try:
            if self.chat_history is None:
                from shared.core.chat_history import ChatHistory
                self.chat_history = ChatHistory(self.shared.profile_slot_root(self.slot))
                self.chat_history.import_legacy()
            while pending:
                identifier = self.chat_history.append(**pending[0])
                pending.pop(0)  # Only remove entries after a successful commit.
                saved += identifier is not None
            self._archive_warning = False
        except (OSError, sqlite3.Error) as exc:
            if not getattr(self, '_archive_warning', False):
                en = getattr(self, 'language', 'de') == 'en'
                emit('notice', text=('Chat history could not be saved yet. Retrying with the next chat message. Keep the game open until saving works again.' if en else
                     'Der Chatverlauf konnte noch nicht gespeichert werden. Bei der nächsten Chatnachricht wird es erneut versucht. Bitte das Spiel bis zur erfolgreichen Speicherung geöffnet lassen.'))
                diagnostic('chat_archive_write_failed', error_type=type(exc).__name__, detail=str(exc), pending=len(pending))
                emit('diagnostic', text=f'Chat archive: {exc}')
            self._archive_warning = True
        if saved:
            emit('chat_archived')

    def battle_editor_request(self, msg):
        from shared.core import battle_editor
        if msg.get('profile_slot') != self.slot:
            raise ValueError('editor_profile')
        battle_editor.require_unlocked(self.core.state.state)
        op = msg['op']
        selected = None
        if op == 'battle_editor_save':
            item = battle_editor.save(self.core.state.state, msg.get('data'),
                                      mod_id=msg.get('mod_id'), revision=msg.get('revision'))
            selected = item['id']
        elif op == 'battle_editor_play':
            mod = battle_editor.playable(self.core.state.state, msg.get('mod_id'))
            # Exercise the actual battle engine against an in-memory save. Even
            # potion use, loss, early exit and exceptions cannot alter the profile.
            import copy
            original_state = self.core.state
            sandbox = copy.copy(original_state)
            sandbox.state = copy.deepcopy(original_state.state)
            sandbox.save = lambda: None
            sandbox.state['player']['hp'] = sandbox.state['player']['max_hp']
            context = dict(self.context, editor_mode=True, combat_source='editor',
                           battle_profile=mod['battle_profile'])
            context.pop('guide_mode', None)
            self.core.state = sandbox
            try:
                self.core.run_fight(mod['fight_type'], context)
            finally:
                self.core.state = original_state
                self.core._active_context = None
            selected = mod['id']
        emit('battle_editor_result', ok=True, op=op, selected=selected,
             items=battle_editor.catalog(self.core.state.state), profile_slot=self.slot)

    def complete_chat_turn(self):
        turn = self.context.get('gui_chat_turn')
        if not turn or turn.committed:
            return
        turn.check()
        OUT.flush(force=True)
        emit('chat_generated', turn_id=turn.id)
        turn.presented.wait()
        turn.check()
        with self.game_event_output():
            turn.commit()

    def snapshot(self):
        quest_plugin = next((p for p in self.pm.iter_all_plugins() if getattr(p, "plugin_id", "") == "quests"), None) if self.pm else None
        if quest_plugin:
            for message in quest_plugin.refresh_combat_quests():
                print(message)
        summary = dict(self.shared.profile_summary(self.slot, language=self.language))
        if self.core:
            state = self.core.state.state
            summary.update(state.get('player', {}))
            from apps.maat_rpg.plugins.battle.plugin_main import get_title_for_level, _localize_level_title
            summary['level_title'] = _localize_level_title(state.get('player', {}).get('title') or get_title_for_level(summary.get('level', 1)))
            summary['fights_won'] = state.get('stats', {}).get('fights_won', 0)
            summary['final_wins'] = state.get('stats', {}).get('final_wins', 0)
            summary['boss_wins'] = state.get('stats', {}).get('boss_wins', 0)
            summary['combat_unlocked'] = bool(state.get('world', {}).get('combat_unlocked', False))
            summary['boss_progress'] = state.get('stats', {}).get('boss_progress', 0)
            summary['principles'] = state.get('world', {}).get('principles_restored', 0)
            summary['next_xp'] = self.shared.xp_needed_for_level(summary.get('level', 1) + 1)
            from shared.core.terra_journey import snapshot as journey_snapshot
            summary['journey'] = journey_snapshot(state, self.core._load_story_state())
        summary['chat_messages'] = int(self.core.state.state.get('quests',{}).get('meta',{}).get('messages_total',0)) if self.core else 0
        from shared.core.hero_classes import selected_class, choice_pending
        summary['hero_class'] = selected_class(self.core.state.state) if self.core else 'normal'
        summary['class_choice_pending'] = choice_pending(self.core.state.state) if self.core else False
        emit('profile', data=summary)
        from shared.core.talents import snapshot as talent_snapshot
        emit('talents', data=talent_snapshot(self.core.state.state if self.core else {},self.language))
        emit('dungeons',level=summary.get('level',1),records=self.core.state.state.get('dungeon_runs',{}) if self.core else {},plus=self.core.state.state.get('dungeon_plus',{}) if self.core else {})
        from shared.core.shop_catalog import shop_snapshot
        shop_data = shop_snapshot(self.core.state.state.get('player', {}) if self.core else {})
        quest_plugin = next((p for p in self.pm.iter_all_plugins() if getattr(p, 'plugin_id', '') == 'quests'), None) if self.pm else None
        shop_data['contracts'] = quest_plugin.contract_board() if quest_plugin else []
        shop_data['earned_titles'] = self.core.state.state.get('player', {}).get('earned_titles', []) if self.core else []
        emit('shop', data=shop_data)
        self.quest_snapshot()
        if self.core:
            from shared.core.minigames import offer
            emit("minigame", data=offer(self.core.state.state))
            self.core.state.save()
        from shared.core.achievement_catalog import snapshot as achievement_snapshot
        from shared.core.maat_paths import state_file
        def saved_achievements(filename):
            try:
                with open(state_file(filename),encoding='utf-8') as f:return json.load(f)
            except (OSError,ValueError):return {}
        achievement_data=achievement_snapshot(self.core.state.state if self.core else {},
             saved_achievements('achievements_state.json'),saved_achievements('achievements.json'),self.language)
        if self.core:
            from shared.core.achievement_history import enrich
            achievement_data=enrich(self.core.state.state,achievement_data,self.language)
            self.core.state.save()
        emit('achievements',data=achievement_data)

    def quest_snapshot(self):
        plugin = next((p for p in self.pm.iter_all_plugins() if getattr(p, 'plugin_id', '') == 'quests'), None) if self.pm else None
        groups = {}
        statuses = {'active':'Aktive Aufgabe', 'available':'Bereit zum Annehmen', 'locked':'Wird im Spielverlauf freigeschaltet', 'completed':'Abgeschlossen'}
        if plugin:
            plugin._refresh_daily_quests()
            for group,status in statuses.items():
                groups[group] = []
                for quest in plugin.qstate.get(group, []):
                    if not isinstance(quest, dict):
                        continue
                    display = plugin._quest_display(quest)
                    from shared.core.talents import grants_quest_point
                    target = (quest.get('required_days') or quest.get('days') or 1) if quest.get('type') == 'daily_streak' else quest.get('target')
                    progress = int(quest.get('progress', 0) or 0)
                    if quest.get('counter_key') == 'messages_total' and not quest.get('purchase_price'):
                        progress = max(progress, int(plugin.qstate.get('meta', {}).get('messages_total', 0)))
                    text = lambda value, **values: progression_text(value,self.language,**values)
                    status_label = text(status)
                    if quest.get('purchase_price') and group == 'locked':
                        status_label = text('Auftragsbrett · {gold} Gold',gold=quest['purchase_price'])
                    elif quest.get('daily_reset'):
                        status_label = text('Heute erledigt · morgen erneut' if group == 'completed' else 'Täglich wiederholbar')
                    if int(quest.get('level_tier',0)) > 0:
                        status_label += text(' · Stufe {level}',level=plugin._quest_unlock_level(quest))
                    if group == 'locked' and quest.get('requires_combat'):
                        status_label += text(' · Kampfmodus freischalten')
                    groups[group].append(dict(id=quest.get('id',''), name=display.get('name','Quest'), desc=display.get('desc',''),
                        category=quest.get('quest_category', 'other'),
                        talent_points=1 if grants_quest_point(quest) else 0,
                        progress=progress, target=target, progress_text=plugin._quest_progress_text(quest),
                        is_daily=quest.get('type') == 'daily_streak', completed=group == 'completed',
                        effective_xp=plugin._quest_xp_effective(quest), path_bonus=plugin._quest_path_bonus_preview(quest),
                        status_label=status_label))
        emit('quests', data={'groups':groups})

    def models(self):
        from shared.core.llm_loader import list_available_models, load_saved_model_name, load_saved_perf
        items = [name for name in list_available_models() if name.lower().endswith('.gguf')]
        selected = load_saved_model_name()
        if selected and Path(selected).is_absolute() and Path(selected).is_file() and Path(selected).suffix.lower() == '.gguf' and selected not in items:
            items.append(selected)
        from shared.core.model_safety import previous_load_attempt
        emit('models', items=items, selected=selected, performance=load_saved_perf(), previous_load_attempt=previous_load_attempt())

    def restore_chat_prompt(self):
        """Rebind each backend to the session's identity without discarding memories."""
        conversation=self.boot.conversation
        base=self.boot.system_prompt.strip()
        if base:
            if conversation and conversation[0].get('role')=='system':
                current=str(conversation[0].get('content') or '')
                if not current.startswith(base):
                    conversation[0]=dict(conversation[0],content=base+('\n\n'+current if current else ''))
            else:
                conversation.insert(0,{'role':'system','content':base})
        self.context['conversation']=conversation

    def unload_model(self):
        """Free native buffers while Python and the Metal device are still alive.

        Plugin callbacks retain this Runtime in reference cycles. Dropping the
        last obvious reference does not guarantee Llama.__del__ runs before
        ggml's process-exit destructor checks for outstanding Metal resources.
        """
        model = getattr(self, '_unreleased_model', None)
        if model is None:
            model = self.llm
        if model is None:
            return
        # A failed close can leave partially freed buffers. Keep ownership for
        # another cleanup attempt, but never expose that model as chat-ready.
        self._unreleased_model = model
        self.context.pop('llm', None)
        self.llm = None
        instance = model.get('instance') if isinstance(model, dict) else model
        diagnostic('model_release_begin', backend=model.get('backend') if isinstance(model, dict) else None)
        close = getattr(instance, 'close', None)
        if callable(close):
            close()
        self._unreleased_model = None
        import gc
        gc.collect()
        diagnostic('model_release_done')

    def load_model(self, name, backend='llama', n_ctx=20000, temperature=.8, tuning=None):
        load_started = time.monotonic()
        diagnostic('model_load_requested', model=Path(name).name, context=n_ctx)
        from shared.core.llm_loader import list_available_models, save_last_model_choice, save_perf
        from shared.core.maat_paths import get_models_dir
        path = Path(name) if Path(name).is_absolute() else get_models_dir() / name
        if (not Path(name).is_absolute() and name not in list_available_models()) or not path.is_file() or path.suffix.lower() != '.gguf':
            raise ValueError('Bitte eine vorhandene GGUF-Datei auswählen.')
        with path.open('rb') as model_file:
            if model_file.read(4) != b'GGUF':
                raise ValueError('Die ausgewählte Datei ist keine gültige GGUF-Datei.')
        from shared.core.hardware_profile import detect_hardware, automatic_settings
        from shared.core.gguf_adapters import selected_adapter
        from shared.core.intel_runtime import prepare_library
        from shared.core.model_settings import normalize_tuning, resolve_settings, normalize_context
        if tuning is None:
            tuning = self.shared.load_profile_settings(self.slot).get('gui_model_tuning')
        tuning = normalize_tuning(tuning)
        n_ctx = normalize_context(n_ctx)
        prepare_library()
        detected = detect_hardware()
        adapter = selected_adapter(detected.get('machine', ''))
        if adapter == 'llama_intel':
            from shared.core.intel_gguf_backend import automatic_settings as adapter_settings
        else:
            adapter_settings = automatic_settings
        hardware = resolve_settings(adapter_settings(detected, path), tuning, n_ctx)
        diagnostic('model_backend_route', requested=backend, selected=adapter,
                   machine=detected.get('machine'), backend_info=detected.get('backend_info', ''),
                   library_path=detected.get('library_path', ''),
                   cpu_variant=os.environ.get('MAAT_CPU_VARIANT', 'default'),
                   tuning_mode=tuning['mode'])
        diagnostic('model_load_settings', model=path.name, context=n_ctx, hardware=hardware)
        emit('hardware', data=hardware)
        perf = dict(n_ctx=n_ctx, temperature=max(0., min(2., float(temperature))), top_p=.9,
                    gui_mode=True, raise_errors=True, backend=adapter, threads=hardware['threads'], gpu_layers=hardware['gpu_layers'],
                    model_tuning=tuning, load_options=dict(hardware['options']))
        # Unload first so model changes do not require two full models in RAM.
        self.unload_model()
        diagnostic('previous_model_released')
        from shared.core.model_safety import check_model_safety, mark_load_attempt, clear_load_attempt
        safety = check_model_safety(path, perf['n_ctx'], hardware)
        diagnostic('model_load_memory', **safety)
        emit('model_safety', data=safety)
        # Persist before native allocation: an OS crash must not trigger the
        # same automatic load again at the next application start.
        mark_load_attempt(name, perf['n_ctx'])
        emit('model', status='loading', name=name)
        from shared.core.backend_router import load_backend
        from importlib.metadata import version, PackageNotFoundError
        try:
            backend_version = version('llama-cpp-python')
        except PackageNotFoundError:
            backend_version = 'unknown'
        diagnostic('native_model_allocation_begin', backend_version=backend_version,
                   cpu_variant=os.environ.get('MAAT_CPU_VARIANT', 'default'))
        loading_log = io.StringIO()
        with redirect_stdout(loading_log):
            # A changed backend/cache layout needs a fresh safety check. Do not
            # silently retry a failed GPU allocation with different CPU options.
            self.llm = load_backend(str(path), backend=adapter, max_ctx=perf['n_ctx'], temperature=perf['temperature'], n_threads=perf['threads'], n_gpu_layers=perf['gpu_layers'], load_options=hardware['options'], allow_cpu_fallback=False)
            diagnostic('native_model_allocation_done', seconds=round(time.monotonic()-load_started, 3))
            diagnostic('model_backend_loaded', selected=self.llm.get('backend'),
                       settings=self.llm.get('load_settings', {}),
                       fallback=self.llm.get('hardware_fallback'))
            if adapter == 'llama_intel' and self.llm.get('load_settings', {}).get('repack_weights', False) is None:
                hardware['adjustments'].append('intel_repack_unavailable')
                emit('hardware', data=hardware)
            if self.llm.get('hardware_fallback'):
                hardware['acceleration'] = 'CPU (GPU-Laden fehlgeschlagen)'
                hardware['gpu_layers'] = 0
                hardware['options'].update(n_batch=128, n_ubatch=64)
                perf['gpu_layers'] = 0
                perf['load_options'] = dict(self.llm.get('load_settings', hardware['options']))
                emit('hardware', data=hardware)
                emit('diagnostic', text=self.llm['hardware_fallback'])
            self.llm['_maat_perf'] = perf
            self.context['llm'] = self.llm
            self.restore_chat_prompt()
            self.perf = perf
            save_last_model_choice(name)
            save_perf(perf)
            self.shared.write_profile_settings(self.slot, {'gui_model_tuning': tuning})
        clear_load_attempt()
        diagnostic('model_ready', model=path.name, seconds=round(time.monotonic()-load_started, 3))
        if loading_log.getvalue():
            emit('diagnostic', text=loading_log.getvalue())
        from shared.core.rpg_generation_context import model_architecture
        from shared.core.model_family import model_family
        emit('model', status='ready', name=name, architecture=model_architecture(self.llm), family=model_family(self.llm))
        if getattr(self, 'companion_active', False) and self.shared.load_profile_settings(self.slot).get('gui_perspective') == 'companion':
            # Keep the existing human Maatis role and dialogue; loading is not a new turn.
            self.free_companion=True
            emit('companion',data=self.companion_view())

    def request_class_selection(self):
        from shared.core.hero_classes import choice_pending, choose_class
        if not self.core or not choice_pending(self.core.state.state):
            return
        self.stop_speech('class_selection')
        OUT.flush()
        request_id = uuid.uuid4().hex
        emit('class_selection', id=request_id)
        while True:
            message = receive()
            if message.get('op') == 'shutdown':
                raise WorkerStopped()
            if message.get('op') == 'stop_speech':
                self.stop_speech('class_selection')
            if message.get('op') == 'class_select' and message.get('id') == request_id:
                try:
                    value = choose_class(self.core.state, message.get('value'))
                except (ValueError, OSError) as exc:
                    emit('class_error', id=request_id, text='Klasse konnte nicht gespeichert werden: ' + str(exc))
                    continue
                emit('class_selected', id=request_id, value=value)
                self.snapshot()
                return

    def present_story(self, lines, music, entry, *, remember=True):
        self.stop_speech('story')
        OUT.flush()
        request_id = uuid.uuid4().hex
        from shared.core.story_campaign import companion_story_active
        artwork = None
        if companion_story_active():
            from gui.companion_stories import scene_payload, SCENES
            module = entry.get('module', '')
            if module in SCENES:
                alternate = scene_payload(module, getattr(self, 'language', 'de'))
                if module == 'credits':
                    credit_start=next((i for i,line in enumerate(lines) if 'MAAT-RPG — Credits' in line),len(lines))
                    credit_end=next((i for i in range(credit_start,len(lines)) if any(marker in lines[i] for marker in ('Spezielle Danksagung', 'Special thanks'))),len(lines))
                    lines = list(alternate['lines']) + ['','─',''] + lines[credit_start:credit_end]
                else:
                    lines = alternate['lines']
                artwork = alternate['image']
                entry = dict(entry, name=alternate['name'], module=alternate['module'])
            elif module == 'reflection':
                artwork = 'ai-keeper.png'
                entry = dict(entry, module='companion_reflection')
        emit('story_scene', id=request_id, lines=lines, music=music, image=artwork, language=getattr(self, 'language', 'de'),
             name=entry.get('name', 'Geschichte'), module=entry.get('module','story1'))
        while True:
            message = receive()
            if message.get('op') == 'shutdown':
                raise WorkerStopped()
            if message.get('op') == 'story_done' and message.get('id') == request_id:
                if remember and companion_story_active() and hasattr(self, 'companion'):
                    self.companion.state['memories'].append(dict(title=entry.get('name', 'Gemeinsame Geschichte'),
                        answer='', decision='Experienced with Maatis' if self.language == 'en' else 'Mit Maatis erlebt', reaction=' '.join(lines[-3:])))
                    self.companion.state['memories'] = self.companion.state['memories'][-30:]
                    self.companion.save()
                return

    def replay_credits(self, profile_slot):
        from shared.core.terra_replay import unlocked
        from gui.cutscenes import cutscene_payload
        if profile_slot != self.slot:
            raise ValueError('Das Profil hat sich geändert. Bitte die Karte erneut öffnen.')
        if not self.core or not unlocked(self.core.state.state):
            raise ValueError('Das Ende der Welt öffnet sich nach dem fünften Finale.')
        payload = cutscene_payload(ROOT/'apps/maat_rpg/plugins/battle/credits.py', getattr(self, 'language', 'de'))
        if not payload:
            raise ValueError('Der Abspann konnte nicht gefunden werden.')
        self.stop_speech('credits')
        self.present_story(**payload, remember=False)

    def run_scene(self, path):
        self.stop_speech('scene')
        from gui.cutscenes import cutscene_payload
        payload = cutscene_payload(path, getattr(self, 'language', 'de'))
        if payload is not None:
            self.present_story(**payload)
            return
        import runpy
        emit('scene', name=Path(path).stem)
        module = runpy.run_path(str(path), run_name='maat_gui_scene')
        if callable(module.get('main')):
            module['main']()

    def intro(self):
        self.stop_speech('intro')
        import runpy
        mod = runpy.run_path(str(ROOT / 'apps/maat_rpg/plugins/rpg_intro/plugin_main.py'))
        emit('scene', name='Die Rückkehr der Prinzipien')
        track = ROOT / 'apps/maat_rpg/plugins/rpg_intro' / ('Intro_EN.mp3' if self.language == 'en' else 'intro.mp3')
        music = RemoteAudio(str(track))
        music.play_once()
        try:
            lines = mod['INTRO_TEXT'].get(self.language, mod['INTRO_TEXT']['de'])
            for i in range(0, len(lines), 4):
                print('\n'.join(lines[i:i+4]))
                if prompt('Enter: weiter · q: Intro beenden').lower() == 'q':
                    break
        finally:
            music.stop()

    def companion_view(self):
        view = self.companion.view()
        if getattr(self, 'free_companion', False) or not self.companion.state.get('identity_answered', False):
            view.update(scene=None, playstyle='free', last=None)
        return view

    def begin_battle(self, ftype, context):
        self.stop_speech('random_battle' if context.get('combat_source') == 'random' else 'battle')
        emit('battle', active=True, enemy_name='', enemy_hp=0, enemy_max_hp=0,
             fight_type=ftype, enemy_level=None, combat_source=context.get('combat_source'),
             arena_difficulty=context.get('arena_difficulty'))

    def stop_speech(self, reason='menu'):
        if getattr(self, 'pm', None):
            for plugin in self.pm.iter_all_plugins():
                cancel = getattr(plugin, 'cancel_speech', None)
                if not callable(cancel):
                    cancel = getattr(plugin, 'begin_response_speech', None)
                if callable(cancel):
                    cancel()
        emit('speech_stopped', reason=reason)

    @contextmanager
    def combat_output(self):
        """Tag the whole encounter, including rewards after the final HUD update."""
        OUT.flush()
        previous, OUT.combat = OUT.combat, True
        try:
            yield
        finally:
            OUT.flush()
            OUT.combat = previous

    @contextmanager
    def game_event_output(self):
        """Keep plugin text ordered without interrupting spoken chat.

        Stories, battles, decisions and menus stop speech at their explicit
        entry points. Achievements, XP and other status output may coexist.
        """
        OUT.flush()
        try:
            yield
        finally:
            OUT.flush()

    def stop_previous_speech(self):
        if getattr(self, 'pm', None):
            for plugin in self.pm.iter_all_plugins():
                cancel = getattr(plugin, 'begin_response_speech', None)
                if callable(cancel):
                    cancel()

    def maatis_dialogue(self, text=None):
        from shared.core.streaming import stream_chat_completion, stream_to_console
        memory=getattr(self,'context',{}).get('super_memory')
        if memory:
            memory.sync_context(self.context)
        if getattr(self,'context',{}).pop('super_memory_reset_dialogue',False):
            self.companion.state['dialogue'] = []
        from shared.core.conversation_history import MAX_MESSAGES
        history = self.companion.state.get('dialogue', [])[-MAX_MESSAGES:]
        from shared.core.companion_prompt import build_companion_prompt
        language = getattr(self, 'language', 'de')
        system = build_companion_prompt(language)
        request = text if text is not None else (
            'Continue our conversation. Refer to my last answer or a shared memory and ask one open question.'
            if language == 'en' else
            'Setze unser Gespräch fort. Greife meine letzte Antwort oder eine gemeinsame Erinnerung auf und stelle eine offene Frage.')
        conversation = [{'role':'system','content':system}] + history + [{'role':'user','content':request}]
        OUT.flush(force=True)
        emit('chat_generation')
        self._companion_response_id = uuid.uuid4().hex
        emit('chat_response', action='begin', id=self._companion_response_id)
        print('Maatis: ', end='', flush=True)
        perf = dict(self.perf or {}, max_tokens=512, gui_mode=True, raise_errors=True)
        reply = stream_to_console(stream_chat_completion(self.llm, conversation, perf, [], runtime_context=dict(getattr(self,'context',{}),on_first_response_token=self.stop_previous_speech)), echo=True, raise_errors=True, on_first_visible=lambda: emit('chat_first_token')) or ''
        if not reply.strip():
            raise RuntimeError('Maatis hat keine sichtbare Antwort erzeugt. Bitte erneut versuchen oder Thinking im KI-Menü ausschalten.')
        OUT.flush(force=True)
        emit('chat_response', action='end', id=self._companion_response_id)
        self.complete_chat_turn()
        if reply.strip():
            self.companion.state['dialogue'] = (history + [{'role':'user','content':request}, {'role':'assistant','content':reply}])[-MAX_MESSAGES:]
            self.companion.save()
            self.archive_chat('assistant', reply, 'companion')
        print()
        return reply

    def select_story_campaign(self, companion):
        from shared.core.story_campaign import set_companion_story, story_state_file
        set_companion_story(companion)
        self.companion_active = companion
        self.context['memory_perspective'] = 'companion' if companion else 'adventure'
        if self.pm:
            for plugin in self.pm.iter_all_plugins():
                if getattr(plugin, 'plugin_id', '') == 'story_loader' and str(plugin.state_path) != str(story_state_file()):
                    plugin._save_state()
                    plugin.state_path = story_state_file()
                    plugin.state = plugin._load_state()
                    plugin._inject_story_context(self.context)

    def companion_start(self):
        self.select_story_campaign(True)
        self.free_companion = self.llm is not None
        emit('companion', data=self.companion_view())
        if not self.companion.state.get('identity_answered', False):
            # Authored opening: predictable, streamed by the GUI, never generated twice.
            print('Maatis: Wer bist du?')
            self.archive_chat('assistant', 'Wer bist du?', 'companion')
            return
        if self.free_companion:
            self.maatis_dialogue()
            return
        scene = self.companion.view()['scene']
        question = scene['question'] if scene else 'Maatis: Was möchtest du als Nächstes entdecken?'
        print('\n' + question)
        self.archive_chat('assistant', question, 'companion')

    def companion_answer(self, text, choice):
        from gui.ai_companion import validate_reply_length
        validate_reply_length(text)
        self._companion_response_id = None
        self.select_story_campaign(True)
        introducing = not self.companion.state.get('identity_answered', False)
        free_dialogue = getattr(self, 'free_companion', False) and self.llm is not None
        scene = self.companion.view()['scene']
        if not introducing and not free_dialogue and scene and choice not in range(len(scene['options'])):
            raise ValueError('Wähle zuerst eine Entscheidung für deine Antwort.')
        self.archive_chat('user', text, 'companion')
        if introducing:
            self.companion.state['identity_answered'] = True
            self.companion.state.setdefault('dialogue', []).extend([
                {'role':'assistant', 'content':'Wer bist du?'},
                {'role':'user', 'content':text},
            ])
            self.companion.state['memories'].append(dict(title='Unsere erste Begegnung', answer=text[:2000],
                decision='Ich stelle mich Maatis vor', reaction='Maatis hört deiner eigenen Stimme zu.'))
            self.companion.save()
            # Present the first answer's scene before random encounters or other
            # hooks, including when entering this campaign on an older profile.
            if self.pm:
                story = next((p for p in self.pm.iter_all_plugins() if getattr(p, 'plugin_id', '') == 'story_loader'), None)
                if story and 1 not in story.state.get('played', []):
                    entry = next((e for e in story.config['stories'] if e.get('id') == 1), None)
                    if entry:
                        story._play_story_entry(entry, self.context)
        self.context.update(last_user_input=text, conversation=self.boot.conversation)
        if self.pm:
            with self.game_event_output():
                handled, out = self.pm.handle_before_chat(text, self.context)
            if handled:
                if out:
                    print(out)
                    self.archive_chat('assistant', out, 'companion')
                return
            if isinstance(out, str) and out.strip():
                text = out
        if introducing:
            reply = 'Danke, dass du mir von dir erzählst. Was möchtest du mit mir über diese Welt herausfinden?'
            print('Maatis: ' + reply)
            self.archive_chat('assistant', reply, 'companion')
            if not free_dialogue and scene:
                print(scene['question'])
                self.archive_chat('assistant', scene['question'], 'companion')
            self.companion.state.setdefault('dialogue', []).append({'role':'assistant','content':reply})
            self.companion.save()
            self.companion_after_response(reply)
            emit('companion', data=self.companion_view())
            return
        if getattr(self, 'free_companion', False) and self.llm is not None:
            from gui.ai_companion import validate_reply_length
            validate_reply_length(text)
            reply = self.maatis_dialogue(text)
            self.companion_after_response(reply)
            emit('companion', data=self.companion_view())
            return
        result = self.companion.answer(text, choice)
        view = self.companion.view()
        emit('companion', data=view)
        if result:
            print('Maatis: ' + result['reaction'])
            self.archive_chat('assistant', result['reaction'], 'companion')
        reply = result['reaction'] if result else ''
        if self.llm is not None:
            from shared.core.streaming import stream_chat_completion, stream_to_console
            scene = view['scene']
            from shared.core.companion_prompt import build_reaction_prompt
            facts = dict(trust=view['trust'], reaction=result['reaction'] if result else None,
                         next_question=scene['question'] if scene else None)
            conversation = [
                {'role':'system', 'content':build_reaction_prompt(self.language)},
                {'role':'user', 'content':json.dumps({'spielzustand':facts,'antwort_der_begleiter_ki':text}, ensure_ascii=False)}]
            emit('chat_generation')
            try:
                OUT.flush(force=True)
                self._companion_response_id = uuid.uuid4().hex
                emit('chat_response', action='begin', id=self._companion_response_id)
                reply = stream_to_console(stream_chat_completion(self.llm, conversation, self.perf, [], runtime_context=dict(getattr(self,'context',{}),on_first_response_token=self.stop_previous_speech)), echo=True, raise_errors=True, on_first_visible=lambda: emit('chat_first_token'))
                OUT.flush(force=True)
                emit('chat_response', action='end', id=self._companion_response_id)
                self.complete_chat_turn()
                self.archive_chat('assistant', reply, 'companion')
            except Exception as exc:
                emit('notice', text=f'Maatis nutzt die geschriebene Reaktion; lokale Erzählung nicht verfügbar: {exc}')
        elif not result:
            fallback = 'Maatis: Ich höre dir zu. Für freie Gespräche lade bitte ein lokales GGUF-Modell; die Aufgaben funktionieren auch ohne Modell.'
            print(fallback)
            self.archive_chat('assistant', fallback, 'companion')
        self.companion_after_response(reply)
        scene = view['scene']
        if scene:
            print('\n' + scene['question'])
            self.archive_chat('assistant', scene['question'], 'companion')
        elif result:
            closing = 'Maatis: Der erste Aufgabenbogen ist abgeschlossen. Wir können weiterreden oder gemeinsam in die Arena gehen.'
            print('\n' + closing)
            self.archive_chat('assistant', closing, 'companion')

    def companion_after_response(self, reply):
        self.complete_chat_turn()
        if self.pm:
            with self.game_event_output():
                updated = self.pm.handle_after_response(reply or '', self.context)
            if updated and updated != reply:
                identifier = getattr(self, '_companion_response_id', None)
                if identifier:
                    OUT.flush(force=True)
                    emit('chat_response', action='replace', id=identifier, original=reply, text=updated)
                elif reply and updated.startswith(reply):
                    print(updated[len(reply):])

    def ensure_maatis_chat_opening(self):
        """Old saves could mark story 1 played before the first GUI chat."""
        if not self.pm:
            return
        story = next((p for p in self.pm.iter_all_plugins() if getattr(p, 'plugin_id', '') == 'story_loader'), None)
        if not story or story.state.get('gui_first_chat_opening_seen'):
            return
        entry = next((e for e in story.config['stories'] if e.get('id') == 1), None)
        if not entry:
            return
        if 1 in story.state.get('played', []):
            # Replay only the presentation, without replaying profile changes,
            # journal rewards or resetting any counters from the saved game.
            scene = story._load_story_module(entry['module'], entry)
            if scene is None:
                return
            story._run_story_interactive(scene, entry.get('music'), entry=entry)
        else:
            story._play_story_entry(entry, self.context)
        story.state['gui_first_chat_opening_seen'] = True
        story._save_state()

    def text(self, text):
        if text == '/dungeon-plus':
            from shared.core.dungeon_campaign import run_endless
            run_endless(self.core,self.present_story,emit,on_progress=self.snapshot,language=self.language)
            return
        if text.startswith('/dungeon-enter '):
            from shared.core.dungeon_campaign import run
            run(self.core,int(text.split()[-1]),self.present_story,emit,on_progress=self.snapshot,language=self.language)
            return
        legacy_dungeons={'/dungeon60':0,'/d500':1,'/d1000':2}
        if text.split(' ')[0] in legacy_dungeons:
            if len(text.split())>1:
                from shared.core.gameplay_i18n import tr
                print(tr('Öffne Dungeons in der Seitenleiste. Die fünf Räume folgen dort automatisch aufeinander.', self.language))
            else:
                from shared.core.dungeon_campaign import run
                run(self.core,legacy_dungeons[text],self.present_story,emit,on_progress=self.snapshot,language=self.language)
            return
        if text == '/ai-training':
            self.select_story_campaign(True)
            self.companion_active = True
            self.free_companion = False
            emit('companion', data=self.companion_view())
            scene = self.companion.view()['scene']
            print(scene['question'] if scene else 'Aufgabenbogen abgeschlossen.')
            return
        if text == '/ai-start':
            self.companion_start()
            return
        if text == '/evo':
            evo = self.context.get('evo_engine')
            print(evo.get_status_text() if evo else 'Self-Evolution nicht aktiv.')
            return
        if text == '/models':
            from apps.maat_rpg.plugins.model_downloader.plugin_main import ensure_model
            ensure_model(str(ROOT / 'apps/maat_rpg/plugins/model_downloader'), force_open=True)
            self.models()
            return
        if text == '/intro':
            self.intro()
            return
        if text.strip() in {'/menu', '/menü'}:
            self.stop_speech('menu')
            emit('navigate', page=0)
            return
        if text.startswith('/'):
            result = self.boot.command_router.execute(text, self.context)
            if result:
                print(result)
            if text.startswith(('/shop buy ', '/contracts buy ')):
                emit('shop_result', text=result or '')
            if self.context.pop('reset_conversation_after_battle', False):
                self.boot.conversation[:] = self.boot.conversation[:1]
            return
        if self.llm is None:
            raise ValueError('Noch kein KI-Modell geladen. Wähle unter Einstellungen ein lokales Modell und klicke auf Laden.')
        self.archive_chat('user', text)
        self.select_story_campaign(False)
        self.ensure_maatis_chat_opening()
        self.restore_chat_prompt()
        conversation = self.boot.conversation
        self.context.update(conversation=conversation, last_user_input=text)
        if self.pm:
            with self.game_event_output():
                handled, out = self.pm.handle_before_chat(text, self.context)
            if handled:
                if out:
                    print(out)
                    self.archive_chat('assistant', out)
                return
            if isinstance(out, str) and out.strip():
                text = out
        pending_message = {'role': 'user', 'content': text}
        self.context['_pending_chat_message'] = pending_message
        conversation.append(pending_message)
        from shared.core import streaming
        streaming.key_pressed = lambda: False
        streaming.FIRST_RUN_DONE = True
        from shared.core.streaming import stream_chat_completion, stream_to_console
        guarded = bool(self.pm and self.pm.has_before_final_response(self.context))
        plugins = [] if guarded else (self.pm.get_streaming_plugins() if self.pm else [])
        OUT.flush(force=True)
        emit('chat_generation')
        response_id = uuid.uuid4().hex
        emit('chat_response', action='begin', id=response_id)
        self.restore_chat_prompt()
        generator = stream_chat_completion(self.llm, conversation, self.perf, plugins, runtime_context=self.context)
        # Existing thinking filter and streaming hooks remain authoritative.
        reply = stream_to_console(generator, echo=not guarded, raise_errors=True, on_first_visible=lambda: emit('chat_first_token')) or ''
        if not reply.strip():
            raise RuntimeError('Das Modell hat keine Antwort erzeugt. Bitte erneut versuchen.')
        if guarded:
            result = self.pm.handle_before_final_response(reply, self.context)
            if result is not None:
                reply = result
            print(reply)
        OUT.flush(force=True)
        emit('chat_response', action='end', id=response_id)
        self.complete_chat_turn()
        original = reply
        if self.pm:
            with self.game_event_output():
                result = self.pm.handle_after_response(reply, self.context)
            if result is not None:
                reply = result
        if guarded:
            self.pm.handle_after_final_response(reply, self.context)
        if reply != original:
            OUT.flush(force=True)
            emit('chat_response', action='replace', id=response_id, original=original, text=reply)
        conversation.append({'role': 'assistant', 'content': reply})
        self.archive_chat('assistant', reply)
        evo = self.context.get('evo_engine')
        if evo is not None:
            try:
                result = evo.evaluate_from_context(reply, self.context)
                if result and result.get('status') == 'applied':
                    print(progression_text('KI-Entwicklung: +{xp} XP', self.language, xp=result.get('xp_gained', 50)))
            except Exception as exc:
                emit('notice', text=f'Self-Evolution: {exc}')
        rpg = self.context.get('rpg', {})
        rpg['messages_since_reset'] = rpg.get('messages_since_reset', 0) + 1
        if rpg['messages_since_reset'] >= 25:
            conversation[:] = conversation[:1]
            rpg['messages_since_reset'] = 0
        from shared.core.conversation_history import MAX_MESSAGES
        conversation[:] = conversation[:1] + conversation[1:][-MAX_MESSAGES:]


def main():
    sys.stdout = OUT
    sys.stderr = OUT
    builtins.input = prompt
    try:
        # Explicit private data root for tests or portable installations; never changes HOME.
        override = os.environ.get('MAAT_GUI_DATA_ROOT')
        if override:
            from shared.core import maat_paths
            def base():
                path = Path(override).resolve()
                path.mkdir(parents=True, exist_ok=True)
                return path
            maat_paths.get_default_app_support_dir = base
            maat_paths._default_app_support_dir = base
        from gui.runtime_diagnostics import configure
        diagnostics_path = configure('worker', announce=False)
        if diagnostics_path:
            emit('diagnostic', text=f'MAAT worker log: {diagnostics_path}\n')
        runtime = Runtime(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
        threading.Thread(target=read_controls, daemon=True).start()
        OUT.flush()
        emit('ready')
        if '--title-demo' in sys.argv:
            import time
            stage = int(sys.argv[sys.argv.index('--title-demo') + 1]) % 3
            menu = next(p for p in runtime.pm.iter_all_plugins() if getattr(p, 'plugin_id', '') == 'game_menu')
            menu._title_demo_stage = stage
            menu._title_key_pressed = lambda: (time.sleep(.02) or False)
            menu._run_title_demo({'rpg': {'battle_core': runtime.core}})
            return 0
        while True:
            msg = receive()
            if msg.get('op') == 'shutdown':
                break
            if msg.get('op') == 'stop_speech':
                runtime.stop_speech('menu')
                continue
            emit('busy', value=True)
            OUT.tail = ''
            turn = TURNS.get(msg.get('turn_id'))
            if turn:
                runtime.context['gui_chat_turn'] = turn
            try:
                if msg.get('op') == 'text':
                    runtime.request_class_selection()
                    runtime.text(str(msg.get('text', '')))
                elif msg.get('op') in ('battle_editor_list', 'battle_editor_save', 'battle_editor_play'):
                    try:
                        runtime.battle_editor_request(msg)
                    except (ValueError, OSError) as exc:
                        emit('battle_editor_result', ok=False, op=msg['op'], profile_slot=runtime.slot,
                             error=str(exc) if str(exc).startswith('editor_') else 'editor_io')
                elif msg.get('op') == 'class_resume':
                    runtime.request_class_selection()
                elif msg.get('op') == 'terra_credits':
                    try:
                        runtime.replay_credits(msg.get('profile_slot'))
                    except (ValueError, OSError) as exc:
                        from shared.core.gameplay_i18n import tr as map_text
                        emit('terra_credits_error',text=map_text('Abspann nicht geöffnet: {error}',runtime.language,
                            error=map_text(str(exc),runtime.language)))
                elif msg.get('op') in ('terra_replay', 'terra_random'):
                    from shared.core.terra_replay import queue, select_random
                    from shared.core.gameplay_i18n import tr as map_text
                    from shared.core.monster_catalog import enemy_display_name
                    try:
                        if msg.get('profile_slot') != runtime.slot:
                            raise ValueError('Das Profil hat sich geändert. Bitte die Karte erneut öffnen.')
                        if msg.get('op') == 'terra_random':
                            select_random(runtime.core.state)
                            text=map_text('Zufallskämpfe aktiv · Normale Gegner erscheinen weiterhin beim Chatten.',runtime.language)
                        else:
                            target = queue(runtime.core.state, msg.get('target'))
                            text=map_text('Vorgemerkt: {name} · Beim nächsten Zufallskampf im Chat.',runtime.language,
                                name=enemy_display_name(target['name'],runtime.language))
                        emit('terra_replay_result', ok=True, text=text)
                    except (ValueError, OSError) as exc:
                        emit('terra_replay_result', ok=False, text=map_text('Kampfauswahl nicht gespeichert: {error}',runtime.language,
                            error=map_text(str(exc),runtime.language)))
                elif msg.get('op') == 'talent_buy':
                    from shared.core.talents import buy
                    try:
                        if msg.get('profile_slot') != runtime.slot:
                            raise ValueError(progression_text('Das Profil hat sich geändert. Bitte den Talentbaum erneut öffnen.',runtime.language))
                        receipt = buy(runtime.core.state, msg.get('talent'),
                                      expected_rank=msg.get('rank'), class_id=msg.get('class_id'),language=runtime.language)
                        emit('talent_result', ok=True, text=receipt)
                    except (ValueError, OSError) as exc:
                        emit('talent_result', ok=False, text=progression_text('Talent nicht gelernt: {error}',runtime.language,error=str(exc)))
                elif msg.get('op') == 'companion_answer':
                    runtime.request_class_selection()
                    runtime.companion_answer(str(msg.get('text', '')), int(msg.get('choice', -1)))
                elif msg.get('op') == 'load_model':
                    runtime.load_model(msg['name'], msg.get('backend', 'llama'), msg.get('n_ctx', 20000), msg.get('temperature', .8), msg.get('tuning'))
                elif msg.get('op') == 'hall_start':
                    runtime.stop_speech('minigame')
                    from shared.core.minigames import begin_practice
                    emit('minigame_started',data=begin_practice(runtime.core.state,msg.get('game')))
                elif msg.get('op') == 'hall_result':
                    from shared.core.minigames import resolve_practice
                    emit('minigame_result',text=resolve_practice(runtime.core.state,msg.get('ticket'),msg.get('moves')))
                elif msg.get('op') == 'minigame_start':
                    runtime.stop_speech('minigame')
                    from shared.core.minigames import begin_attempt
                    emit('minigame_started', data=begin_attempt(runtime.core.state, msg.get('id')))
                elif msg.get('op') == 'minigame':
                    from shared.core.minigames import resolve
                    emit('minigame_result', text=resolve(runtime.core.state, msg.get('id'), msg.get('moves'), msg.get('skip', False), msg.get('ticket')))
                elif msg.get('op') == 'wiki_lookup':
                    from shared.core.offline_wiki import OfflineWiki, settings
                    from shared.core.wiki_i18n import tr as wiki_text
                    if not hasattr(runtime, 'wiki_preview'):
                        runtime.wiki_preview = OfflineWiki()
                    runtime.wiki_preview.language = runtime.language
                    try:
                        hit = runtime.wiki_preview.lookup(str(msg.get('term', '')), settings().get('offline_wiki_zim_path', ''))
                        result = wiki_text('{title}\n\n{text}\n\nQuelle: {source}',runtime.language,**hit)
                    except Exception as exc:
                        result = wiki_text('Offline-Wikipedia: {error}',runtime.language,error=exc)
                    emit('wiki_result', text=result)
                elif msg.get('op') == 'models':
                    runtime.models()
                runtime.complete_chat_turn()
            except ChatCancelled as exc:
                runtime.stop_speech('cancel')
                OUT.pending = ''
                emit('chat_cancelled', turn_id=turn.id if turn else None,
                     text=exc.notice(runtime.language) if isinstance(exc, RepetitionStopped) else None)
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as exc:
                diagnostic_failure('worker_command_failed', exc)
                if msg.get('op') == 'load_model':
                    diagnostic('model_load_failed', error_type=type(exc).__name__, detail=str(exc),
                               report=getattr(exc, 'report', None))
                    from gui.model_errors import load_error
                    message,detail=load_error(exc, runtime.language)
                    emit('model_error', text=message, detail=detail)
                else:
                    emit('error', text=str(exc))
                emit('model', status='unloaded' if runtime.llm is None else 'ready')
            finally:
                pending = runtime.context.pop('_pending_chat_message', None)
                if turn and not turn.committed and pending is not None:
                    runtime.boot.conversation[:] = [m for m in runtime.boot.conversation if m is not pending]
                runtime.context.pop('gui_chat_turn', None)
                if turn:
                    TURNS.pop(turn.id, None)
                runtime.snapshot()
                OUT.flush(force=True)
                emit('busy', value=False)
    except (EOFError, WorkerStopped):
        pass
    except BaseException as exc:
        diagnostic_failure('worker_failed', exc)
        emit('error', text=f'Spielprozess: {exc}', detail=traceback.format_exc())
        return 1
    finally:
        if 'runtime' in locals():
            try:
                runtime.stop_previous_speech()
            finally:
                try:
                    runtime.unload_model()
                except Exception as exc:
                    diagnostic_failure('model_release_failed', exc)
        emit('audio', action='clear')
        OUT.flush(force=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
