import unittest
from test_desktop import APP
from PySide6.QtCore import QCoreApplication, QEvent
from gui.battle_arena import BattleArena, CombatStage, weakness_key
from apps.maat_rpg.session_models import BattleSnapshot

class BattleFeedbackTests(unittest.TestCase):
    def dispose(self, widget):
        widget.close();widget.deleteLater()
        QCoreApplication.sendPostedEvents(widget,QEvent.DeferredDelete)

    def test_hit_target_queue_and_cleanup(self):
        stage=CombatStage()
        try:
            stage.show_effect(dict(attacker='player',damage=14))
            self.assertEqual((stage.hit_target,stage.hit_damage),('enemy',14))
            stage.show_effect(dict(attacker='enemy',damage=7))
            self.assertEqual(stage.hit_target,'enemy')
            for _ in range(7):stage.advance_effect()
            self.assertEqual((stage.hit_target,stage.hit_damage),('player',7))
            stage.clear_effects()
            self.assertIsNone(stage.hit_target)
            self.assertFalse(stage.hit_timer.isActive())
            stage.show_effect(dict(attacker='enemy',damage=0))
            self.assertEqual(stage.hit_damage,0)
        finally:self.dispose(stage)

    def test_weakness_pulse_and_boss_in_play_and_demo(self):
        for demo in (False,True):
            arena=BattleArena(demo=demo)
            try:
                arena.resize(680,760);arena.show();APP.processEvents()
                arena.update_state(dict(active=True,round_number=1,enemy_name='Schattenwächter',fight_type='boss',enemy_level=12,weakness='Schöpfungskraft',resonance=100))
                if not demo:
                    arena.set_hint_waiting(True)
                    self.assertNotIn('✦', arena.actions['s'].text())
                    arena.weakness_timer.timeout.emit()
                self.assertEqual(arena.weakness,'s')
                self.assertTrue(arena.actions['s'].weakness_highlight)
                self.assertIn('✦',arena.actions['s'].text())
                self.assertIn('LVL 12',arena.enemy_name.text())
                self.assertIn('BOSS',arena.enemy_name.text())
                self.assertTrue(arena.resonance.pulse_timer.isActive())
                self.assertIn('RESONANZ VOLL',arena.resonance.format())
                self.assertEqual(arena.action_columns,5)
                self.assertFalse(any(b.isEnabled() for b in arena.actions.values()))
                arena.update_state(dict(enemy_name='Funke',fight_type='normal',enemy_level=None,weakness='Harmony',resonance=45))
                self.assertIsNone(arena.actions['s'].graphicsEffect())
                self.assertFalse(arena.actions['s'].weakness_highlight)
                self.assertTrue(arena.actions['h'].weakness_highlight)
                self.assertFalse(arena.resonance.pulse_timer.isActive())
                self.assertNotIn('BOSS',arena.enemy_name.text())
                self.assertNotIn('LVL',arena.enemy_name.text())
                arena.resize(1280,880);APP.processEvents()
                self.assertEqual(arena.action_columns,10)
                arena.update_state({'resonance':100})
                arena.hide()
                self.assertFalse(arena.resonance.pulse_timer.isActive())
                self.assertFalse(arena.stage.hit_timer.isActive())
            finally:self.dispose(arena)
        self.assertEqual(weakness_key('Creation'),'s')
        self.assertEqual(weakness_key('Respekt'),'r')
        self.assertIsNone(weakness_key('—'))

    def test_transport_preserves_enemy_metadata(self):
        from gui.live_session import LiveSession
        session=LiveSession()
        try:
            session._handle(dict(event='battle',active=True,enemy_name='Boss',fight_type='final',enemy_level=50,round_number=3))
            session.release_battle_presentation()
            self.assertEqual(session._battle_state.fight_type,'final')
            self.assertEqual(session._battle_state.enemy_level,50)
            self.assertEqual(session._battle_state.round_number,3)
        finally:session.shutdown()

    def test_repeated_boss_updates_and_end_preserve_highlight_without_native_effects(self):
        # Crash log: style_actions -> QGraphicsDropShadowEffect constructor during
        # a boss-demo state update. Exercise redraws and the end/clear boundary.
        from unittest.mock import patch
        arena = BattleArena(demo=True)
        try:
            arena.resize(1020, 760); arena.show(); APP.processEvents()
            buttons = dict(arena.actions)
            names = [('h','Harmonie'), ('b','Balance'), ('s','Schöpfungskraft'),
                     ('v','Verbundenheit'), ('r','Respekt')]
            with patch('PySide6.QtWidgets.QGraphicsDropShadowEffect',
                       side_effect=AssertionError('Native shadow must not be allocated in combat')):
                for encounter in range(20):
                    for turn, (key, name) in enumerate(names, 1):
                        arena.update_state(dict(active=True, round_number=turn, fight_type='boss',
                                                enemy_name='Schattenwächter', enemy_hp=100-turn,
                                                enemy_max_hp=100, player_hp=100, player_max_hp=100,
                                                weakness=name, resonance=turn*20))
                        arena.style_actions()  # Repeated transport updates, same round.
                        APP.processEvents()
                        for action, btn in arena.actions.items():
                            self.assertIs(btn, buttons[action])
                            self.assertIsNone(btn.graphicsEffect())
                            self.assertEqual(btn.weakness_highlight, action == key)
                            self.assertEqual('✦' in btn.text(), action == key)
                        self.assertFalse(arena.actions[key].grab().isNull())
                    arena.update_state(dict(active=False, enemy_hp=0))
                    APP.processEvents()
                    self.assertTrue(arena.actions['r'].weakness_highlight)
                    arena.clear_opponent()
                    APP.processEvents()
                    self.assertFalse(any(btn.weakness_highlight for btn in arena.actions.values()))
        finally: self.dispose(arena)

    def test_round_hints_and_cleanup(self):
        arena = BattleArena()
        try:
            for turn in range(1, 7):
                arena.update_state(dict(active=True, round_number=turn, enemy_name='Funke', weakness='Respekt'))
                self.assertEqual('Schwäche:' in arena.details.text(), turn % 3 == 0)
                self.assertNotIn('✦', arena.actions['r'].text())
                self.assertFalse(arena.weakness_timer.isActive())
                arena.set_hint_waiting(True)
                self.assertTrue(arena.weakness_timer.isActive())
                self.assertGreater(arena.weakness_timer.remainingTime(), 29000)
                self.assertNotIn('✦', arena.actions['r'].text())
                arena.weakness_timer.stop()
                arena.weakness_timer.timeout.emit()
                self.assertIn('✦', arena.actions['r'].text())
                arena.update_state(dict(round_number=turn, resonance=20))
                self.assertIn('✦', arena.actions['r'].text())
                arena.set_hint_waiting(False)
                self.assertNotIn('✦', arena.actions['r'].text())
            arena.update_state(dict(active=False))
            arena.set_hint_waiting(True)
            arena.weakness_timer.timeout.emit()
            self.assertNotIn('✦', arena.actions['r'].text())
            self.assertFalse(arena.weakness_timer.isActive())
            arena.clear_opponent()
            self.assertEqual(arena._round, 0)
            self.assertFalse(arena._hint_elapsed.isValid())
            arena.append_text('Schwachstelle: Respekt\nWeakness: Respect\nEin Gegner greift an!\n')
            self.assertNotIn('Respekt', arena.log.toPlainText())
            self.assertNotIn('Respect', arena.log.toPlainText())
            self.assertIn('Ein Gegner greift an!', arena.log.toPlainText())
        finally:
            self.dispose(arena)
