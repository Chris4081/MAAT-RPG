# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MenuScreen(QWidget):
    enter_chat_requested = Signal()
    back_requested = Signal()
    setting_changed = Signal(str, bool)
    language_changed = Signal(str)
    profile_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(18)

        title = QLabel("MAAT-RPG Menu")
        title.setObjectName("titleLabel")
        subtitle = QLabel("Desktop shell for profiles, language, and live status.")
        subtitle.setObjectName("subtitleLabel")

        shell = QHBoxLayout()
        left_card = QFrame()
        left_layout = QVBoxLayout(left_card)
        left_layout.setSpacing(14)

        self.profile_combo = QComboBox()
        self._set_profile_items(["Standard Profile", "Profile 2", "Profile 3", "Profile 4"])
        self.profile_combo.currentIndexChanged.connect(self.profile_changed.emit)

        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Deutsch", "de")
        self.language_combo.currentIndexChanged.connect(lambda: self.language_changed.emit(self.language_combo.currentData()))

        self.music_box = QCheckBox("Music")
        self.voice_box = QCheckBox("Voice / TTS")
        self.thinking_box = QCheckBox("Thinking Mode")
        self.rpg_context_box = QCheckBox("Story & Battle Context")
        self.hallu_box = QCheckBox("Hallu Mode")

        self.music_box.toggled.connect(lambda state: self.setting_changed.emit("music", state))
        self.voice_box.toggled.connect(lambda state: self.setting_changed.emit("voice", state))
        self.thinking_box.toggled.connect(lambda state: self.setting_changed.emit("thinking", state))
        self.rpg_context_box.toggled.connect(lambda state: self.setting_changed.emit("rpg_context", state))
        self.hallu_box.toggled.connect(lambda state: self.setting_changed.emit("hallu", state))

        left_layout.addWidget(QLabel("Profile"))
        left_layout.addWidget(self.profile_combo)
        left_layout.addWidget(QLabel("Language"))
        left_layout.addWidget(self.language_combo)
        left_layout.addWidget(self.music_box)
        left_layout.addWidget(self.voice_box)
        left_layout.addWidget(self.thinking_box)
        left_layout.addWidget(self.rpg_context_box)
        left_layout.addWidget(self.hallu_box)
        left_layout.addStretch(1)

        right_card = QFrame()
        right_layout = QGridLayout(right_card)
        right_layout.setHorizontalSpacing(18)
        right_layout.setVerticalSpacing(10)

        self.fields = {}
        rows = [
            ("Path Profile", "path_profile"),
            ("Rank", "rank"),
            ("Motive", "motive"),
            ("Level", "level"),
            ("XP", "xp"),
            ("Gold", "gold"),
            ("Potions", "potions"),
            ("Boss Victories", "boss_victories"),
        ]
        for row_index, (label, key) in enumerate(rows):
            right_layout.addWidget(QLabel(label), row_index, 0)
            value_label = QLabel("-")
            right_layout.addWidget(value_label, row_index, 1)
            self.fields[key] = value_label

        self.status_label = QLabel("-")
        self.model_label = QLabel("-")

        buttons = QHBoxLayout()
        back_button = QPushButton("Back")
        enter_button = QPushButton("Open Chat")
        back_button.clicked.connect(self.back_requested.emit)
        enter_button.clicked.connect(self.enter_chat_requested.emit)
        buttons.addWidget(back_button)
        buttons.addWidget(enter_button)

        shell.addWidget(left_card, 1)
        shell.addWidget(right_card, 2)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(shell)
        layout.addWidget(self.status_label)
        layout.addWidget(self.model_label)
        layout.addLayout(buttons)

    def _set_profile_items(self, labels: list[str]) -> None:
        current_index = self.profile_combo.currentIndex()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(labels)
        if 0 <= current_index < self.profile_combo.count():
            self.profile_combo.setCurrentIndex(current_index)
        self.profile_combo.blockSignals(False)

    def apply_snapshot(self, snapshot) -> None:
        player = snapshot.player
        self.thinking_box.setText("Thinking-Modus" if snapshot.language == "de" else "Thinking Mode")
        self.rpg_context_box.setText(
            "Story- und Kampfkontext (neue Modelle)"
            if snapshot.language == "de"
            else "Story & Battle Context (new models)"
        )
        if snapshot.profile_labels:
            self._set_profile_items(snapshot.profile_labels)
        self.fields["path_profile"].setText(player.path_profile)
        self.fields["rank"].setText(player.rank)
        self.fields["motive"].setText(player.motive)
        self.fields["level"].setText(str(player.level))
        self.fields["xp"].setText(f"{player.xp} / {player.next_xp}")
        self.fields["gold"].setText(str(player.gold))
        self.fields["potions"].setText(str(player.potions))
        self.fields["boss_victories"].setText(str(player.boss_victories))
        self.status_label.setText(snapshot.status_text)
        self.model_label.setText(snapshot.model_status)
        self.music_box.setChecked(snapshot.music_enabled)
        self.voice_box.setChecked(snapshot.voice_enabled)
        self.thinking_box.setChecked(snapshot.thinking_enabled)
        self.rpg_context_box.setChecked(snapshot.rpg_context_enabled)
        self.hallu_box.setChecked(snapshot.hallu_mode)

        idx = self.profile_combo.findText(snapshot.profile_name)
        if idx >= 0 and idx != self.profile_combo.currentIndex():
            self.profile_combo.setCurrentIndex(idx)

        lang_idx = 0 if snapshot.language == "en" else 1
        if lang_idx != self.language_combo.currentIndex():
            self.language_combo.setCurrentIndex(lang_idx)
