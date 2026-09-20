import os
from pathlib import Path
import unittest
from PySide6.QtCore import Qt,QCoreApplication,QEvent
from PySide6.QtWidgets import QTreeWidgetItemIterator
from test_desktop import APP
from test_live_rpg import Worker
from gui.quest_log import QuestLog
from gui.command_menu import CommandMenu
from gui.desktop import STYLE

class QuestHubTests(unittest.TestCase):
    def test_real_quest_progress_and_complete_command_catalog(self):
        worker=Worker()
        log=QuestLog()
        menu=CommandMenu()
        try:
            worker.command('/ai-start')
            worker.send(op='companion_answer',choice=0,text='Ich prüfe alle Hinweise mit dir gemeinsam und erkläre dir meine Entscheidung sorgfältig, bevor wir den nächsten Schritt in der Bibliothek unternehmen.')
            events=worker.until(lambda e:e['event']=='busy' and not e['value'])
            data=[e['data'] for e in events if e['event']=='quests'][-1]
            log.update_data(data)
            q=next(q for q in data['groups']['active'] if q['id']=='know_maat_ki')
            self.assertEqual(q['progress'],1)
            self.assertEqual(q['target'],10)
            self.assertIn('Lerne Maatis kennen',log.list.item(0).text())
            self.assertEqual(log.progress.value(),1)
            self.assertFalse(log.accept.isVisible())
            # The read-only journal must not execute anything on selection.
            emitted=[]
            log.command_requested.connect(emitted.append)
            log.filter.setCurrentIndex(log.filter.findData('locked'))
            self.assertTrue(log.list.count()>0)
            self.assertFalse(emitted)
            log.filter.setCurrentIndex(0)
            catalog=next(e['items'] for e in worker.boot if e['event']=='commands')
            menu.populate(catalog)
            found=set()
            iterator=QTreeWidgetItemIterator(menu)
            while iterator.value():
                item=iterator.value()
                command=item.data(0,Qt.UserRole)
                if command:found.add(command['command'])
                iterator+=1
            self.assertEqual(found,{i['command'] for i in catalog})
            self.assertGreater(menu.topLevelItemCount(),4)
            selected=[]
            menu.chosen.connect(selected.append)
            menu.populate(catalog,'d500 next')
            root=menu.topLevelItem(0).child(0)
            menu.setCurrentItem(root.child(0))
            self.assertEqual(selected[-1]['command'],'/d500 next')
            if os.environ.get('MAAT_GUI_SCREENSHOTS'):
                folder=Path(os.environ['MAAT_GUI_SCREENSHOTS'])
                for widget,name in [(log,'quest-log'),(menu,'command-menu')]:
                    widget.setStyleSheet(STYLE+'\n'+widget.styleSheet())
                    widget.resize(900,680)
                    if widget is menu:menu.populate(catalog)
                    widget.show()
                    APP.processEvents()
                    widget.grab().save(str(folder/(name+'.png')))
        finally:
            worker.close()
            for widget in (log,menu):
                widget.close();widget.deleteLater()
                QCoreApplication.sendPostedEvents(widget,QEvent.DeferredDelete)
