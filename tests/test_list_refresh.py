"""Regressions for the macOS QListWidgetItemWrapper teardown crash."""
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt, QCoreApplication, QEvent
from test_desktop import APP
from gui.shop import Shop
from gui.quest_log import QuestLog
from apps.maat_rpg.plugins.quests.paid_contracts import PAID_CONTRACTS

class ListRefreshTests(unittest.TestCase):
    def test_busy_and_identical_snapshots_keep_contract_rows_alive(self):
        shop=Shop()
        data={'gold':3000,'level':50,'contracts':[dict(q,status='locked') for q in PAID_CONTRACTS]}
        try:
            shop.update_data(data)
            shop.contracts.list.setCurrentRow(7)
            row=shop.contracts.list.currentItem()
            resets=[]
            shop.contracts.list.model().modelReset.connect(lambda:resets.append(True))
            for i in range(100):
                shop.set_ready(i%2==0)
                shop.update_data(data)
                APP.processEvents()
            self.assertEqual(resets,[])
            self.assertIs(shop.contracts.list.currentItem(),row)
            self.assertEqual(row.data(Qt.UserRole),'contract50_08')
            shop.set_ready(True)
            self.assertTrue(shop.contracts.buy.isEnabled())
        finally:
            shop.close();shop.deleteLater()
            QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)

    def test_repeated_quest_and_contract_changes_keep_selection_and_details(self):
        quest=QuestLog();shop=Shop()
        data={'groups':{'active':[dict(id=str(i),name=f'Quest {i}',desc='Test',target=500,progress=0) for i in range(148)]}}
        try:
            quest.update_data(data);quest.list.setCurrentRow(12)
            for n in range(150):
                data['groups']['active'][12]['progress']=n
                quest.update_data(data)
                self.assertEqual(quest.list.currentItem().data(Qt.UserRole)['id'],'12')
                self.assertEqual(quest.progress.value(),n)
                shop.update_data({'gold':3000,'level':50,'contracts':[dict(q,status='active' if n%2 else 'locked',progress=n) for q in PAID_CONTRACTS]})
                shop.contracts.filter.setCurrentIndex(n%4)
                APP.processEvents()
            quest.update_data({'groups':{}})
            self.assertEqual(quest.list.count(),0)
            self.assertIn('Ein neuer Weg wartet',quest.detail.toPlainText())
        finally:
            for w in (quest,shop):w.close();w.deleteLater()
            QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
