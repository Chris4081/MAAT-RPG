"""Native battle-profile editor, sharing the arena's animation renderer."""
import base64
from PySide6.QtCore import Qt, Signal, QBuffer, QIODevice, QSignalBlocker
from PySide6.QtGui import QImageReader
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPlainTextEdit, QComboBox, QDoubleSpinBox, QPushButton,
    QFileDialog, QMessageBox)
from shared.core.battle_editor import ARTS, EFFECTS, WEAKNESSES
from shared.core.monster_catalog import KIND_ART
from gui.battle_arena import CombatStage
from gui.ui_i18n import LocalizedUI, tr

EN = {
    '⚒   Kampfeditor': '⚒   Battle editor', 'Kampfeditor': 'Battle editor',
    'DEINE GEGNER / NACH DEM FINALE': 'YOUR OPPONENTS / AFTER THE FINALE',
    'Erfinde deinen nächsten Gegner.': 'Create your next opponent.',
    'Eigene Monster und Terminal-Vorlagen · Lokal gespeichert, für alle Profile verfügbar.': 'Custom monsters and terminal templates · Saved locally, available to all profiles.',
    'Vorlage': 'Template', '+ Neues Monster': '+ New monster',
    'Name': 'Name', 'Kampftyp': 'Battle type', 'Normaler Gegner': 'Regular enemy',
    'Grafik': 'Artwork', 'Angriffseffekt': 'Attack effect', 'Schwachstelle': 'Weakness',
    'Jede Runde zufällig': 'Random each round', 'KP-Faktor': 'HP multiplier',
    'Schadensfaktor': 'Damage multiplier', 'Auftritt': 'Entrance', 'Siegtext': 'Victory text',
    'Eigene Zeilen beim Erscheinen des Gegners …': 'Your own lines when the opponent appears …',
    'Eigene Zeilen nach dem Sieg …': 'Your own lines after victory …',
    'Eigenes Bild …': 'Import image …', 'Standardgrafik': 'Use built-in artwork',
    'Speichern': 'Save', 'Als Kopie speichern': 'Save as copy',
    'Testkampf starten →': 'Start test battle →', 'Angriff ansehen': 'Preview attack',
    '← Hauptmenü': '← Main menu',
    'Stärke relativ zu deinem Level. Testkämpfe geben keine Belohnungen; KP, Tränke und Reise bleiben erhalten.': 'Strength scales with your level. Test battles give no rewards; HP, potions and journey progress are preserved.',
    'Eigene Bilder nutzen Bewegung, Trefferfeedback und den gewählten Effekt; vorhandene Grafiken zusätzlich ihre Angriffsbilder.': 'Imported images use movement, hit feedback and the selected effect; built-in artwork also uses its attack portraits.',
    'Erst speichern, dann kämpfen.': 'Save first, then fight.',
    'Monster gespeichert.': 'Monster saved.', 'Vorlage geladen.': 'Template loaded.',
    'Testkampf beendet.': 'Test battle finished.',
    'Ungespeicherte Änderungen': 'Unsaved changes',
    'Änderungen verwerfen?': 'Discard changes?',
    'Monsterbild wählen': 'Choose a monster image', 'Bilder (*.png *.jpg *.jpeg *.webp)': 'Images (*.png *.jpg *.jpeg *.webp)',
    'Bild konnte nicht geladen werden (max. 4096 × 4096 Pixel).': 'Could not load the image (maximum 4096 × 4096 pixels).',
    'Bild ausgewählt · wird beim Speichern übernommen.': 'Image selected · applied when you save.',
    'Klinge': 'Blade', 'Klauen': 'Claws', 'Welle': 'Wave', 'Blitz': 'Lightning',
    'Sand': 'Sand', 'Schöpfung': 'Creation', 'Verbindung': 'Connection', 'Impuls': 'Impulse',
    'editor_locked': 'The battle editor unlocks after all five final victories.',
    'editor_numbers': 'HP multiplier: 0.1–10; damage multiplier: 0.1–5. Please enter valid numbers.',
    'editor_invalid': 'Please select a valid battle type, artwork, effect and weakness.',
    'editor_name': 'Enter a monster name with 1–64 characters and no line breaks.',
    'editor_text': 'Entrance and victory text may contain up to 1,000 characters each.',
    'editor_image': 'The image could not be saved. Please select it again.',
    'editor_copy': 'Save this terminal template as a new copy first.',
    'editor_changed': 'The file changed outside the editor. Load it again or save as a copy.',
    'editor_missing': 'This monster is no longer available. Open the editor again.',
    'editor_profile': 'The profile changed. Please open the editor again.',
    'editor_io': 'Could not save or read the monster file. Check the mod folder and available storage.',
}
DE_ERRORS = {
    'editor_locked': 'Der Kampfeditor wird nach allen fünf Finalsiegen freigeschaltet.',
    'editor_numbers': 'KP-Faktor: 0,1–10; Schadensfaktor: 0,1–5. Bitte gültige Zahlen eingeben.',
    'editor_invalid': 'Bitte gültigen Kampftyp, Grafik, Effekt und Schwachstelle wählen.',
    'editor_name': 'Bitte einen Monsternamen mit 1–64 Zeichen ohne Zeilenumbrüche eingeben.',
    'editor_text': 'Auftritt und Siegtext dürfen jeweils maximal 1.000 Zeichen enthalten.',
    'editor_image': 'Das Bild konnte nicht gespeichert werden. Bitte erneut auswählen.',
    'editor_copy': 'Diese Terminal-Vorlage zuerst als neue Kopie speichern.',
    'editor_changed': 'Die Datei wurde außerhalb des Editors geändert. Erneut laden oder als Kopie speichern.',
    'editor_missing': 'Dieses Monster ist nicht mehr vorhanden. Bitte den Editor erneut öffnen.',
    'editor_profile': 'Das Profil hat sich geändert. Bitte den Editor erneut öffnen.',
    'editor_io': 'Monsterdatei konnte nicht gespeichert oder gelesen werden. Mod-Ordner und freien Speicher prüfen.',
}


