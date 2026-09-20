"""All level-22–50 definitions, triggers and save migration with real plugins."""
import io,sys
from pathlib import Path
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime,timedelta
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'maatos'))
from shared.core import maat_paths
root=Path(sys.argv[1])
maat_paths.get_default_app_support_dir=lambda:root
maat_paths._default_app_support_dir=lambda:root
from gui.game_worker import Runtime
from apps.maat_rpg.plugins.quests.extended_quests import EXPANDED_QUESTS
assert len(EXPANDED_QUESTS)==60
assert len({q['id'] for q in EXPANDED_QUESTS})==60
with redirect_stdout(io.StringIO()),patch('gui.game_worker.emit'):
    r=Runtime(1)
    q=next(p for p in r.pm.iter_all_plugins() if p.plugin_id=='quests')
    player=r.core.state.state['player']
    qs=q.qstate
    qs['meta'].update(messages_total=20,quest_intro_shown=True,last_unlock_level=20)
    for level in range(21,51):
        player.update(level=level,xp=0)
        q._check_unlocks()
        unlocked={v['id'] for v in qs['active']+qs['completed']}
        for definition in EXPANDED_QUESTS:
            assert (definition['id'] in unlocked)==(definition['level_tier']*2<=level),(level,definition['id'])
    # Simulate a high-level save made before this pack, preserving one completed quest.
    for group in ('active','available','locked','completed'):
        qs[group]=[v for v in qs[group] if not v['id'].startswith('journey_')]
    original=deepcopy(qs['active'][0])
    original.update(progress=3,completed_at='2026-09-06T12:00:00')
    qs['active']=[v for v in qs['active'] if v['id']!=original['id']]
    qs['completed'].append(original)
    q._ensure_default_quests()
    q._ensure_default_quests()
    all_ids=[v['id'] for group in ('active','available','locked','completed') for v in qs[group]]
    assert len(all_ids)==len(set(all_ids))
    assert next(v for v in qs['completed'] if v['id']==original['id'])==original
    q._check_unlocks()
    assert sum(v['id'].startswith('journey_') for v in qs['active'])==60
    # Each new definition can complete, and does not pay twice.
    for definition in EXPANDED_QUESTS:
        current=deepcopy(definition)
        qs['active']=[current]
        qs['completed']=[]
        player.update(level=50,xp=0)
        expected=q._quest_xp_effective(current)
        messages=[]
        if current['type']=='chat_keyword':
            q._check_keyword_quests('Ein ganz anderes Thema.',messages)
            assert not qs['completed']
            q._check_keyword_quests('Lass uns über '+current['keywords'][0]+' sprechen.',messages)
            q._check_keyword_quests(current['keywords'][0],messages)
        elif current['type']=='battle_win':
            r.core.state.state['stats']['fights_won']=current['target']-1
            q._check_battle_quests(messages)
            assert not qs['completed']
            r.core.state.state['stats']['fights_won']=current['target']
            q._check_battle_quests(messages)
            q._check_battle_quests(messages)
        else:
            for day in range(current['days']):
                clock=Mock(wraps=datetime)
                clock.now.return_value=datetime(2026,9,1)+timedelta(days=day)
                with patch.dict(q._check_daily_quests.__func__.__globals__,datetime=clock):
                    q._check_daily_quests(current['keyword'],messages)
                    q._check_daily_quests(current['keyword'],messages)
                if day<current['days']-1:assert current['progress']==day+1
        assert len(qs['completed'])==1,definition['id']
        assert player['xp']==expected,(definition['id'],player['xp'],expected)
    # Re-add other definitions and prove persistence/idempotence after a restart.
    q._ensure_default_quests()
    q._save_runtime_state()
    restarted=Runtime(1)
    restored=next(p for p in restarted.pm.iter_all_plugins() if p.plugin_id=='quests')
    all_ids=[v['id'] for group in ('active','available','locked','completed') for v in restored.qstate[group]]
    assert len(all_ids)==len(set(all_ids))
    assert {v['id'] for v in EXPANDED_QUESTS}.issubset(all_ids)
print('60 quests: level gates, all triggers, one-time rewards and save migration passed.')
