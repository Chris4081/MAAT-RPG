"""English gameplay integration: canonical IDs, rewards and timing stay intact."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QLabel
from test_desktop import APP
import test_gui_language as language_helpers
from test_live_rpg import Worker
from apps.maat_rpg import session_shared
from gui.battle_arena import BattleArena
from shared.core.dungeon_campaign import dungeon, run, run_endless


class GameplayLanguageTests(unittest.TestCase):
    setUp = language_helpers.LanguageTests.setUp
    close_windows = language_helpers.LanguageTests.close_windows
    window = language_helpers.LanguageTests.window
    ready = language_helpers.LanguageTests.ready

    def test_english_character_class_dungeon_and_live_updates(self):
        session_shared.write_application_language('en')
        session_shared.write_profile_settings(1, {'language':'en'})
        w = self.window()
        self.ready(w)
        w.enter_menu()
        w.begin_game()
        w.intro.finish()
        w.perspective_screen.cards['adventure'].click()
        w.text_stream.finish()
        w.game._handle({'event':'profile','data':{'level':50,'hp':220,'max_hp':240,
                                                'potions':12,'fights_won':35,'boss_wins':2}})
        w.receive({'event':'dungeons','level':50,'records':{'0':{'attempts':4,'completed':3,'best_room':5}},
                   'plus':{'attempts':2,'best_wave':17,'total_wins':24}})
        self.assertIn('Healing potions: 12', w.character_sidebar.items.text())
        self.assertIn('Boss wins: 2', w.character_sidebar.wins.text())
        self.assertIn('Completions: 3', w.character_sidebar.dungeon_summary.text())
        self.assertIn('Best: 17 waves', w.character_sidebar.dungeon_summary.text())
        self.assertIn('Principles restored', w.character_values.text())
        self.assertIn('No active quests', w.character_sidebar.quest_hint.text())
        self.assertIn('Words &amp; discoveries', w.character_sidebar.achievement_categories.text())
        self.assertIn('category:Worte%20%26%20Entdeckungen', w.character_sidebar.achievement_categories.text())
        self.assertIn('messages', w.character_sidebar.terra_map.progress.text())
        self.assertIn('Enter Dungeon+', w.dungeons.plus_button.text())
        names=[label.text() for label in w.dungeons.findChildren(QLabel)]
        self.assertTrue(any('Gate of 60 Voices' in name for name in names))
        self.assertTrue(any('Heart of the Five Principles' in name for name in names))
        self.assertTrue(w.dungeons.buttons[8][0].isEnabled())
        self.assertFalse(w.dungeons.buttons[9][0].isEnabled())
        selected=[]
        w.class_selection.selected.connect(selected.append)
        w.class_selection.start('test-only')
        w.class_selection.cards['magier'].click()
        self.assertEqual(w.class_selection.cards['magier'].text(),'Mage')
        self.assertIn('wizard', w.class_selection.description.text())
        self.assertEqual(w.class_selection.confirm.text(),'Continue as Mage  →')
        w.class_selection.confirm.click()
        self.assertEqual(selected,['magier'])
        self.assertIn('Saving class', w.class_selection.confirm.text())
        self.assertEqual(w.title_screen.arena.language,'en')

    def test_arena_language_preserves_attack_ids_damage_and_weakness_delay(self):
        for demo in (False, True):
            arena=BattleArena(demo=demo)
            try:
                arena.set_language('en')
                state=dict(active=True,round_number=1,enemy_name='Crystal Guardian',
                    fight_type='boss',enemy_level=12,weakness='Schöpfungskraft',resonance=100,
                    combat_source='demo' if demo else 'random',arena_difficulty='hard',
                    player_hp=130,player_max_hp=150,enemy_hp=90,enemy_max_hp=200)
                original=copy.deepcopy(state)
                arena.update_state(state)
                self.assertEqual(state,original)
                self.assertEqual(arena.actions['potion'].text(),'Potion')
                self.assertEqual(arena.actions['escape'].text(),'Escape')
                self.assertIn('Creation',arena.actions['s'].toolTip())
                self.assertIn('HARD',arena.difficulty_badge.text())
                self.assertIn('FULL RESONANCE',arena.resonance.format())
                if not demo:
                    self.assertNotIn('Weakness:',arena.details.text())
                    arena.set_hint_waiting(True)
                    remaining=arena.weakness_timer.remainingTime()
                    arena.set_language('de')
                    self.assertGreater(arena.weakness_timer.remainingTime(),remaining-500)
                    arena.set_language('en')
                    self.assertEqual(arena.weakness,'s')
                    arena.weakness_timer.timeout.emit()
                    self.assertTrue(arena.actions['s'].weakness_highlight)
                arena.update_state({'round_number':3,'weakness':'Creation','aura':'silence'})
                self.assertIn('Weakness: Creation',arena.details.text())
                self.assertIn('Aura: Silence',arena.details.text())
                received=[]
                arena.action_requested.connect(received.append)
                arena.actions['s'].setEnabled(True)
                arena.actions['s'].click()
                self.assertEqual(received,['s'])
                self.assertEqual(arena.hero_hp.value(),130)
                self.assertEqual(arena.enemy_hp.value(),90)
                arena.stage.show_effect({'attacker':'player','attack':'focus','heal':12,'damage':0})
                self.assertEqual(arena.stage.hit_label,'+12 HP')
                arena.clear_opponent()
                arena.set_language('de')
                self.assertIsNone(arena.stage.name)
            finally:
                arena.close()
                arena.deleteLater()
                QCoreApplication.sendPostedEvents(arena,QEvent.DeferredDelete)

    def test_all_dungeon_stories_translate_without_changing_progression(self):
        for index in range(9):
            outcomes=[]
            for language in ('de','en'):
                core=Mock()
                core.state.state={'player':{'level':50,'hp':100},'stats':{'fights_won':0}}
                fights=[]
                def fight(kind,context):
                    fights.append(context)
                    core.state.state['stats']['fights_won']+=1
                    core.state.state['player']['hp']-=5
                core.run_fight.side_effect=fight
                narrate=Mock();notify=Mock()
                self.assertTrue(run(core,index,narrate,notify,language=language))
                outcomes.append(copy.deepcopy(core.state.state))
                self.assertEqual(len(fights),5)
                self.assertEqual(len(narrate.call_args_list),6)
                self.assertEqual([c.kwargs['action'] for c in notify.call_args_list if c.args==('audio',)],['play','stop'])
                self.assertTrue(all(c.args[1] is None for c in narrate.call_args_list))
                if language=='en':
                    self.assertIn('Room 1/5',narrate.call_args_list[0].args[2]['name'])
                    self.assertIn('Five battles lie ahead',narrate.call_args_list[0].args[0][-1])
                    self.assertIn('Opponent 5/5',fights[-1]['battle_profile']['intro_lines'][0])
                    self.assertIn('Completed',narrate.call_args_list[-1].args[2]['name'])
            self.assertEqual(outcomes[0],outcomes[1])
            de,en=dungeon(index),dungeon(index,'en')
            for key in ('id','level','theme','boss_music'):
                self.assertEqual(de[key],en[key])
            self.assertNotEqual(de['name'],en['name'])
            self.assertTrue(all(a!=b for a,b in zip(de['original'],en['original'])))

    def test_endless_english_narrative_keeps_playlist_and_loss_exit(self):
        core=Mock()
        core.state.state={'player':{'level':50,'hp':100},'stats':{'fights_won':0}}
        contexts=[]
        def fight(kind,context):
            contexts.append(context)
            if len(contexts)<3:core.state.state['stats']['fights_won']+=1
        core.run_fight.side_effect=fight
        narrate=Mock();notify=Mock()
        self.assertEqual(run_endless(core,narrate,notify,language='en'),2)
        self.assertIn('The Endless Depths',narrate.call_args_list[0].args[2]['name'])
        self.assertIn('2 victorious waves',narrate.call_args_list[-1].args[0][0])
        self.assertIn('Wave 3',contexts[-1]['battle_profile']['intro_lines'][0])
        audio=[c.kwargs for c in notify.call_args_list if c.args==('audio',)]
        self.assertEqual([c['action'] for c in audio],['play','stop'])
        self.assertEqual(audio[0]['playlist'],[dungeon(i)['theme'] for i in range(3)])
        self.assertEqual(core.state.state['dungeon_plus']['last_result'],'beendet')

    def test_real_english_worker_dungeon_uses_english_choices_and_scenes(self):
        worker=Worker(seed={'settings_state.json':{'language':'en'},
            'battle_state.json':{'player':{'level':10,'hp':9999,'max_hp':9999},
                                'stats':{'boss_progress':7},'world':{'combat_unlocked':False}}})
        all_events=[]
        try:
            worker.send(op='text',text='/dungeon-enter 0')
            for _ in range(180):
                events=worker.until(lambda e:e['event']=='prompt' or (e['event']=='busy' and not e['value']),timeout=30)
                all_events+=events
                last=events[-1]
                if last['event']!='prompt':break
                # Canonical input values remain unchanged in the English worker.
                choices=last.get('choices',[])
                choice=next((c for c in choices if 'Creation' in c['label']),None)
                value=choice['value'] if choice else '1'
                worker.send(op='answer',id=last['id'],value=value)
            else:self.fail('English dungeon did not finish')
            scenes=[e for e in all_events if e['event']=='story_scene']
            self.assertEqual(len(scenes),6)
            self.assertIn('Gate of 60 Voices · Room 1/5',scenes[0]['name'])
            self.assertIn('You enter the tunnel of voices.',scenes[0]['lines'])
            self.assertTrue(any('Attack' in c['label'] for e in all_events if e['event']=='prompt' for c in e.get('choices',[])))
            saved=json.loads((Path(worker.temp.name)/'state/battle_state.json').read_text())
            self.assertEqual(saved['dungeon_runs']['0']['completed'],1)
            self.assertEqual(saved['stats']['boss_progress'],7)
            audio=[e for e in all_events if e['event']=='audio' and e.get('owner')=='dungeon-run']
            self.assertEqual([e['action'] for e in audio],['play','stop'])
        finally:
            worker.close()


if __name__=='__main__':
    unittest.main()
