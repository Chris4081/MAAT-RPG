"""Profile-local AI plugin controls, independent of model loading and music."""
from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtWidgets import (QCheckBox, QComboBox, QVBoxLayout, QWidget, QScrollArea,
                               QLayout, QSizePolicy, QLabel, QRadioButton, QButtonGroup,
                               QSpinBox, QHBoxLayout, QGridLayout, QLineEdit)
from gui.desktop import card
from shared.core.ai_plugin_settings import DEFAULTS, STYLE_DEFAULTS
from shared.core.maat_style import (normalize_emoji_mode, normalize_old_smiley_mode,
    normalize_tone_mode, normalize_opening_mode, normalize_density_mode, normalize_heading_mode,
    normalize_list_mode, STYLE_CHOICES, STYLE_CHECKS, diagnostic_text)
from shared.core.reply_style import PRESETS, MODE_LABELS, OPTIONS, MIN_TARGET, MAX_TARGET, normalize_settings


SMILEY_CHOICES = STYLE_CHOICES['style_emoji_mode']
STYLE_MODES = (
    ('style_tone_mode', ('Grundton', 'Base tone'), normalize_tone_mode),
    ('style_opening_mode', ('Einstieg / Anrede', 'Opening / address'), normalize_opening_mode),
    ('style_density_mode', ('Absatzdichte', 'Paragraph density'), normalize_density_mode),
    ('style_heading_mode', ('Überschriften', 'Headings'), normalize_heading_mode),
    ('style_list_mode', ('Listen', 'Lists'), normalize_list_mode),
    ('style_emoji_mode', ('Emojis · 🙂 ✨', 'Emojis · 🙂 ✨'), normalize_emoji_mode),
    ('style_old_smiley_mode', ('Klassische Smileys · :) :D ^^ xD ;)', 'Classic smileys · :) :D ^^ xD ;)'), normalize_old_smiley_mode),
)


ENTRIES = (
    ('reply_style_enabled', ('Antwortstil', 'Reply style'),
     ('Bestimme, wie kurz oder ausführlich deine KI antwortet. Funktioniert auch ohne MAAT Style.',
      'Choose how briefly or fully your AI replies. Works independently of MAAT Style.')),
    ('response_formatting_enabled', ('Antworten formatieren', 'Format replies'),
     ('Formatiert fertige KI-Antworten mit Überschriften, Tabellen, Codeblöcken und einfachen Formeln. Fordert korrekte Groß- und Kleinschreibung an. Aus: bisherige Textdarstellung. Gilt ab der nächsten Antwort.',
      'Formats completed AI replies with headings, tables, code blocks and simple formulas. Requests correct capitalization. Off: the previous plain-text display. Applies from the next reply.')),
    ('reality_enabled', ('MAAT Reality · Datum und Uhrzeit', 'MAAT Reality · Date and time'),
     ('Gibt der KI bei jeder Antwort das aktuelle Datum, die Uhrzeit und die Zeitzone deines Computers. Zeitangaben bleiben Live-Kontext; sie sind keine gespeicherten Erinnerungen.',
      'Gives the AI your computer’s current date, time and time zone for each reply. Time information stays live context; it is not a saved memory.')),
    ('emotion_enabled', ('Emotionserkennung', 'Emotion detection'),
     ('Erkennt Hinweise auf Stimmung im Text und berücksichtigt sie in den MAAT-Feldern. Eine grobe Einschätzung anhand von Wörtern, keine Diagnose.',
      'Detects mood cues in text and uses them in the MAAT fields. A rough estimate based on words, not a diagnosis.')),
    ('hallu_mode', ('PLP Anti-Hallu', 'PLP Anti-Hallu'),
     ('Prüft Antworten vor der Anzeige auf unbelegte Aussagen und erfundene Erinnerungen. Die Ausgabe beginnt deshalb später. Heuristischer Schutz, keine Garantie für richtige Fakten.',
      'Checks answers for unsupported claims and invented memories before display, so output starts later. A heuristic guard, not a guarantee of factual accuracy.')),
    ('maat_style_enabled', ('MAAT Style', 'MAAT Style'),
     ('Bestimme Ton, Einstieg und Aufbau. Der Antwortstil darüber steuert weiterhin Länge und Anschlussfragen.',
      'Choose tone, opening and layout. Reply style above still controls length and follow-up questions.')),
    ('maat_identity_enabled', ('MAAT Identity', 'MAAT Identity'),
     ('Stärkt die MAAT-Rolle und ihre ehrlichen Grenzen. Im Modus „Ich bin die KI“ bleibt das Modell Maatis.',
      'Reinforces the MAAT role and its honest boundaries. In “I am the AI” mode, the model remains Maatis.')),
)


