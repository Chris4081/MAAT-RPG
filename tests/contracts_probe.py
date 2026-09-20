"""Exercise all 25 paid quests against a temporary real RPG state."""
import io, sys
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'maatos'))
from shared.core import maat_paths
root=Path(sys.argv[1])
maat_paths.get_default_app_support_dir=lambda:root
maat_paths._default_app_support_dir=lambda:root
from gui.game_worker import Runtime
from apps.maat_rpg.plugins.quests.paid_contracts import PAID_CONTRACTS
with redirect_stdout(io.StringIO()),patch('gui.game_worker.emit'):
    r=Runtime(1)
    q=next(p for p in r.pm.iter_all_plugins() if p.plugin_id=='quests')
    ids=[v['id'] for group in ('active','available','locked','completed') for v in q.qstate[group]]
    assert len(ids)==len(set(ids))==188,len(ids)
    player=r.core.state.state['player'];stats=r.core.state.state['stats']
    player.update(level=49,gold=100000,potions=0,sigils=0,xp=0)
    assert 'Level 50' in q.buy_contract('contract50_01')
    assert player['gold']==100000
    player['level']=50
    q.qstate['meta'].update(messages_total=10000,quest_intro_shown=True)
    q._check_unlocks()
    assert len([v for v in q.qstate['locked'] if v.get('purchase_price')])==25
    player['gold']=499
    assert 'Nicht genug' in q.buy_contract('contract50_01')
    assert player['gold']==499
    player['gold']=100000
    stats['fights_won']=10000
    for definition in PAID_CONTRACTS:
        before=player['gold']
        assert 'Auftrag gekauft' in q.buy_contract(definition['id'])
        assert player['gold']==before-definition['purchase_price']
        q.buy_contract(definition['id'])
        assert player['gold']==before-definition['purchase_price']
        current=next(v for v in q.qstate['active'] if v['id']==definition['id'])
        q.refresh_paid_contracts()
        assert current['progress']==0
        q._ensure_default_quests()
        assert current['counter_start']>=10000
    # Restart with all purchases: baseline, ownership and gold survive migration.
    r=Runtime(1)
    q=next(p for p in r.pm.iter_all_plugins() if p.plugin_id=='quests')
    player=r.core.state.state['player'];stats=r.core.state.state['stats']
    assert player['gold']==75000,player['gold']
    assert len([v for v in q.qstate['active'] if v.get('purchase_price')])==25
    for definition in PAID_CONTRACTS:
        current=next(v for v in q.qstate['active'] if v['id']==definition['id'])
        # Isolate one target to verify every reward and threshold independently.
        saved=q.qstate['active'];q.qstate['active']=[current]
        source=q.qstate['meta'] if definition['counter_key']=='messages_total' else stats
        key='messages_total' if definition['counter_key']=='messages_total' else 'fights_won'
        source[key]=current['counter_start']+current['target']-1
        q.refresh_paid_contracts()
        assert current in q.qstate['active']
        assert current['progress']==current['target']-1
        before=(player['xp'],player['potions'],player['sigils'])
        source[key]+=1
        r.snapshot()  # Real post-combat refresh must award immediately, before another chat.
        assert current in q.qstate['completed']
        assert player['xp']-before[0]==definition['reward_xp']
        assert player['potions']-before[1]==definition['reward_items'].get('potions',0)
        assert player['sigils']-before[2]==definition['reward_items'].get('sigils',0)
        after=(player['xp'],player['potions'],player['sigils'],player['gold'])
        q.refresh_paid_contracts();q.buy_contract(current['id'])
        assert after==(player['xp'],player['potions'],player['sigils'],player['gold'])
        q.qstate['active']=[v for v in saved if v['id']!=current['id']]
    assert len(player['earned_titles'])==5
    q._save_runtime_state()
print('188 unique quests; all 25 purchases, level/funds gates, fresh counters, persistence and one-time rewards passed.')
