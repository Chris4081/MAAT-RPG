from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QMessageBox
from gui.desktop import label, button


class CompanionPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.data = {}
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        for filename, caption in [('maatis-human.png','MAATIS · fragt dich'),('ai-keeper.png','DU · die Begleiter-KI')]:
            if filename == 'maatis-human.png':
                from gui.hero_portrait import HeroPortrait
                portrait = self.hero_portrait = HeroPortrait(64)
            else:
                portrait = QLabel()
                portrait.setPixmap(QPixmap(str(Path(__file__).parent/'assets'/filename)).scaled(64,64,Qt.KeepAspectRatio,Qt.SmoothTransformation))
            portrait.setAccessibleName(caption)
            row.addWidget(portrait)
            row.addWidget(label(caption),1)
        layout.addLayout(row)
        self.status = label('KI-Begleiter · Fortschritt wird geladen')
        layout.addWidget(self.status)
        self.reflection = label('Spielwertung für Entscheidungen · keine Bewertung deiner Persönlichkeit oder der Wahrheit freier Texte.', 'muted')
        layout.addWidget(self.reflection)
        self.choice = QComboBox()
        layout.addWidget(self.choice)
        actions = QHBoxLayout()
        actions.addWidget(button('Erinnerungen & Fähigkeiten', self.memories))
        actions.addWidget(button('Hinweis', self.hint))
        self.training = button('Aufgabenbogen', lambda: None)
        self.story = button('Freies Gespräch', lambda: None)
        actions.addWidget(self.training)
        actions.addWidget(self.story)
        self.fight = button('Maatis führen  ⚔', lambda: None)
        actions.addWidget(self.fight)
        layout.addLayout(actions)

    def update_state(self, data):
        self.data = data
        self.status.setText(f'KI-Level {data["level"]} · {data["xp"]} KI-XP · Vertrauen {data["trust"]}% · Kapitel {min(data["chapter"]+1,6)}/6')
        self.choice.clear()
        scene = data.get('scene')
        if scene and data['xp'] >= 180:
            self.status.setText(self.status.text() + ' · Intuition: ' + scene['field'])
        if scene:
            self.choice.addItem('Entscheidung wählen …', -1)
            for i, option in enumerate(scene['options']): self.choice.addItem(option, i)
        self.choice.setVisible(bool(scene))
        if data.get('playstyle') == 'free':
            self.status.setText(f'Maatis im freien Gespräch · Vertrauen {data["trust"]}%')
            self.reflection.setText('Du bist die Begleiter-KI. Antworte Maatis frei; Aufgaben-XP gibt es im Aufgabenbogen.')
        last = data.get('last')
        if last:
            gate = 'bestanden' if last['verified'] is True else 'nicht bestanden' if last['verified'] is False else 'offene Entscheidung'
            self.reflection.setText('Spielwertung · ' + ' | '.join(f'{k} {v:.2f}' for k,v in last['scores'].items()) + f'\nStabilität {last["stability"]:.2f} · Faktenprüfung: {gate} · +{last["gain"]} KI-XP')

    def memories(self):
        skills = ', '.join(self.data.get('skills', [])) or 'Noch keine Meilensteine erreicht'
        entries = ['Fähigkeiten: ' + skills, 'Erinnerungsanker (40 XP): Maatis berücksichtigt bis zu vier statt einer Erinnerung.\nPrüfimpuls (100 XP): genaue Aufgabenhinweise.\nStrukturelle Intuition (180 XP): Vorschau des nächsten MAAT-Schwerpunkts.', 'Entwicklungswerte: ' + str(self.data.get('fields', {}))]
        entries += [m['title']+'\nDeine Entscheidung: '+m['decision']+'\nDu: '+m['answer']+'\nMaatis: '+m['reaction'] for m in self.data.get('memories', [])]
        dialog = QMessageBox(self)
        dialog.setWindowTitle('Gemeinsame Erinnerungen')
        dialog.setTextFormat(Qt.PlainText)
        dialog.setText('\n\n'.join(entries))
        dialog.exec()

    def hint(self):
        scene = self.data.get('scene')
        text = scene['hint'] if scene and self.data.get('xp',0) >= 100 else 'Prüfe die gegebenen Informationen und unterscheide Wissen von Vermutungen. Ab 100 KI-XP gibt Prüfimpuls genaue Hinweise.' if scene else 'Alle Aufgaben abgeschlossen. Freie Gespräche benötigen ein lokales Modell.'
        QMessageBox.information(self, 'Prüfhinweis', text)
