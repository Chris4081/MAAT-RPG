"""Level balance in the actual combat loop, using private saves and no audio/model."""
import io
import random
import statistics
import tempfile
import unittest
from contextlib import nullcontext, redirect_stdout
from unittest.mock import Mock, patch
from test_desktop import APP
from apps.maat_rpg.plugins.battle import plugin_main as battle
from shared.core import arena_difficulty, gui_bridge


class EncounterScalingTests(unittest.TestCase):
    def encounter(self, *, level=50, source='random', tier='normal', kind='normal',
                  baseline=False, hp=None, extra=None, language='de', seed=17, tactical=False,
                  potions=5, hero=None, skills=None, actions=None):
        events=[]
        rng=random.getstate()
        with tempfile.TemporaryDirectory() as folder, redirect_stdout(io.StringIO()), \
                patch.object(battle, 'BattleMusicManager'), \
                patch.object(battle, '_battle_ui_language', return_value=language):
            core=battle.BattleCore(folder)
            core.state.state=core.state._default()
            core.state.state['player'].update(level=level, max_hp=100+(level-1)*10,
                hp=100+(level-1)*10 if hp is None else hp)
            core.state.state['stats'].update(fights_won=37, boss_progress=20)
            if hero is not None:
                core.state.state['hero_class'] = hero
            if skills is not None:
                core.state.state['player']['skills'] = skills
            core.state.save=Mock()
            core._load_story_state=lambda:{}
            core._save_story_state=Mock()
            core._register_boss_codex_entry=Mock()
            core._choose_music=Mock(return_value=(None,None))
            core._slow_line=Mock()
            core._prompt=Mock(return_value='1')  # Keep attacking Harmony; no healing or talents.
            if tactical:
                core.state.state['player']['potions']=potions
                def choose(prompt, **kwargs):
                    if prompt != battle._battle_text('action_prompt'):
                        return '3'  # Creation, without reading hidden weakness hints.
                    hud=self.first_hud(list(reversed(events)))
                    if hud['resonance']>=100:return '5'
                    if hud['player_hp']<hud['player_max_hp']*.3 and core.state.state['player']['potions']:
                        return '4'
                    return '1'
                core._prompt=choose
            if actions is not None:
                core.state.state['player']['potions']=potions
                scripted = iter(actions)
                core._prompt = lambda *args, **kwargs: next(scripted, '1')
            core._reward_on_victory=Mock(return_value='reward')
            context=dict(combat_source=source, arena_difficulty=tier, fast_output=True, **(extra or {}))
            override=(patch.object(arena_difficulty, 'normal_encounter_stats',
                return_value=None) if baseline else nullcontext())
            gui_bridge.install(lambda event,**data:events.append(dict(event=event,**data)))
            try:
                random.seed(seed)
                with override:
                    log=core.run_fight(kind,context)
                return events,core.state.state,log
            finally:
                gui_bridge.install(None)
                random.setstate(rng)

    def first_hud(self, events):
        return next(e for e in events if e['event']=='battle' and e.get('active'))

    def damage(self, events):
        return sum(e.get('damage',0) for e in events
                   if e['event']=='battle_effect' and e.get('attacker')=='enemy')

    def test_tier_challenge_stays_comparable_across_levels(self):
        # Fixed reference strategy/build, using seeds not used for tuning.
        # Creation + impulse when ready; at most one potion below 30% HP.
        reference = {'maat_fields': dict.fromkeys('HBSVR', .8)}
        yellow_hp = []
        for level in (1, 7, 15, 30, 50):
            for tier, potions in [('easy', 0), ('normal', 0), ('hard', 0), ('hard', 1)]:
                with self.subTest(level=level, tier=tier, potions=potions):
                    runs = [self.encounter(level=level, tier=tier, tactical=True,
                        potions=potions, seed=seed, extra=reference) for seed in range(1000, 1032)]
                    win_rate = sum(events[-1].get('enemy_hp') == 0 for events, _, _ in runs)/len(runs)
                    remaining = statistics.mean(state['player']['hp']/state['player']['max_hp']
                                                for _, state, _ in runs)
                    if tier == 'easy':
                        self.assertEqual(win_rate, 1)
                        self.assertGreater(remaining, .4)
                    elif tier == 'normal':
                        self.assertGreaterEqual(win_rate, .90)
                        self.assertGreater(remaining, .12)
                        self.assertLess(remaining, .30)
                        yellow_hp.append(remaining)
                    elif potions:
                        self.assertGreaterEqual(win_rate, .85)
                        self.assertGreaterEqual(sum(state['player']['potions'] == 0
                                                    for _, state, _ in runs)/len(runs), .9)
                    else:
                        self.assertLessEqual(win_rate, .35)
        self.assertLess(max(yellow_hp)-min(yellow_hp), .10)

    def test_random_and_arena_use_the_same_balance_and_tier(self):
        for tier in ('easy', 'normal', 'hard'):
            random_events, _, _ = self.encounter(tier=tier, source='random', hp=99999)
            arena_events, _, _ = self.encounter(tier=tier, source='arena', hp=99999)
            self.assertEqual(self.first_hud(random_events)['enemy_max_hp'],
                             self.first_hud(arena_events)['enemy_max_hp'])
            self.assertEqual(self.damage(random_events), self.damage(arena_events))
            self.assertEqual(self.first_hud(arena_events)['arena_difficulty'], tier)

    def test_hard_endgame_is_winnable_with_impulse_and_potions_without_talents(self):
        for seed in range(5):
            with self.subTest(seed=seed):
                events,state,_=self.encounter(tier='hard',seed=seed,tactical=True)
                final=next(e for e in reversed(events) if e['event']=='battle' and not e.get('active'))
                self.assertEqual(final['enemy_hp'],0)
                self.assertGreater(state['player']['hp'],1)
                self.assertTrue(any(e.get('attack')=='impulse' for e in events))

    def test_level_damage_share_is_stable_and_does_not_scale_to_current_hp(self):
        for source in ('random','arena'):
            for tier in ('easy', 'normal', 'hard'):
                previous=(0,0)
                shares=[]
                for level in range(1,51):
                    base=(40+level*8,5+level*2)
                    hp,damage=arena_difficulty.normal_encounter_stats(*base,level,'normal',
                        {'combat_source':source, 'arena_difficulty':tier})
                    self.assertGreater(hp,previous[0])
                    self.assertGreater(damage,previous[1])
                    shares.append(damage/(100+(level-1)*10))
                    previous=(hp,damage)
                self.assertLess(max(shares)-min(shares), .01)
        regular,_,_=self.encounter(hp=1)
        cheat,_,_=self.encounter(hp=99999)
        self.assertEqual(self.first_hud(regular)['enemy_max_hp'],self.first_hud(cheat)['enemy_max_hp'])

    def test_potion_heals_current_damage_and_empty_inventory_never_restores_old_hp(self):
        for potions in (0, 1):
            with self.subTest(potions=potions):
                events, state, _ = self.encounter(level=7, tier='easy', potions=potions,
                    actions=['1', '3', '4'], extra={'maat_fields':dict.fromkeys('HBSVR', .8)})
                hits = [e for e in events if e['event']=='battle_effect' and e.get('attacker')=='enemy']
                heals = [e for e in events if e.get('attack')=='heal']
                if potions:
                    self.assertEqual(len(heals), 1)
                    expected = min(80, 160-hits[0]['player_hp'])
                    self.assertEqual(heals[0]['heal'], expected)
                    self.assertEqual(hits[1]['player_hp_before'], hits[0]['player_hp']+expected)
                    self.assertEqual(state['player']['potions'], 0)
                else:
                    self.assertFalse(heals)
                    self.assertEqual(hits[1]['player_hp_before'], hits[0]['player_hp'])

    def test_bosses_finales_dungeons_and_introductions_keep_the_same_combat(self):
        for kind,source,extra in [('boss','random',{}),('boss','arena',{}),
                ('final','random',{}),('final','arena',{}),('normal','dungeon',{}),
                ('normal','demo',{}),('normal','random',{'guide_mode':True}),
                ('normal','arena',{'title_demo_mode':True})]:
            with self.subTest(kind=kind,source=source,extra=extra):
                args=dict(kind=kind,source=source,extra=extra,hp=1)
                before,_,_=self.encounter(**args,baseline=True)
                after,_,_=self.encounter(**args)
                self.assertEqual(before,after)

    def test_defeat_keeps_completed_wins_and_localizes_retry_distance(self):
        for language in ('de','en'):
            for kind,needed in [('boss',5),('final',10)]:
                with self.subTest(language=language,kind=kind):
                    _,state,log=self.encounter(kind=kind,hp=1,language=language)
                    phrase=(f'{needed} Zufallssiege oder {needed*2} Arenasiege' if language=='de'
                            else f'{needed} random encounters or {needed*2} arena fights')
                    self.assertIn(phrase,log)
                    self.assertEqual(state['stats']['fights_won'],37)
                    self.assertEqual(state['player']['hp'],1)


if __name__=='__main__':unittest.main()
