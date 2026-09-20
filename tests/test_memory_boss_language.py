"""English memory notices, unchanged private content and authored boss titles."""
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime
import io
import os
from pathlib import Path
import tempfile
import unicodedata
import unittest
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication,QEvent,Qt
from PySide6.QtWidgets import QMessageBox
from test_desktop import APP
from test_live_rpg import Worker
import test_gui_language as language_helpers
from apps.maat_rpg import session_shared
from shared.plugins.super_memory.plugin_main import Plugin
from shared.core.super_memory import SuperMemory
from shared.core.monster_catalog import BOSS_NAMES,FINAL_NAMES,enemy_display_name
from gui.memories import Memories


class MemoryLanguageTests(unittest.TestCase):
    def test_real_save_notifications_errors_and_reports_follow_language(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SuperMemory(folder);plugin=Plugin();plugin.store=store
            with patch('shared.core.rpg_i18n.get_language',return_value='en'):
                self.assertEqual(plugin.command('/mem save Mein Projekt bleibt vollständig lokal.'),'🧠 Memory saved.')
                context={};plugin.before_chat('I prefer concise answers.',context)
                with redirect_stdout(io.StringIO()) as output:
                    plugin.after_response('Understood.',context)
                self.assertIn('new memory/memories saved · Memories → Saves',output.getvalue())
                with redirect_stdout(io.StringIO()) as output:plugin.after_response('Understood.',context)
                self.assertEqual(output.getvalue(),'')
                context['super_memory_error']='Neue Erinnerung konnte nicht gespeichert werden.'
                with redirect_stdout(io.StringIO()) as output:plugin.after_response('Understood.',context)
                self.assertIn('The new memory could not be saved.',output.getvalue())
                self.assertIn('Working memory:',plugin.command('/mem stats'))
                for kind,expected in [('timeline','MAAT Timeline (all memories)'),('milestones','MAAT Milestones (all memories)'),('recent','Recent memories:')]:
                    result=store.report(kind,language='en')
                    self.assertIn(expected,result)
                    self.assertNotIn('Quelle:',result);self.assertNotIn('vor ',result)
                for lang,title in [('en','Memory created'),('de','Erinnerung angelegt')]:
                    box=store.engine._format_save_box([{'memory':'Unveränderter Inhalt'}],language=lang)
                    self.assertIn(title,box);self.assertIn('Unveränderter Inhalt',box)
                before=deepcopy(store.entries())
                self.assertIn('Arbeitsgedächtnis:',store.report(language='de'))
                self.assertEqual(store.entries(),before)
                with patch.object(store,'save',side_effect=OSError('simulated error')):
                    self.assertIn('Memory action failed',plugin.command('/mem save Test'))

    def test_memory_ui_labels_sources_filters_and_confirmations_keep_saved_prose(self):
        with tempfile.TemporaryDirectory() as folder:
            page=Memories();page.set_profile(folder)
            try:
                page.store.append('user','Meine privaten Notizen bleiben auf Deutsch.','companion','2026-09-15T12:00:00')
                page.saves.store.save('Mein Projekt ist lokal.',runtime_context={'memory_perspective':'companion'})
                page.set_count(5);page.saves.refresh()
                before=deepcopy(page.saves.store.entries())
                for lang in ('en','de','en'):
                    page.set_language(lang)
                    self.assertIn('Meine privaten Notizen bleiben auf Deutsch.',page.transcript.toPlainText())
                    self.assertEqual(page.saves.store.entries(),before)
                self.assertIn('You · Companion AI',page.transcript.toPlainText())
                self.assertIn('Delete message',page.transcript.toPlainText())
                self.assertEqual(page.month.itemText(3),'March')
                self.assertEqual(page.order.itemText(0),'Newest days first')
                self.assertEqual(page.saves.tabs.tabText(3),'Settings')
                self.assertEqual(page.saves.tabs.tabText(2),'Timeline and maintenance')
                self.assertIn('Source: companion AI (player)',page.saves.detail.toPlainText())
                self.assertIn('Mein Projekt ist lokal.',page.saves.detail.toPlainText())
                page.saves.new_text.setPlainText('Noch eine deutsche Notiz.')
                page.saves.save_entry();self.assertEqual(page.saves.status.text(),'Memory saved.')
                self.assertIn('Noch eine deutsche Notiz.',[r['content'] for r in page.saves.store.entries()])
                page.saves.search.setText('Noch eine')
                self.assertEqual(page.saves.list.count(),1)
                page.saves.set_language('de');page.saves.set_language('en')
                self.assertEqual(page.saves.search.text(),'Noch eine')
                with patch.object(QMessageBox,'question',return_value=QMessageBox.No) as dialog:
                    page.saves.confirm_delete('entry')
                self.assertEqual(dialog.call_args.args[1],'Permanently delete saves')
                self.assertIn('This action cannot be undone',dialog.call_args.args[2])
                self.assertEqual(len(page.saves.store.entries()),2)
                with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):page.saves.confirm_delete('entry')
                self.assertEqual(len(page.saves.store.entries()),1)
                self.assertIn('1 saves deleted',page.saves.status.text())
                self.assertEqual(len(page.store.messages('2026-09-15')),1)
            finally:
                page.close();page.deleteLater();QCoreApplication.sendPostedEvents(page,QEvent.DeferredDelete)

    def test_actual_worker_memory_commands_remain_english(self):
        worker=Worker(seed={'settings_state.json':{'language':'en'}})
        try:
            for command,expected in [('/mem save Mein Projekt verwendet Python.','Memory saved.'),('/mem','Working memory:'),('/mem timeline','MAAT Timeline (all memories)'),('/mem milestones','MAAT Milestones (all memories)')]:
                output=''.join(e.get('text','') for e in worker.command(command) if e['event']=='output')
                self.assertIn(expected,output)
        finally:worker.close()


