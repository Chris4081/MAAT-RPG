"""Private-runtime audit of every authored story and real post-victory hooks."""
import builtins
import io
import json
import os
from pathlib import Path
import re
import sys
from contextlib import redirect_stdout
from unittest.mock import patch

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'maatos'))
folder=Path(sys.argv[1])
language=sys.argv[2]
companion=sys.argv[3]=='companion'
os.environ['MAAT_GUI_DATA_ROOT']=str(folder)
from shared.core import maat_paths
maat_paths.get_default_app_support_dir=lambda:folder
maat_paths._default_app_support_dir=lambda:folder
from apps.maat_rpg import session_shared
session_shared.write_application_language(language)
session_shared.write_profile_settings(1,{'language':language,'gui_perspective':'companion' if companion else 'adventure'})
from gui.game_worker import Runtime
from gui.companion_stories import REFLECTIONS, scene_payload
from gui.cutscenes import cutscene_payload

events=[];prompts=[]
def emit(kind,**data):
    events.append(dict(event=kind,**data))
def acknowledge():
    scene=next(e for e in reversed(events) if e['event']=='story_scene')
    return dict(op='story_done',id=scene['id'])
def choose(prompt=''):
    prompts.append(prompt)
    return '1'

with redirect_stdout(io.StringIO()), patch('gui.game_worker.emit',side_effect=emit), \
     patch('gui.game_worker.receive',side_effect=acknowledge), patch.object(builtins,'input',side_effect=choose):
    runtime=Runtime(1)
    assert runtime.language==language
    runtime.core.state.state['world']['combat_unlocked']=True
    story=next(p for p in runtime.pm.iter_all_plugins() if p.plugin_id=='story_loader')
    config=json.loads((root/'maatos/apps/maat_rpg/plugins/story_loader/stories/config.json').read_text())
    for entry in config['stories']:
        story._play_story_entry(entry,runtime.context)
    assert story.state['choices']['reflection_path']=='harmonie'
    assert story.state['choices']['combat_vow']=='protect'
    for key in REFLECTIONS:
        # Real generated normal-language lines, alternate replacements for the AI.
        runtime.core.state.state['stats']['boss_wins']=3
        runtime.core.state.state['world']['principles_restored']=1
        runtime.core.state.save()
        story.state['reflection_seen']=[]
        if companion:
            story._play_reflection(dict(key=key,lines=['DO NOT SHOW THIS'],music='quest2_reflection.mp3'))
        else:
            # Exercise available authored reflections through their actual state gates.
            while (reflection:=story._build_inner_reflection()):
                story._play_reflection(reflection)
            break
    runtime.core.state.state['stats'].update(boss_wins=0,boss_progress=20)
    for boss in range(1,6):
        runtime.core._reward_on_victory('boss',100,runtime.context)
        event=next(e for e in reversed(events) if e['event']=='story_scene')
        module=f'boss_scene_{boss}'
        assert event['module']==('companion_' if companion else '')+module,(boss,event)
        expected=(scene_payload(module,language) if companion else
                  cutscene_payload(root/'maatos/apps/maat_rpg/plugins/battle'/f'{module}.py',language))
        assert event['lines']==expected['lines']
        assert runtime.core.state.state['stats']['boss_wins']==boss
    runtime.core.state.state['world'].update(principles_restored=0,credits_played=False,companion_credits_played=False)
    runtime.core.state.state['stats']['final_wins']=0
    for final in range(5):
        runtime.core._reward_on_victory('final',100,runtime.context)
    credits=next(e for e in reversed(events) if e['event']=='story_scene')
    assert credits['module']==('companion_' if companion else '')+'credits'
    assert Path(credits['music']).name == ('credits_en.mp3' if language == 'en' else 'credits_theme.mp3')
    assert 'Christof Krieg' in '\n'.join(credits['lines'])
    assert sum(e.get('module')==credits['module'] for e in events)==1
    runtime.replay_credits(1)
    replay=next(e for e in reversed(events) if e['event']=='story_scene')
    assert replay['lines']==credits['lines']
    scenes=[e for e in events if e['event']=='story_scene']
    assert len({e['module'] for e in scenes})==13 # six story chapters, five bosses, reflections, credits
    for scene in scenes:
        assert scene['language']==language
        assert Path(scene['music']).is_file(),scene['music']
        if scene.get('image'):
            assert (root/'maatos/gui/assets'/scene['image']).is_file()
        if language=='en':
            text=scene['name']+'\n'+'\n'.join(scene['lines'])
            match=re.search(r'\b(Drücke|Schatten|Zwischenakt|Erinnerung|Die Stimme|Du |Deine |Dein |Wähle|Schöpfungskraft|Verbundenheit|Spezielle Danksagung)\b',text)
            assert not match,(scene['module'],match.group(0))
    if language=='en':
        assert any('Choose a decision' in p for p in prompts)
        assert not any('Wähle' in p or 'Zuhören' in p for p in prompts)
    else:
        assert any('Wähle eine Entscheidung' in p for p in prompts)

(folder/'story-events.json').write_text(json.dumps(scenes,ensure_ascii=False,indent=2)+'\n')
print(f'{language}/{sys.argv[3]}: all 6 chapters, 5 real boss reward hooks, reflections, finale, replay and choices passed.')
