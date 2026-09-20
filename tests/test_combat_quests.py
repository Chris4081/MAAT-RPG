import json
import unittest
from pathlib import Path
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch
from test_desktop import APP
from test_live_rpg import Worker
from apps.maat_rpg.plugins.quests.plugin_main import Plugin, _ALL_QUEST_DEFINITIONS
from apps.maat_rpg.plugins.quests.combat_quests import COMBAT_QUESTS, progress_counters
from apps.maat_rpg.plugins.quests.companion_quests import display
from shared.core.dungeon_campaign import run, run_endless
from gui.quest_log import QuestLog
from gui.character_sidebar import CharacterSidebar
from gui.game_worker import Runtime


class SavedState:
    def __init__(self, level=50):
        self.state = dict(player=dict(level=level, xp=0, hp=500, max_hp=500), stats={}, world={})
        self.saved = None

    def save(self):
        self.saved = deepcopy(self.state)

    def add_xp(self, xp):
        self.state['player']['xp'] += xp
        level = self.state['player']['level']
        return level, level


def quest_plugin(level=50):
    state = SavedState(level)
    core = SimpleNamespace(state=state)
    plugin = Plugin(core=core)
    plugin._lang = lambda: 'de'
    plugin._load_story_state = lambda: {}
    return plugin, core


def set_counter(root, key, value):
    if key.startswith('dungeon_clear:'):
        root['dungeon_runs'] = {key.split(':')[1]: dict(completed=value)}
    elif key == 'dungeon_clears':
        root['dungeon_runs'] = {'0': dict(completed=value)}
    elif key == 'dungeon_unique':
        root['dungeon_runs'] = {str(i): dict(completed=1) for i in range(value)}
    elif key.startswith('dungeon_plus_'):
        root['dungeon_plus'] = {('best_wave' if key.endswith('best') else 'total_wins'): value}
    else:
        root.setdefault('stats', {})[key] = value


