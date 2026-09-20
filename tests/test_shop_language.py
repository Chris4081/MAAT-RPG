"""The real shop stays bilingual without changing purchases or saved quest IDs."""
from copy import deepcopy
import json
import os
from pathlib import Path
import unittest
from PySide6.QtCore import Qt, QCoreApplication, QEvent
from PySide6.QtWidgets import QLabel
from test_desktop import APP
from test_live_rpg import Worker
import test_gui_language as language_helpers
from apps.maat_rpg import session_shared
from apps.maat_rpg.plugins.quests.paid_contracts import PAID_CONTRACTS, TITLES
from apps.maat_rpg.plugins.quests.english_content import display, TITLES as EN_TITLES
from gui.shop import Shop
from shared.core.shop_catalog import shop_snapshot, item_price


def shop_data(events):
    return next(e['data'] for e in reversed(events) if e['event']=='shop')


class ShopLanguageTests(unittest.TestCase):
    def test_cards_contract_details_filters_and_progress_survive_language_switch(self):
        worker=Worker(seed={'battle_state.json':{'player':{'level':50,'gold':5000}}})
        shop=Shop()
        try:
            data=shop_data(worker.boot)
            self.assertEqual(len(data['contracts']),25)
            data['earned_titles']=TITLES
            data['contracts'][0].update(status='active',progress=3,path_bonus='Pfad-Bonus: +1 Schutz-Siegel bei Abschluss.')
            original=deepcopy(data)
            shop.update_data(data);shop.set_ready(True);shop.set_language('en')
            self.assertEqual(shop.tabs.tabText(0),'Supplies')
            self.assertEqual(shop.tabs.tabText(1),'📜 Contract board')
            potion=shop.items['potion'];potion['quantity'].setValue(2)
            self.assertEqual(potion['name'].text(),'Healing Potion')
            self.assertIn('50%',potion['description'].text())
            self.assertIn('In your bag:',potion['info'].text())
            self.assertEqual(potion['buy'].text(),f'Buy · {item_price("potion",50)*2} gold')
            board=shop.contracts
            self.assertIn('Progress: 3 / 5',board.details.toPlainText())
            self.assertIn('Path bonus: +1 warding sigil',board.details.toPlainText())
            self.assertEqual(board.buy.text(),'Already purchased · Active in your quest log')
            for title in EN_TITLES.values():self.assertIn(title,board.titles.text())
            for row,q in enumerate(data['contracts']):
                board.list.setCurrentRow(row)
                expected=display(q,q,False)
                self.assertIn(expected['name'],board.list.item(row).text())
                for line in expected['desc'].splitlines():
                    self.assertIn(line,board.details.toPlainText())
            board.filter.setCurrentIndex(3)
            self.assertEqual(board.list.count(),5)
            self.assertIn('2,000 gold',board.buy.text())
            selected=board.list.currentItem().data(Qt.UserRole)
            for lang in ('de','en','de','en'):
                shop.set_language(lang)
                self.assertEqual(board.filter.currentData(),2000)
                self.assertEqual(board.list.currentItem().data(Qt.UserRole),selected)
                self.assertEqual(potion['quantity'].value(),2)
                self.assertEqual(data,original)
            commands=[];shop.purchase_requested.connect(commands.append)
            board.buy.click();board.buy.click()
            self.assertEqual(commands,[f'/contracts buy {selected}'])
            self.assertEqual(shop.receipt.text(),'Purchasing contract …')
            self.assertFalse(potion['buy'].isEnabled())
        finally:
            worker.close();shop.close();shop.deleteLater()
            QCoreApplication.sendPostedEvents(shop,QEvent.DeferredDelete)

    def test_real_english_purchase_receipts_errors_and_saved_inventory(self):
        worker=Worker(seed={'settings_state.json':{'language':'en'},
            'battle_state.json':{'player':{'level':50,'gold':5000,'potions':0,'sigils':0}}})
        try:
            for command,phrase in [('/shop buy potion 2','You buy 2 healing potion(s)'),
                    ('/shop buy sigil 1','You buy 1 warding sigil(s)'),
                    ('/contracts buy contract50_01','Contract bought:'),
                    ('/contracts buy contract50_01','already been bought'),
                    ('/shop buy potion 99','not have enough gold'),
                    ('/shop buy potion 0','greater than 0'),
                    ('/shop buy unknown 1','not sold here'),
                    ('/shop buy potion invalid','valid amount')]:
                events=worker.command(command)
                receipt=next(e['text'] for e in events if e['event']=='shop_result')
                self.assertIn(phrase,receipt)
            data=shop_data(events)
            self.assertEqual(data['gold'],5000-2*item_price('potion',50)-item_price('sigil',50)-500)
            saved=json.loads((Path(worker.temp.name)/'state/battle_state.json').read_text())
            self.assertEqual((saved['player']['potions'],saved['player']['sigils']),(2,1))
            q=next(q for q in saved['quests']['active'] if q['id']=='contract50_01')
            self.assertEqual(q['name'],PAID_CONTRACTS[0]['name'])
            self.assertNotIn('translations',q)
            self.assertEqual(q['progress'],0)
        finally:worker.close()


class ShopLiveLanguageTests(unittest.TestCase):
    setUp=language_helpers.LanguageTests.setUp
    close_windows=language_helpers.LanguageTests.close_windows
    window=language_helpers.LanguageTests.window
    ready=language_helpers.LanguageTests.ready

    def test_live_shop_and_contract_board_english_previews(self):
        session_shared.write_application_language('en')
        session_shared.set_profile_name(1,'Shop language test')
        path=session_shared.profile_slot_root(1)/'state/battle_state.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({'player':{'level':50,'gold':5000}}))
        w=self.window();self.ready(w);w.phase='playing'
        w.execute('/shop');w.resize(1440,1080);APP.processEvents()
        self.assertEqual(w.shop.language,'en')
        self.assertEqual(w.shop.items['sigil']['name'].text(),'Warding Sigil')
        self.assertEqual(w.shop.receipt.text(),'Choose your supplies.')
        out=Path(os.environ['MAAT_LANGUAGE_PREVIEWS']) if os.environ.get('MAAT_LANGUAGE_PREVIEWS') else None
        if out:
            out.mkdir(parents=True,exist_ok=True);self.assertTrue(w.grab().save(str(out/'shop-en.png')))
        w.execute('/contracts');APP.processEvents()
        self.assertEqual(w.shop.contracts.heading.text(),'📜  CONTRACT BOARD · LEVEL 50+')
        self.assertIn('Win 5 real battles',w.shop.contracts.details.toPlainText())
        if out:self.assertTrue(w.grab().save(str(out/'contracts-en.png')))
