import unittest
import json
from pathlib import Path
from PySide6.QtCore import QCoreApplication,QEvent
from test_desktop import APP
from test_live_rpg import Worker
from gui.shop import Shop
from shared.core.shop_catalog import item_price,shop_snapshot

class ShopTests(unittest.TestCase):
    def test_original_command_purchases_and_saves_at_shared_prices(self):
        worker=Worker(seed={'battle_state.json':{'player':{'level':15,'gold':1000,'potions':0,'sigils':0}}})
        def state(events):return next(e['data'] for e in reversed(events) if e['event']=='shop')
        try:
            data=state(worker.boot)
            self.assertEqual([i['price'] for i in data['items']],[145,237])
            data=state(worker.command('/shop buy potion 2'))
            self.assertEqual(data['gold'],710)
            self.assertEqual(data['items'][0]['owned'],2)
            data=state(worker.command('/shop buy sigil 2'))
            self.assertEqual(data['gold'],236)
            self.assertEqual(data['items'][1]['owned'],2)
            for command in ['/shop buy potion 2','/shop buy potion -1','/shop buy sigil 0','/shop buy missing 1','/shop buy potion invalid']:
                self.assertEqual(state(worker.command(command)),data)
            saved=json.loads((Path(worker.temp.name)/'state/battle_state.json').read_text())['player']
            self.assertEqual((saved['gold'],saved['potions'],saved['sigils']),(236,2,2))
            output=''.join(e.get('text','') for e in worker.command('/shop') if e['event']=='output')
            self.assertIn('145 Gold',output);self.assertIn('237 Gold',output)
        finally:worker.close()

    def test_cards_use_quantity_affordability_and_prevent_double_click(self):
        shop=Shop();commands=[];shop.purchase_requested.connect(commands.append)
        try:
            shop.update_data(shop_snapshot(dict(level=1,gold=150,potions=3)))
            shop.set_ready(True)
            potion=shop.items['potion'];potion['quantity'].setValue(2)
            self.assertIn('150 Gold',potion['buy'].text())
            potion['buy'].click();potion['buy'].click()
            self.assertEqual(commands,['/shop buy potion 2'])
            self.assertFalse(potion['buy'].isEnabled())
            shop.update_data(shop_snapshot(dict(level=1,gold=0,potions=5)))
            shop.set_ready(True)
            self.assertFalse(potion['buy'].isEnabled())
            self.assertIn('Im Beutel: 5',potion['info'].text())
            self.assertGreater(item_price('potion',50),item_price('potion',15))
            self.assertGreater(item_price('sigil',50),item_price('sigil',15))
        finally:
            shop.close();shop.deleteLater()
            QCoreApplication.sendPostedEvents(shop,QEvent.DeferredDelete)
