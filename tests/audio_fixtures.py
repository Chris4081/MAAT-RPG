"""Optional soundtrack fixtures made only from the project's original cue.

Never depend on the separately distributed Suno music or write into game assets.
"""
from pathlib import Path
import shutil
import tempfile


def music_fixture(testcase):
    folder = tempfile.TemporaryDirectory(prefix='maat-test-music-')
    testcase.addCleanup(folder.cleanup)
    root = Path(folder.name)
    cue = Path(__file__).resolve().parents[1] / 'maatos/apps/maat_rpg/plugins/battle/music/victory.mp3'
    for relative in ('game_menu/menu_theme.mp3', 'game_menu/menu_theme_en.mp3',
                     'rpg_intro/intro.mp3', 'rpg_intro/Intro_EN.mp3',
                     'battle/music/battle_normal.mp3'):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cue, target)
    return root