class WrappedLabel(QLabel):
    """Keep translated paragraphs readable when a scroll layout gets shorter."""
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_wrap()

    def adjust_wrap(self):
        height = self.heightForWidth(max(1, self.width()))
        if height > 0 and self.minimumHeight() != height:
            self.setMinimumHeight(height)


class PluginSettingsPanel(QWidget):
    def __init__(self, load, save, parent=None):
        super().__init__(parent)
        self.load_settings, self.save_settings = load, save
        self.language = 'de'
        self._texts = []
        self.boxes = {}
        self.style_combos = {}
        self.style_checks = {}
        layout = QVBoxLayout(self)
        def text(pair, role='muted'):
            widget = WrappedLabel(pair[0])
            widget.setObjectName(role)
            widget.setWordWrap(True)
            self._texts.append((widget, pair))
            return widget
        layout.addWidget(text(('Deine KI · Deine Plugins', 'Your AI · Your plugins'), 'title'))
        layout.addWidget(text(('Pro Profil gespeichert · Gilt ab der nächsten Nachricht.',
                               'Saved per profile · Applies from the next message.')))
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        content = QVBoxLayout(body)
        content.setSizeConstraint(QLayout.SetMinAndMaxSize)
        for key, title, description in ENTRIES:
            tile, row = card()
            tile.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            row.setSizeConstraint(QLayout.SetMinimumSize)
            box = QCheckBox(title[0])
            box.setMinimumHeight(38)
            box.setStyleSheet('QCheckBox { font-size:18px; font-weight:600; padding:5px; }')
            self.boxes[key] = box
            self._texts.append((box, title))
            box.toggled.connect(lambda checked, name=key: self.save_settings({name: checked}))
            row.addWidget(box)
            row.addWidget(text(description))
            default_text = (('Standard: an · Normal', 'Default: on · Normal') if key == 'reply_style_enabled' else
                            ('Standard: an', 'Default: on') if DEFAULTS[key] else ('Standard: aus', 'Default: off'))
            row.addWidget(text(default_text, 'eyebrow'))
            if key == 'reply_style_enabled':
                self.reply_options = self._build_reply_options(text)
                row.addWidget(self.reply_options)
                box.toggled.connect(self.reply_options.setEnabled)
                box.toggled.connect(self._update_style_preview)
            if key == 'maat_style_enabled':
                self.style_options = self._build_style_options(text)
                row.addWidget(self.style_options)
                box.toggled.connect(self.style_options.setEnabled)
                box.toggled.connect(self._update_style_preview)
            content.addWidget(tile)
        content.addWidget(text(('Bereits vorhanden: MAAT Thinking, Super Memory, Offline-Wikipedia und Sprachausgabe. Ihre Einstellungen findest du weiterhin in den bisherigen Menüs.',
                                'Already available: MAAT Thinking, Super Memory, offline Wikipedia and speech output. Their settings remain in the existing menus.')))
        content.addStretch()
        self.scroll.setWidget(body)
        layout.addWidget(self.scroll, 1)
        self.set_language('de')
        self.refresh()
        from gui.settings_scroll import protect_settings_scroll
        protect_settings_scroll(self)

    def _build_style_options(self, text):
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(10)
        grid = QGridLayout()
        for index, (key, caption, _) in enumerate(STYLE_MODES):
            field = QWidget()
            column = QVBoxLayout(field)
            column.setContentsMargins(0, 0, 0, 0)
            combo = QComboBox()
            combo.setMinimumContentsLength(12)
            combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            combo.setAccessibleName(caption[0])
            for value, labels in STYLE_CHOICES[key]:
                combo.addItem(labels[0], value)
            combo.currentIndexChanged.connect(lambda _, name=key, control=combo:
                self._save_style({name: control.currentData()}))
            self.style_combos[key] = combo
            label = text(caption)
            label.setBuddy(combo)
            column.addWidget(label)
            column.addWidget(combo)
            grid.addWidget(field, index // 2, index % 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        for key, caption in STYLE_CHECKS:
            box = QCheckBox()
            box.setMinimumHeight(32)
            self._texts.append((box, caption))
            self.style_checks[key] = box
            box.toggled.connect(lambda checked, name=key: self._save_style({name: checked}))
            layout.addWidget(box)
        layout.addWidget(text(('Automatischer Ton kann den Grundton passend zur Nachricht ersetzen. Absatzdichte ändert die Anordnung, nicht den Zielumfang. Begrüßungen dürfen kurz bleiben. Wenige Emojis und keine klassischen Smileys sind Standard.',
                               'Automatic tone may override the base tone to match the message. Paragraph density changes layout, not target length. Greetings may stay brief. Defaults: few emojis, no classic smileys.')))
        self.style_debug_panel = QWidget()
        debug = QVBoxLayout(self.style_debug_panel)
        debug.setContentsMargins(0, 4, 0, 0)
        debug.addWidget(text(('Stil-Test ohne Modellaufruf: Der Beispieltext wird nicht gespeichert. Im Spiel protokolliert die Diagnose nur Stilwerte, keine Chattexte.',
                             'Style test without a model call: the example text is not saved. During play, diagnostics log only style values, never chat text.')))
        self.style_example = QLineEdit()
        self.style_example.textChanged.connect(self._update_style_preview)
        debug.addWidget(self.style_example)
        self.style_preview = QLabel()
        self.style_preview.setWordWrap(True)
        self.style_preview.setTextInteractionFlags(Qt.TextSelectableByMouse)
        debug.addWidget(self.style_preview)
        layout.addWidget(self.style_debug_panel)
        return host

    def _save_style(self, changes):
        self.save_settings(changes)
        self._update_style_preview()

    def _update_style_preview(self, *_):
        if not hasattr(self, 'style_preview'):
            return
        settings = {key: combo.currentData() for key, combo in self.style_combos.items()}
        settings.update({key: box.isChecked() for key, box in self.style_checks.items()})
        settings['maat_style_enabled'] = self.boxes['maat_style_enabled'].isChecked()
        settings['reply_style_enabled'] = self.boxes['reply_style_enabled'].isChecked()
        self.style_debug_panel.setVisible(settings.get('style_debug', False))
        self.style_preview.setText(diagnostic_text(settings, self.style_example.text(), self.language))

    def _build_reply_options(self, text):
        options = QWidget()
        layout = QVBoxLayout(options)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(10)
        self.reply_modes = {}
        self.reply_group = QButtonGroup(options)
        for mode, labels in MODE_LABELS.items():
            radio = QRadioButton(labels[0])
            radio.setMinimumHeight(32)
            radio.setStyleSheet('''QRadioButton { font-size:18px; padding:3px; }
                QRadioButton:checked { color:#e2c878; font-weight:600; }
                QRadioButton::indicator { width:14px; height:14px; border-radius:8px;
                    border:1px solid #778cac; background:#0b1930; }
                QRadioButton::indicator:checked { background:#dac48e; border:1px solid #f5dda0; }
                QRadioButton::indicator:disabled { background:#172438; border-color:#405169; }''')
            self._texts.append((radio, labels))
            self.reply_group.addButton(radio)
            radio.toggled.connect(lambda checked, name=mode: self._select_reply_mode(name) if checked else None)
            self.reply_modes[mode] = radio
            layout.addWidget(radio)
        self.reply_target = QLabel()
        self.reply_target.setWordWrap(True)
        self.reply_target.setStyleSheet('font-size:18px; font-weight:600;')
        layout.addWidget(self.reply_target)
        limits = QHBoxLayout()
        self.reply_min = QSpinBox()
        self.reply_max = QSpinBox()
        for spin, labels in ((self.reply_min, ('Von', 'From')), (self.reply_max, ('Bis', 'To'))):
            spin.setRange(MIN_TARGET, MAX_TARGET)
            spin.setSingleStep(10)
            spin.setKeyboardTracking(False)
            label = text(labels)
            label.setBuddy(spin)
            limits.addWidget(label)
            limits.addWidget(spin, 1)
        layout.addLayout(limits)
        self.reply_min.valueChanged.connect(lambda _: self._save_reply_range('min'))
        self.reply_max.valueChanged.connect(lambda _: self._save_reply_range('max'))
        self.reply_force = QCheckBox()
        self.reply_force.setMinimumHeight(32)
        self._texts.append((self.reply_force, ('Inhaltliche Antworten vertiefen', 'Develop substantive answers')))
        self.reply_force.toggled.connect(self._save_reply_force)
        layout.addWidget(self.reply_force)
        layout.addWidget(text(('An: Bei inhaltlichen Fragen möglichst den Zielumfang erreichen – mit passenden Erklärungen und Beispielen. Begrüßungen und vollständige kurze Antworten dürfen kurz bleiben. Keine erzwungene Mindestlänge und kein zweiter Modellaufruf. Tokens sind keine Wörter; Ausgabe- und Kontextlimits bleiben bestehen. Eine Stilauswahl setzt den Bereich zurück.',
                               'On: For substantive questions, aim for the target length with relevant explanations and examples. Greetings and complete short answers may stay short. No forced minimum and no second model call. Tokens are not words; output and context limits remain unchanged. Selecting a style resets the range.')))
        self.reply_checks = {}
        for key, labels in OPTIONS:
            box = QCheckBox(labels[0])
            box.setMinimumHeight(32)
            box.toggled.connect(lambda checked, name=key: self.save_settings({name: checked}))
            self._texts.append((box, labels))
            self.reply_checks[key] = box
            layout.addWidget(box)
        return options

    def _select_reply_mode(self, mode):
        low, high = PRESETS[mode]
        self._show_reply_range(low, high)
        self.save_settings({'reply_style_mode': mode, 'reply_style_min_tokens': low,
                            'reply_style_max_tokens': high})

    def _save_reply_force(self, checked):
        self.save_settings({'reply_style_force_length': checked})
        self._label_reply_range()

    def _show_reply_range(self, low, high):
        with QSignalBlocker(self.reply_min), QSignalBlocker(self.reply_max):
            self.reply_min.setValue(low)
            self.reply_max.setValue(high)
        self._label_reply_range()

    def _save_reply_range(self, changed):
        low, high = self.reply_min.value(), self.reply_max.value()
        if low > high:
            if changed == 'min':
                high = low
            else:
                low = high
        self._show_reply_range(low, high)
        self.save_settings({'reply_style_min_tokens': low, 'reply_style_max_tokens': high})

    def _label_reply_range(self):
        en = self.language == 'en'
        caption = 'Target length' if en else 'Zielumfang'
        unit = 'tokens' if en else 'Tokens'
        self.reply_target.setText(f'{caption}: {self.reply_min.value()}–{self.reply_max.value()} {unit}')
        self.reply_min.setAccessibleName('Minimum target tokens' if en else 'Zielumfang mindestens Tokens')
        self.reply_max.setAccessibleName('Maximum target tokens' if en else 'Zielumfang höchstens Tokens')

    def refresh(self):
        settings = self.load_settings()
        for key, box in self.boxes.items():
            with QSignalBlocker(box):
                box.setChecked(bool(settings.get(key, DEFAULTS[key])))
        for key, _, normalize in STYLE_MODES:
            combo = self.style_combos[key]
            with QSignalBlocker(combo):
                combo.setCurrentIndex(combo.findData(normalize(settings.get(key, STYLE_DEFAULTS[key]))))
        for key, box in self.style_checks.items():
            with QSignalBlocker(box):
                box.setChecked(bool(settings.get(key, STYLE_DEFAULTS[key])))
        self.style_options.setEnabled(self.boxes['maat_style_enabled'].isChecked())
        self._update_style_preview()
        reply = normalize_settings(settings)
        for mode, radio in self.reply_modes.items():
            with QSignalBlocker(radio):
                radio.setChecked(mode == reply['reply_style_mode'])
        with QSignalBlocker(self.reply_force):
            self.reply_force.setChecked(reply['reply_style_force_length'])
        self._show_reply_range(reply['reply_style_min_tokens'], reply['reply_style_max_tokens'])
        for key, box in self.reply_checks.items():
            with QSignalBlocker(box):
                box.setChecked(reply[key])
        self.reply_options.setEnabled(self.boxes['reply_style_enabled'].isChecked())

    def set_language(self, language):
        self.language = 'en' if language == 'en' else 'de'
        self._label_reply_range()
        index = int(self.language == 'en')
        for widget, pair in self._texts:
            widget.setText(pair[index])
            if isinstance(widget, WrappedLabel):
                widget.adjust_wrap()
        for key, caption, _ in STYLE_MODES:
            combo = self.style_combos[key]
            combo.setAccessibleName(caption[index])
            with QSignalBlocker(combo):
                for i, (_, labels) in enumerate(STYLE_CHOICES[key]):
                    combo.setItemText(i, labels[index])
        placeholder = 'Example: Please explain this Python error.' if index else 'Beispiel: Erkläre mir bitte diesen Python-Fehler.'
        self.style_example.setPlaceholderText(placeholder)
        self.style_example.setAccessibleName('Style test text' if index else 'Stil-Testtext')
        self._update_style_preview()
