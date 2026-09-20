import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

class CompanionStoryTests(unittest.TestCase):
    def test_campaign_through_finale(self):
        with tempfile.TemporaryDirectory(prefix='maat-ki-story-') as folder:
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('companion_story_probe.py')),folder],capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout[-2000:]+result.stderr[-4000:])
