import subprocess,sys,tempfile,unittest
from pathlib import Path
class Daily50Tests(unittest.TestCase):
    def test_repeatable_daily_progression(self):
        with tempfile.TemporaryDirectory(prefix='maat-daily50-') as folder:
            r=subprocess.run([sys.executable,str(Path(__file__).with_name('daily50_probe.py')),folder],capture_output=True,text=True,timeout=60)
            self.assertEqual(r.returncode,0,r.stdout[-1000:]+r.stderr[-3000:])
