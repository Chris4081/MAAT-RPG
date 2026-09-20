import subprocess, sys, tempfile, unittest
from pathlib import Path
from test_desktop import APP
from test_live_rpg import Worker
from gui.shop import Shop
from shared.core.shop_catalog import shop_snapshot
from apps.maat_rpg.plugins.quests.paid_contracts import PAID_CONTRACTS

class ContractTests(unittest.TestCase):
    def test_backend_rewards_and_persistence(self):
        with tempfile.TemporaryDirectory(prefix='maat-contracts-') as folder:
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('contracts_probe.py')),folder],capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout[-1500:]+result.stderr[-3000:])

    def test_worker_command_wiring(self):
        worker=Worker(seed={'battle_state.json':{'player':{'level':50,'gold':2000}}})
        try:
            events=worker.command('/contracts buy contract50_01')
            data=next(e['data'] for e in reversed(events) if e['event']=='shop')
            self.assertEqual(data['gold'],1500)
            self.assertEqual(data['contracts'][0]['status'],'active')
            self.assertTrue(any(e['event']=='shop_result' for e in events))
            events=worker.command('/contracts buy contract50_01')
            data=next(e['data'] for e in reversed(events) if e['event']=='shop')
            self.assertEqual(data['gold'],1500)
        finally:worker.close()

    def test_board_gates_preview_filter_and_duplicate_click(self):
        shop=Shop();commands=[];shop.purchase_requested.connect(commands.append)
        data=shop_snapshot(dict(level=49,gold=500))
        data['contracts']=[dict(q,status='locked') for q in PAID_CONTRACTS]
        shop.update_data(data);shop.set_ready(True)
        board=shop.contracts
        self.assertEqual(board.list.count(),25)
        self.assertFalse(board.buy.isEnabled())
        data['level']=50;shop.update_data(data)
        self.assertTrue(board.buy.isEnabled())
        self.assertIn('Gewinne 5',board.details.toPlainText())
        self.assertIn('800 Basis-EP',board.details.toPlainText())
        board.buy.click();board.buy.click()
        self.assertEqual(commands,['/contracts buy contract50_01'])
        board.filter.setCurrentIndex(3)
        self.assertEqual(board.list.count(),5)
        shop.set_ready(True)
        self.assertFalse(board.buy.isEnabled())
        data['gold']=2000;shop.update_data(data)
        self.assertTrue(board.buy.isEnabled())
        data['contracts'][20]['status']='completed';shop.update_data(data)
        self.assertFalse(board.buy.isEnabled())
        shop.close()
