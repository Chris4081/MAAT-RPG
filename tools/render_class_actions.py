"""Render the real arena with synthetic HP; no worker, model or player save."""
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'maatos'))
from PIL import Image
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import QCoreApplication, QEvent


def main():
    with tempfile.TemporaryDirectory(prefix='maat-action-preview-') as temp, patch.object(Path,'home',return_value=Path(temp)):
        os.environ['MAAT_GUI_DATA_ROOT'] = temp
        from gui.battle_arena import BattleArena
        from gui.desktop import STYLE
        app = QApplication.instance() or QApplication([])
        app.setStyleSheet(STYLE)
        arena = BattleArena()
        arena.resize(1120,860)
        arena.show()
        out = ROOT/'gui-preview/class-animations-v1'
        out.mkdir(exist_ok=True)
        gallery = Image.new('RGB',(1120*2,860*3),'#080f23')
        try:
            classes = ['normal','robo','engelchen','magier','priester','puppy']
            attacks = ['Harmonie','Balance','Verbundenheit','Schöpfungskraft','Respekt','heal']
            for i,(cls,attack) in enumerate(zip(classes,attacks)):
                arena.stage.set_hero_class(cls)
                arena.update_state(dict(active=True,enemy_name='Schattenwächter',arena_difficulty='normal',
                    player_level=25,player_hp=180,player_max_hp=240,enemy_hp=96,enemy_max_hp=180,resonance=72))
                arena.hero_name.setText(f'MAATIS · {cls.upper()} · LVL 25')
                arena.append_text(f'{attack}: Maatis bündelt seine Kraft.\n')
                arena.stage.show_effect(dict(attacker='player',attack=attack,damage=14,heal=24))
                QTest.qWait(350)
                filename = out/f'arena-{cls}.png'
                arena.grab().save(str(filename))
                gallery.paste(Image.open(filename),(i%2*1120,i//2*860))
                arena.stage.clear_effects()
                arena.log.clear()
                arena.pending = ''
            gallery.save(out/'arena-all-classes.png')
            # Record actual timer-driven pose changes, motion and return to idle.
            arena.resize(960,720)
            frames=[]
            for cls,attack in [('robo','Harmonie'),('magier','Schöpfungskraft'),('puppy','heal')]:
                arena.stage.set_hero_class(cls)
                arena.hero_name.setText(f'MAATIS · {cls.upper()} · LVL 25')
                arena.stage.show_effect(dict(attacker='player',attack=attack,damage=14,heal=24))
                for frame in range(20):
                    QTest.qWait(100)
                    path = Path(temp)/'frame.png'
                    arena.grab().save(str(path))
                    frames.append(Image.open(path).convert('RGB').resize((768,576)))
            frames[0].save(out/'aktionen.gif',save_all=True,append_images=frames[1:],duration=100,loop=0)
        finally:
            arena.close(); arena.deleteLater()
            QCoreApplication.sendPostedEvents(arena,QEvent.DeferredDelete)
    print(out)


if __name__ == '__main__':main()