class CombatQuestTests(unittest.TestCase):
    def test_exact_level_and_feature_gates(self):
        self.assertEqual(len(COMBAT_QUESTS), 40)
        self.assertEqual(len({q['id'] for q in _ALL_QUEST_DEFINITIONS}), 188)
        for level in range(1, 51):
            for enabled in (False, True):
                p, core = quest_plugin(level)
                core.state.state['world']['combat_unlocked'] = enabled
                p.qstate['meta'].update(messages_total=20, quest_intro_shown=True, last_unlock_level=50)
                p._check_unlocks()
                active = {q['id'] for q in p.qstate['active']}
                for q in COMBAT_QUESTS:
                    expected = level >= q['minimum_level'] and (enabled or not q['requires_combat'])
                    self.assertEqual(q['id'] in active, expected, (q['id'], level, enabled))
        p, core = quest_plugin()
        core.state.state['world']['combat_unlocked'] = True
        p.qstate['meta']['messages_total'] = 19
        p._check_unlocks()
        self.assertFalse({q['id'] for q in COMBAT_QUESTS} & {q['id'] for q in p.qstate['active']})

    def test_all_targets_rewards_no_double_payment_and_independent_sources(self):
        for definition in COMBAT_QUESTS:
            with self.subTest(quest=definition['id']):
                p, core = quest_plugin()
                q = deepcopy(definition)
                p.qstate.update(active=[q], locked=[], completed=[])
                root = core.state.state
                # An unrelated huge win count must never satisfy specific-source tasks.
                root['stats'].update(fights_won=99999, fights_total=99999)
                p._check_battle_quests([])
                self.assertFalse(p.qstate['completed'])
                set_counter(root, q['counter_key'], q['target'] - 1)
                p._check_battle_quests([])
                self.assertEqual(q.get('progress', 0), q['target'] - 1)
                self.assertFalse(p.qstate['completed'])
                expected = p._quest_xp_effective(q)
                set_counter(root, q['counter_key'], q['target'])
                messages = []
                p._check_battle_quests(messages)
                self.assertEqual(root['player']['xp'], expected)
                self.assertEqual(q['progress'], q['target'])
                self.assertEqual(len(p.qstate['completed']), 1)
                p._check_battle_quests(messages)
                self.assertEqual(root['player']['xp'], expected)
                self.assertEqual(sum('Quest abgeschlossen:' in m for m in messages), 1)
                self.assertEqual(sum('+1 Talentpunkt' in m for m in messages), 1)
                self.assertEqual(len(messages), 2)  # completion + the new one-time talent reward

    def test_migration_keeps_old_completions_and_new_partial_progress(self):
        p, core = quest_plugin()
        old = deepcopy(next(q for q in _ALL_QUEST_DEFINITIONS if q['id'] == 'first_win'))
        old.update(progress=1, completed_at='2026-09-01T10:00:00')
        partial = deepcopy(next(q for q in COMBAT_QUESTS if q['id'] == 'dungeon_0_clears_3'))
        partial['progress'] = 2
        p.qstate.update(active=[partial], completed=[old], locked=[], available=[])
        p._ensure_default_quests()
        p._ensure_default_quests()
        ids = [q['id'] for group in ('active', 'completed', 'locked', 'available') for q in p.qstate[group]]
        self.assertEqual(len(ids), 188)
        self.assertEqual(len(set(ids)), 188)
        self.assertEqual(p.qstate['completed'], [old])
        self.assertEqual(partial['progress'], 2)
        p._save_runtime_state()
        restored_state = SavedState()
        restored_state.state = deepcopy(core.state.saved)
        restored = Plugin(core=SimpleNamespace(state=restored_state))
        self.assertEqual(restored.qstate, p.qstate)

    def test_five_room_clear_and_aborted_runs(self):
        p, core = quest_plugin(10)
        q = deepcopy(next(q for q in COMBAT_QUESTS if q['id'] == 'dungeon_0_clears_1'))
        p.qstate.update(active=[q], locked=[], completed=[])
        def win(*args, **kwargs):
            core.state.state['stats']['fights_won'] = core.state.state['stats'].get('fights_won', 0) + 1
            p.refresh_combat_quests()
            self.assertFalse(p.qstate['completed'])  # A fifth fight alone is not yet a clear record.
        core.run_fight = win
        scenes = []
        def narrate(lines, music, entry):
            if entry['module'] == 'dungeon_end':
                self.assertEqual(q['progress'], 1)  # Reward is ready before the closing scene.
            scenes.append(entry)
        self.assertTrue(run(core, 0, narrate, Mock(), on_progress=p.refresh_combat_quests))
        self.assertEqual(core.state.state['dungeon_runs']['0']['completed'], 1)
        xp = core.state.state['player']['xp']
        # Losing or fleeing immediately gives neither another clear nor another reward.
        core.run_fight = Mock()
        self.assertFalse(run(core, 0, Mock(), Mock(), on_progress=p.refresh_combat_quests))
        p.refresh_combat_quests()
        self.assertEqual(core.state.state['dungeon_runs']['0']['completed'], 1)
        self.assertEqual(core.state.state['player']['xp'], xp)

    def test_endless_record_vs_lifetime_updates_before_next_wave(self):
        p, core = quest_plugin()
        targets = [deepcopy(q) for q in COMBAT_QUESTS if q['id'] in ('dungeon_plus_wave_5', 'dungeon_plus_wave_10', 'dungeon_plus_total_100')]
        p.qstate.update(active=targets, completed=[], locked=[])
        for attempt in range(2):
            calls = []
            def fight(*args, **kwargs):
                calls.append(kwargs['context'])
                if len(calls) <= 5:
                    root = core.state.state
                    root['stats']['fights_won'] = root['stats'].get('fights_won', 0) + 1
                else:
                    self.assertTrue(any(q['id'] == 'dungeon_plus_wave_5' for q in p.qstate['completed']))
            core.run_fight = fight
            self.assertEqual(run_endless(core, Mock(), Mock(), on_progress=p.refresh_combat_quests), 5)
        plus = core.state.state['dungeon_plus']
        self.assertEqual(plus['best_wave'], 5)
        self.assertEqual(plus['total_wins'], 10)
        active = {q['id']: q for q in p.qstate['active']}
        self.assertEqual(active['dungeon_plus_wave_10']['progress'], 5)
        self.assertEqual(active['dungeon_plus_total_100']['progress'], 10)

    def test_read_only_counters_and_perspectives(self):
        root = dict(stats=dict(fights_won=999), dungeon_runs={'0': dict(attempts=8, best_room=4)}, dungeon_plus=dict(attempts=4, last_wave=9))
        before = deepcopy(root)
        self.assertTrue(all(v == 0 for v in progress_counters(root).values()))
        self.assertEqual(before, root)
        p, _ = quest_plugin()
        for q in COMBAT_QUESTS:
            adapted = display(q)
            self.assertIn('Maatis als KI', adapted['desc'])
            self.assertEqual({k:v for k,v in q.items() if k != 'desc'}, {k:v for k,v in adapted.items() if k != 'desc'})
            p._lang = lambda: 'en'
            self.assertEqual(p._quest_display(q)['desc'], q['en_desc'])

    def test_gui_filters_sidebar_links_and_actual_worker_snapshot(self):
        p, core = quest_plugin(15)
        p.plugin_id = 'quests'
        p.qstate['meta'].update(messages_total=20, quest_intro_shown=True)
        p._check_unlocks()
        core.state.state['dungeon_runs'] = {'1': dict(completed=2)}
        p.refresh_combat_quests()
        runtime = Runtime.__new__(Runtime)
        runtime.language = 'de'
        runtime.pm = SimpleNamespace(iter_all_plugins=lambda: [p])
        with patch('gui.game_worker.emit') as emit:
            runtime.quest_snapshot()
        data = emit.call_args.kwargs['data']
        q = next(q for q in data['groups']['active'] if q['id'] == 'dungeon_1_clears_3')
        self.assertEqual((q['progress'], q['target']), (2, 3))
        self.assertIn('Stufe 15', q['status_label'])
        log = QuestLog()
        sidebar = CharacterSidebar()
        try:
            log.update_data(data)
            log.category.setCurrentIndex(log.category.findData('dungeon'))
            self.assertGreater(log.list.count(), 0)
            from PySide6.QtCore import Qt
            for i in range(log.list.count()):
                self.assertEqual(log.list.item(i).data(Qt.UserRole)['category'], 'dungeon')
            log.category.setCurrentIndex(log.category.findData('combat'))
            log.select_quest(q['id'])
            self.assertEqual(log.progress.value(), 2)
            self.assertEqual(log.category.currentData(), 'all')
            self.assertEqual(log.list.currentItem().data(Qt.UserRole)['id'], q['id'])
            sidebar.update_quests({'groups': {'active': [q]}})
            self.assertEqual(sidebar.quest_rows[0][2].format(), '2/3')
            self.assertEqual(sidebar.quest_rows[0][0].property('quest_link'), q['id'])
        finally:
            log.deleteLater()
            sidebar.deleteLater()
            APP.processEvents()

    def test_real_worker_awards_dungeon_clear_before_any_new_chat(self):
        w = Worker(seed={'battle_state.json': {
            'player': {'level': 50, 'hp': 99999, 'max_hp': 99999},
            'world': {'combat_unlocked': False},
            'quests': {'meta': {'messages_total': 20, 'quest_intro_shown': True}},
        }})
        events, battle = [], {}
        try:
            w.send(op='text', text='/dungeon-enter 1')
            for _ in range(250):
                batch = w.until(lambda e: e['event'] == 'prompt' or (e['event'] == 'busy' and not e['value']), timeout=30)
                events.extend(batch)
                for e in batch:
                    if e['event'] == 'battle':
                        battle.update(e)
                if batch[-1]['event'] != 'prompt':
                    break
                choice = {'harmonie': '1', 'balance': '2', 'schöpfungskraft': '3', 'verbundenheit': '4', 'respekt': '5'}.get(str(battle.get('weakness', '')).lower(), '3')
                w.send(op='answer', id=batch[-1]['id'], value=choice)
            else:
                self.fail('Dungeon did not finish')
            saved = json.loads((Path(w.temp.name) / 'state/battle_state.json').read_text())
            self.assertEqual(saved['dungeon_runs']['1']['completed'], 1)
            self.assertEqual(saved['quests']['meta']['messages_total'], 20)
            q = next(q for q in saved['quests']['completed'] if q['id'] == 'dungeon_1_clears_1')
            self.assertEqual(q['progress'], 1)
            snapshots = [e['data']['groups'] for e in events if e['event'] == 'quests']
            self.assertTrue(any(any(q['id'] == 'dungeon_1_clears_1' for q in g['completed']) for g in snapshots))
            partial = next(q for q in snapshots[-1]['active'] if q['id'] == 'dungeon_1_clears_3')
            self.assertEqual(partial['progress'], 1)
            self.assertIn('1/3', partial['progress_text'])
            xp = saved['player']['xp']
            w.command('/quests')
            updated = json.loads((Path(w.temp.name) / 'state/battle_state.json').read_text())
            self.assertEqual(updated['player']['xp'], xp)
        finally:
            w.close()
