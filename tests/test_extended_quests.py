import subprocess,sys,tempfile,unittest
from pathlib import Path

class ExtendedQuestsTests(unittest.TestCase):
    def test_all_new_quests_and_existing_saves(self):
        with tempfile.TemporaryDirectory(prefix='maat-level50-') as folder:
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('extended_quests_probe.py')),folder],capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout[-2000:]+result.stderr[-4000:])
