import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

class ProgressionParityTests(unittest.TestCase):
    def test_original_progression_in_companion_mode(self):
        for mode in ('classic','companion'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix='maat-progression-') as folder:
                result=subprocess.run([sys.executable,str(Path(__file__).with_name('progression_probe.py')),folder,mode],capture_output=True,text=True,timeout=60)
                self.assertEqual(result.returncode,0,result.stdout[-2000:]+result.stderr[-4000:])
