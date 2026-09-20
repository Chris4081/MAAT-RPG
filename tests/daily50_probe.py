import io,sys
from pathlib import Path
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime
from unittest.mock import Mock,patch
from importlib.machinery import SourceFileLoader
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'maatos'))
from shared.core import maat_paths
root=Path(sys.argv[1]);maat_paths.get_default_app_support_dir=lambda:root;maat_paths._default_app_support_dir=lambda:root
from gui.game_worker import Runtime
from apps.maat_rpg.plugins.quests.daily_50 import DAILY_50_QUESTS
clock=Mock(wraps=datetime);clock.now.return_value=datetime(2026,9,6,12)
with redirect_stdout(io.StringIO()),patch('gui.game_worker.emit'):
    r=Runtime(1)
    q=next(p for p in r.pm.iter_all_plugins() if p.plugin_id=='quests')
    player=r.core.state.state['player']
    with patch.dict(q._check_unlocks.__func__.__globals__,datetime=clock):
        q.qstate['meta'].update(messages_total=50,quest_intro_shown=True,last_unlock_level=48)
        player.update(level=49,xp=0)
        q._check_unlocks()
        assert not any(v['id'].startswith('daily50_') for v in q.qstate['active'])
        player['level']=50;q._check_unlocks()
        daily=[v for v in q.qstate['active'] if v['id'].startswith('daily50_')]
        assert len(daily)==12
        q.qstate['active']=daily
        q.qstate['completed']=[]
        expected=sum(q._quest_xp_effective(v) for v in daily)
        for quest in list(daily):
            q._check_daily_quests(quest['keyword'],[])
            q._check_daily_quests(quest['keyword'],[])
        assert player['xp']==expected,(player['xp'],expected,[(v['id'],v.get('progress')) for v in q.qstate['active']],[(v['id'],v.get('completions')) for v in q.qstate['completed']])
        q._refresh_daily_quests()
        assert not q.qstate['active']
        assert len(q.qstate['completed'])==12
        assert all(v['completions']==1 for v in q.qstate['completed'])
        # Moving the clock backwards cannot reopen or reward the tasks.
        clock.now.return_value=datetime(2026,9,5,12)
        q._refresh_daily_quests();assert not q.qstate['active']
        clock.now.return_value=datetime(2026,9,7,12)
        q._refresh_daily_quests();assert len(q.qstate['active'])==12
        for quest in list(q.qstate['active']):q._check_daily_quests(quest['keyword'],[])
        assert player['xp']==expected*2
        assert all(v['completions']==2 for v in q.qstate['completed'])
        q._save_runtime_state()
    # Reload with the same date; snapshots must not reset or duplicate today's rewards.
    # Runtime reloads plugins into new modules and refreshes them on boot.
    # Give that fresh module the same clock before its Plugin is constructed.
    original_exec = SourceFileLoader.exec_module
    def load_at_test_time(loader, module):
        original_exec(loader, module)
        if Path(loader.path).parts[-2:] == ('quests', 'plugin_main.py'):
            module.datetime = clock
    with patch.object(SourceFileLoader,'exec_module',load_at_test_time):
        restarted=Runtime(1)
        restored=next(p for p in restarted.pm.iter_all_plugins() if p.plugin_id=='quests')
        restored._refresh_daily_quests()
        assert not any(v['id'].startswith('daily50_') for v in restored.qstate['active'])
        assert len([v for v in restored.qstate['completed'] if v['id'].startswith('daily50_')])==12
        before=restarted.core.state.state['player']['xp']
        for quest in DAILY_50_QUESTS:restored._check_daily_quests(quest['keyword'],[])
        assert restarted.core.state.state['player']['xp']==before
print('12 dailies: level 50 gate, day change, repeat protection, clock rollback and restart passed.')
