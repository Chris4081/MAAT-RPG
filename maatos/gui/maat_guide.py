"""Bilingual, profile-gated MAAT guide with an optional unsaved exercise."""
import math
from html import escape
from PySide6.QtCore import Qt, QLocale, QSignalBlocker
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QTextBrowser, QScrollArea, QDoubleSpinBox, QPlainTextEdit, QPushButton, QComboBox)
from gui.maat_guide_content import (FIELDS_DE, FIELDS_EN, INTRO_DE, INTRO_EN,
    METHOD_DE, METHOD_EN, FORMULAS, FORMULA_NOTES, COPY)

# Keep the existing import names available for callers of the original guide.
FIELDS, INTRO, METHOD = FIELDS_DE, INTRO_DE, METHOD_DE


def stability(values):
    h, b, s, v, r = values
    if any(not math.isfinite(x) or not 0 <= x <= 1 for x in values):
        raise ValueError('Values must be between 0 and 1.')
    return min(r, (h * b * s * v) ** .25)


def maat_score(values):
    """Simple average on a 0–10 scale, from five normalized assessments."""
    stability(values)  # Same domain and exactly five fields.
    return sum(values) * 2


class MaatGuide(QWidget):
    def __init__(self):
        super().__init__()
        self.count = 0
        self.language = 'de'
        self.setObjectName('maatGuide')
        self.setStyleSheet('QWidget#maatGuide,QWidget#guideFormulas,QWidget#guideExercise{background:#07172e;} QTabWidget::pane{background:#07172e;border:1px solid #34516e;} QScrollArea{background:#07172e;border:0;} QLabel{font-size:18px;color:#dbe3ec;} QTextBrowser,QPlainTextEdit{background:#10243c;color:#e5e9eb;border:1px solid #34516e;border-radius:8px;padding:14px;font-size:18px;} QDoubleSpinBox,QComboBox{font-size:19px;padding:7px;color:#f4d68b;background:#122c46;} QPushButton{padding:12px;background:#244968;color:#ffe0a0;border-radius:8px;} QTabBar::tab{padding:12px;background:#10243c;color:#c9d9e8;} QTabBar::tab:selected{background:#274963;color:#ffe0a0;}')
        layout = QVBoxLayout(self)
        self.title = QLabel()
        self.title.setWordWrap(True)
        self.title.setStyleSheet('font-size:28px;color:#ebcc89')
        layout.addWidget(self.title)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        layout.addWidget(self.tabs, 1)
        self.introduction = self.browser()
        self.method = self.browser()
        self.tabs.addTab(self.introduction, '')
        self.tabs.addTab(self.method, '')

        self.formulas_page = QWidget()
        self.formulas_page.setObjectName('guideFormulas')
        self.formulas_page.setAttribute(Qt.WA_StyledBackground, True)
        formulas_layout = QVBoxLayout(self.formulas_page)
        self.formula_hint = QLabel()
        self.formula_hint.setWordWrap(True)
        formulas_layout.addWidget(self.formula_hint)
        self.formula_select = QComboBox()
        self.formula_select.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.formula_select.setMinimumContentsLength(18)
        self.formula_select.currentIndexChanged.connect(self.show_formula)
        formulas_layout.addWidget(self.formula_select)
        self.formula_browser = self.browser()
        formulas_layout.addWidget(self.formula_browser, 1)
        self.tabs.addTab(self.formulas_page, '')

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body.setObjectName('guideExercise')
        body.setAttribute(Qt.WA_StyledBackground, True)
        form = QVBoxLayout(body)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        form.addWidget(self.hint)
        self.scale_hint = QLabel()
        self.scale_hint.setWordWrap(True)
        form.addWidget(self.scale_hint)
        self.situation = QPlainTextEdit()
        self.situation.setMaximumHeight(110)
        form.addWidget(self.situation)
        self.values, self.notes, self.field_labels = [], [], []
        for key, name, question, hint in FIELDS_DE:
            label = QLabel()
            label.setWordWrap(True)
            self.field_labels.append(label)
            form.addWidget(label)
            row = QHBoxLayout()
            value = QDoubleSpinBox()
            value.setRange(-.01, 1)
            value.setSingleStep(.05)
            value.setDecimals(2)
            value.setValue(-.01)
            row.addWidget(value)
            note = QPlainTextEdit()
            note.setMaximumHeight(75)
            row.addWidget(note, 1)
            form.addLayout(row)
            self.values.append(value)
            self.notes.append(note)
            value.valueChanged.connect(self.calculate)
        self.result = QLabel()
        self.result.setWordWrap(True)
        self.result.setStyleSheet('color:#eacc89;font-size:22px;padding:14px;')
        form.addWidget(self.result)
        self.next_step = QPlainTextEdit()
        self.next_step.setMaximumHeight(100)
        form.addWidget(self.next_step)
        self.reset_button = QPushButton()
        self.reset_button.clicked.connect(self.reset_exercise)
        form.addWidget(self.reset_button)
        scroll.setWidget(body)
        self.tabs.addTab(scroll, '')
        self.retranslate()
        from gui.settings_scroll import protect_settings_scroll
        protect_settings_scroll(self)

    @staticmethod
    def browser():
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.document().setDefaultStyleSheet(
            'body{line-height:1.6} h2,h3{color:#eacb86} p{margin-bottom:20px}'
            '.equation{font-family:monospace;font-size:22px;color:#ffe0a0}'
            '.limits{color:#b8c9db;font-size:16px}')
        return browser

    def set_language(self, language):
        if language not in ('de', 'en') or language == self.language:
            return
        self.language = language
        self.retranslate()

    def retranslate(self):
        copy = COPY[self.language]
        locale = QLocale('en_US' if self.language == 'en' else 'de_DE')
        self.setLocale(locale)
        self.title.setText(copy['title'])
        for i, title in enumerate(copy['tabs']):
            self.tabs.setTabText(i, title)
        for browser, content in [(self.introduction, INTRO_EN if self.language == 'en' else INTRO_DE),
                                 (self.method, (METHOD_EN if self.language == 'en' else METHOD_DE) + copy['method_link'])]:
            position = browser.verticalScrollBar().value()
            browser.setHtml(content)
            browser.verticalScrollBar().setValue(position)
        selected = self.formula_select.currentData()
        with QSignalBlocker(self.formula_select):
            self.formula_select.clear()
            for formula in FORMULAS[self.language]:
                self.formula_select.addItem(formula['title'], formula['id'])
            self.formula_select.setCurrentIndex(max(0, self.formula_select.findData(selected)))
        self.formula_select.setAccessibleName(copy['formula_select'])
        self.formula_hint.setText(copy['formula_hint'])
        self.show_formula()
        self.hint.setText(copy['try'])
        self.scale_hint.setText(copy['scale_hint'])
        self.situation.setPlaceholderText(copy['situation'])
        fields = FIELDS_EN if self.language == 'en' else FIELDS_DE
        for label, value, note, (key, name, question, _) in zip(self.field_labels, self.values, self.notes, fields):
            label.setText(f'{key} · {name}\n{question}')
            with QSignalBlocker(value):
                value.setLocale(locale)
                value.setSpecialValueText(copy['open'])
                value.setAccessibleName(copy['rating'].format(key=key))
            note.setPlaceholderText(copy['note'])
        self.next_step.setPlaceholderText(copy['next_step'])
        self.reset_button.setText(copy['reset'])
        self.calculate()
        self.set_count(self.count)

    def show_formula(self, *_):
        selected = self.formula_select.currentData()
        formula = next((item for item in FORMULAS[self.language] if item['id'] == selected), FORMULAS[self.language][0])
        copy = COPY[self.language]
        self.formula_browser.setHtml(
            f'<h2>{escape(formula["title"])}</h2>'
            f'<p class="equation">{escape(formula["equation"])}</p>' + formula['body']
            + (f'<h3>{copy["scales"]}</h3><p>{escape(FORMULA_NOTES[self.language])}</p>' if selected != 'maat' else '')
            + f'<h3>{copy["interpretation"]}</h3><p class="limits">{escape(copy["limits"])}</p>')
        self.formula_browser.verticalScrollBar().setValue(0)

    def set_count(self, count):
        self.count = max(0, int(count))
        unlocked = self.count >= 20
        copy = COPY[self.language]
        self.status.setText(copy['unlocked'] if unlocked else copy['locked'].format(count=min(self.count, 20)))
        self.tabs.setVisible(unlocked)

    def calculate(self):
        values = [value.value() for value in self.values]
        copy = COPY[self.language]
        if any(value < 0 for value in values):
            self.result.setText(copy['pending'])
            return
        score = stability(values)
        self.result.setText(copy['result'].format(
            average=self.locale().toString(maat_score(values), 'f', 2),
            stability=self.locale().toString(score, 'f', 2),
            scaled=self.locale().toString(score * 10, 'f', 2)))

    def reset_exercise(self):
        self.situation.clear()
        self.next_step.clear()
        for value in self.values:
            with QSignalBlocker(value):
                value.setValue(-.01)
        for note in self.notes:
            note.clear()
        self.calculate()

    def reset_profile(self):
        self.reset_exercise()
        self.formula_select.setCurrentIndex(0)
        self.tabs.setCurrentIndex(0)
        self.set_count(0)
