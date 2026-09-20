"""Real combat consumption, persisted stock and live HUD updates; private saves."""
import io
import random
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from test_desktop import APP
from test_live_window import SilentAudio
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QLabel
from apps.maat_rpg.plugins.battle import plugin_main as battle
from gui.character_sidebar import CharacterSidebar
from gui.live_session import LiveSession
from gui.live_window import LiveWindow
from shared.core import gui_bridge


class PotionInventoryTests(unittest.TestCase):
    def dispose(self, widget):
        widget.close()
        widget.deleteLater()
        QCoreApplication.sendPostedEvents(widget, QEvent.DeferredDelete)

    def test_real_fights_send_consumed_inventory_before_the_next_round(self):
        for language in ('de', 'en'):
            for kind, source in (('boss', 'arena'), ('final', 'random'),
                                 ('normal', 'arena'), ('normal', 'random'), ('normal', 'dungeon')):
                with self.subTest(language=language, kind=kind, source=source), \
                        tempfile.TemporaryDirectory() as folder, redirect_stdout(io.StringIO()), \
                        patch.object(battle, 'state_file', return_value=Path(folder)/'battle_state.json'), \
                        patch.object(battle, 'BattleMusicManager'), \
                        patch.object(battle, '_battle_ui_language', return_value=language):
                    core = battle.BattleCore(folder)
                    core.state.state['player'].update(hp=40, max_hp=160, level=7, potions=6)
                    core.state.save()
                    core._load_story_state = lambda: {}
                    core._save_story_state = Mock()
                    core._register_boss_codex_entry = Mock()
                    core._choose_music = Mock(return_value=(None, None))
                    core._slow_line = Mock()
                    # Exclude reward drops from this consumption test.
                    core._reward_on_victory = Mock(return_value='')
                    choices = iter(['4'])
                    core._prompt = lambda *args, **kwargs: next(choices, '1')
                    session, sidebar = LiveSession(), CharacterSidebar()
                    sidebar.set_language(language)
                    session.on_snapshot(lambda s: sidebar.update_player(s.player))
                    session._handle(dict(event='profile', data={'potions': 6}))
                    session.on_transport(lambda e: session.release_encounter() if e['event']=='encounter_intro'
                                         else session.release_battle_presentation() if e['event']=='battle_presentation' else None)
                    events = []
                    def forward(event, **data):
                        packet = dict(event=event, **data)
                        events.append(packet)
                        session._handle(packet)
                        if event == 'battle_effect' and data.get('attack') == 'heal':
                            self.assertEqual(data['player_potions'], 5)
                            self.assertEqual(session.get_snapshot().player.potions, 5)
                            self.assertTrue(sidebar.items.text().endswith(': 5'))
                            # The actual save is already updated before this event.
                            self.assertEqual(battle.BattleState(folder).state['player']['potions'], 5)
                    rng = random.getstate()
                    gui_bridge.install(forward)
                    try:
                        random.seed(41)
                        core.run_fight(kind, {'combat_source': source, 'fast_output': True})
                        hud = [e for e in events if e['event']=='battle']
                        self.assertEqual(hud[0]['player_potions'], 6)
                        self.assertTrue(all(e['player_potions']==5 for e in hud[1:]))
                        self.assertEqual(len([e for e in events if e.get('attack')=='heal']), 1)
                        self.assertEqual(battle.BattleState(folder).state['player']['potions'], 5)
                    finally:
                        gui_bridge.install(None)
                        random.setstate(rng)
                        session.shutdown()
                        self.dispose(sidebar)

    def test_repeated_use_saves_each_decrement_and_never_consumes_at_full_hp(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(battle, 'state_file', return_value=Path(folder)/'battle_state.json'):
            core = battle.BattleCore(folder)
            player = core.state.state['player']
            player.update(hp=100, max_hp=100, potions=6)
            core.state.save()
            self.assertFalse(core._use_potion_in_fight()[1])
            self.assertEqual(player['potions'], 6)
            for remaining in range(5, -1, -1):
                player['hp'] = 20
                self.assertTrue(core._use_potion_in_fight()[1])
                self.assertEqual(player['hp'], 70)
                self.assertEqual(battle.BattleState(folder).state['player']['potions'], remaining)
            player['hp'] = 20
            self.assertFalse(core._use_potion_in_fight()[1])
            self.assertEqual((player['hp'], player['potions']), (20, 0))

    def test_live_inventory_zero_and_partial_events_keep_other_profile_fields(self):
        session = LiveSession()
        try:
            session._handle(dict(event='profile', data={'potions': 6, 'gold': 321, 'level': 7}))
            session._handle(dict(event='battle', active=True, player_potions=5))
            for remaining in (4, 3, 2, 1, 0):
                session._handle(dict(event='battle_effect', attack='heal', player_potions=remaining))
                self.assertEqual(session.get_snapshot().player.potions, remaining)
            session._handle(dict(event='battle_effect', attacker='enemy', damage=10))
            session._handle(dict(event='battle', active=True, player_hp=90))
            player = session.get_snapshot().player
            self.assertEqual((player.potions, player.gold, player.level), (0, 321, 7))
        finally:
            session.shutdown()

    def test_bilingual_menu_labels_and_no_tinyllama_context_advice(self):
        window = LiveWindow(audio=SilentAudio())
        try:
            for language, title in (('de', 'Heiltrank'), ('en', 'Healing Potion')):
                window.game._language = language
                window.game._snapshot = window.game._build_snapshot()
                window.apply_menu_language()
                self.assertEqual(window.arena.actions['potion'].text(), title)
                self.assertEqual(window.arena.actions['potion'].toolTip(), title)
                labels = [label.text() for label in window.ki_dialog.findChildren(QLabel)]
                self.assertTrue(any('TinyLlama' in text for text in labels))
                self.assertFalse(any('TinyLlama' in text and ('2.048' in text or '2,048' in text) for text in labels))
        finally:
            self.dispose(window)


if __name__ == '__main__':
    unittest.main()
