"""Original story content displayed as a click-paced illustrated scene."""
import re
from pathlib import Path
from PySide6.QtGui import QColor, QPixmap
from gui.intro_screen import IntroScreen


class StoryScreen(IntroScreen):
    def start_scene(self, event):
        self.cancel()
        self.language = event.get('language', getattr(self, 'language', 'de'))
        self.request_id = event['id']
        module = str(event.get('module',''))
        self.scene_module=module
        image = 'intro-awakening.png' if module in ('story1','') else 'story-reflection.png' if module in ('story2','reflection','credits','boss_scene_4') else 'story-temple.png'
        requested_image = event.get('image')
        if requested_image in {'ai-keeper.png', 'maatis-human.png', 'intro-awakening.png', 'story-reflection.png', 'story-temple.png'}:
            image = requested_image
        from gui.hero_portrait import portrait_path
        self.artwork.pixmap = QPixmap(str(portrait_path(getattr(self, 'hero_class', 'normal'))
                                      if image == 'maatis-human.png' else Path(__file__).parent/'assets'/image))
        self.artwork.background = QColor('#080f23' if image == 'maatis-human.png' else '#000000')
        fallback_title = 'Story' if self.language == 'en' else 'Geschichte'
        self.artwork.setAccessibleName(event.get('name',fallback_title))
        self.artwork.update()
        self.layout().itemAt(0).widget().setText(event.get('name',fallback_title.upper()))
        self.skip_button.setText('Text überspringen' if module.startswith('dungeon_') else 'Szene überspringen')
        self.segments = [part for line in event.get('lines', []) if str(line).strip() not in ('','⸻','---','—','–','─')
                         for part in re.split(r'(?<=[.!?])\s+', str(line).strip()) if part]
        if not self.segments:
            self.segments = ['The story continues.' if self.language == 'en' else 'Die Geschichte geht weiter.']
        self.segment = 0
        self.running = True
        self.progress.setRange(0,len(self.segments))
        music = event.get('music')
        if music and Path(music).is_file():
            self.audio_requested.emit({'action':'play','owner':'story-screen','path':music,'loop':True})
        self.show_sentence()
        self.text.setFocus()

    def sentence_ready(self):
        super().sentence_ready()
        if self.segment == len(self.segments)-1:
            self.next_button.setText('Zurück ins Spiel  →')
            self.hint.setText('Klick / Enter · Zurück ins Spiel   |   Esc · Szene überspringen')
            if getattr(self,'scene_module','') in ('dungeon_room','dungeon_end'):
                destination='Zum Kampf' if self.scene_module=='dungeon_room' else 'Zur Dungeon-Auswahl'
                self.next_button.setText(destination+'  →')
                self.hint.setText('Klick / Enter · '+destination+'   |   Esc · Text überspringen')

        self.translate_controls()

    def cancel(self):
        self.timer.stop()
        if self.running:
            self.audio_requested.emit({'action':'stop','owner':'story-screen'})
        self.running = False
