"""Real alternate-story hooks, private persistence, no model or audio needed."""
import builtins
import io
import sys
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'maatos'))
from shared.core import maat_paths
folder=Path(sys.argv[1])
maat_paths.get_default_app_support_dir=lambda:folder
maat_paths._default_app_support_dir=lambda:folder
from gui.game_worker import Runtime, ROOT
from gui.companion_stories import SCENES, REFLECTIONS
from shared.core.story_campaign import story_state_file
output=io.StringIO()
events=[]
def emit(kind, **data):
    events.append(dict(event=kind, **data))
def acknowledge():
    return dict(op='story_done',id=next(e['id'] for e in reversed(events) if e['event']=='story_scene'))
text='Ich bin deine Begleiter-KI und möchte dich unterstützen, offene Fragen ehrlich prüfen und unsere gemeinsamen Erinnerungen bewahren.'
with redirect_stdout(output), patch('gui.game_worker.emit',side_effect=emit), patch('gui.game_worker.receive',side_effect=acknowledge), patch.object(builtins,'input',return_value='1'), patch('random.randint',return_value=5), patch('random.random',return_value=1.0):
    r=Runtime(1)
    story=next(p for p in r.pm.iter_all_plugins() if p.plugin_id=='story_loader')
    original_path=Path(story.state_path)
    original_data=original_path.read_bytes() if original_path.exists() else None
    r.companion_start()
    assert 'Maatis: Wer bist du?' in output.getvalue()
    assert not any(e['event']=='story_scene' for e in events)
    assert not story.state['played'] and story.state['messages_total']==0
    identity=next(p for p in r.pm.iter_all_plugins() if p.plugin_id=='rpg_identity')
    with patch('random.randint',return_value=1):
        assert identity.before_chat(text,r.context)==(False,text)
    try:r.companion_answer('Hallo',-1)
    except ValueError:pass
    else:raise AssertionError('Short answer accepted')
    assert story.state['messages_total']==0
    r.llm={'backend':'llama','chat_state':{'architecture':'llama'}}
    r.free_companion=True
    with patch('shared.core.streaming.stream_chat_completion',return_value=iter(['Wie gehen wir weiter?'])), patch('shared.core.streaming.stream_to_console',return_value='Wie gehen wir weiter?'):
        # No random battle interaction is required for the story milestones.
        r.core.run_fight=lambda *a,**k:''
        for n in range(1,31):
            r.companion_answer(text,-1)
            assert story.state['messages_total']==n, (n,story.state['messages_total'],output.getvalue()[-2000:])
            if n==1:
                scenes=[e for e in events if e['event']=='story_scene']
                assert len(scenes)==1 and scenes[0]['module']=='companion_story1'
                assert r.companion.state['identity_answered']
            if n==10: assert 2 in story.state['played']
            if n==30: assert 3 in story.state['played']
        for boss,principles,module in [(1,0,'story4_boss1'),(3,0,'story5_boss3'),(3,1,'story6_final1')]:
            r.core.state.state['stats']['boss_wins']=boss
            r.core.state.state['world']['principles_restored']=principles
            r.core.state.save()
            r.companion_answer(text,-1)
            assert any(e.get('module')=='companion_'+module for e in events)
    for key in REFLECTIONS:
        story._play_reflection(dict(key=key, lines=['CLASSIC SHOULD NOT APPEAR'], music='quest2_reflection.mp3'))
        assert 'CLASSIC SHOULD NOT APPEAR' not in str(events[-1])
    for name in [f'boss_scene_{i}' for i in range(1,6)]:
        r.run_scene(ROOT/'apps/maat_rpg/plugins/battle'/(name+'.py'))
    # The real fifth-principle victory delivers the alternate credits, even if
    # this profile already saw the original campaign's credits.
    r.core.state.state['world'].update(principles_restored=4,credits_played=True)
    r.core._reward_on_victory('final',100,r.context)
    assert r.core.state.state['world']['companion_credits_played']
    credits_count=sum(e.get('module')=='companion_credits' for e in events)
    r.core._reward_on_victory('final',100,r.context)
    assert sum(e.get('module')=='companion_credits' for e in events)==credits_count==1
    scenes=[e for e in events if e['event']=='story_scene']
    assert {'companion_'+key for key in SCENES}.issubset({e['module'] for e in scenes})
    for e in scenes:
        assert e['module'].startswith('companion_')
        assert Path(e['music']).is_file(), e['music']
        assert (ROOT/'gui/assets'/e['image']).is_file()
    assert story.state['choices']['reflection_path']=='harmonie'
    assert story.state['choices']['combat_vow']=='protect'
    assert Path(story_state_file()).name=='companion_story_state.json'
    if original_data is not None: assert original_path.read_bytes()==original_data
    saved_counter=story.state['messages_total']
    r.select_story_campaign(False)
    assert str(story.state_path)==str(original_path)
    assert story.state['messages_total']==0
    r.select_story_campaign(True)
    assert story.state['messages_total']==saved_counter
    scene_count=len(scenes)
    r.llm=None
    r.companion_start()
    assert len([e for e in events if e['event']=='story_scene'])==scene_count
    from gui.ai_companion import CompanionCampaign
    saved=CompanionCampaign(r.companion.path)
    assert saved.state['identity_answered']
    assert any(m['title'].endswith('Ein Morgen ohne Thron') for m in saved.state['memories'])
print('Alternate opening, 12 scenes, 9 reflections, triggers, choices, assets and independent persistence passed.')
