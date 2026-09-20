"""Embedded, read-only save overview; opening it never bootstraps a profile."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QLayout
from gui.desktop import label, button, card
from gui.hero_portrait import HeroPortrait, class_name
from gui.ui_i18n import tr
from apps.maat_rpg import session_shared


class ProfileSelection(QWidget):
    selected = Signal(int)
    delete_requested = Signal(int)
    rename_requested = Signal(int)
    create_requested = Signal()
    cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.language = 'de'
        self.active_slot = 1
        self.cards = {}
        self.summaries = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)
        top = QHBoxLayout()
        self.eyebrow = label('', 'eyebrow')
        self.eyebrow.setWordWrap(False)
        top.addWidget(self.eyebrow)
        top.addStretch()
        layout.addLayout(top)
        self.heading = label('', 'title')
        self.hint = label('', 'muted')
        self.hint.setWordWrap(True)
        layout.addWidget(self.heading)
        layout.addWidget(self.hint)
        self.create_button = button('', self.create_requested.emit, True)
        layout.addWidget(self.create_button, 0, Qt.AlignLeft)
        self.empty = label('', 'muted')
        layout.addWidget(self.empty)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet('QScrollArea { background: transparent; border: none; }')
        self.body = QWidget()
        self.grid = QGridLayout(self.body)
        self.grid.setContentsMargins(0, 4, 8, 8)
        self.grid.setSpacing(14)
        self.scroll.setWidget(self.body)
        layout.addWidget(self.scroll, 1)
        self.note = label('', 'muted')
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.back = button('', self.cancelled.emit)
        layout.addWidget(self.back, 0, Qt.AlignLeft)

    def ui(self, text, **values):
        return tr(text, self.language).format(**values)

    def start(self, active_slot, language, *, startup=False):
        self.active_slot = active_slot
        self.startup = startup
        self.language = language
        self.refresh()
        self.scroll.verticalScrollBar().setValue(0)
        focus = self.cards.get(active_slot, {}).get('select', self.create_button)
        focus.setFocus(Qt.OtherFocusReason)

    def set_language(self, value):
        if value in ('de', 'en') and value != self.language:
            self.language = value
            self.refresh()

    def refresh(self):
        self.eyebrow.setText(self.ui('DEINE REISEN DURCH TERRA'))
        self.heading.setText(self.ui('Wähle dein Profil'))
        slots = session_shared.existing_profile_slots()
        self.hint.setText(self.ui('{count}/10 Profile · Wähle deine Reise oder lege ein neues Profil an.', count=len(slots)))
        self.create_button.setText(self.ui('+ Neues Profil'))
        self.create_button.setEnabled(len(slots) < session_shared.PROFILE_SLOT_COUNT)
        self.create_button.setToolTip(self.ui('Alle zehn Profilplätze sind belegt.') if len(slots) == session_shared.PROFILE_SLOT_COUNT else '')
        self.empty.setText(self.ui('Noch kein Profil vorhanden. Lege dein erstes Abenteuer an.'))
        self.empty.setVisible(not slots)
        self.note.setText(self.ui('Jedes Profil hat seinen eigenen Spielstand, Erinnerungen und Modelleinstellungen.'))
        self.back.setText(self.ui('← Zum Startbildschirm' if getattr(self, 'startup', False) else '← Zurück zu den Einstellungen'))
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self.cards.clear()
        self.summaries.clear()
        for slot in slots:
            try:
                data = session_shared.profile_summary(slot, self.language)
            except (ValueError, TypeError, OverflowError):
                data = dict(slot=slot, used=True, name=session_shared.profile_slot_label(slot, self.language),
                            hero_class='normal', level=1, unavailable=True)
            self.summaries[slot] = data
            box, body = card()
            box.setObjectName('profileCard')
            box.setMinimumHeight(236)
            body.setSizeConstraint(QLayout.SetMinimumSize)
            active = slot == self.active_slot
            box.setStyleSheet('QWidget#profileCard { background: #0e223e; border: 1px solid '
                             + ('#c7a966' if active else '#304f70') + '; border-radius: 12px; }'
                             + ' QWidget#profileCard QLabel { background: transparent; }')
            body.setContentsMargins(16, 13, 16, 13)
            body.setSpacing(7)
            header = QHBoxLayout()
            badge = label(f'{slot:02d}  ·  ' + self.ui('Zuletzt gewählt' if active else 'Gespeicherte Reise' if data['used'] else 'Freier Platz'), 'eyebrow')
            badge.setWordWrap(False)
            badge.setMinimumHeight(32)
            header.addWidget(badge)
            header.addStretch()
            rename = button(self.ui('Umbenennen …'), lambda _=False, value=slot: self.rename_requested.emit(value))
            rename.setStyleSheet('padding: 6px 10px; font-size: 12px;')
            header.addWidget(rename)
            if data['used'] and slot != 1:
                remove = button(self.ui('Löschen …'), lambda _=False, value=slot: self.delete_requested.emit(value))
                remove.setToolTip(self.ui('Profil endgültig löschen?'))
                remove.setStyleSheet('padding: 6px 10px; font-size: 12px;')
                header.addWidget(remove)
            body.addLayout(header)
            hero = QHBoxLayout()
            portrait = HeroPortrait(82)
            portrait.set_class(data['hero_class'])
            portrait.setAccessibleName('Maatis · ' + class_name(data['hero_class'], self.language))
            hero.addWidget(portrait)
            titles = QVBoxLayout()
            name = label(data['name'], 'heading')
            name.setTextFormat(Qt.PlainText)
            name.setWordWrap(True)
            titles.addWidget(name)
            klass = label('Level ' + str(data['level']) + ' · ' + class_name(data['hero_class'], self.language))
            klass.setWordWrap(True)
            titles.addWidget(klass)
            model_name = data.get('model_name') or self.ui('Noch kein Modell gewählt')
            model = label(self.ui('Modell: {name}', name=model_name), 'muted')
            model.setTextFormat(Qt.PlainText)
            model.setWordWrap(True)
            model.setToolTip(model_name)
            titles.addWidget(model)
            hero.addLayout(titles, 1)
            body.addLayout(hero)
            stats = label(self.ui('Kämpfe: {fights}  ·  Siege: {wins}  ·  Boss-Siege: {bosses}\nDungeons: {done}/{runs} abgeschlossen\nDungeon+ · Rekord: Welle {best}',
                fights=data.get('fights_total', 0), wins=data.get('fights_won', 0), bosses=data.get('boss_wins', 0),
                done=data.get('dungeon_completed', 0), runs=data.get('dungeon_attempts', 0),
                best=data.get('dungeon_plus_best', 0)), 'muted')
            stats.setWordWrap(True)
            if data.get('unavailable'):
                stats.setText(self.ui('Spielstand konnte nicht vollständig gelesen werden.'))
            footer = QHBoxLayout()
            footer.addWidget(stats, 1)
            play = button(self.ui('Diese Reise wählen →' if data['used'] else 'Neues Abenteuer →'),
                          lambda _=False, value=slot: self.selected.emit(value), 'primary')
            play.setAccessibleName(data['name'] + ' · ' + play.text())
            play.setEnabled(not data.get('unavailable'))
            footer.addWidget(play, 0, Qt.AlignBottom)
            body.addLayout(footer)
            self.cards[slot] = dict(widget=box, select=play, stats=stats, name=name, klass=klass,
                                    model=model, rename=rename)
        self.arrange_cards()

    def arrange_cards(self):
        self.grid.setColumnStretch(0, 1)
        for index, row in enumerate(self.cards.values()):
            self.grid.addWidget(row['widget'], index, 0, Qt.AlignTop)
        # Short lists sit at the top rather than stretching a single profile.
        for index in range(self.grid.rowCount() + 1):
            self.grid.setRowStretch(index, int(index == len(self.cards)))
