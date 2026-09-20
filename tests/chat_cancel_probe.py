"""Real RPG hooks, private saves, synthetic token stream; no model is loaded."""
import builtins
import io
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'maatos'))
for key in list(os.environ):
    if key.startswith('MAAT_') and key.endswith('_DIR'):
        os.environ.pop(key)
from shared.core import maat_paths, streaming
root = Path(sys.argv[1])
maat_paths.get_default_app_support_dir = lambda: root
maat_paths._default_app_support_dir = lambda: root
from gui.game_worker import Runtime
from shared.core.chat_turn import ChatTurn, ChatCancelled

with redirect_stdout(io.StringIO()), patch('gui.game_worker.emit') as output, patch.object(builtins, 'input', return_value='1'), patch.object(Runtime, 'present_story'):
    r = Runtime(1)
    plugins = {p.plugin_id:p for p in r.pm.iter_all_plugins()}
    battle, story, quests = [plugins[key] for key in ('battle','story_loader','quests')]
    r.llm = {'backend':'llama','instance':object()}
    r.perf = {'gui_mode':True, 'raise_errors':True}
    r.context['llm'] = r.llm
    evolution = Mock()
    evolution.evaluate_from_context.return_value = None
    r.context['evo_engine'] = evolution
    companion = len(sys.argv) > 2 and sys.argv[2] == 'companion'
    if companion:
        r.select_story_campaign(True)
        r.companion.state.update(identity_answered=True, dialogue=[])
        r.free_companion=True
    battle.state.state['hero_class'] = {'selected':'robo','pending':False}
    mode = 'cancel_after_tokens'
    completed_fights = []

    def fake_fight(*args, **kwargs):
        battle.state.add_xp(300)
        battle.state.state['stats']['fights_won'] += 1
        battle.state.state['stats']['messages_since_last_fight'] = 0
        battle.state.save()
        completed_fights.append(True)
        return 'Completed battle'

    def tokens(*args, **kwargs):
        quality = [m['content'] for m in args[1] if m['role']=='system' and m['content'].startswith('[MAAT_INTERNAL_QUALITY]')]
        assert len(quality)==1 and 'MAAT100 (100%)' in quality[0]
        yield 'Wir betrachten '
        if mode == 'cancel_after_tokens': turn.cancel()
        if mode == 'error': raise RuntimeError('Synthetic model error')
        if mode == 'repetition':
            yield from ['🚀 :) 🚀 '] * 100
            raise AssertionError('Repetition guard failed to close generation')
        yield 'gemeinsam den Weg.'

    def emit(kind, **data):
        if kind == 'chat_generated':
            assert battle.state.state['stats']['messages_total'] == count_before
            assert quests.qstate['meta']['messages_total'] == count_before
            if mode == 'cancel_during_display': turn.cancel()
            else: turn.presented.set()

    output.side_effect = emit
    r.core.run_fight = fake_fight
    # This scenario must reach the synthetic model. The optional 1/40 lore
    # response otherwise legitimately bypasses it and makes cancellation flaky.
    with patch.object(plugins['rpg_identity'], 'before_chat', return_value=(False,None)), patch.object(streaming, 'backend_stream_chat', side_effect=tokens), patch.dict(battle.before_chat.__func__.__globals__, run_levelup_fx=lambda *a, **kw:None):
        for mode in ('cancel_after_tokens', 'cancel_during_display', 'repetition', 'error', 'success', 'cancel_after_fight', 'success'):
            count_before = battle.state.state['stats']['messages_total']
            xp_before = battle.state.state['player']['xp']
            turn = ChatTurn(mode)
            r.context['gui_chat_turn'] = turn
            if mode == 'cancel_after_fight':
                battle.state.state['world']['combat_unlocked'] = True
                battle.state.state['stats']['messages_since_last_fight'] = 9
                mode = 'cancel_during_display'
            fights_before = len(completed_fights)
            evolution_before = evolution.evaluate_from_context.call_count
            try:
                message='Harmonie und Balance helfen uns, gemeinsam diesen Weg zu erkunden. Wir prüfen aufmerksam die Hinweise in der Bibliothek und überlegen uns einen sicheren nächsten Schritt.'
                if companion:
                    r.companion_answer(message, -1)
                else:
                    r.text(message)
            except (ChatCancelled, RuntimeError):
                assert mode != 'success'
            else:
                assert mode == 'success', mode
            finally:
                pending = r.context.pop('_pending_chat_message', None)
                if not turn.committed:
                    r.boot.conversation[:] = [m for m in r.boot.conversation if m is not pending]
                r.context.pop('gui_chat_turn', None)
            expected = count_before + int(mode == 'success')
            if mode != 'success':
                assert evolution.evaluate_from_context.call_count == evolution_before
            assert battle.state.state['stats']['messages_total'] == expected
            assert story.state['messages_total'] == expected
            assert quests.qstate['meta']['messages_total'] == expected
            for pid in ('dungeon_60','dungeon_500','dungeon_1000'):
                assert plugins[pid].dungeon.state.data['msg'] == expected, pid
            if mode != 'success':
                fight_xp = 300 if len(completed_fights) > fights_before else 0
                assert battle.state.state['player']['xp'] == xp_before + fight_xp
            if expected == 0:
                assert not plugins['achievements'].state['unlocked']
            if len(completed_fights) > fights_before:
                assert battle.state.state['stats']['fights_won'] >= 1
        assert len(completed_fights) == 1
        history = r.companion.state['dialogue'] if companion else r.boot.conversation
        assert len([m for m in history if m['role']=='user']) == 2
print('cancel, display cancel, error, retry and retained battle rewards: OK')