class BossLanguageTests(unittest.TestCase):
    def test_all_boss_forms_legacy_names_dungeon_announcements_and_path_titles(self):
        from apps.maat_rpg.plugins.battle import plugin_main as battle
        from apps.maat_rpg.plugins.dungeon_500 import plugin_main as d500
        from apps.maat_rpg.plugins.dungeon_1000 import plugin_main as d1000
        from apps.maat_rpg.plugins.story_loader import plugin_main as story
        core=battle.BattleCore.__new__(battle.BattleCore)
        for mode,total in [('boss',25),('final',5)]:
            for i in range(1,total+1):
                with patch.object(battle,'_battle_ui_language',return_value='de'):de=core._boss_profile(mode,i,i)
                with patch.object(battle,'_battle_ui_language',return_value='en'):en=core._boss_profile(mode,i,i)
                for key in ('title','special','intro'):
                    self.assertNotEqual(de[key],en[key])
                for key in ('aura_cycle','damage_mult'):self.assertEqual(de.get(key),en.get(key))
                if de.get('phase2'):self.assertNotEqual(de['phase2']['name'],en['phase2']['name'])
        for name in BOSS_NAMES+FINAL_NAMES:
            expected=enemy_display_name(name,'en')
            for variant in (unicodedata.normalize('NFD',name),name.replace('ä','ae').replace('ö','oe').replace('ü','ue'),name.upper()):
                self.assertEqual(enemy_display_name(variant,'en'),expected)
        for module in (d500,d1000):
            for name in module.BOSS_NAMES:
                with patch.object(module,'_lang',return_value='en'),patch.object(module.random,'choice',return_value=name):
                    self.assertEqual(module.random_boss_name(),enemy_display_name(name,'en'))
        plugin=story.Plugin.__new__(story.Plugin);plugin._language=lambda:'en'
        with patch.object(battle,'_battle_ui_language',return_value='en'):
            for path in ('respekt','harmonie','schoepfung'):
                for vow in ('protect','truth','remember'):
                    plugin.state={'choices':{'reflection_path':path,'combat_vow':vow}}
                    profile=plugin._build_path_profile()
                    self.assertNotRegex(profile['title'],r'Grenz|Klang|Formtr|Schutz|Wahrheit|Erinnerung')
                    self.assertNotRegex(profile['motif'],r'Grenzen|Erinnerung|Schoepfung|Klang|Wahrheit|Moeglichkeit')
                    self.assertTrue(core._profile_boss_line(profile,{},'taunt'))
                    self.assertTrue(core._profile_reactive_entrance(profile,{'title':'Test Boss'},'boss'))
            profile={'title':'Grenzhüter des Schutzes','rank':'Erwachend'}
            self.assertIn('Boundary Keeper of Protection',core._profile_boss_line(profile,{},'taunt'))
            merged=core._localize_boss_profile(core._merge_boss_profile(core._boss_profile('boss',1,1),{'title':'Waechter der Resonanz'}))
            self.assertEqual(merged['title'],'Guardian of Resonance')
        self.assertEqual(enemy_display_name('My custom boss','en'),'My custom boss')


class MemoryLiveLanguageTests(unittest.TestCase):
    setUp=language_helpers.LanguageTests.setUp
    close_windows=language_helpers.LanguageTests.close_windows
    window=language_helpers.LanguageTests.window
    ready=language_helpers.LanguageTests.ready

    def test_live_memory_page_english_preview(self):
        session_shared.write_application_language('en');session_shared.set_profile_name(1,'Memory language test')
        w=self.window();self.ready(w);w.phase='playing'
        w.memories.store.append('user','I prefer short answers and local models.','adventure','2026-09-15T12:00:00')
        w.memories.saves.store.save('The player prefers short answers and local models.',runtime_context={'memory_perspective':'adventure'})
        w.memories.set_count(5);w.memories.saves.refresh()
        self.assertEqual(w.memories.language,'en')
        self.assertEqual(w.memories.body.tabText(0),'Chat history')
        w.stack.setCurrentWidget(w.memories);w.memories.body.setCurrentIndex(1)
        w.resize(1440,960);APP.processEvents()
        if os.environ.get('MAAT_LANGUAGE_PREVIEWS'):
            target=Path(os.environ['MAAT_LANGUAGE_PREVIEWS']);target.mkdir(parents=True,exist_ok=True)
            self.assertTrue(w.grab().save(str(target/'memories-en.png')))
