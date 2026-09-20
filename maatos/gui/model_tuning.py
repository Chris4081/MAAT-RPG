"""Expandable manual model controls. No GPU probing or model loading in the UI."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QComboBox, QSpinBox, QCheckBox
from shared.core.model_settings import INTEGER_LIMITS, normalize_tuning
from shared.core.gguf_adapters import selected_adapter
from gui.ui_i18n import translate_widgets, tr


class ModelTuningPanel(QWidget):
    changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('modelTuningPanel')
        self.setStyleSheet('QWidget#modelTuningPanel QSpinBox { background:#0b1c36; color:#eee6d5; border:1px solid #34516e; border-radius:6px; padding:7px; } QWidget#modelTuningPanel QSpinBox QLineEdit { border:none; padding:0; background:transparent; }')
        self._restoring = False
        self.intel_adapter = selected_adapter() == 'llama_intel'
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        caption = QLabel('Leistung & Laden')
        caption.setObjectName('heading')
        layout.addWidget(caption)
        self.mode = QComboBox()
        self.mode.addItem('Auto · Standard', 'auto')
        self.mode.addItem('Manuell', 'manual')
        layout.addWidget(self.mode)
        self.auto_hint = QLabel('Automatisch passend zum System · ca. 80 % der CPU-Threads für Antworten.')
        if self.intel_adapter:
            self.auto_hint.setText('GGUF (Intel) · Physische CPU-Kerne für Antworten, parallele Verarbeitung für den Kontext · Repacking aus.')
        self.auto_hint.setWordWrap(True)
        self.auto_hint.setObjectName('muted')
        layout.addWidget(self.auto_hint)
        self.manual_panel = QWidget()
        grid = QGridLayout(self.manual_panel)
        grid.setContentsMargins(0, 6, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)
        self.fields = {}
        definitions = [
            ('threads', 'CPU-Threads · Antworten', 'Anzahl der CPU-Threads beim Erzeugen neuer Tokens.'),
            ('threads_batch', 'CPU-Threads · Prompt einlesen', 'Anzahl der CPU-Threads beim Verarbeiten von Eingabe und Kontext.'),
            ('gpu_layers', 'GPU-Layer', '−1: alle möglichen Layer · 0: nur CPU · positive Zahl: begrenzte GPU-Auslagerung.'),
            ('n_batch', 'Batchgröße', 'Maximale Anzahl von Prompt-Tokens pro Verarbeitungsschritt.'),
            ('n_ubatch', 'Mikro-Batchgröße', 'Gleichzeitig berechnete Tokens. Kleinere Werte sparen Arbeitsspeicher.'),
        ]
        for index, (key, title, tip) in enumerate(definitions):
            row, column = (index // 2) * 2, index % 2
            field = QSpinBox()
            field.setRange(*INTEGER_LIMITS[key])
            field.setToolTip(tip)
            field.setMinimumHeight(36)
            title_label = QLabel(title)
            title_label.setWordWrap(True)
            grid.addWidget(title_label, row, column)
            grid.addWidget(field, row + 1, column)
            self.fields[key] = field
            field.valueChanged.connect(self._changed)
        self.flash = QComboBox()
        for title, value in [('Auto · Modellvorgabe', 'auto'), ('Ein', 'on'), ('Aus', 'off')]:
            self.flash.addItem(title, value)
        self.flash.setToolTip('Optimierte Aufmerksamkeitsberechnung. Auto berücksichtigt das Modell und die Hardware.')
        self.flash.setMinimumHeight(36)
        grid.addWidget(QLabel('Flash Attention'), 4, 1)
        grid.addWidget(self.flash, 5, 1)
        self.mmap = QCheckBox('Speicherschonend laden · mmap')
        self.mmap.setToolTip('Modellgewichte direkt aus der Datei einblenden. Meist die passende Wahl.')
        self.mlock = QCheckBox('Modell im RAM halten · mlock')
        self.mlock.setToolTip('Verhindert das Auslagern von Modellgewichten, sofern das System es erlaubt. Benötigt genügend freien RAM.')
        grid.addWidget(self.mmap, 6, 0, 1, 2)
        grid.addWidget(self.mlock, 7, 0, 1, 2)
        self.repack = QCheckBox('Intel: Modellgewichte beim Laden umordnen · Repacking')
        self.repack.setToolTip('Kann Antworten beschleunigen, braucht beim Laden aber zusätzliche Zeit und Speicher. Standard: aus.')
        self.repack.setVisible(self.intel_adapter)
        grid.addWidget(self.repack, 8, 0, 1, 2)
        gpu_hint = QLabel('GPU-Layer: −1 = alle möglichen · 0 = nur CPU')
        gpu_hint.setWordWrap(True)
        gpu_hint.setObjectName('muted')
        if self.intel_adapter:
            gpu_hint.setText('GGUF (Intel) verwendet die CPU. GPU-Layer werden hier auf 0 gesetzt.')
            self.fields['gpu_layers'].setEnabled(False)
        grid.addWidget(gpu_hint, 9, 0, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addWidget(self.manual_panel)
        hint = QLabel('Pro Profil gespeichert · Wird beim nächsten „Modell laden“ übernommen.')
        hint.setWordWrap(True)
        hint.setObjectName('muted')
        layout.addWidget(hint)
        for signal in (self.mode.currentIndexChanged, self.flash.currentIndexChanged, self.mmap.toggled, self.mlock.toggled, self.repack.toggled):
            signal.connect(self._changed)
        self.restore(None)

    def settings(self):
        manual = {key: field.value() for key, field in self.fields.items()}
        manual.update(flash_attn=self.flash.currentData(), use_mmap=self.mmap.isChecked(), use_mlock=self.mlock.isChecked())
        manual['repack_weights'] = self.repack.isChecked()
        return dict(mode=self.mode.currentData(), manual=manual)

    def restore(self, value):
        selected = normalize_tuning(value)
        self._restoring = True
        try:
            self.mode.setCurrentIndex(self.mode.findData(selected['mode']))
            self.fields['n_ubatch'].setMaximum(selected['manual']['n_batch'])
            for key, field in self.fields.items():
                field.setValue(selected['manual'][key])
            self.flash.setCurrentIndex(self.flash.findData(selected['manual']['flash_attn']))
            self.mmap.setChecked(selected['manual']['use_mmap'])
            self.mlock.setChecked(selected['manual']['use_mlock'])
            self.repack.setChecked(selected['manual']['repack_weights'])
        finally:
            self._restoring = False
        self._update_visibility()

    def _update_visibility(self):
        manual = self.mode.currentData() == 'manual'
        self.manual_panel.setVisible(manual)
        self.auto_hint.setVisible(not manual)

    def _changed(self, *_):
        if self._restoring:
            return
        self._restoring = True
        try:
            self.fields['n_ubatch'].setMaximum(self.fields['n_batch'].value())
        finally:
            self._restoring = False
        self._update_visibility()
        self.changed.emit(self.settings())

    def set_language(self, language):
        translate_widgets(self, language)
        for field in self.fields.values():
            field.setToolTip(tr(field.toolTip(), language))
