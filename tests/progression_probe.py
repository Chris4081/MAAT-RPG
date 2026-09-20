"""Isolated real-plugin progression probe, invoked by test_progression_parity."""
import builtins
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'maatos'))
from shared.core import maat_paths
root = Path(sys.argv[1])
maat_paths.get_default_app_support_dir = lambda: root
maat_paths._default_app_support_dir = lambda: root
from gui.game_worker import Runtime
text = 'Wir prüfen gemeinsam den Weg und sammeln sorgfältig die Hinweise, bevor wir den nächsten Schritt in der Bibliothek unternehmen.'
with redirect_stdout(io.StringIO()), patch('gui.game_worker.emit'), patch.object(builtins, 'input', return_value='1'), patch.object(Runtime, 'present_story'):
    r = Runtime(1)
    plugins = {p.plugin_id:p for p in r.pm.iter_all_plugins()}
    story, battle, quests = (plugins[k] for k in ('story_loader','battle','quests'))
    fights=[]
    def fight(kind, context=None):
        assert context.get('combat_source')=='random'
        assert context.get('arena_difficulty') in ('easy','normal','hard')
        fights.append((battle.state.state['stats']['messages_total'],kind))
        battle.state.state['stats']['messages_since_last_fight']=0
        return ''
    r.core.run_fight=fight
    # Keep the real hooks, but avoid cosmetic level-up delays and random encounters.
    with patch.object(battle.before_chat.__func__.__globals__['random'], 'randint', return_value=5), patch.dict(battle.before_chat.__func__.__globals__, run_levelup_fx=lambda *a:None):
        classic = len(sys.argv)>2 and sys.argv[2]=='classic'
        if not classic:
            r.companion_start()
            assert story.state['played']==[]
        assert story.state['messages_total']==0
        r.free_companion=True
        r.llm=object()
        r.maatis_dialogue=lambda text: 'Maatis: Wir gehen vorsichtig weiter.'
        from shared.core import streaming
        streaming.stream_chat_completion=lambda *a,**kw: iter(['Wir gehen vorsichtig weiter.'])
        streaming.stream_to_console=lambda chunks,**kw: ''.join(chunks)
        send = r.text if classic else lambda text: r.companion_answer(text,-1)
        for n in range(1,61):
            send(text)
            assert story.state['messages_total']==n, ('story count',n)
            assert battle.state.state['stats']['messages_total']==n, ('battle count',n)
            assert quests.qstate['meta']['messages_total']==n, ('quest count',n)
            for pid in ('dungeon_60','dungeon_500','dungeon_1000'):
                assert plugins[pid].dungeon.state.data['msg']==n,(pid,n)
            if n==9: assert 2 not in story.state['played']
            if n==10: assert 2 in story.state['played']
            if n==29: assert 3 not in story.state['played']
            if n==30: assert 3 in story.state['played']
            if n==31: assert battle.state.state['world']['combat_unlocked']
            if n==19: assert not quests.qstate['meta']['quest_intro_shown']
            if n==20: assert quests.qstate['meta']['quest_intro_shown']
            if n==40: assert quests.qstate['meta']['shop_hint_shown']
            if n==50: assert quests.qstate['meta']['daily_hint_shown']
            assert plugins['dungeon_60'].dungeon.state.data['unlocked']==(n>=60)
        assert fights and fights[0][0]==32, fights
        assert battle.state.state['player']['xp']>0
        for pid,threshold in [('dungeon_500',500),('dungeon_1000',1000)]:
            p=plugins[pid]
            p.dungeon.state.data.update(msg=threshold-2,unlocked=False)
            send(text)
            assert not p.dungeon.state.data['unlocked']
            send(text)
            assert p.dungeon.state.data['unlocked']
        send(text+' Harmonie')
        assert 'harmonie' in plugins['achievements'].state['unlocked']
        level=battle.state.state['player']['level']
        assert not any(0 < q.get('level_tier',0) <= level//2 and not q.get('purchase_price') for q in quests.qstate['locked'])
        stats=battle.state.state['stats']
        for wins,boss,final,expected in [(9,0,0,'normal'),(10,0,0,'boss'),(50,5,0,'final'),(51,5,1,'normal')]:
            stats.update(fights_won=wins,boss_wins=boss,final_wins=final,boss_progress=20 if expected=="boss" else 0)
            assert r.core._auto_fight_type()==expected
        # Arena gate applies to every manual entry, with no direct boss bypass.
        world=battle.state.state['world']
        world['combat_unlocked']=False
        before=len(fights)
        for command in ('/fight','/fightboss','/fightfinal'):
            assert '🔒' in battle.command(command,r.context)[1]
        assert len(fights)==before
        world['combat_unlocked']=True
        stats.update(boss_progress=0,boss_wins=0,final_wins=0)
        assert '🔒' in battle.command('/fightboss',r.context)[1]
        captured=[]
        r.core.run_fight=lambda kind,context: captured.append((kind,context)) or ''
        battle.command('/fight',r.context)
        assert captured[-1][0]=='normal' and captured[-1][1]['combat_source']=='arena'
        assert not captured[-1][1].get('guide_mode')
        player=battle.state.state['player']
        reward_context=dict(r.context,run_scene=lambda path:None)
        for sources in (['random']*10,['arena']*20,['random']*5+['arena']*10):
            stats.update(boss_progress=0,boss_wins=0,final_wins=0)
            for source in sources:
                assert r.core._auto_fight_type()=='normal'
                r.core._reward_on_victory('normal',100,dict(reward_context,combat_source=source))
            assert stats['boss_progress']==20
            assert r.core._auto_fight_type()=='boss'
            r.core._reward_on_victory('boss',100,dict(reward_context,combat_source='arena'))
            assert stats['boss_progress']==0
            assert r.core._auto_fight_type()=='normal'
        gains=[]
        for source in ('random','arena'):
            xp=player['xp']
            r.core._reward_on_victory('normal',100,dict(reward_context,combat_source=source))
            gains.append(player['xp']-xp)
        assert gains[1]==gains[0]//2, gains
        from shared.core.arena_difficulty import TIERS, normal_encounter_stats
        for source in ('arena','random'):
            gains=[]
            for key,tier in TIERS.items():
                with patch.object(battle.command.__func__.__globals__['random'],'choice',return_value=key):
                    battle.command('/fight',r.context)
                assert captured[-1][1]['arena_difficulty']==key
                ctx=dict(reward_context,combat_source=source,arena_difficulty=key)
                xp=player['xp']
                r.core._reward_on_victory('normal',100,ctx)
                gains.append(player['xp']-xp)
                events=[]
                abort=type(r.core).run_fight.__globals__['TitleDemoAbort']
                with patch.object(r.core,'_enemy_stats',return_value=(100,10,100)), patch.object(builtins,'input',side_effect=abort), patch('shared.core.gui_bridge.emit',side_effect=lambda kind,**data: events.append((kind,data))):
                    type(r.core).run_fight(r.core,'normal',ctx)
                hud=next(data for kind,data in events if kind=='battle' and 'enemy_max_hp' in data)
                assert hud['enemy_max_hp']==normal_encounter_stats(100,10,player['level'],'normal',ctx)[0]
                assert hud['arena_difficulty']==key
            assert 0<gains[0]<gains[1]<gains[2],gains
        stats.update(fights_won=0,boss_wins=0,final_wins=0,boss_progress=0)
        player=battle.state.state['player']
        world=battle.state.state['world']
        world.update(principles_restored=0,credits_played=False)
        player['skills']=[]
        scenes=[]
        context=dict(r.context,run_scene=lambda path:scenes.append(Path(path).stem))
        for i in range(1,6):
            r.core._reward_on_victory('boss',10,context)
            assert len(player['skills'])==i
            assert scenes[-1]==f'boss_scene_{i}'
        for i in range(1,6):
            r.core._reward_on_victory('final',10,context)
            assert world['principles_restored']==i
            assert world.get('credits_played' if classic else 'companion_credits_played', False)==(i==5)
        r.core._reward_on_victory('final',10,context)
        assert scenes.count('credits')==1
        # The real worker refreshes combat quests after every completed action.
        # This probe called reward methods directly, so synchronize before reload.
        r.snapshot()
        saved_count=quests.qstate['meta']['messages_total']
        saved_completed=list(quests.qstate['completed'])
        restarted=Runtime(1)
        restored=next(p for p in restarted.pm.iter_all_plugins() if p.plugin_id=='quests')
        assert restored.state is restarted.core.state
        assert restored.qstate['meta']['messages_total']==saved_count
        assert restored.qstate['completed']==saved_completed
        # Real lethal attacks leave exactly 1 HP in saves and transported HUDs.
        for source in ('arena','random'):
            player.update(hp=20,max_hp=100,skills=[],sigils=0,xp=0,level=50)
            world['combat_unlocked']=False
            stats['messages_since_last_fight']=0
            events=[]
            ctx=dict(gui_mode=True,fast_output=True,combat_source=source,arena_difficulty='normal',scripted_actions=['1','1'])
            with patch.object(r.core,'_enemy_stats',return_value=(10000,10000,100)), patch.object(r.core,'_apply_guard',side_effect=lambda damage,turn:(damage,'')), patch.object(r.core,'_modify_incoming_damage',side_effect=lambda damage,*args:(damage,'')), patch('shared.core.gui_bridge.emit',side_effect=lambda kind,**data:events.append((kind,data))):
                type(r.core).run_fight(r.core,'normal',ctx)
            assert player['hp']==1,(source,player['hp'])
            assert all(data['player_hp']>=1 for kind,data in events if 'player_hp' in data)
            battle.after_response('Der Kampf ist beendet.',r.context)
            assert player['hp']==1
            battle.before_chat('/xp',r.context)
            assert player['hp']==1
            battle.before_chat(text,r.context)
            assert player['hp']==21,player['hp']
            battle.after_response('Wir erholen uns.',r.context)
            assert player['hp']==21
            for _ in range(4):
                stats['messages_since_last_fight']=0
                battle.before_chat(text,r.context)
            assert player['hp']==100
print('Progression boundaries passed: story 10/30, combat, quests 20/40/50, dungeons 60/500/1000, boss/final cadence.')