def text(source, language):
    if source.startswith('editor_'):
        return (EN if language == 'en' else DE_ERRORS).get(source, source)
    return EN.get(source, tr(source, language)) if language == 'en' else source


class BattleEditor(LocalizedUI, QWidget):
    save_requested = Signal(dict)
    play_requested = Signal(str)
    back_requested = Signal()

    def __init__(self):
        super().__init__()
        self.entries = []
        self.current = {}
        self.dirty = False
        self.ready = False
        self._loading = True
        self._labels = []
        self._status_key = ''
        self.image_key = ''
        self.portrait_png = ''
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        for caption, role in [('DEINE GEGNER / NACH DEM FINALE', 'eyebrow'), ('Erfinde deinen nächsten Gegner.', 'title'),
                              ('Eigene Monster und Terminal-Vorlagen · Lokal gespeichert, für alle Profile verfügbar.', 'muted')]:
            widget = QLabel(); widget.setObjectName(role); widget.setWordWrap(True)
            self._labels.append((widget, caption)); layout.addWidget(widget)
        self.selector = QComboBox()
        self.selector.currentIndexChanged.connect(self.select)
        layout.addWidget(self.selector)
        body = QHBoxLayout(); layout.addLayout(body)
        form_widget = QWidget(); form = QFormLayout(form_widget)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.fields = {}
        self.name = QLineEdit(); self.name.setMaxLength(64)
        self.kind = QComboBox()
        self.art = QComboBox()
        self.effect = QComboBox()
        self.weakness = QComboBox()
        self.hp = QDoubleSpinBox(); self.hp.setRange(.1, 10)
        self.damage = QDoubleSpinBox(); self.damage.setRange(.1, 5)
        for spin in (self.hp, self.damage):
            spin.setSingleStep(.1); spin.setDecimals(1); spin.setSuffix(' ×'); spin.setValue(1)
        self.intro = QPlainTextEdit(); self.intro.setMaximumHeight(85)
        self.victory = QPlainTextEdit(); self.victory.setMaximumHeight(85)
        for caption, widget in [('Name', self.name), ('Kampftyp', self.kind), ('Grafik', self.art),
                                ('Angriffseffekt', self.effect), ('Schwachstelle', self.weakness),
                                ('KP-Faktor', self.hp), ('Schadensfaktor', self.damage),
                                ('Auftritt', self.intro), ('Siegtext', self.victory)]:
            label = QLabel(); self._labels.append((label, caption)); form.addRow(label, widget)
        body.addWidget(form_widget, 1)
        right = QVBoxLayout(); body.addLayout(right, 1)
        self.preview = CombatStage(); self.preview.setMinimumSize(300, 260)
        right.addWidget(self.preview, 1)
        self.preview_button = self.make_button('Angriff ansehen', self.preview_attack)
        right.addWidget(self.preview_button)
        row = QHBoxLayout()
        self.import_button = self.make_button('Eigenes Bild …', self.import_image)
        self.reset_image = self.make_button('Standardgrafik', self.clear_image)
        row.addWidget(self.import_button); row.addWidget(self.reset_image); right.addLayout(row)
        for caption in ['Eigene Bilder nutzen Bewegung, Trefferfeedback und den gewählten Effekt; vorhandene Grafiken zusätzlich ihre Angriffsbilder.',
                        'Stärke relativ zu deinem Level. Testkämpfe geben keine Belohnungen; KP, Tränke und Reise bleiben erhalten.']:
            label = QLabel(); label.setWordWrap(True); label.setObjectName('muted')
            self._labels.append((label, caption)); layout.addWidget(label)
        self.status = QLabel(); self.status.setWordWrap(True); self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)
        row = QHBoxLayout(); layout.addLayout(row)
        self.back = self.make_button('← Hauptmenü', self.go_back)
        self.save_button = self.make_button('Speichern', self.submit)
        self.copy_button = self.make_button('Als Kopie speichern', lambda: self.submit(copy=True))
        self.play_button = self.make_button('Testkampf starten →', lambda: self.play_requested.emit(self.current['id']))
        self.play_button.setObjectName('primary')
        for widget in (self.back, self.copy_button, self.save_button, self.play_button): row.addWidget(widget)
        self.retranslate()
        self.name.textChanged.connect(self.changed)
        for widget in (self.kind, self.art, self.effect, self.weakness): widget.currentIndexChanged.connect(self.changed)
        for widget in (self.hp, self.damage): widget.valueChanged.connect(self.changed)
        for widget in (self.intro, self.victory): widget.textChanged.connect(self.changed)
        self.set_entries([])
        from gui.settings_scroll import protect_settings_scroll
        protect_settings_scroll(self)

    def ui(self, source, **values):
        value = text(source, self.language)
        return value.format(**values) if values else value

    def make_button(self, caption, slot):
        widget = QPushButton(); self._labels.append((widget, caption)); widget.clicked.connect(slot)
        return widget

    def retranslate(self):
        for widget, caption in self._labels: widget.setText(self.ui(caption))
        from shared.core.monster_catalog import enemy_display_name
        options = [(self.kind, [('Normaler Gegner', 'normal'), ('Boss', 'boss')]),
                   (self.art, [(enemy_display_name(k, self.language), v) for k, v in KIND_ART.items()]),
                   (self.effect, list(zip(('Klinge', 'Klauen', 'Welle', 'Blitz', 'Sand', 'Balance', 'Schöpfung', 'Verbindung', 'Respekt', 'Impuls'), EFFECTS))),
                   (self.weakness, [('Jede Runde zufällig', '')] + [(w, w) for w in WEAKNESSES[1:]])]
        for combo, items in options:
            value = combo.currentData()
            with QSignalBlocker(combo):
                combo.clear()
                for caption, key in items: combo.addItem(self.ui(caption), key)
                combo.setCurrentIndex(max(0, combo.findData(value)))
        with QSignalBlocker(self.selector):
            if self.selector.count(): self.selector.setItemText(0, self.ui('+ Neues Monster'))
        self.intro.setPlaceholderText(self.ui('Eigene Zeilen beim Erscheinen des Gegners …'))
        self.victory.setPlaceholderText(self.ui('Eigene Zeilen nach dem Sieg …'))
        from PySide6.QtCore import QLocale
        self.setLocale(QLocale('en_US' if self.language == 'en' else 'de_DE'))
        self.preview.set_language(self.language)
        self.status.setText(self.ui(self._status_key))
        self.refresh_controls()

    def set_entries(self, entries, selected=None):
        self.entries = entries
        with QSignalBlocker(self.selector):
            self.selector.clear(); self.selector.addItem(self.ui('+ Neues Monster'), None)
            for item in entries: self.selector.addItem(item['name'], item['id'])
            self.selector.setCurrentIndex(max(0, self.selector.findData(selected)))
        self.load_draft(next((item for item in entries if item['id'] == selected), {}))

    def discard_ok(self):
        return not self.dirty or QMessageBox.question(self, self.ui('Ungespeicherte Änderungen'), self.ui('Änderungen verwerfen?')) == QMessageBox.Yes

    def select(self, index):
        if not self.discard_ok():
            with QSignalBlocker(self.selector): self.selector.setCurrentIndex(max(0, self.selector.findData(self.current.get('id'))))
            return
        self.load_draft(next((item for item in self.entries if item['id'] == self.selector.itemData(index)), {}))

    def load_draft(self, data):
        self._loading = True
        self.current = dict(data)
        self.image_key = data.get('image', ''); self.portrait_png = ''
        self.name.setText(data.get('name', ''))
        for combo, key, default in [(self.art, 'art', ARTS[0]), (self.effect, 'effect', 'slash'),
                                    (self.weakness, 'weakness', ''), (self.kind, 'fight_type', 'normal')]:
            combo.setCurrentIndex(max(0, combo.findData(data.get(key, default))))
        self.hp.setValue(float(data.get('hp_mult', 1))); self.damage.setValue(float(data.get('damage_mult', 1)))
        self.intro.setPlainText(data.get('intro', '')); self.victory.setPlainText(data.get('victory', ''))
        self._loading = False; self.dirty = False
        self.result('Vorlage geladen.' if data else 'Erst speichern, dann kämpfen.')
        self.update_preview(); self.refresh_controls()

    def changed(self, *_):
        if self._loading: return
        self.dirty = True; self.update_preview(); self.refresh_controls()

    def update_preview(self):
        self.preview.set_enemy(self.name.text() or 'MAAT', self.visual())

    def visual(self):
        return dict(art=self.art.currentData(), effect=self.effect.currentData(), image=self.image_key,
                    portrait_png=self.portrait_png)

    def preview_attack(self):
        self.preview.show_effect(dict(attacker='enemy', attack='normal', damage=14, enemy_name=self.name.text()))

    def set_ready(self, ready):
        self.ready = ready; self.refresh_controls()

    def refresh_controls(self):
        if not hasattr(self, 'play_button'): return
        self.play_button.setEnabled(self.ready and bool(self.current.get('editable')) and not self.dirty)
        self.save_button.setEnabled(self.ready)
        self.save_button.setText(self.ui('Speichern' if not self.current or self.current.get('editable') else 'Als Kopie speichern'))
        for widget in (self.copy_button, self.selector, self.import_button, self.reset_image, self.back,
                       self.name, self.kind, self.art, self.effect, self.weakness, self.hp, self.damage, self.intro, self.victory):
            widget.setEnabled(self.ready)

    def submit(self, copy=False):
        draft = dict(name=self.name.text(), fight_type=self.kind.currentData(), art=self.art.currentData(),
                     effect=self.effect.currentData(), weakness=self.weakness.currentData(),
                     hp_mult=self.hp.value(), damage_mult=self.damage.value(), intro=self.intro.toPlainText(),
                     victory=self.victory.toPlainText(), image=self.image_key, portrait_png=self.portrait_png)
        update = self.current.get('editable') and not copy
        self.save_requested.emit(dict(data=draft, mod_id=self.current.get('id') if update else None,
                                      revision=self.current.get('revision') if update else None))

    def result(self, message):
        self._status_key = message; self.status.setText(self.ui(message))

    def go_back(self):
        if self.discard_ok():
            self.load_draft(self.current); self.back_requested.emit()

    def clear_image(self):
        self.image_key = ''; self.portrait_png = ''; self.changed()

    def import_image(self):
        filename, _ = QFileDialog.getOpenFileName(self, self.ui('Monsterbild wählen'), '', self.ui('Bilder (*.png *.jpg *.jpeg *.webp)'))
        if not filename: return
        reader = QImageReader(filename)
        size = reader.size()
        if not size.isValid() or max(size.width(), size.height()) > 4096:
            self.result('Bild konnte nicht geladen werden (max. 4096 × 4096 Pixel).'); return
        image = reader.read()
        if image.isNull():
            self.result('Bild konnte nicht geladen werden (max. 4096 × 4096 Pixel).'); return
        image = image.scaled(720, 720, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        buffer = QBuffer(); buffer.open(QIODevice.WriteOnly); image.save(buffer, 'PNG')
        self.portrait_png = base64.b64encode(bytes(buffer.data())).decode('ascii')
        self.image_key = ''; self.changed()
        self.result('Bild ausgewählt · wird beim Speichern übernommen.')
