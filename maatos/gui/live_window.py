"""Playable native frontend using the real RPG worker and Qt audio."""
from pathlib import Path
import sqlite3
from PySide6.QtCore import Qt, QTimer, QEvent, QLocale
from PySide6.QtGui import QColor, QTextCursor
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QLabel,
    QProgressBar, QComboBox, QCheckBox, QSlider, QSpinBox, QLineEdit, QTextBrowser,
    QScrollArea, QTabWidget, QMessageBox, QInputDialog, QFileDialog, QDialog, QDoubleSpinBox, QApplication)
from gui.desktop import MaatWindow, Sanctum, label, button, card
from gui.title_artwork import JourneyArtwork, saved_journey
from gui.text_stream import TextStream
from gui.live_session import LiveSession
from gui.audio_manager import AudioManager
from apps.maat_rpg import session_shared
from gui.runtime_diagnostics import event as diagnostic


class LiveWindow(MaatWindow):
    def __init__(self, session=None, audio=None):
        self._editor_unlocked = False
        self._editor_return = False
        self._guide_messages = 0
        self._history_unlock_pending = False
        self.phase = 'startup'
        self._started = False
        self._start_on_ready = False
        self.model_ready = False
        self.saved_model = None
        self.loaded_model_architecture = ""
        self.loaded_model_family = ""
        self._auto_model_pending = False
        self._startup_model_attempted = False
        self._startup_model_failed = False
        self._startup_profile_pending = True
        self._profile_launch_pending = False
        self._model_error_pending = False
        self._deferred = []
        self._audio_stops = {}
        self._startup_log = ''
        self._ki_reply_streaming = False
        self._chat_turn_active = False
        self._chat_focus_force = False
        self.text_stream = TextStream()
        self.game = session or LiveSession()
        self.game.on_transport(self.receive)
        self.audio = audio or AudioManager()
        self.audio.music_enabled = False
        self.controls = []
        self._battle_text = ''
        self._hero_class = 'normal'
        self._talent_data = {}
        self._class_choice_pending = False
        self._pending_class_event = None
        self._companion_after_class = False
        self._battle_pending = ''
        self._battle_presenting = False
        self._presenting_combat_text = False
        self._encounter_intro = False
        self._encounter_started = False
        self._arena_choices = []
        self._pending_principle = None
        self._minigame_offer = None
        self._discovered_games = []
        self._arcade_highscores = {}
        self._minigame_grant = None
        self._dungeon_active = False
        self._dungeon_return = False
        self._active_minigame = None
        self._return_to_chat = False
        self._battle_return_source = None
        self._focus_chat_after_battle = False
        self._chat_return_timer = QTimer()
        self._chat_return_timer.setSingleShot(True)
        self._chat_return_timer.setInterval(1800)
        self._chat_return_timer.timeout.connect(self.return_from_battle)
        self.command_items = []
        super().__init__(self.game)
        from gui.level_up_notice import LevelUpNotice
        self.level_up_notice = LevelUpNotice(self)
        content = self.centralWidget().layout().itemAt(1).layout()
        content.insertWidget(content.indexOf(self.stack), self.level_up_notice)
        from gui.navigation import ChatActivity
        self.chat_activity = ChatActivity(self.journal, self.nav_buttons[3],
            self.chat_page_is_open,
            lambda: self.phase in ('playing', 'story', 'class_selection'))
        self.stack.currentChanged.connect(self.chat_activity.acknowledge_if_open)
        self._chat_return_timer.setParent(self)
        from gui.transcript_scroll import TranscriptScroll
        self._chat_scroll = TranscriptScroll(self.journal, self.stack.widget(3), self.input)
        self._world_scroll = TranscriptScroll(self.world_output)
        self._chat_focus_timer = QTimer(self)
        self._chat_focus_timer.setSingleShot(True)
        self._chat_focus_timer.timeout.connect(self.focus_chat_input)
        self.setWindowTitle('MAAT RPG · Die Rückkehr der Prinzipien')
        self.footer.setText(self.ui('Spiel wird geladen …'))
        self.audio.status.connect(self.show_audio_status)
        if hasattr(self.audio,"outputs_changed"):
            self.audio.outputs_changed.connect(self.refresh_audio_outputs)
        self.apply_audio_settings()
        self.text_stream.setParent(self)
        self.text_stream.chunk.connect(self.present_text)
        self.text_stream.drained.connect(self.stream_drained)
        self._chat_generated_id = None
        self._chat_cancel_requested = False
        self.encounter_stream=TextStream(self,interval=140)
        self.encounter_stream.chunk.connect(self.append_encounter_text)
        self.encounter_pause=QTimer(self)
        self.encounter_pause.setSingleShot(True)
        self.encounter_pause.setInterval(600)
        self.encounter_pause.timeout.connect(self.finish_encounter_intro)
        self.encounter_stream.drained.connect(self.encounter_pause.start)
        self.nav_buttons[0].setText(self.ui('◇   Hauptmenü'))
        self.nav_buttons[3].setText(self.ui('≡   MAAT-KI'))
        from gui.title_screen import TitleScreen, TitleDemo
        self.title_screen = TitleScreen()
        self.arena.stage.effect_started.connect(lambda event: self.play_attack_sound(event, demo=False))
        self.title_screen.arena.stage.effect_started.connect(lambda event: self.play_attack_sound(event, demo=True))
        self.stack.addWidget(self.title_screen)
        self.title_demo = TitleDemo(self)
        self.title_demo.presented.connect(self.present_demo)
        self.title_demo.completed.connect(self.demo_finished)
        self.title_screen.start_requested.connect(self.request_title_start)
        self.title_idle = QTimer(self)
        self.title_idle.setSingleShot(True)
        self.title_idle.timeout.connect(self.start_title_demo)
        self.demo_stage = 0
        self._demo_return_pending = False
        self._demo_return_timer = QTimer(self)
        self._demo_return_timer.setSingleShot(True)
        self._demo_return_timer.timeout.connect(self.finish_demo_return)
        from gui.combat_input import CombatAdvanceInput
        self.combat_input = CombatAdvanceInput()
        from gui.application_input import ApplicationInputFilter
        self.application_input = ApplicationInputFilter(self)
        QApplication.instance().installEventFilter(self.application_input)
        from gui.perspective_screen import PerspectiveScreen
        self.perspective_screen = PerspectiveScreen()
        self.stack.addWidget(self.perspective_screen)
        self.perspective_screen.selected.connect(self.choose_initial_perspective)
        from gui.class_selection import ClassSelection
        self.class_selection = ClassSelection()
        self.stack.addWidget(self.class_selection)
        self.class_selection.selected.connect(self.submit_class)
        self._class_timer = QTimer(self)
        self._class_timer.setInterval(50)
        self._class_timer.timeout.connect(self.present_class_selection)
        from gui.story_screen import StoryScreen
        self.story_screen = StoryScreen()
        self.stack.addWidget(self.story_screen)
        self.story_screen.completed.connect(self.finish_story_scene)
        self.story_screen.audio_requested.connect(self.audio.handle_event)
        from gui.game_hall import GameHall
        self.game_hall=GameHall(self._discovered_games,self.play_hall_game)
        self.game_hall_index=self.stack.addWidget(self.game_hall)
        from gui.credits_screen import CreditsScreen
        self.credits_screen=CreditsScreen()
        self.stack.addWidget(self.credits_screen)
        self.credits_screen.completed.connect(self.finish_story_scene)
        self.credits_screen.audio_requested.connect(self.audio.handle_event)
        from gui.dungeons import Dungeons
        self.dungeons = Dungeons()
        self.dungeon_index = self.stack.addWidget(self.dungeons)
        self.dungeons.enter_requested.connect(self.enter_dungeon)
        self.dungeons.plus_requested.connect(self.enter_dungeon_plus)
        from gui.maat_guide import MaatGuide
        self.maat_guide=MaatGuide()
        self.guide_index=self.stack.addWidget(self.maat_guide)
        from gui.memories import Memories
        self.memories = Memories()
        self.memories_index = self.stack.addWidget(self.memories)
        self.memories.set_count(self._guide_messages)
        from gui.talent_tree import TalentTree
        self.talent_tree = TalentTree()
        self.talent_index = self.stack.addWidget(self.talent_tree)
        self.talent_tree.purchase_requested.connect(self.purchase_talent)
        self.talent_tree.quests_requested.connect(self.open_talent_quests)
        from shared.core.talents import snapshot as talent_snapshot
        self.talent_tree.update_data(self._talent_data or talent_snapshot({}))
        from gui.terra_map import TerraJourneyView
        self.terra_view=TerraJourneyView()
        self.terra_page=QScrollArea();self.terra_page.setWidgetResizable(True)
        self.terra_page.setWidget(self.terra_view)
        self.terra_index=self.stack.addWidget(self.terra_page)
        self._terra_return_index=3
        self.terra_view.back_requested.connect(lambda:self.navigate(self._terra_return_index))
        self.character_sidebar.terra_map.activated.connect(self.open_terra_map)
        self.terra_view.boss_selected.connect(self.select_terra_boss)
        self.terra_view.random_requested.connect(self.select_terra_random)
        self.terra_view.credits_requested.connect(self.open_terra_credits)
        # Keep every navigation entry usable on short screens as the menu grows.
        shell = self.centralWidget().layout()
        navigation = shell.itemAt(0).widget()
        self.arrange_navigation(navigation)
        navigation.setMinimumHeight(navigation.sizeHint().height())
        self.navigation_scroll = QScrollArea()
        # The previous frame was hidden by navigate(0); its new wrapper must
        # also start hidden, before showing/maximizing the native window.
        self.navigation_scroll.hide()
        self.navigation_scroll.setFixedWidth(218)
        self.navigation_scroll.setFrameShape(QScrollArea.NoFrame)
        self.navigation_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.navigation_scroll.setWidgetResizable(True)
        self.navigation_scroll.setStyleSheet('QScrollArea{background:#060c1c;border:none;}')
        shell.replaceWidget(navigation, self.navigation_scroll)
        self.navigation_scroll.setWidget(navigation)
        self.apply_hero_class(self._hero_class)
        from gui.language_screen import LanguageScreen
        self.language_screen = LanguageScreen()
        self.stack.addWidget(self.language_screen)
        self.language_screen.selected.connect(self.select_profile_language)
        self.language_screen.cancelled.connect(self.cancel_language_choice)
        from gui.profile_selection import ProfileSelection
        self.profile_screen = ProfileSelection()
        self.stack.addWidget(self.profile_screen)
        self.profile_screen.selected.connect(self.choose_profile)
        self.profile_screen.cancelled.connect(self.cancel_profile_choice)
        self.profile_screen.delete_requested.connect(self.delete_profile)
        self.profile_screen.rename_requested.connect(self.rename_profile)
        self.profile_screen.create_requested.connect(self.create_profile)
        self.update_title_artwork(saved_journey(self.game._profile_slot()))
        from gui.battle_editor import BattleEditor
        self.battle_editor = BattleEditor()
        self.editor_scroll = QScrollArea(); self.editor_scroll.setWidgetResizable(True)
        self.editor_scroll.setWidget(self.battle_editor)
        self.editor_index = self.stack.addWidget(self.editor_scroll)
        self.battle_editor.save_requested.connect(lambda request: self.editor_request('battle_editor_save', **request))
        self.battle_editor.play_requested.connect(self.play_editor_battle)
        self.battle_editor.back_requested.connect(lambda: self.navigate(0))
        self.apply_menu_language()
        if self.game.needs_language_choice:
            self.show_language_choice()
        else:
            self.show_title()

    def start_session(self):
        # The base window calls this while constructing its pages. Read the
        # last save for the title/demo, but start no worker or model before choice.
        self.game.ready = self.game.busy = False
        self.game._emit_snapshot()

    def can_choose_profile(self):
        return (not self.game.busy and not self.game.prompt_id
                and not self._active_minigame and not self._battle_active
                and not self._encounter_intro and not self.text_stream.running
                and not self._pending_class_event
                and not self._deferred and not self._dungeon_active
                and self.phase in ('title', 'title_demo', 'menu', 'playing', 'profiles'))

    def show_profile_choice(self):
        if not self.can_choose_profile():
            return
        self.level_up_notice.dismiss()
        self._profile_return_phase = 'playing' if self.phase == 'playing' else 'menu'
        self.game.stop_speech()
        self.title_idle.stop()
        self._demo_return_timer.stop()
        self._demo_return_pending = False
        self.title_demo.stop()
        self.title_screen.blink.stop()
        self.ki_dialog.hide()
        self.phase = 'profiles'
        self.navigation_scroll.hide()
        self.character_sidebar.hide()
        self.profile_badge.hide()
        self.footer.hide()
        self.audio.handle_event({'action': 'clear'})
        self.audio.location(True, self.game.get_snapshot().language)
        self.profile_screen.start(self.game._profile_slot(), self.game.get_snapshot().language,
                                  startup=self._startup_profile_pending)
        self.stack.setCurrentWidget(self.profile_screen)
        self.update_controls()

    def cancel_profile_choice(self):
        if self.phase != 'profiles':
            return
        if self._startup_profile_pending:
            self.show_title()
            return
        self.phase = self._profile_return_phase
        self.profile_badge.show()
        self.footer.show()
        self.navigate(4)
        self.update_controls()

    def choose_profile(self, slot):
        if self.phase != 'profiles' or not self.can_choose_profile():
            return
        if type(slot) is not int or not 1 <= slot <= session_shared.PROFILE_SLOT_COUNT:
            return
        if not self._startup_profile_pending and slot == self.game._profile_slot():
            self.cancel_profile_choice()
            return
        self._startup_profile_pending = False
        self._profile_launch_pending = True
        self.change_profile(slot - 1)
        if not self.game.needs_language_choice:
            self.show_title()
            self.prepare_startup_model()

    def create_profile(self):
        if self.phase != 'profiles' or not self.can_choose_profile():
            return
        ui = self.profile_screen.ui
        if len(session_shared.existing_profile_slots()) >= session_shared.PROFILE_SLOT_COUNT:
            QMessageBox.information(self, ui('Neues Profil'), ui('Alle zehn Profilplätze sind belegt.'))
            return
        name, ok = QInputDialog.getText(self, ui('Neues Profil'), ui('Wie soll dein Profil heißen? (1–48 Zeichen)'))
        if not ok:
            return
        try:
            slot = session_shared.create_profile(name)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, ui('Profil konnte nicht gespeichert werden'), ui(str(exc)))
            return
        self.profile_screen.refresh()
        self.choose_profile(slot)

    def rename_profile(self, slot):
        if self.phase != 'profiles' or not self.can_choose_profile() or not session_shared.profile_slot_exists(slot):
            return
        ui = self.profile_screen.ui
        name, ok = QInputDialog.getText(self, ui('Profil umbenennen'), ui('Wie soll dein Profil heißen? (1–48 Zeichen)'),
                                      text=session_shared.profile_slot_label(slot, self.profile_screen.language))
        if not ok:
            return
        try:
            session_shared.set_profile_name(slot, name)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, ui('Profil konnte nicht gespeichert werden'), ui(str(exc)))
            return
        # Refresh labels only. Keep the active worker, loaded model and chat intact.
        self.game._snapshot = self.game._build_snapshot()
        self.game._emit_snapshot()
        self.profile_screen.refresh()

    def ui(self, text, **values):
        from gui.ui_i18n import tr
        translated = tr(text, self.game.get_snapshot().language)
        return translated.format(**values) if values else translated

    def show_audio_status(self, text):
        self.audio_status.setText(self.ui(text))

    def apply_menu_language(self):
        from gui.ui_i18n import translate_widgets
        language = self.game.get_snapshot().language
        self.history_messages.setAccessibleName(self.ui('Nachrichten im KI-Kontext'))
        locale = QLocale('en_US' if language == 'en' else 'de_DE')
        if self.locale() != locale:
            self.setLocale(locale)
        if self.ki_dialog.locale() != locale:
            self.ki_dialog.setLocale(locale)
        roots = [self.stack.widget(0), self.stack.widget(1), self.stack.widget(4), self.ki_dialog,
                 self.centralWidget().layout().itemAt(0).widget(), self.perspective]
        for name in ('perspective_screen', 'footer', 'send_button',
                     'reveal_button', 'input', 'chat_model_panel', 'start_battle', 'tactical_input'):
            widget = getattr(self, name, None)
            if widget is not None:
                roots.append(widget)
        for parent in (self.profile_badge.parentWidget(), self.journal.parentWidget(), getattr(self, 'title_screen', None)):
            if parent is not None:
                roots.extend(parent.findChildren(QLabel, options=Qt.FindDirectChildrenOnly))
        if hasattr(self, 'title_screen'):
            roots.append(self.title_screen.start_button)
        for root in roots:
            translate_widgets(root, language)
        if hasattr(self, 'world_tabs'):
            for label in self.world_tabs.parentWidget().findChildren(QLabel, options=Qt.FindDirectChildrenOnly):
                translate_widgets(label,language)
            for i in range(self.world_tabs.count()):
                self.world_tabs.setTabText(i,self.ui(self.world_tabs.tabText(i)))
        for name in ('intro', 'story_screen', 'title_screen', 'wiki_settings'):
            screen = getattr(self, name, None)
            if screen is not None:
                screen.language = language
        for name in ('arena', 'character_sidebar', 'dungeons', 'class_selection', 'quest_log', 'talent_tree', 'game_hall', 'monster_catalog', 'terra_view', 'achievements', 'shop', 'memories', 'maat_guide'):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.set_language(language)
        translate_widgets(self.command_page, language)
        if self.command_tree.language != language:
            self.command_tree.set_language(language)
            self.filter_commands()
        from gui.battle_editor import text as editor_text
        self.editor_button.setText(editor_text('⚒   Kampfeditor', language))
        if hasattr(self, 'battle_editor'): self.battle_editor.set_language(language)
        self.refresh_minigame_offer()
        self.model_tuning.set_language(language)
        self.model_timing.set_language(language)
        self.refresh_model_safety()
        if hasattr(self, 'title_screen'):
            self.title_screen.arena.set_language(language)
        from gui.hero_portrait import class_name
        self.character_class_label.setText('MAATIS · ' + class_name(self._hero_class, language))
        self.setWindowTitle(self.ui('MAAT RPG · Die Rückkehr der Prinzipien'))
        self.ki_dialog.setWindowTitle(self.ui('MAAT RPG · KI & Modelle'))
        if hasattr(self, 'plugin_panel'):
            self.plugin_panel.set_language(language)
            self.settings_tabs.setTabText(0, 'General' if language == 'en' else 'Allgemein')
        for pyramid in self.findChildren(Sanctum):
            if isinstance(pyramid, JourneyArtwork):
                pyramid.set_language(language)
            elif pyramid.property('language') != language:
                pyramid.setProperty('language', language)
                pyramid.update()

    def update_title_artwork(self, journey):
        # Only real profile events reach this method; demo victories are isolated.
        self.title_screen.landscape.set_journey(journey)
        self.menu_pyramid.set_journey(journey)

    def show_language_choice(self):
        if not hasattr(self, 'language_screen'):
            return  # Session starts while the base window is still being built.
        if self.game.busy or self.game.prompt_id or self._battle_active or self.text_stream.running or self._active_minigame:
            return
        self._language_return_phase = 'playing' if self.phase == 'playing' else 'menu'
        self.game.stop_speech()
        self.title_idle.stop()
        self.phase = 'language'
        self.navigation_scroll.hide()
        self.character_sidebar.hide()
        self.profile_badge.hide()
        self.footer.hide()
        self.ki_dialog.hide()
        self.audio.location(False, self.game.get_snapshot().language)
        self.audio.handle_event({'action': 'clear'})
        self.stack.setCurrentWidget(self.language_screen)
        self.language_screen.start(self.game.get_snapshot().language,
                                   allow_cancel=not self.game.needs_language_choice)
        self.update_controls()

    def cancel_language_choice(self):
        if self.game.needs_language_choice:
            return
        self.phase = self._language_return_phase
        self.profile_badge.show()
        self.footer.show()
        self.navigate(4)

    def select_profile_language(self, language):
        if self.phase != 'language':
            return
        if not self.game.needs_language_choice and language == self.game.get_snapshot().language:
            self.cancel_language_choice()
            return
        try:
            if not self.game.set_language(language, start_worker=not self._startup_profile_pending):
                return
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, self.ui('Sprache / Language'),
                'Sprache konnte nicht gespeichert werden. / Could not save language.\n' + str(exc))
            return
        self._startup_model_attempted = self._startup_model_failed = False
        self.model_ready = False
        self.apply_menu_language()
        self.apply_audio_settings()
        self.show_title()

    def arrange_navigation(self, navigation):
        """Reorder visual buttons only; page IDs and existing unlocks stay stable."""
        layout = navigation.layout()
        labels = []
        while layout.count():
            item = layout.takeAt(0)
            if isinstance(item.widget(), QLabel): labels.append(item.widget())
        layout.setContentsMargins(14,22,14,18)
        layout.setSpacing(6)
        # Reuse the existing brand and footer labels.
        for widget in labels[:2]: layout.addWidget(widget)
        self.nav_buttons[5].setText(self.ui('📜   Quests && Aktionen'))
        self.nav_buttons[5].setToolTip(self.ui('Questlog · Spielaktionen · Shop · Erfolge · Monsterkatalog'))
        self.navigation_groups = (
            ('REISE', (self.nav_buttons[3], self.nav_buttons[5], self.memories_button)),
            ('MAATIS', (self.nav_buttons[1], self.talent_button)),
            ('KÄMPFE & SPIELE', (self.nav_buttons[2], self.dungeon_button, self.game_hall_button)),
            ('HILFE & MENÜ', (self.guide_button, self.nav_buttons[4], self.nav_buttons[0])),
        )
        self.navigation_order = []
        for title, widgets in self.navigation_groups:
            heading = label(title, 'eyebrow')
            heading.setStyleSheet('background:transparent;color:#8ba1c1;font-size:10px;letter-spacing:1px;padding-top:7px;')
            layout.addWidget(heading)
            for widget in widgets:
                widget.setMinimumHeight(40)
                widget.setStyleSheet('QPushButton{font-size:13px;padding:9px 23px 9px 10px;}')
                layout.addWidget(widget)
                self.navigation_order.append(widget)
        layout.addStretch(1)
        for widget in labels[2:]: layout.addWidget(widget)
        # Tab/keyboard navigation follows the same order as the visible menu.
        for before, after in zip(self.navigation_order,self.navigation_order[1:]):
            QWidget.setTabOrder(before,after)

    def chat_page_is_open(self):
        return (self.phase == 'playing' and self.stack.currentIndex() == 3
                and self.journal.isVisible() and not self.isMinimized()
                and QApplication.activeModalWidget() is None)

    def apply_hero_class(self, value):
        from gui.hero_portrait import normalize_class, class_name
        self._hero_class = normalize_class(value)
        self.arena.stage.set_hero_class(self._hero_class)
        self.character_sidebar.set_hero_class(self._hero_class)
        self.character_portrait.set_class(self._hero_class)
        self.character_class_label.setText('MAATIS · ' + class_name(self._hero_class,self.game.get_snapshot().language))
        self.companion_panel.hero_portrait.set_class(self._hero_class)
        if hasattr(self, 'title_screen'):
            self.title_screen.arena.stage.set_hero_class(self._hero_class)
        if hasattr(self, 'perspective_screen'):
            self.perspective_screen.set_hero_class(self._hero_class)
        if hasattr(self, 'story_screen'):
            self.story_screen.hero_class = self._hero_class
        if hasattr(self, 'terra_view'): self.terra_view.board.set_class(self._hero_class)

    def open_terra_map(self):
        if (self.phase!='playing' or self._battle_active or self._active_minigame
                or self._encounter_intro or self._dungeon_active or self._pending_class_event):
            return
        if self.stack.currentIndex()!=self.terra_index:self._terra_return_index=self.stack.currentIndex()
        self.navigate(self.terra_index)

    def select_terra_boss(self, target):
        if not self.terra_replay_ready():
            return
        self.game.busy = True
        self.terra_view.replay_result(self.ui('Boss wird vorgemerkt …'))
        self.update_controls()
        self.game.write(dict(op='terra_replay',target=target,profile_slot=self.game._profile_slot()))

    def select_terra_random(self):
        if not self.terra_replay_ready():
            return
        self.game.busy=True
        self.terra_view.replay_result(self.ui('Zufallskämpfe werden aktiviert …'))
        self.update_controls()
        self.game.write(dict(op='terra_random',profile_slot=self.game._profile_slot()))

    def terra_replay_ready(self):
        return (self.phase=='playing' and self.terra_view.data.get('kind')=='complete'
                and self.game.ready and not self.game.busy and not self.game.prompt_id
                and not self.text_stream.running and not self._deferred and not self._battle_active
                and not self._active_minigame and not self._encounter_intro
                and not self._dungeon_active and not self._pending_class_event)

    def open_terra_credits(self):
        if not self.terra_replay_ready():return
        self.game.busy=True
        self.terra_view.replay_result(self.ui('Abspann wird geöffnet …'))
        self.update_controls()
        self.game.write(dict(op='terra_credits',profile_slot=self.game._profile_slot()))

    def present_class_selection(self):
        if not self._pending_class_event:
            self._class_timer.stop()
            return
        if (self.phase != 'playing' or self.text_stream.running or self._deferred
                or self._battle_active or self.arena.stage.effect or self.arena.stage.effects):
            return
        event, self._pending_class_event = self._pending_class_event, None
        self._class_timer.stop()
        self.phase = 'class_selection'
        self.decision.hide()
        self.reveal_button.hide()
        self.stack.setCurrentWidget(self.class_selection)
        self.centralWidget().layout().itemAt(0).widget().hide()
        self.character_sidebar.hide()
        self.class_selection.start(event['id'])
        self.footer.setText(self.ui('Wähle deine Klasse · Die Auswahl bleibt in diesem Profil erhalten.'))
        self.update_controls()

    def submit_class(self, value):
        if self.phase == 'class_selection':
            self.game.write({'op': 'class_select', 'id': self.class_selection.request_id, 'value': value})

    def resume_class_selection(self):
        if not self._class_choice_pending:
            return False
        self._companion_after_class = self.perspective.currentData() == 'companion'
        self.game.busy = True
        self.game.transport({'event': 'busy', 'value': True})
        self.game.write({'op': 'class_resume'})
        return True

    def begin_story_scene(self, event):
        self._story_return = self.stack.currentIndex()
        self.phase = 'story'
        self.decision.hide()
        screen=self.credits_screen if event.get('module') in ('credits','companion_credits') else self.story_screen
        self._active_story_screen=screen
        self.stack.setCurrentWidget(screen)
        self.centralWidget().layout().itemAt(0).widget().hide()
        self.character_sidebar.hide()
        self.audio.location(False, self.game.get_snapshot().language)
        screen.language = self.game.get_snapshot().language
        screen.start_scene(event)
        self.footer.setText(self.ui('Abspann · Leertaste: Pause · Esc: Zurück ins Spiel' if screen is self.credits_screen else 'Hintergrundgeschichte · Klick / Enter: weiter · Esc: Szene überspringen'))
        self.update_controls()

    def finish_story_scene(self):
        screen=getattr(self,'_active_story_screen',self.story_screen)
        identifier=screen.request_id
        screen.cancel()
        self.phase = 'playing'
        self.navigate(getattr(self, '_story_return', 3))
        self.game.write({'op':'story_done', 'id':identifier})
        self.update_controls()

    def choose_initial_perspective(self, mode):
        if self.phase != 'perspective':
            return
        self.perspective.setCurrentIndex(self.perspective.findData(mode))
        self.save_perspective()
        self.start_selected_game()

    def show_title(self):
        self.game.stop_speech()
        self.level_up_notice.dismiss()
        self.phase = 'title'
        self.navigation_scroll.hide()
        self.character_sidebar.hide()
        self.stack.setCurrentWidget(self.title_screen)
        self.title_screen.show_title()
        self.profile_badge.hide()
        self.footer.hide()
        self.audio.location(True, self.game.get_snapshot().language)
        if self._startup_profile_pending or self.model_ready:
            self.title_screen.set_model_state("ready")
            self.title_idle.start(20000)
        else:
            self.title_screen.set_model_state("loading" if not self.game.ready or self.game.busy else "choose")
        self.update_controls()

    def handle_application_input(self, obj, event):
        if self.combat_input.handle(self, obj, event):
            return True
        if (event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape
                and isinstance(obj, QWidget) and obj.window() is self
                and self.game.chat_turn_id and not self.game.prompt_id
                and self.phase == 'playing' and not self._battle_active
                and not self._encounter_intro and not self._active_minigame):
            if not self._chat_cancel_requested and self.game.cancel_chat():
                self._chat_cancel_requested = True
                self._chat_generated_id = None
                self.text_stream.clear()
                self.reveal_button.hide()
                self.footer.setText(self.ui('Antwort wird abgebrochen …'))
                self.update_controls()
            return True
        if (obj is self and hasattr(self, 'chat_activity')
                and event.type() in (QEvent.WindowActivate, QEvent.WindowStateChange, QEvent.Show)):
            QTimer.singleShot(0, self.chat_activity.acknowledge_if_open)
        if (obj is getattr(self, 'menu_pyramid', None) and self.phase == 'menu'
                and obj.isEnabled()
                and ((event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton)
                     or (event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space)))):
            self.show_title()
            return True

        if self._active_minigame:
            game=self._active_minigame['widget']
            if event.type()==QEvent.ApplicationDeactivate or (obj is self and event.type()==QEvent.WindowDeactivate):
                game.pause()
            if event.type()==QEvent.KeyPress and event.key()==Qt.Key_Escape:
                game.reject()
                return True

        if (getattr(self, 'phase', '') in ('title', 'title_demo')
                and event.type() in (QEvent.KeyPress, QEvent.MouseButtonPress)
                and isinstance(obj, QWidget) and obj.window() is self
                and (event.type() == QEvent.MouseButtonPress or event.key() in (Qt.Key_Return, Qt.Key_Enter))):
            self.request_title_start()
            return True
        return False

    def request_title_start(self):
        if self._startup_profile_pending:
            self.show_profile_choice()
        elif self.model_ready and not self.game.busy:
            self.enter_menu()
        elif self.game.ready and not self.game.busy:
            self.open_models()

    def prepare_startup_model(self):
        if self._startup_profile_pending or self.phase != 'title' or not self.game.ready or self.game.busy:
            return
        if self.model_ready:
            if self._profile_launch_pending:
                self.enter_menu()
                return
            self.title_screen.set_model_state('ready')
            self.title_idle.start(20000)
            return
        self.title_idle.stop()
        if self.saved_model and not self._startup_model_attempted:
            self._startup_model_attempted=True
            self.model_combo.setCurrentText(self.saved_model)
            self.title_screen.set_model_state('loading')
            self.load_model()
        else:
            self.title_screen.set_model_state('error' if self._startup_model_failed else 'choose')
            self.model_status.setText(self.ui('Wähle eine GGUF-Datei und klicke auf „Modell laden“. Sie wird beim nächsten Start automatisch geladen.'))
            self.open_models()

    def enter_menu(self):
        self._profile_launch_pending = False
        self._demo_return_timer.stop()
        self._demo_return_pending = False
        self.title_idle.stop()
        self.title_screen.blink.stop()
        self.title_demo.stop()
        self.audio.handle_event({'action': 'clear'})
        self.phase = 'menu'
        self.profile_badge.show()
        self.footer.show()
        self.navigate(0)

    def start_title_demo(self):
        if self.phase != 'title' or (not self.model_ready and not self._startup_profile_pending) or self.game.busy:
            return
        self.phase = 'title_demo'
        self.title_screen.show_demo()
        # Keep menu music until the replay provides its battle track.
        self.audio.location(True, self.game.get_snapshot().language)
        self.title_demo.start(self.demo_stage, profile_slot=self.game._profile_slot())

    def present_demo(self, event):
        if self.phase != 'title_demo':
            return
        if event.get('event') == 'audio':
            # The terminal worker finishes before its paced on-screen replay.
            # Its cleanup must not silence the remaining visible demo.
            if event.get('action') == 'play':
                path=Path(event.get('path',''))
                battle_music=Path(__file__).resolve().parents[1]/'apps/maat_rpg/plugins/battle/music'
                if path.parent == battle_music:
                    self.audio.handle_event(dict(event, owner='native-title-demo', loop=True))
                    self.audio.location(False, self.game.get_snapshot().language)
        else:
            self.title_screen.present(event)

    def play_attack_sound(self, event, *, demo):
        if self.phase == ('title_demo' if demo else 'playing'):
            self.audio.handle_event({'action': 'effect', 'attack_event': dict(event)})

    def demo_finished(self):
        if self.phase != 'title_demo' or self._demo_return_pending:
            return
        self._demo_return_pending = True
        diagnostic('demo_return_requested', stage=self.demo_stage)
        self.title_demo.stop()
        stage = self.title_screen.arena.stage
        stage.clear_effects()
        stage.sway_timer.stop()
        self.title_screen.arena.resonance.pulse_timer.stop()
        # Leave the demo's timer/signal callback before hiding its renderers and
        # switching audio. Repeated completion signals cannot schedule two returns.
        self._demo_return_timer.start(0)

    def finish_demo_return(self):
        if not self._demo_return_pending or self.phase != 'title_demo':
            return
        self._demo_return_pending = False
        diagnostic('demo_return_begin', stage=self.demo_stage)
        self.audio.location(True, self.game.get_snapshot().language)
        self.audio.handle_event({'action': 'stop', 'owner':'native-title-demo'})
        self.demo_stage += 1
        self.show_title()
        if self.demo_stage == 3:
            self.demo_stage = 0
            self.title_idle.start(180000)
        diagnostic('demo_return_finished', next_stage=self.demo_stage, visible=self.isVisible())


    def _build_home(self):
        l = self.page('MAAT RPG', 'Die Rückkehr der Prinzipien', 'Eine Reise durch Erinnerung, Resonanz und die fünf Prinzipien.')
        # Keep the unlocked endgame tool above the artwork: below the menu
        # statistics it falls outside the viewport on smaller laptop windows.
        self.editor_button = button('⚒   Kampfeditor', self.open_battle_editor)
        self.editor_button.hide()
        l.addWidget(self.editor_button)
        self.menu_pyramid = JourneyArtwork()
        self.menu_pyramid.setCursor(Qt.PointingHandCursor)
        self.menu_pyramid.setFocusPolicy(Qt.StrongFocus)
        self.menu_pyramid.setAccessibleName('Zum Startbildschirm zurückkehren')
        self.menu_pyramid.setToolTip(self.ui('Zum Titelbild · Nach 20 Sekunden startet die Demo'))
        l.addWidget(self.menu_pyramid, 1)
        row = QHBoxLayout()
        self.home_stats = []
        for title in ['LEVEL', 'GOLD', 'BOSS-SIEGE']:
            w, c = card()
            c.addWidget(label(title, 'eyebrow'))
            value = label('—', 'number')
            c.addWidget(value)
            self.home_stats.append(value)
            row.addWidget(w)
        l.addLayout(row)
        w, c = card()
        c.addWidget(label('Hauptmenü', 'heading'))
        self.perspective = QComboBox()
        self.perspective.addItem('Die Reise von Maatis · Du sprichst mit der KI', 'adventure')
        self.perspective.addItem('Ich bin die KI · Maatis spricht mit dir', 'companion')
        self.perspective.currentIndexChanged.connect(self.save_perspective)
        self.perspective.setParent(self)
        self.perspective.hide()
        self.begin_button = button('1   Spiel starten  →', self.begin_game, True)
        c.addWidget(self.begin_button)
        c.addWidget(button('✧   KI & Modelle · GGUF', self.open_models))
        self.menu_pick_model = button('Modell aus Pfad wählen …', self.pick_model_from_menu)
        c.addWidget(self.menu_pick_model)
        row = QHBoxLayout()
        self.options_button = button('2   Optionen', lambda: self.navigate(4))
        self.new_button = button('3   Neues Spiel', self.new_game)
        row.addWidget(self.options_button)
        row.addWidget(self.new_button)
        c.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(button('4   Info', self.show_info))
        row.addWidget(button('5   Beenden', self.close))
        c.addLayout(row)
        l.addWidget(w)

    def _build_journal(self):
        super()._build_journal()
        page = self.stack.widget(3).widget()
        for w in page.findChildren(QLabel):
            if w.text().startswith('Demo-Dialog'):
                w.setText(self.ui('Dein Gespräch mit der lokalen MAAT-KI und die Ereignisse deiner Reise.'))
        self.input.setPlaceholderText(self.ui('Sprich mit Maatis oder nutze einen Spielbefehl …'))
        for w in page.findChildren(QLabel):
            if w.objectName() == 'title':
                w.setText(self.ui('MAAT-KI'))
            elif w.objectName() == 'eyebrow':
                w.setText(self.ui('DEIN ABENTEUER / DIALOG'))
        self.chat_level_panel, level_layout = card()
        self.chat_level_text = label('')
        self.chat_xp_bar = QProgressBar()
        self.chat_xp_bar.setObjectName('xp')
        self.chat_xp_bar.setTextVisible(False)
        self.chat_xp_bar.setFixedHeight(12)
        level_layout.addWidget(self.chat_level_text)
        level_layout.addWidget(self.chat_xp_bar)
        from gui.model_timing import ModelTiming
        self.model_timing = ModelTiming(
            lambda: session_shared.load_profile_settings(self.game._profile_slot()),
            lambda updates: session_shared.write_profile_settings(self.game._profile_slot(), updates))
        level_layout.addWidget(self.model_timing)
        self.wiki_source = label('', 'muted')
        self.wiki_source.setTextFormat(Qt.PlainText)
        self.wiki_source.setWordWrap(True)
        self.wiki_source.hide()
        level_layout.addWidget(self.wiki_source)
        page.layout().insertWidget(page.layout().indexOf(self.journal), self.chat_level_panel)
        self._last_xp_gain = None
        self._xp_profile = None
        from gui.character_sidebar import CharacterSidebar
        self.character_sidebar = CharacterSidebar()
        self.character_sidebar.quest_requested.connect(self.open_sidebar_quest)
        self.character_sidebar.navigation_requested.connect(self.open_sidebar_link)
        self.centralWidget().layout().addWidget(self.character_sidebar)
        self.character_sidebar.hide()
        self.chat_model_panel, c = card()
        self.minigame_card, mini_layout = card()
        self.minigame_title=label('🎮 Minispiele freigeschaltet!', 'heading')
        self.minigame_reward=label('')
        mini_layout.addWidget(self.minigame_title);mini_layout.addWidget(self.minigame_reward)
        self.minigame_play = button('🐍 Spielen', self.open_minigame, True)
        self.minigame_skip = button('Weiterreisen', self.skip_minigame)
        mini_layout.addWidget(self.minigame_play);mini_layout.addWidget(self.minigame_skip)
        self.minigame_card.hide()
        page.layout().insertWidget(page.layout().indexOf(self.journal)+1, self.minigame_card)
        self.journal.setMinimumHeight(220)
        row = QHBoxLayout()
        self.chat_model_combo = QComboBox()
        self.chat_load_button = button('KI laden', self.load_chat_model, True)
        row.addWidget(self.chat_model_combo, 1)
        row.addWidget(self.chat_load_button)
        self.chat_pick_model = button('Modell aus Pfad wählen …', self.pick_model)
        c.addWidget(self.chat_pick_model)
        c.addLayout(row)
        self.chat_model_status = label('Lokales Modell auswählen', 'muted')
        c.addWidget(self.chat_model_status)
        page.layout().insertWidget(3, self.chat_model_panel)
        from gui.companion_panel import CompanionPanel
        self.companion_panel = CompanionPanel()
        self.companion_panel.training.clicked.connect(lambda: self.execute('/ai-training', stay=True))
        self.companion_panel.story.clicked.connect(lambda: self.execute('/ai-start', stay=True))
        self.companion_panel.fight.clicked.connect(lambda: self.execute('/fight', stay=True))
        page.layout().insertWidget(page.layout().indexOf(self.journal), self.companion_panel)
        self.companion_panel.hide()
        self.reply_token_hint = label('', 'muted')
        self.reply_token_hint.setToolTip('Modellunabhängige Schätzung: Textstücke werden nach UTF-8-Länge gezählt; Leerraum zählt nicht. Der GGUF-Tokenizer kann andere Werte liefern.')
        page.layout().addWidget(self.reply_token_hint)
        self.input.textChanged.connect(self.update_reply_tokens)
        self.reply_token_hint.hide()

    def _build_character(self):
        super()._build_character()
        from gui.hero_portrait import HeroPortrait
        self.character_portrait = HeroPortrait(180)
        self.character_class_label = label('MAATIS · Normal · noch keine Klasse', 'heading')
        box, content = card()
        row = QHBoxLayout()
        row.addWidget(self.character_portrait)
        row.addWidget(self.character_class_label, 1)
        content.addLayout(row)
        self.stack.widget(1).widget().layout().insertWidget(3, box)

    def _build_battle(self):
        super()._build_battle()
        for btn in self.action_buttons.values():
            btn.hide()
        self.start_battle.setText('Arenakampf starten · ½ EP')
        self.controls.append(self.start_battle)
        l = self.stack.widget(2).widget().layout()
        row = QHBoxLayout()
        self.battle_launch_buttons = [self.start_battle]
        l.addLayout(row)
        from gui.battle_arena import BattleArena
        for i in range(l.count()):
            widget = l.itemAt(i).widget()
            if widget and widget is not self.start_battle:
                widget.hide()
        self.arena = BattleArena()
        self.encounter_notice = QLabel()
        self.encounter_notice.setWordWrap(True)
        self.encounter_notice.setStyleSheet("background:#243b59;color:#ffe0a0;border:1px solid #b49250;border-radius:8px;padding:12px;font-size:22px;font-weight:700;")
        self.encounter_notice.hide()
        self.arena.layout().insertWidget(0, self.encounter_notice)
        self.tactical_input = QLineEdit()
        self.tactical_input.setPlaceholderText('Rat an Maatis · z. B. Fokus: Sammle Kraft, bevor du angreifst.')
        self.tactical_input.returnPressed.connect(self.tactical_advice)
        self.arena.layout().addWidget(self.tactical_input)
        self.tactical_input.hide()
        self.arena.action_requested.connect(self.arena_action)
        l.insertWidget(0, self.arena, 1)
        self.arena_progress = label('Arena · ½ Kampf-EP', 'muted')
        l.addWidget(self.arena_progress)
        self.battle_log = self.arena.log

    def open_minigame(self):
        if not self.minigame_play.isEnabled() or not self._minigame_offer:return
        self.submit_minigame(dict(op='minigame_start',id=self._minigame_offer['id']))

    def refresh_minigame_offer(self):
        from shared.core.minigame_i18n import game_info
        if not hasattr(self, 'minigame_card'):
            return
        self.minigame_skip.setText(self.ui('Weiterreisen'))
        if self._minigame_offer:
            name,goal,xp,gold=game_info(self._minigame_offer['game'],self.game.get_snapshot().language)
            self.minigame_title.setText(self.ui('🎮 Minispiel · {name}',name=name))
            self.minigame_reward.setText(self.ui('{goal} · {xp} EP + {gold} Gold · Einmalige Belohnung',goal=goal,xp=xp,gold=gold))
            remaining=max(0,2-self._minigame_offer.get('attempts',0))
            self.minigame_play.setText(self.ui('Spielen · {remaining}/2 Versuche übrig',remaining=remaining))

    def run_minigame_attempt(self):
        offer=self._minigame_grant
        self._minigame_grant=None
        if not offer or self.phase!='playing' or not self.game.ready or self._active_minigame:return
        from gui.game_hall import game_dialog
        language=self.game.get_snapshot().language
        game=game_dialog(offer['game'],offer['seed'],self.stack,practice=offer.get('practice',False),language=language)
        game.setWindowFlags(Qt.Widget)
        game.setModal(False)
        game.music_running.connect(self.minigame_music)
        practice=offer.get('practice',False)
        caption=self.ui('Spielhalle · Freies Spielen · ohne EP/Gold') if practice else self.ui('Chat-Herausforderung · Versuch {attempts}/2',attempts=offer['attempts'])
        game.layout().insertWidget(1,label(caption,'muted'))
        if practice:
            from shared.core.arcade_scores import record_text
            game.layout().insertWidget(2,label(record_text(offer['game'],self._arcade_highscores.get(offer['game']),language),'muted'))
        if practice and hasattr(game,'hint'):
            import re
            hint=re.sub(r' · \d+ EP \+ \d+ Gold','',game.hint.text())
            game.hint.setText('\n'.join(line for line in hint.splitlines() if not line.startswith('Belohnung:')))

        game.back.setText(self.ui('Zurück zur Spielhalle' if practice else 'Zurück zum Chat'))
        index=self.stack.addWidget(game)
        self._active_minigame=dict(widget=game,offer=offer,index=index)
        game.finished.connect(lambda result:self.finish_minigame(game))
        self.stack.setCurrentWidget(game)
        self.character_sidebar.hide()
        self.decision.hide()
        self.reveal_button.hide()
        self.footer.setText(caption+' · '+self.ui('Leertaste: Pause · Esc: Spiel verlassen'))
        self.update_controls()
        # Start only once the embedded board is visible and ready for keyboard focus.
        QTimer.singleShot(0,lambda:self.start_embedded_minigame(game))

    def start_embedded_minigame(self,game):
        if self._active_minigame and self._active_minigame['widget'] is game:
            game.toggle()

    def finish_minigame(self,game):
        active=self._active_minigame
        if not active or active['widget'] is not game:return
        offer=active['offer']
        moves=list(game.game.moves) if offer.get('practice') else game.winning_moves or []
        self._active_minigame=None
        self.minigame_music(False)
        self.navigate(self.game_hall_index if offer.get('practice') else 3)
        self.stack.removeWidget(game)
        game.deleteLater()
        if offer.get('practice'):
            self.submit_minigame(dict(op='hall_result',ticket=offer['ticket'],moves=moves))
        else:
            self.submit_minigame(dict(op='minigame',id=offer['id'],ticket=offer['ticket'],moves=moves))
            self._focus_chat_after_battle=True

    def discard_minigame(self):
        active,self._active_minigame=self._active_minigame,None
        if active:
            game=active['widget']
            game.reject()
            self.stack.removeWidget(game)
            game.deleteLater()
            self.minigame_music(False)

    def open_game_hall(self):
        if self.game_hall_button.isEnabled():
            self.navigate(self.game_hall_index)

    def play_hall_game(self,kind,parent):
        if kind not in self._discovered_games or not self.game_hall_button.isEnabled():return
        self.submit_minigame(dict(op='hall_start',game=kind))

    def minigame_music(self, running):
        track=Path(__file__).resolve().parents[1]/'apps/maat_rpg/plugins/battle/music/Sandsack-Highscore.m4a'
        event=dict(action='play' if running else 'stop',owner='native-minigame')
        if running:event.update(path=str(track),loop=True)
        self.audio.handle_event(event)

    def submit_minigame(self, message):
        self.game.busy = True
        self.update_controls()
        self.game.write(message)

    def skip_minigame(self):
        if self.minigame_skip.isEnabled() and self._minigame_offer:
            self.submit_minigame(dict(op='minigame',id=self._minigame_offer['id'],skip=True))

    def tactical_advice(self):
        text = self.tactical_input.text().strip()
        code = text.split(':', 1)[0].strip().lower()
        aliases = {'fokus':'focus', 'trank':'potion', 'heiltrank':'potion', 'healing potion':'potion', 'flucht':'escape', 'wegrennen':'escape', 'run away':'escape', 'impuls':'impulse'}
        code = aliases.get(code, code)
        action = self.arena.actions.get(code)
        if action is None or not action.isEnabled():
            self.footer.setText(self.ui('Beginne mit H:, B:, S:, V:, R:, Fokus:, Heiltrank:, Skill:, Impuls: oder Wegrennen: – passend zur aktuellen Auswahl.'))
            return
        self.journal.moveCursor(QTextCursor.End)
        self.journal.setTextColor(QColor('#dac48e'))
        self.journal.insertPlainText(self.ui('\nDu · Taktischer Rat: ') + text + '\n')
        self.tactical_input.clear()
        self.arena_action(code)

    def arena_action(self, key):
        if not self.game.prompt_id or self.text_stream.running:
            return
        terms = {'h':('harmonie','harmony'), 'b':('balance',), 's':('schöpfung','creation'),
                 'v':('verbundenheit','connection','connectedness'), 'r':('respekt','respect'),
                 'skill':('skill','fähigkeit'), 'focus':('fokus','focus'), 'potion':('trank','potion'),
                 'impulse':('impuls','impulse'), 'escape':('wegrennen','run away','flucht','flee','escape')}
        choice = next((c for c in self._arena_choices if any(t in c['label'].lower() for t in terms[key])), None)
        if choice is None and key in 'hbsvr':
            choice = next((c for c in self._arena_choices if any(t in c['label'].lower() for t in ('angriff','attack'))), None)
            if choice:
                self._pending_principle = key
        if choice:
            self.game.submit_choice(choice['value'])
            self._arena_choices = []
            self.update_arena_actions()

    def update_arena_actions(self):
        names = ' '.join(c['label'].lower() for c in self._arena_choices)
        top = 'angriff' in names or 'attack' in names
        terms = {'h':('harmonie','harmony'), 'b':('balance',), 's':('schöpfung','creation'),
                 'v':('verbundenheit','connection','connectedness'), 'r':('respekt','respect'),
                 'skill':('skill','fähigkeit'), 'focus':('fokus','focus'), 'potion':('trank','potion'),
                 'impulse':('impuls','impulse'), 'escape':('wegrennen','run away','flucht','flee','escape')}
        principles = all(any(t in names for t in terms[key]) for key in 'hbsvr')
        usable = bool(self.game.prompt_id) and not self.text_stream.running and self.phase == 'playing' and (top or principles)
        for key, btn in self.arena.actions.items():
            btn.setEnabled(usable and ((key in 'hbsvr' and top) or any(t in names for t in terms[key])))
        self.arena.set_hint_waiting(usable)
        return top or principles

    def _build_settings(self):
        l = self.page('OPTIONEN', 'Dein Ort. Dein Klang.', 'Profile, Musik und das lokale KI-Modell.')
        w, c = card()
        c.addWidget(label('Spielprofil', 'heading'))
        self.profile_choice_button = button('Profil wählen', self.show_profile_choice)
        c.addWidget(self.profile_choice_button)
        c.addWidget(label('Profilwechsel ist möglich, sobald die laufende Aktion beendet ist.', 'muted'))
        l.addWidget(w)
        w, c = card()
        c.addWidget(label('Sprache / Language', 'heading'))
        self.language_button = button('Sprache ändern …', self.show_language_choice)
        c.addWidget(self.language_button)
        c.addWidget(label('Die Sprache gilt für das gesamte Spiel und alle Profile. Ein Wechsel startet die Spielverbindung neu.', 'muted'))
        l.addWidget(w)
        w, c = card()
        c.addWidget(label('Schriftgröße', 'heading'))
        self.text_size_combo = QComboBox()
        for title, value in [('Klein · 18 px', 'small'), ('Mittel · 26 px · Standard', 'medium'), ('Groß · 36 px', 'large')]:
            self.text_size_combo.addItem(title, value)
        self.text_size_combo.setCurrentIndex(1)
        self.text_size_combo.currentIndexChanged.connect(self.save_text_size)
        c.addWidget(self.text_size_combo)
        self.text_size_preview = label('Die Welt erinnert sich. Deine Reise beginnt.', 'muted')
        c.addWidget(self.text_size_preview)
        c.addWidget(label('Gilt sofort für Chat, Eingabe und Erzählverlauf. Der kompakte Kampftext bleibt bei 18 px.', 'muted'))
        l.addWidget(w)
        w, c = card()
        c.addWidget(label('Musik & Sound', 'heading'))
        c.addWidget(label('Die Quellcode-Version enthält keine Hintergrundmusik. Eigene Soundeffekte sind enthalten; Musik ist standardmäßig aus.', 'muted'))
        self.music_box = QCheckBox('Musik im Menü, in Geschichten und im Kampf')
        self.sound_box = QCheckBox('Soundeffekte und Levelaufstieg')
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume_text = label('Lautstärke 35 %', 'muted')
        self.audio_status = label('Audio bereit', 'muted')
        self.audio_output = QComboBox()
        self.audio_output.addItem('Systemstandard', '')
        if hasattr(self.audio,'available_outputs'):
            for identifier,name in self.audio.available_outputs():self.audio_output.addItem(name,identifier)
        self.audio_output.currentIndexChanged.connect(self.save_audio_output)
        c.addWidget(label('Audioausgabe', 'muted'))
        c.addWidget(self.audio_output)
        c.addWidget(button('Audioausgabe neu verbinden', self.reconnect_audio))
        for item in [self.music_box, self.sound_box, self.volume_text, self.volume, self.audio_status]:
            c.addWidget(item)
        self.music_box.toggled.connect(self.save_audio_settings)
        self.sound_box.toggled.connect(self.save_audio_settings)
        self.volume.valueChanged.connect(self.save_audio_settings)
        l.addWidget(w)
        w, c = card()
        c.addWidget(label('Lokale KI', 'heading'))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumContentsLength(20)
        self.model_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.backend_combo = QComboBox()
        from shared.core.gguf_adapters import available_adapters
        for adapter_id, title in available_adapters():
            self.backend_combo.addItem(title, adapter_id)
        self.backend_combo.setEnabled(False)
        self.context_size = QSpinBox()
        from shared.core.model_settings import MIN_CONTEXT, MAX_CONTEXT, DEFAULT_CONTEXT
        self.context_size.setRange(MIN_CONTEXT, MAX_CONTEXT)
        self.context_size.setValue(DEFAULT_CONTEXT)
        self.context_size.setToolTip('Standard: 20.000 Tokens · Maximal: 100.000 Tokens. Der tatsächliche Speicherbedarf hängt vom Modell ab.')
        self.context_size.setSingleStep(1024)
        self.hardware_status = label('Aktive Ladeeinstellungen · noch kein Modell geladen.', 'muted')
        c.addWidget(self.hardware_status)
        self.memory_warning = label('Speichergrenze: 99 % RAM. Alle manuellen Ladeoptionen bleiben wählbar. Achtung: Diese Einstellungen können den Computer verlangsamen oder zum Absturz bringen. Der Schutz kann das nicht sicher verhindern.', 'muted')
        self.memory_warning.setStyleSheet('color:#f0d08a;background:#302b25;padding:12px;border-radius:8px;')
        c.addWidget(self.memory_warning)
        self._model_safety_report = None
        self.model_memory_status = label('', 'muted')
        self.model_memory_status.hide()
        c.addWidget(self.model_memory_status)
        self.model_status = label('Noch kein Modell geladen.', 'muted')
        self.load_button = button('Modell laden', self.load_model, True)
        self.controls.append(self.load_button)
        for item in [self.model_combo, self.backend_combo, label('Kontextgröße', 'muted'), self.context_size, self.model_status]:
            c.addWidget(item)
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(.1)
        self.temperature.setValue(.8)
        for field in (self.context_size, self.temperature):
            field.setMinimumHeight(38)
            field.setStyleSheet('QAbstractSpinBox { background:#0b1c36; color:#eee6d5; border:1px solid #34516e; border-radius:6px; padding:7px; } QAbstractSpinBox QLineEdit { border:none; padding:0; background:transparent; }')
        c.addWidget(label('Kreativität / Temperatur', 'muted'))
        c.addWidget(self.temperature)
        from gui.model_tuning import ModelTuningPanel
        self.model_tuning = ModelTuningPanel()
        self.model_tuning.changed.connect(self.save_model_tuning)
        c.addWidget(self.model_tuning)
        self.pick_model_button = button('Modell aus Pfad wählen …', self.pick_model)
        c.addWidget(self.pick_model_button)
        c.addWidget(label('Llama · TinyLlama · Qwen · Gemma · Mistral · GPT-OSS — Chatvorlage aus der GGUF-Datei; TinyLlama Chat v1.0 auch mit passender Ersatzvorlage. Die Datei bleibt an ihrem Speicherort.', 'muted'))
        c.addWidget(label('Nutze ein Instruct-/Chat-Modell. Neue Modellarchitekturen benötigen eine passende llama.cpp-Version. Mehr Kontext benötigt mehr Arbeitsspeicher.', 'muted'))
        self.model_error = label('', 'muted')
        c.addWidget(self.model_error)
        self.ki_card = w
        l.addWidget(button('KI & Modelle öffnen', self.open_models))
        self.ki_dialog = QDialog(self)
        self.ki_dialog.setWindowTitle('MAAT RPG · KI & Modelle')
        self.ki_dialog.setMinimumWidth(620)
        self.ki_dialog.setModal(True)
        dialog_layout = QVBoxLayout(self.ki_dialog)
        dialog_layout.addWidget(label('Die Stimme deiner Reise', 'title'))
        self.model_scroll = QScrollArea()
        self.model_scroll.setWidgetResizable(True)
        self.model_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.model_scroll.setWidget(w)
        self.model_scroll.setMinimumHeight(280)
        dialog_layout.addWidget(self.model_scroll, 1)
        model_actions = QHBoxLayout()
        model_actions.addWidget(self.load_button, 1)
        model_actions.addWidget(button('Fertig · Zurück zum Spiel', self.ki_dialog.accept), 1)
        dialog_layout.addLayout(model_actions)
        available = self.screen().availableGeometry()
        self.ki_dialog.resize(min(740, available.width() - 40), min(780, available.height() - 60))
        w, c = card()
        c.addWidget(label('Dialog & Sprachausgabe', 'heading'))
        from shared.core.conversation_history import MIN_MESSAGES, MAX_MESSAGES, DEFAULT_MESSAGES
        c.addWidget(label('Nachrichten im KI-Kontext', 'heading'))
        self.history_messages = QSpinBox()
        self.history_messages.setRange(MIN_MESSAGES, MAX_MESSAGES)
        self.history_messages.setValue(DEFAULT_MESSAGES)
        self.history_messages.setMinimumHeight(38)
        self.history_messages.setAccessibleName('Nachrichten im KI-Kontext')
        self.history_messages.valueChanged.connect(self.save_history_messages)
        c.addWidget(self.history_messages)
        c.addWidget(label('2–20 vorherige Nachrichten · Standard: 10. Eigene Eingaben und KI-Antworten zählen einzeln; deine neue Eingabe kommt hinzu.', 'muted'))
        c.addWidget(label('Pro Profil · Gilt ab der nächsten Antwort in beiden Spielrollen. Chatarchiv und gespeicherte Erinnerungen bleiben erhalten. Lange Texte können trotzdem viel Kontext benötigen.', 'muted'))
        self.dialog_settings = {}
        for key, title in [('maat_thinking_enabled', 'MAAT Thinking aktivieren'), ('thinking_enabled', 'Thinking-Modus'), ('rpg_context_enabled', 'Spielkontext ausblenden'), ('say_tts_enabled', 'Sprachausgabe über das vorhandene TTS-Plugin')]:
            box = QCheckBox(title)
            box.toggled.connect(lambda value, k=key: session_shared.write_profile_settings(self.game._profile_slot(), {k: not value if k == 'rpg_context_enabled' else value}))
            self.dialog_settings[key] = box
            if key == 'thinking_enabled':
                box.setToolTip(self.ui('Standardmäßig aus. Die sichtbare MAAT-Reflexion bleibt Teil der Antwort.'))
                self.ki_card.layout().addWidget(box)
                self.ki_card.layout().addWidget(label('GPT-OSS: aus = niedrige Denkstufe, an = mittlere Denkstufe. Der Chat zeigt nur die fertige Antwort.', 'muted'))
            else:
                c.addWidget(box)
            if key == 'maat_thinking_enabled':
                box.setToolTip('Stufe 100 · Stille Qualitätsprüfung nach H/B/S/V/R mit höchstens drei angeleiteten Überarbeitungen. Die Wirkung hängt vom Modell ab.')
                c.addWidget(label('MAAT Thinking verbessert vor der Modellausgabe intern den Denkprozess.', 'muted'))
                c.addWidget(label('MAAT100 · Standardmäßig an · Gilt ab der nächsten Antwort. Die Wirkung hängt vom Modell ab.', 'muted'))
        c.addWidget(label('Verfügbarkeit der Stimme hängt vom vorhandenen TTS-Backend deines Systems ab.', 'muted'))
        l.addWidget(w)
        from gui.wiki_settings import WikiSettings
        self.wiki_settings = WikiSettings(
            lambda: session_shared.load_profile_settings(self.game._profile_slot()),
            lambda updates: session_shared.write_profile_settings(self.game._profile_slot(), updates))
        self.wiki_settings.test_requested.connect(self.test_offline_wiki)
        l.addWidget(self.wiki_settings)
        self.restart_button = button('Spielverbindung neu starten', self.restart)
        l.addWidget(self.restart_button)
        from gui.plugin_settings import PluginSettingsPanel
        self.plugin_panel = PluginSettingsPanel(
            lambda: session_shared.load_profile_settings(self.game._profile_slot()),
            lambda updates: session_shared.write_profile_settings(self.game._profile_slot(), updates), self)
        l.addStretch()
        # Keep the tab bar fixed, with one scroll area per settings page.
        self.general_settings = self.stack.widget(4)
        self.stack.removeWidget(self.general_settings)
        self.settings_tabs = QTabWidget()
        self.settings_tabs.setStyleSheet('QTabWidget::pane{border:1px solid #294562;border-radius:10px;} '
            'QTabBar::tab{padding:12px 22px;background:#102743;color:#b9cbde;} '
            'QTabBar::tab:selected{background:#234768;color:#f3deb0;}')
        self.settings_tabs.addTab(self.general_settings, 'Allgemein')
        self.settings_tabs.addTab(self.plugin_panel, 'Plugins')
        self.settings_tabs.currentChanged.connect(self.refresh_plugin_tab)
        settings_page = QWidget()
        settings_layout = QVBoxLayout(settings_page)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.addWidget(button('← Zurück zum Hauptmenü', lambda: self.navigate(0)))
        settings_layout.addWidget(self.settings_tabs, 1)
        self.stack.insertWidget(4, settings_page)
        from gui.settings_scroll import protect_settings_scroll
        protect_settings_scroll(l.parentWidget())
        protect_settings_scroll(self.ki_dialog)

    def update_wiki_source(self, event):
        titles = event.get('titles') or []
        terms = event.get('terms') or []
        if titles:
            self.wiki_source.setText(self.ui('📚 Offline-Quelle für diese Antwort: {titles}',titles=' · '.join(titles)))
            self.wiki_source.setToolTip(event.get('excerpt', ''))
        elif terms:
            self.wiki_source.setText(self.ui('📚 Kein Offline-Auszug verfügbar: {terms}',terms=' · '.join(terms)))
            self.wiki_source.setToolTip(event.get('error', ''))
        else:
            self.wiki_source.clear()
            self.wiki_source.setToolTip('')
        self.wiki_source.setVisible(bool(titles or terms))

    def test_offline_wiki(self, term):
        if not self.game.ready or self.game.busy or self.game.prompt_id:
            self.wiki_settings.result.setPlainText('Bitte warte, bis die aktuelle Spielaktion beendet ist.')
            return
        self.wiki_settings.result.setPlainText('Suche in der lokalen ZIM …')
        self.game.busy = True
        self.game.transport({'event': 'busy', 'value': True})
        self.game.write({'op': 'wiki_lookup', 'term': term})

    def _build_extensions(self):
        # World hub: existing commands, inventory and all installed plugin actions.
        l = self.page('06 / WELT & AUFGABEN', 'Die Welt wartet auf dich.', 'Geschichten, Aufgaben, Ausrüstung und die Tiefen der Dungeons.')
        self.world_tabs = QTabWidget()
        self.world_tabs.setStyleSheet('QTabWidget::pane{border:1px solid #294562;border-radius:10px;} QTabBar::tab{padding:12px 20px;background:#102743;color:#b9cbde;} QTabBar::tab:selected{background:#234768;color:#f3deb0;}')
        from gui.quest_log import QuestLog
        self.quest_log = QuestLog()
        self.quest_log.command_requested.connect(self.execute)
        self.controls.append(self.quest_log.accept)
        self.world_tabs.addTab(self.quest_log, '📜 Questlog')
        w, c = card()
        self.command_page = w
        c.addWidget(label('Entdecke deine Möglichkeiten', 'heading'))
        c.addWidget(label('Kategorie öffnen, Aktion auswählen und ausführen.', 'muted'))
        self.command_filter = QLineEdit()
        self.command_filter.setPlaceholderText('Befehle durchsuchen …')
        self.command_filter.textChanged.connect(self.filter_commands)
        c.addWidget(self.command_filter)
        from gui.command_menu import CommandMenu
        self.command_tree = CommandMenu()
        self.command_tree.chosen.connect(self.choose_command)
        c.addWidget(self.command_tree)
        self.command_combo = QComboBox()
        self.command_combo.setParent(w)
        self.command_combo.hide()
        self.command_combo.currentIndexChanged.connect(self.command_description)
        self.command_help = label('Wähle eine Aktion aus den Untermenüs.', 'muted')
        self.command_help.setWordWrap(True)
        self.arguments = QLineEdit()
        self.arguments.setPlaceholderText('Zusätzliche Angaben, falls benötigt – z. B. ein Suchbegriff')
        self.command_run = button('Ausgewählte Aktion ausführen', self.run_selected)
        self.controls.append(self.command_run)
        for item in (self.command_help,self.arguments,self.command_run):c.addWidget(item)
        self.world_tabs.addTab(w, '⌘ Spielaktionen')
        self.world_output = QTextBrowser()
        self.world_output.document().setMaximumBlockCount(500)
        from gui.reading_style import large_transcript
        large_transcript(self.world_output)
        self.world_tabs.addTab(self.world_output, '✦ Ergebnisse')
        from gui.shop import Shop
        self.shop = Shop()
        self.shop.purchase_requested.connect(self.buy_shop_item)
        shop_scroll = QScrollArea()
        shop_scroll.setWidgetResizable(True)
        shop_scroll.setWidget(self.shop)
        self.world_tabs.addTab(shop_scroll, '🏪 Shop')
        from gui.achievements import Achievements
        self.achievements = Achievements()
        self.world_tabs.addTab(self.achievements, '🏆 Erfolge')
        from gui.monster_catalog import MonsterCatalog
        self.monster_catalog = MonsterCatalog()
        self.monster_tab = self.world_tabs.addTab(self.monster_catalog, '🔒 Monster · Level 50')
        self.world_tabs.setTabEnabled(self.monster_tab, False)
        l.addWidget(self.world_tabs)
        nav = self.centralWidget().layout().itemAt(0).widget().layout()
        b = button('📜   Questlog & Aktionen', lambda: self.navigate(5))
        b.setCheckable(True)
        nav.insertWidget(8, b)
        self.nav_buttons.append(b)
        self.game_hall_button=button('🎮   Spielhalle', self.open_game_hall)
        self.game_hall_button.setCheckable(True)
        nav.insertWidget(9,self.game_hall_button)
        self.memories_button=button('🔒   Erinnerungen', self.open_memories)
        self.memories_button.setCheckable(True)
        nav.insertWidget(10,self.memories_button)
        self.dungeon_button=button('🏰   Dungeons',self.open_dungeons)
        self.dungeon_button.setCheckable(True)
        nav.insertWidget(nav.indexOf(self.nav_buttons[2])+1,self.dungeon_button)
        self.guide_button=button('🔒   Guide · 0/20',self.open_maat_guide)
        self.guide_button.setCheckable(True)
        nav.insertWidget(nav.indexOf(self.nav_buttons[3])+1,self.guide_button)
        self.talent_button = button('🔒   Talentbaum', self.open_talents)
        self.talent_button.setCheckable(True)
        nav.insertWidget(nav.indexOf(self.nav_buttons[1])+1, self.talent_button)
        # Decisions remain visible even when inspecting another page.
        self.decision, c = card()
        self.prompt_label = label('', 'heading')
        c.addWidget(self.prompt_label)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setMaximumHeight(145)
        choices = QWidget()
        self.choice_layout = QGridLayout(choices)
        area.setWidget(choices)
        c.addWidget(area)
        self.answer = QLineEdit()
        self.answer.setPlaceholderText('Eigene Eingabe / Bestätigung …')
        self.answer.returnPressed.connect(self.answer_prompt)
        row = QHBoxLayout()
        row.addWidget(self.answer, 1)
        row.addWidget(button('Weiter / Antworten', self.answer_prompt, True))
        c.addLayout(row)
        self.decision.hide()
        content = self.centralWidget().layout().itemAt(1).layout()
        content.insertWidget(content.count()-1, self.decision)
        self.reveal_button = button('Text sofort anzeigen', self.text_stream.finish)
        content.insertWidget(content.count()-1, self.reveal_button)
        self.reveal_button.hide()
        from gui.intro_screen import IntroScreen
        self.intro = IntroScreen()
        self.stack.addWidget(self.intro)
        self.intro.completed.connect(self.intro_finished)
        self.intro.audio_requested.connect(self.audio.handle_event)

    def append_encounter_text(self,text):
        self.journal.moveCursor(QTextCursor.End)
        self.journal.insertPlainText(text)
        self.journal.ensureCursorVisible()

    def start_encounter_intro(self):
        if not self._encounter_intro or self._encounter_started or self.text_stream.running:return
        self._encounter_started=True
        self.navigate(3)
        self.append_encounter_text('\n\n')
        text='Ein Wesen erscheint …' if self.game.get_snapshot().language=='de' else 'A creature appears …'
        self.encounter_stream.append(text)
        self.reveal_button.hide()
        self.update_controls()

    def finish_encounter_intro(self):
        self.append_encounter_text('\n')
        self._encounter_intro=False
        self._encounter_started=False
        self.game.release_encounter()
        self.update_controls()

    def cancel_encounter_intro(self):
        self._encounter_intro=False
        self._encounter_started=False
        if hasattr(self,'encounter_stream'):
            self.encounter_stream.clear();self.encounter_pause.stop()

    def receive(self, event):
        if event.get('event') == 'language_required':
            self.show_language_choice()
            return
        try:
            self._receive_event(event)
        finally:
            if hasattr(self, 'language_screen') and event.get('event') not in ('output', 'diagnostic', 'battle_effect', 'chat_response'):
                self.apply_menu_language()

    def _receive_event(self, event):
        kind = event.get('event')
        if hasattr(self, 'model_timing') and not (kind=='chat_first_token' and self._chat_cancel_requested):
            self.model_timing.handle(event)
        if kind == 'class_selection':
            self._class_choice_pending = True
            self._class_return_index = 3 if self._battle_return_source == 'random' or self._return_to_chat else self.stack.currentIndex()
            self._return_to_chat = False
            self._chat_return_timer.stop()
            self._pending_class_event = event
            self._class_timer.start()
            self.present_class_selection()
            self.update_controls()
            return
        if kind in ('class_selected', 'class_error'):
            if self.phase != 'class_selection' or event.get('id') != self.class_selection.request_id:
                return
            if kind == 'class_error':
                self.class_selection.show_error(event.get('text', 'Die Klasse konnte nicht gespeichert werden.'))
            else:
                self._class_choice_pending = False
                self.apply_hero_class(event['value'])
                self.phase = 'playing'
                self.navigate(self._class_return_index)
                self.update_controls()
            return
        if kind=='encounter_intro':
            if self.phase != 'playing':
                self.game.release_encounter()
                return
            self._encounter_intro=True
            self.arena.clear_opponent()
            self._battle_presenting=False
            self.start_encounter_intro()
            return
        if (kind in ('prompt', 'story_scene', 'battle_presentation') or (kind == 'busy' and not event.get('value'))) and self.text_stream.running:
            self._deferred.append(event)
            self.update_controls()
            return
        if kind == 'battle_presentation':
            self.game.release_battle_presentation()
            return
        if kind == 'dungeons' and hasattr(self,'dungeons'):
            self.character_sidebar.update_dungeons(event.get('records',{}),event.get('plus',{}))
            self.dungeons.update_data(event.get('level',1),event.get('records',{}),event.get('plus',{}))
        if kind == 'dungeon_progress':
            self._dungeon_active=event.get('active',False)
            self._dungeon_return=not self._dungeon_active
            self.dungeons.progress.setText((self.ui('Dungeon+ · Welle {room} · ∞',room=event['room']) if event.get('total') is None else self.ui('{name} · Raum {room}/5',name=event['name'],room=event['room'])) if self._dungeon_active else self.ui('Durchlauf beendet · Wähle deine nächste Expedition.'))
            self.update_controls()
        if kind == 'stopped':
            self._dungeon_active=False
            self._dungeon_return=False
            if hasattr(self, 'talent_tree') and self.talent_tree.submitted:
                self.talent_tree.result('Spielverbindung beendet. Der gespeicherte Stand wird beim Neustart geprüft.', False)
        if kind == 'story_scene':
            self.begin_story_scene(event)
        if kind == 'model_safety':
            self._model_safety_report = event['data']
            self.refresh_model_safety()
        if kind == 'model_error':
            self._model_error_pending=True
            self._auto_model_pending=False
            self._startup_model_attempted=True
            self._startup_model_failed=True
            self.model_error.setText(event.get('text','Das Modell konnte nicht geladen werden.'))
            self.model_error.setToolTip(event.get('detail',''))
            self.model_error.setStyleSheet('color:#ffc0b5;background:#3b2230;padding:12px;border-radius:8px;font-size:16px;')
        if kind == 'hardware':
            self._model_safety_report = None
            self.refresh_model_safety()
            h = event['data']
            mode = self.ui('Manuell' if h.get('mode') == 'manual' else 'Auto · Standard')
            self.hardware_status.setText(self.ui('Geladen: {mode} · {platform} · {acceleration}\n{threads} Threads für Antworten · {batch} beim Einlesen',
                mode=mode, platform=h['platform'], acceleration=h['acceleration'], threads=h['threads'], batch=h['threads_batch']))
            notes = []
            if 'gpu_unavailable' in h.get('adjustments', []):
                notes.append(self.ui('Keine GPU-Auslagerung verfügbar · CPU wird verwendet.'))
            if 'batch_capped' in h.get('adjustments', []):
                notes.append(self.ui('Die Batchgröße wurde auf die Kontextgröße begrenzt.'))
            if 'intel_repack_unavailable' in h.get('adjustments', []):
                notes.append(self.ui('Diese KI-Bibliothek bietet keine Repacking-Steuerung. Ihre nativen Vorgaben bleiben aktiv.'))
            if notes:
                self.hardware_status.setText(self.hardware_status.text() + '\n' + '\n'.join(notes))
        if kind == 'diagnostic':
            self._technical_log = (getattr(self, '_technical_log', '') + event.get('text',''))[-32000:]
            self.model_status.setToolTip(self._technical_log)
        if kind == 'minigame_started':
            self._minigame_grant=event.get('data')
        if kind == 'minigame':
            from shared.core.minigames import CATALOG
            self._discovered_games=[k for k in event.get('data',{}).get('discovered',[]) if k in CATALOG]
            self._arcade_highscores=event.get('data',{}).get('highscores',{})
            if hasattr(self,'game_hall'):self.game_hall.update_discoveries(self._discovered_games,self._arcade_highscores)
            self._minigame_offer = event.get('data', {}).get('pending')
            self.minigame_card.setVisible(bool(self._minigame_offer))
            self.refresh_minigame_offer()
            self.update_controls()
        if kind == 'minigame_result':
            self.journal.append(event.get('text', ''))
        if kind == 'shop':
            self.shop.update_data(event['data'])
        if kind == 'shop_result':
            self.shop.set_receipt(event.get('text',''))
        if kind == 'achievements':
            self.achievements.update_data(event['data'])
            self.character_sidebar.update_achievements(event['data'])
        if kind == 'quests':
            self.quest_log.update_data(event['data'])
            self.character_sidebar.update_quests(event['data'])
        if kind == 'talents':
            previous = self._talent_data
            self._talent_data = event['data']
            if hasattr(self, 'talent_tree'): self.talent_tree.update_data(event['data'])
            if self.phase == 'playing' and event['data'].get('unlocked'):
                if not previous.get('unlocked'):
                    self.footer.setText(self.ui('✦ Talentbaum freigeschaltet · {points} Punkte warten auf dich!',points=event['data']['available']))
                elif event['data']['earned'] > previous.get('earned', 0):
                    self.footer.setText(self.ui('✦ +{points} Talentpunkte · Öffne deinen Talentbaum.',points=event['data']['earned']-previous.get('earned',0)))
            self.update_controls()
        if kind == 'talent_result' and hasattr(self, 'talent_tree'):
            self.talent_tree.result(event.get('text', ''), event.get('ok', False))
        if kind == 'companion':
            self.companion_panel.update_state(event['data'])
        if kind == 'battle_editor_result' and hasattr(self, 'battle_editor'):
            if event.get('profile_slot') == self.game._profile_slot():
                if event.get('ok'):
                    self.battle_editor.set_entries(event.get('items', []), event.get('selected'))
                    self.battle_editor.result({'battle_editor_save':'Monster gespeichert.', 'battle_editor_play':'Testkampf beendet.'}.get(event.get('op'), 'Erst speichern, dann kämpfen.'))
                else:
                    self.battle_editor.result(event.get('error', 'editor_io'))
                    if event.get('op') == 'battle_editor_play':
                        self._return_to_chat = True
                        self._battle_return_source = 'editor'
        if kind == 'profile':
            self._editor_unlocked = int(event['data'].get('final_wins', 0)) >= 5
            previous_messages = self._guide_messages
            self._guide_messages=max(0,int(event['data'].get('chat_messages',0)))
            if previous_messages < 5 <= self._guide_messages:
                self._history_unlock_pending = True
            if hasattr(self,'maat_guide'):self.maat_guide.set_count(self._guide_messages)
            if hasattr(self,'memories'):self.memories.set_count(self._guide_messages)
            self.guide_button.setText('✦   MAAT-Guide' if self._guide_messages>=20 else f'🔒   Guide · {self._guide_messages}/20')
            self.update_controls()
            self._combat_unlocked = bool(event['data'].get('combat_unlocked', False))
            self._class_choice_pending = bool(event['data'].get('class_choice_pending', False))
            self.apply_hero_class(event['data'].get('hero_class', 'normal'))
            self._boss_progress = int(event['data'].get('boss_progress', 0))
            self.character_sidebar.update_profile(event['data'])
            if hasattr(self,'terra_view') and event['data'].get('journey'):
                self.terra_view.update_data(event['data']['journey'])
                self.update_title_artwork(event['data']['journey'])
        if kind == 'terra_replay_result':
            self.terra_view.replay_result(event.get('text',''),event.get('ok',False))
        if kind == 'terra_credits_error':
            self.terra_view.replay_result(event.get('text',''),False)
        if kind == 'chat_archived' and hasattr(self,'memories_index') and self.stack.currentIndex()==self.memories_index:
            self.memories.refresh()
        if kind == 'wiki_context':
            self.update_wiki_source(event)
        if kind == 'wiki_result':
            self.wiki_settings.result.setPlainText(event.get('text', ''))
        if kind == 'level_progress':
            self._last_xp_gain = event.get('gain')
            self.update_chat_level(event['level'], event['xp'], event['next_xp'])
        if kind == 'level_up':
            diagnostic('level_up_notice', level=event.get('level'), phase=self.phase)
            if self.phase == 'playing':
                summary = self.level_up_notice.present(event)
                self._receive_event({'event': 'output', 'text': '\n' + summary + '\n'})
            return
        if kind == 'chat_generation':
            self._ki_reply_streaming = True
            self.footer.setText(self.ui('KI antwortet · Esc: abbrechen, ohne Chatfortschritt zu zählen.'))
            self.reveal_button.hide()
            self.update_controls()
            self.request_chat_focus()
        if kind == 'chat_response':
            if self.phase == 'playing' and not self._chat_cancel_requested:
                from gui.chat_response import ChatResponse
                if not hasattr(self, '_chat_response'):
                    self._chat_response = ChatResponse([self.journal, self.world_output],
                        formatting=lambda: session_shared.load_profile_settings(self.game._profile_slot()).get('response_formatting_enabled', True))
                self.text_stream.mark(lambda event=dict(event): self._chat_response.handle(event))
            return
        if kind == 'chat_generated':
            if not self._chat_cancel_requested:
                self._chat_generated_id = event.get('turn_id')
                if not self.text_stream.running:
                    self.confirm_chat_presented()
            return
        if kind == 'chat_cancelled':
            self._chat_generated_id = None
            self.text_stream.clear()
            self.present_text('\n' + (event.get('text') or self.ui('⏹ Antwort abgebrochen · Diese Nachricht zählt nicht zum Fortschritt.')) + '\n')
            return
        if kind == 'output' and self._chat_cancel_requested:
            return
        if kind in {'output', 'notice', 'error'}:
            text = event.get('text', '')
            if kind == 'error':
                self.model_error.setText(text)
            if kind in {'notice', 'error'}:
                text = '\n' + ('⚠ ' if kind == 'error' else '') + text + '\n'
            if self.phase == 'playing':
                # Capture the destination when output arrives. A queued chat
                # fragment must not become combat text when the HUD changes.
                combat = event.get('combat', self._battle_active)
                self.text_stream.mark(lambda combat=combat: setattr(self, '_presenting_combat_text', combat))
                self.text_stream.append(text)
                self.text_stream.mark(lambda: setattr(self, '_presenting_combat_text', False))
                self.update_reading_controls()
                self.update_controls()
            else:
                self._startup_log = (self._startup_log + text)[-32000:]
            if kind == 'error':
                self.footer.setText(text.strip())
        elif kind == 'prompt':
            self._arena_choices = event.get('choices', [])
            if self._pending_principle and self._battle_active:
                key, self._pending_principle = self._pending_principle, None
                self.arena_action(key)
                if not self._arena_choices:
                    return
            self.prompt_label.setText(event.get('text', 'Entscheidung'))
            while self.choice_layout.count():
                item = self.choice_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            for i, choice in enumerate(event.get('choices', [])):
                b = button(f"{choice['value']} · {choice['label']}", lambda checked=False, v=choice['value']: self.game.submit_choice(v))
                self.choice_layout.addWidget(b, i//3, i%3)
            self.answer.clear()
            standard = self.update_arena_actions()
            self.decision.setVisible(not (self._battle_active and standard and self.stack.currentIndex() == 2))
            if self.decision.isVisible():
                self.answer.setFocus()
            self.footer.setText(self.ui('Deine Entscheidung ist gefragt.'))
        elif kind == 'prompt_closed':
            self._arena_choices = []
            self.update_arena_actions()
            self.decision.hide()
        elif kind == 'commands':
            self.command_items = event['items']
            self.filter_commands()
        elif kind == 'models':
            saved_tuning = session_shared.load_profile_settings(self.game._profile_slot()).get('gui_model_tuning')
            if saved_tuning is None:
                saved_tuning = (event.get('performance') or {}).get('model_tuning')
            self.model_tuning.restore(saved_tuning)
            self.model_combo.clear()
            self.model_combo.addItems(event.get('items', []))
            self.chat_model_combo.clear()
            self.chat_model_combo.addItems(event.get('items', []))
            selected = event.get('selected')
            self.saved_model = selected if selected in event.get('items', []) else None
            if self.saved_model:
                self.model_combo.setCurrentText(self.saved_model)
                self.chat_model_combo.setCurrentText(self.saved_model)
                perf = event.get('performance') or {}
                self.context_size.setValue(int(perf.get('n_ctx', 20000)))
                self.temperature.setValue(float(perf.get('temperature', .8)))
                idx = self.backend_combo.findData(perf.get('backend', 'llama'))
                if idx >= 0:
                    self.backend_combo.setCurrentIndex(idx)
            if not event.get('items'):
                self.model_status.setText(self.ui('Keine lokalen Modelle gefunden. Die Spielaktionen funktionieren auch ohne KI.'))
                self.chat_model_status.setText(self.ui('Kein Modell gefunden. Im Hauptmenü unter KI & Modelle eine GGUF-Datei auswählen.'))
            self.update_rpg_context_option()
            if event.get('previous_load_attempt'):
                self._receive_event({'event':'model_error', 'text':self.ui('Der letzte Modellladeversuch wurde nicht erfolgreich abgeschlossen. Automatisches Laden ist gestoppt. Prüfe Modell und Einstellungen und starte das Laden bewusst erneut.'), 'detail':str(event['previous_load_attempt'])})
        elif kind == 'model':
            states = {'loading': 'Modell wird geladen …', 'ready': 'KI bereit', 'unloaded': 'Kein Modell geladen'}
            self.model_ready = event['status'] == 'ready'
            if self.model_ready:
                self._startup_model_failed=False
            if self.phase == 'title':
                if event['status'] == 'loading':
                    self.title_screen.set_model_state('loading')
                    self.title_idle.stop()
                elif self.model_ready:
                    self._startup_model_failed=False
                    self.title_screen.set_model_state('ready')
                    self.ki_dialog.hide()
                    self.title_idle.start(20000)
                else:
                    self._startup_model_failed=self._startup_model_attempted
                    self.title_screen.set_model_state('error' if self._startup_model_failed else 'choose')
            self.loaded_model_architecture = event.get('architecture', '') if self.model_ready else ''
            self.loaded_model_family = event.get('family', '') if self.model_ready else ''
            if self.model_ready and event.get('name'):
                self.saved_model = event['name']
                self.chat_model_combo.setCurrentText(self.saved_model)
            status = self.ui(states.get(event['status'], event['status'])) + (' · ' + event['name'] if event.get('name') else '')
            self.model_status.setText(status)
            if self.chat_model_combo.count() or event['status'] != 'unloaded':
                self.chat_model_status.setText(status)
            self.update_rpg_context_option()
            self.chat_model_panel.setVisible(not self.model_ready)
            self.update_controls()
        elif kind == 'battle_effect':
            self.arena.stage.show_effect(event)
        elif kind == 'audio':
            owner = event.get('owner')
            if event.get('action') == 'stop' and self.text_stream.running:
                self._audio_stops[owner] = event
            else:
                if event.get('action') == 'play':
                    self._audio_stops.pop(owner, None)
                elif event.get('action') == 'clear':
                    self._audio_stops.clear()
                self.audio.handle_event(event)
        elif kind == 'scene':
            self.navigate(3)
        elif kind == 'navigate':
            self.navigate(event['page'])
        elif kind == 'stopped':
            self._pending_class_event = None
            self._class_timer.stop()
            self._companion_after_class = False
            if self._active_minigame:
                self.discard_minigame()
                self.navigate(3)
            self.text_stream.clear()
            self.cancel_encounter_intro()
            self._ki_reply_streaming = False
            self._chat_turn_active = False
            self.reveal_button.hide()
            self._return_to_chat = False
            self._chat_return_timer.stop()
            self._audio_stops.clear()
            self._deferred.clear()
            self.intro.cancel()
            if hasattr(self, 'story_screen'):
                self.story_screen.cancel()
                self.credits_screen.cancel()
            self.model_ready = False
            self.phase = 'menu'
            self._started = False
            self.navigate(0)
            self.decision.hide()
            self.audio.handle_event({'action': 'clear'})
            self.footer.setText('Spielverbindung wird nach Modell-Ladefehler wiederhergestellt …' if event.get('model_load_failed') else 'Spielverbindung beendet. Neustart unter Einstellungen möglich.')
        if kind in {'busy', 'ready', 'prompt', 'prompt_closed', 'stopped', 'error'}:
            self.update_controls()
        if kind == 'ready':
            if self._model_error_pending:
                self._model_error_pending=False
                QTimer.singleShot(0,self.open_models)
            QTimer.singleShot(0, self.prepare_startup_model)
            self.footer.setText(self.ui('Wähle „Spiel starten“, um deine Reise zu beginnen.'))
            if self._start_on_ready:
                self._start_on_ready = False
                self.begin_game()
        elif kind == 'busy' and not event.get('value'):
            self._chat_cancel_requested = False
            self._chat_generated_id = None
            if self._companion_after_class and not self._class_choice_pending and self.phase == 'playing':
                self._companion_after_class = False
                QTimer.singleShot(0, lambda: self.game.send_text('/ai-start'))
            chat_finished = self._chat_turn_active or self._ki_reply_streaming
            self._ki_reply_streaming = False
            self._chat_turn_active = False
            self.footer.setText(self.ui('RPG bereit · Wähle deinen nächsten Schritt.'))
            if self._minigame_grant:
                QTimer.singleShot(0,self.run_minigame_attempt)
            if self._model_error_pending:
                self._model_error_pending=False
                QTimer.singleShot(0,self.open_models)
            if self.phase == 'title':
                QTimer.singleShot(0,self.prepare_startup_model)
            if chat_finished:
                self.request_chat_focus()

    def open_sidebar_link(self,destination,identifier=''):
        if self.phase!='playing' or self._active_minigame or self._encounter_intro:return
        page={'character':1,'shop':5,'achievements':5,'category':5,'achievement':5,'dungeons':self.dungeon_index}.get(destination)
        if page is None:return
        self.navigate(page)
        if self.stack.currentIndex()!=page:return
        if destination=='shop':self.world_tabs.setCurrentIndex(3)
        elif destination in ('achievements','category','achievement'):
            self.world_tabs.setCurrentWidget(self.achievements)
            self.achievements.search.clear();self.achievements.status.setCurrentIndex(0)
            self.achievements.select_category(identifier if destination=='category' else '')
            if destination=='achievement' and identifier in self.achievements.rows:
                card=self.achievements.rows[identifier][0]
                self.achievements.scroll.ensureWidgetVisible(card)
            else:self.achievements.scroll.verticalScrollBar().setValue(0)

    def open_sidebar_quest(self,identifier=''):
        if self.phase!='playing' or self._active_minigame or self._encounter_intro:return
        self.navigate(5)
        if self.stack.currentIndex()!=5:return
        self.world_tabs.setCurrentWidget(self.quest_log)
        self.quest_log.select_quest(identifier)

    def open_talents(self):
        if self.talent_button.isEnabled(): self.navigate(self.talent_index)

    def open_talent_quests(self):
        self.open_sidebar_quest()
        if self.stack.currentIndex() == 5:
            self.quest_log.category.setCurrentIndex(self.quest_log.category.findData('combat'))

    def purchase_talent(self, request):
        if not self.talent_button.isEnabled() or self.game.busy:
            self.talent_tree.result('Bitte die aktuelle Aktion beenden.', False)
            return
        self.game.busy = True
        self.update_controls()
        self.game.write(dict(request, op='talent_buy', profile_slot=self.game._profile_slot()))

    def open_maat_guide(self):
        if self.guide_button.isEnabled() and self._guide_messages>=20:self.navigate(self.guide_index)

    def open_dungeons(self):
        if self.dungeon_button.isEnabled():self.navigate(self.dungeon_index)

    def enter_dungeon_plus(self):
        if self.dungeon_button.isEnabled() and self.game.get_snapshot().player.level>=50:
            self.game.send_command('/dungeon-plus')

    def enter_dungeon(self,index):
        from shared.core.dungeon_campaign import dungeon
        if not self.dungeon_button.isEnabled() or self.game.get_snapshot().player.level<dungeon(index)['level']:return
        self.game.send_command(f'/dungeon-enter {index}')

    def open_monster_catalog(self):
        if not self.world_tabs.isTabEnabled(self.monster_tab):return
        self.navigate(5)
        if self.stack.currentIndex()==5:self.world_tabs.setCurrentWidget(self.monster_catalog)

    def open_memories(self):
        if self.memories_button.isEnabled():self.navigate(self.memories_index)

    def show_history_unlock(self):
        if (not self._history_unlock_pending or self._guide_messages < 5
                or not hasattr(self,'memories') or not self.memories.store
                or self.phase != 'playing' or self.stack.currentIndex() != 3
                or not self.game.ready or self.game.busy or self.text_stream.running
                or self._deferred or self._battle_active or self._encounter_intro
                or self._active_minigame or self._dungeon_active or self.game.prompt_id):
            return
        try:
            announce = self.memories.store.claim_unlock_notice()
        except (OSError, sqlite3.Error):
            return  # Retry after the next state update; do not consume the notice.
        self._history_unlock_pending = False
        if announce:
            self.journal.append(self.ui('<p style="color:#eed49c"><b>🔓 Verlauf freigeschaltet!</b><br>'
                                'Nach fünf Nachrichten ist dein Gesprächsarchiv geöffnet. '
                                'Im Tab „Erinnerungen“ kannst du nach Tagen, Monaten und Jahren stöbern '
                                'und einzelne Nachrichten oder Tagesverläufe löschen.</p>'))

    def can_compose_chat(self):
        blocked = (self._pending_class_event or self._active_minigame or self._battle_active or self._encounter_intro
                   or self._dungeon_active or self.game.prompt_id
                   or any(e.get('event') in ('prompt', 'story_scene', 'battle_presentation') for e in self._deferred))
        return (self.game.ready and self.phase == 'playing' and not blocked
                and (not self.game.busy or self._chat_turn_active or self._ki_reply_streaming or self.text_stream.running))

    def request_chat_focus(self, force=False):
        if not hasattr(self, '_chat_focus_timer'):
            return
        self._chat_focus_force = self._chat_focus_force or force
        if not self._chat_focus_timer.isActive():
            self._chat_focus_timer.start(0)

    def focus_chat_input(self):
        force, self._chat_focus_force = self._chat_focus_force, False
        if (not self.can_compose_chat() or self.stack.currentIndex() != 3
                or not self.input.isVisible() or not self.input.isEnabled()
                or QApplication.activeModalWidget() or QApplication.activePopupWidget()):
            return
        active = QApplication.activeWindow()
        if active is not None and active is not self:
            return
        focus = QApplication.focusWidget()
        if (not force and focus is not self.input and isinstance(focus, (QLineEdit, QComboBox))
                and focus.isVisible()):
            return  # Do not interrupt model selection or a decision being edited.
        self.input.setFocus(Qt.OtherFocusReason)
        self.stack.widget(3).ensureWidgetVisible(self.input, 0, 12)

    def update_controls(self):
        self.era.setVisible(self.phase not in ('profiles', 'language'))
        if hasattr(self,'terra_view'):self.terra_view.set_replay_ready(self.terra_replay_ready())
        self.character_sidebar.terra_map.setEnabled(self.phase=='playing' and not (
            self._battle_active or self._active_minigame or self._encounter_intro
            or self._dungeon_active or self._pending_class_event))
        ready = not self._pending_class_event and not self._active_minigame and self.game.ready and not self.game.busy and not self.text_stream.running and not self._deferred and not self._encounter_intro
        if hasattr(self, 'editor_button'):
            self.editor_button.setVisible(self._editor_unlocked)
            self.editor_button.setEnabled(ready and self.phase == 'menu' and not self.game.prompt_id)
        if hasattr(self, 'battle_editor'):
            self.battle_editor.set_ready(ready and self._editor_unlocked and not self._battle_active and not self.game.prompt_id)
        for control in self.controls:
            control.setEnabled(ready and self.phase == 'playing')
        dungeon_ready=ready and self.phase=='playing' and not self._battle_active and not self.game.prompt_id and not self._dungeon_active
        talent_unlocked = self._hero_class != 'normal' and self._talent_data.get('unlocked', False)
        self.talent_button.setEnabled(dungeon_ready and talent_unlocked)
        free = self._talent_data.get('available', 0)
        self.talent_button.setText(self.ui(f'✦   Talente · {free} TP' if talent_unlocked else '🔒   Talentbaum'))
        self.talent_button.setToolTip(self.ui('Klassentalente ansehen und lernen' if talent_unlocked else 'Nach dem ersten Kampf eine Klasse wählen.'))
        if hasattr(self, 'talent_tree'): self.talent_tree.set_ready(dungeon_ready and talent_unlocked)
        self.guide_button.setEnabled(dungeon_ready and self._guide_messages>=20)
        self.guide_button.setToolTip('MAAT verstehen und eine Situation reflektieren' if self._guide_messages>=20 else 'Wird nach 20 Chatnachrichten freigeschaltet.')
        self.memories_button.setEnabled(dungeon_ready and self._guide_messages>=5)
        if hasattr(self,'memories'):
            self.memories.saves.set_editable(dungeon_ready and self._guide_messages>=5)
        self.memories_button.setText('◈   Erinnerungen' if self._guide_messages>=5 else '🔒   Erinnerungen')
        self.memories_button.setToolTip('Chatverlauf nach Tag, Monat und Jahr' if self._guide_messages>=5 else f'Wird nach fünf Chatnachrichten freigeschaltet. · {self._guide_messages}/5')
        self.dungeon_button.setEnabled(dungeon_ready)
        if hasattr(self,'dungeons'):self.dungeons.set_ready(dungeon_ready)
        if self._dungeon_return and ready and self.phase=='playing':
            self._dungeon_return=False
            self.navigate(self.dungeon_index)
        monster_level=self.game.get_snapshot().player.level
        monster_unlocked=monster_level>=50
        self.monster_catalog.set_level(monster_level)
        if not monster_unlocked and self.world_tabs.currentIndex()==self.monster_tab:self.world_tabs.setCurrentIndex(0)
        self.world_tabs.setTabEnabled(self.monster_tab,monster_unlocked)
        self.world_tabs.setTabText(self.monster_tab,self.ui('✦ Monsterkatalog' if monster_unlocked else '🔒 Monster · Level 50'))
        arena_unlocked = getattr(self, '_combat_unlocked', False)
        self.start_battle.setEnabled(ready and self.phase == 'playing' and arena_unlocked)
        self.companion_panel.fight.setEnabled(ready and self.phase == 'playing' and arena_unlocked)
        self.nav_buttons[2].setEnabled(arena_unlocked or self._battle_active)
        self.nav_buttons[2].setToolTip('Arena · halbe Kampf-EP' if arena_unlocked else 'Wird mit dem Zufallskampfmodus freigeschaltet.')
        self.arena_progress.setText(self.ui('Boss-Fortschritt: {progress}/20 · Zufallssieg +2 · Arenasieg +1 · Arena: ½ Kampf-EP',progress=getattr(self,'_boss_progress',0)))
        self.start_battle.setToolTip(self.ui('Boss-Fortschritt: {progress}/20 · Zufallssieg +2 · Arenasieg +1',progress=getattr(self,'_boss_progress',0)))
        self.shop.set_ready(ready and self.phase == 'playing' and not self._battle_active)
        self.game_hall_button.setEnabled(ready and self.phase == 'playing' and not self._battle_active and not self.game.prompt_id)
        if hasattr(self,'game_hall'):self.game_hall.set_ready(self.game_hall_button.isEnabled())
        mini_ready = ready and self.phase == 'playing' and not self._battle_active and not self.game.prompt_id and bool(self._minigame_offer)
        self.minigame_play.setEnabled(mini_ready and self._minigame_offer.get('attempts',0)<2)
        self.minigame_skip.setEnabled(mini_ready)
        self.command_run.setEnabled(ready and self.phase == 'playing' and self.command_combo.currentData() is not None)
        self.menu_pyramid.setEnabled(ready and self.phase == 'menu')
        self.begin_button.setEnabled(ready and self.phase == 'menu')
        self.perspective.setEnabled(ready and self.phase == 'menu')
        self.companion_panel.setEnabled(ready and self.phase == 'playing')
        self.new_button.setEnabled(ready and self.phase == 'menu')
        self.language_button.setEnabled(ready and self.phase in ('menu', 'playing') and not self.game.prompt_id
                                       and not self._battle_active and not self._dungeon_active)
        self.profile_choice_button.setEnabled(self.can_choose_profile())
        was_editable = self.input.isEnabled()
        editable = self.can_compose_chat()
        self.input.setEnabled(editable)
        self.send_button.setEnabled(ready and editable)
        self.send_button.setToolTip('Nachricht senden · Enter' if ready else 'Die aktuelle Antwort läuft noch. Du kannst schon tippen; dein Entwurf bleibt erhalten.')
        if editable and not was_editable:
            self.request_chat_focus()
        self.chat_load_button.setEnabled(ready and self.chat_model_combo.count() > 0)
        self.options_button.setEnabled(self.phase == 'menu')
        self.load_button.setEnabled(ready and self.phase != 'intro' and self.model_combo.count() > 0)
        self.pick_model_button.setEnabled(ready and self.phase != 'intro')
        self.menu_pick_model.setEnabled(ready and self.phase == 'menu')
        self.chat_pick_model.setEnabled(ready and self.phase == 'playing')
        self.model_combo.setEnabled(ready)
        self.model_tuning.setEnabled(ready)
        self.update_arena_actions()
        self.update_reading_controls()
        self.schedule_chat_return()
        self.restart_button.setEnabled(not self._active_minigame)
        for i in (1,3,4,5):self.nav_buttons[i].setEnabled(not self._active_minigame)
        if self._active_minigame:self.nav_buttons[2].setEnabled(False)
        self.nav_buttons[0].setEnabled(not self._active_minigame and not self.game.busy and not self.text_stream.running)
        if self._focus_chat_after_battle and editable and self.stack.currentIndex()==3:
            self._focus_chat_after_battle=False
            self.request_chat_focus()
        self.show_history_unlock()
        if self.phase == 'class_selection' or self._pending_class_event:
            for control in (*self.nav_buttons, self.restart_button, self.profile_choice_button, self.input, self.send_button):
                control.setEnabled(False)
        if hasattr(self, 'language_screen'):
            self.apply_menu_language()

    def navigate(self, index):
        if self.phase == 'class_selection' or self._pending_class_event:return
        if self._active_minigame:return
        if index == getattr(self, 'talent_index', -1) and not self._talent_data.get('unlocked'): return
        if index==getattr(self,'guide_index',-1) and self._guide_messages<20:return
        if index==getattr(self,'memories_index',-1) and self._guide_messages<5:return
        if index != 3:self._focus_chat_after_battle=False
        if self._encounter_intro and index!=3:return
        if index == 2 and not (getattr(self, '_combat_unlocked', False) or getattr(self, '_battle_active', False) or self.game.get_snapshot().battle.active):
            return
        if self.phase in ('startup', 'language', 'story', 'perspective', 'title', 'title_demo', 'profiles'):
            return
        if self.phase == 'intro' and index != 6:
            return
        if index == getattr(self, 'editor_index', -1) and not self._editor_unlocked: return
        if self.phase == 'menu' and index not in (0, 4, getattr(self, 'editor_index', -1)):
            return
        if index == 0:
            if self.phase == 'playing' and (self.game.busy or self.text_stream.running):
                return
            self.game.stop_speech()
            self.phase = 'menu'
            self.level_up_notice.dismiss()
            self.audio.handle_event({'action': 'clear'})
        if index != 2 and not self._battle_active:
            self._return_to_chat = False
            self._chat_return_timer.stop()
        super().navigate(index)
        if hasattr(self,'game_hall_index'):
            self.game_hall_button.setChecked(index==self.game_hall_index)
        if hasattr(self,'dungeon_index'):self.dungeon_button.setChecked(index==self.dungeon_index)
        if hasattr(self,'guide_index'):self.guide_button.setChecked(index==self.guide_index)
        if hasattr(self, 'talent_index'): self.talent_button.setChecked(index==self.talent_index)
        if hasattr(self,'memories_index'):
            self.memories_button.setChecked(index==self.memories_index)
            if index==self.memories_index:self.memories.refresh()
        if self.game.prompt_id and not self.text_stream.running and self._arena_choices:
            self.decision.setVisible(index != 2 or not self.update_arena_actions())
        sidebar = self.centralWidget().layout().itemAt(0).widget()
        sidebar.setVisible(self.phase == 'playing')
        self.character_sidebar.setVisible(self.phase == 'playing' and index not in (
            getattr(self, 'talent_index', -1),getattr(self,'terra_index',-1)))
        self.audio.location(not self.game.needs_language_choice and index in (0, 4, getattr(self, 'editor_index', -1)) and self.phase != 'intro' and not getattr(self, '_battle_active', False), self.game.get_snapshot().language)
        if hasattr(self, 'begin_button'):
            self.begin_button.setText('1   Spiel fortsetzen  →' if self._started else '1   Spiel starten  →')
        if hasattr(self, 'restart_button'):
            self.update_controls()
        if index == 3:
            if hasattr(self, 'chat_activity'): self.chat_activity.acknowledge_if_open()
            self.request_chat_focus(force=True)
            if hasattr(self, '_chat_scroll'):
                self._chat_scroll.schedule()

    def apply_snapshot(self, snapshot):
        if snapshot.battle.active and snapshot.battle.combat_source == 'random' and self.phase == 'playing':
            self._return_to_chat=True
            self._battle_return_source='random'
        if snapshot.battle.active and not self._battle_active:
            random_encounter = snapshot.battle.combat_source == 'random'
            self._battle_return_source=snapshot.battle.combat_source
            self._return_to_chat = self._return_to_chat or (self.phase == 'playing' and (self._editor_return or random_encounter or self.stack.currentIndex() == 3))
            self.encounter_notice.setVisible(random_encounter)
            if random_encounter:
                message = '⚔ Ein Wesen erscheint …' if snapshot.language == 'de' else '⚔ A creature appears …'
                self.encounter_notice.setText(message)
            self._chat_return_timer.stop()
        if not snapshot.battle.active:
            self.encounter_notice.hide()
        for control in self.battle_launch_buttons:
            control.setVisible(not snapshot.battle.active)
        if snapshot.battle.active:
            if not self._battle_active:
                self.battle_log.clear()
                self.arena.pending = ''
                self.arena.stage.clear_effects()
            self._battle_presenting = True
        from dataclasses import asdict
        state = asdict(snapshot.battle)
        state.update(player_hp=snapshot.player.hp, player_max_hp=snapshot.player.max_hp, player_level=snapshot.player.level)
        self.arena.update_state(state)
        super().apply_snapshot(snapshot)
        if self._xp_profile != snapshot.profile_name:
            self._xp_profile = snapshot.profile_name
            self._last_xp_gain = None
        self.update_chat_level(snapshot.player.level, snapshot.player.xp, snapshot.player.next_xp)
        self.character_sidebar.update_player(snapshot.player)
        self.update_controls()
        # Profile-name/status refreshes stay on the profile menu and must keep
        # its current track playing, just like the title and settings pages.
        self.audio.location(not self.game.needs_language_choice and (self.phase in ('title', 'profiles') or self.stack.currentIndex() in (0, 4, getattr(self, 'editor_index', -1))) and self.phase not in ('startup', 'intro', 'language') and not snapshot.battle.active, snapshot.language)

    def update_chat_level(self, level, xp, next_xp):
        need = max(1, int(next_xp))
        pct = max(0, min(100, xp / need * 100))
        gain = f'   (+{self._last_xp_gain} XP)' if self._last_xp_gain and self._last_xp_gain > 0 else ''
        self.chat_level_text.setText(f'📘 Level {level}   ·   {pct:.1f}%   ·   XP: {xp}/{need}{gain}')
        self.chat_xp_bar.setRange(0, 1000)
        self.chat_xp_bar.setValue(round(pct * 10))

    def can_return_to_chat(self):
        if self._pending_class_event:
            return False
        if not (self._return_to_chat and self.phase == 'playing' and not self._battle_active
                and not self._encounter_intro and self.stack.currentIndex() == 2):
            return False
        if self._battle_return_source == 'random':
            # The same chat request may still be generating a reply after the fight.
            # Return to its chat instead of waiting there for the entire LLM stream.
            return not self.game.prompt_id and not any(e.get('event')=='story_scene' for e in self._deferred)
        return not self.game.busy and not self.game.prompt_id and not self.text_stream.running and not self._deferred

    def schedule_chat_return(self):
        if self.can_return_to_chat():
            if not self._chat_return_timer.isActive():
                self._chat_return_timer.start()
        else:
            self._chat_return_timer.stop()

    def return_from_battle(self):
        if self.can_return_to_chat():
            self._return_to_chat=False
            self._battle_presenting=False
            if self._editor_return:
                self._editor_return = False
                self.phase = 'menu'
                self.navigate(self.editor_index)
                return
            self._focus_chat_after_battle=True
            self.navigate(3)
            self.input.setFocus()

    def answer_prompt(self):
        if not self.text_stream.running:
            self.game.submit_choice(self.answer.text())

    def update_reading_controls(self):
        from gui.combat_input import advance_state, focus_narration
        in_arena = self.phase == 'playing' and self.stack.currentIndex() == 2
        self.reveal_button.setVisible(self.phase == 'playing' and not in_arena
                                      and self.text_stream.running and not self._ki_reply_streaming)
        mode = advance_state(self)
        if mode == 'reading' and self.arena._advance_mode != 'reading':
            focus_narration(self)
        self.arena.set_advance_hint(mode)

    def execute(self, command, stay=False):
        if self.phase == 'playing' and self.game.ready and not self.game.busy and not self.text_stream.running:
            native = {'/models':self.open_models, '/model':self.open_models, '/restart':self.restart,
                      '/safe-restart':self.restart, '/exit':self.close, '/menu':lambda:self.navigate(0),
                      '/clear':lambda:(self.journal.clear(), self.world_output.clear())}
            if command in native:
                native[command]()
                return
        if command in ('/erfolge','/ach') and self.phase == 'playing':
            self.navigate(5)
            self.world_tabs.setCurrentWidget(self.achievements)
            self.achievements.select_category('Emotionale Erfolge' if command=='/ach' else '')
            return
        if command in ('/shop', '/contracts') and self.phase == 'playing':
            self.navigate(5)
            self.world_tabs.setCurrentIndex(3)
            self.shop.tabs.setCurrentIndex(1 if command == "/contracts" else 0)
            return
        if command in ('/help', '/quests') and self.phase == 'playing':
            self.navigate(5)
            self.world_tabs.setCurrentIndex(1 if command == '/help' else 0)
            return
        if command == '/intro':
            self.begin_intro()
            return
        if self.phase == 'playing' and self.game.ready and not self.game.busy and not self.text_stream.running:
            if not stay:
                self.navigate(5)
            self.world_output.clear()
            if not stay:
                self.world_tabs.setCurrentIndex(2)
            self.game.send_command(command)

    def buy_shop_item(self, command):
        if not self.game.ready or self.game.busy or self.text_stream.running or self.phase != 'playing' or self._battle_active:
            self.update_controls()
            return
        self.game.send_command(command)

    def send(self):
        if (not self.can_compose_chat() or self.game.busy or self.text_stream.running or self._deferred):
            return
        if self.input.text().strip() in ('/help', '/quests', '/shop', '/contracts', '/models', '/model', '/restart', '/safe-restart', '/exit', '/menu', '/clear'):
            command = self.input.text().strip()
            self.input.clear()
            self.execute(command)
            return
        if self.input.text().strip() == '/intro':
            self.input.clear()
            self.begin_intro()
            return
        if self.perspective.currentData() == 'companion' and not self.input.text().startswith('/'):
            text = self.input.text().strip()
            if not text:
                return
            from gui.ai_companion import validate_reply_length
            try:
                validate_reply_length(text)
            except ValueError as exc:
                self.footer.setText(str(exc))
                return
            choice = self.companion_panel.choice.currentData()
            if self.companion_panel.data.get('scene') and (choice is None or choice < 0):
                self.footer.setText('Wähle eine Entscheidung und schreibe eine kurze Antwort an Maatis.')
                return
            self.journal.moveCursor(QTextCursor.End)
            self.journal.setTextColor(QColor('#dac48e'))
            self.journal.insertPlainText(self.ui('\nDu · Begleiter-KI: ') + text + '\n')
            self.input.clear()
            self._chat_turn_active = True
            self.game.answer_companion(text, choice if choice is not None else -1)
            self.request_chat_focus(force=True)
            return
        if self.input.text().strip() and not self.input.text().lstrip().startswith('/'):
            self._chat_turn_active = True
        super().send()
        self.request_chat_focus(force=True)

    def open_battle_editor(self):
        if (not self._editor_unlocked or not self.game.ready or self.game.busy
                or self.game.prompt_id or self._battle_active or self.text_stream.running
                or self.phase not in ('menu', 'playing')):
            return
        self.game.stop_speech()
        self.phase = 'menu'
        self.battle_editor.preview.set_hero_class(self._hero_class)
        self.navigate(self.editor_index)
        self.editor_request('battle_editor_list')

    def editor_request(self, op, **payload):
        if (not self._editor_unlocked or not self.game.ready or self.game.busy
                or self.game.prompt_id or self._battle_active or self.text_stream.running):
            return
        self.game.write(dict(payload, op=op, profile_slot=self.game._profile_slot()))

    def play_editor_battle(self, mod_id):
        if not self._editor_unlocked or not self.battle_editor.play_button.isEnabled(): return
        self.game.stop_speech()
        self.battle_editor.preview.clear_effects()
        self._editor_return = True
        self.phase = 'playing'
        self.navigate(2)
        self.editor_request('battle_editor_play', mod_id=mod_id)

    def filter_commands(self):
        text = self.command_filter.text().casefold()
        self.command_combo.clear()
        for item in self.command_items:
            # The tree searches translated titles/categories, too. Keep every
            # command in the hidden selection model so those matches can run.
            item = self.command_tree.localized(item)
            self.command_combo.addItem(item['command'], item)
        self.command_tree.populate(self.command_items, text)
        self.command_combo.setCurrentIndex(-1)
        self.command_description()

    def choose_command(self, item):
        if not item:
            self.command_combo.setCurrentIndex(-1)
            self.command_description()
            return
        index = self.command_combo.findText(item["command"])
        if index >= 0:
            self.command_combo.setCurrentIndex(index)
            self.arguments.clear()
            examples = {'/shop':'buy potion 2 oder buy sigil 1', '/quest':'info <Quest-ID> oder accept <Quest-ID>', '/wiki':'Begriff zum Nachschlagen', '/mem search':'Suchbegriff', '/mem6 search':'Suchbegriff', '/say voice':'Name der Stimme', '/bki calc':'H B S V R A DD', '/time topic':'Thema', '/questcheck':'Text, dessen Quest-Bedingungen geprüft werden sollen'}
            self.arguments.setPlaceholderText(self.ui(examples.get(item['command'], 'Zusätzliche Angaben, falls benötigt')))
            self.command_description()

    def command_description(self):
        item = self.command_combo.currentData()
        self.command_help.setText((item['command'] + ' · ' + item['description']) if item else self.ui('Wähle eine Aktion in den Untermenüs.'))
        if hasattr(self,'command_run'):
            self.command_run.setEnabled(bool(item) and self.game.ready and not self.game.busy and not self.text_stream.running and self.phase == 'playing')

    def run_selected(self):
        item = self.command_combo.currentData()
        if item:
            self.execute((item['command'] + ' ' + self.arguments.text().strip()).strip())

    def open_models(self):
        self.ki_dialog.show()
        self.ki_dialog.raise_()
        self.ki_dialog.activateWindow()

    def refresh_plugin_tab(self, index):
        if self.settings_tabs.widget(index) is self.plugin_panel:
            self.plugin_panel.set_language(self.game.get_snapshot().language)
            self.plugin_panel.refresh()

    def pick_model_from_menu(self):
        if self.pick_model():self.open_models()

    def pick_model(self):
        current=Path(self.model_combo.currentText())
        directory=current.parent if current.is_absolute() and current.parent.is_dir() else session_shared.BASE_APP_SUPPORT_DIR/'models'
        filename, _ = QFileDialog.getOpenFileName(self, self.ui('Modell aus Pfad wählen'), str(directory), self.ui('GGUF-Modelle (*.gguf *.GGUF)'))
        if filename:
            for combo in (self.model_combo, self.chat_model_combo):
                if combo.findText(filename) < 0:
                    combo.addItem(filename)
                combo.setCurrentText(filename)
            message=self.ui('Ausgewählt · {name} — zum Aktivieren „Modell laden“ wählen.', name=Path(filename).name)
            self.model_status.setText(message)
            self.chat_model_status.setText(self.ui('Ausgewählt · {name} — zum Aktivieren „KI laden“ wählen.', name=Path(filename).name))
            self.update_controls()
            return True
        return False

    def refresh_model_safety(self):
        from shared.core.model_safety import safety_warning
        report = self._model_safety_report
        self.model_memory_status.setText(safety_warning(report, self.game.get_snapshot().language) if report else '')
        self.model_memory_status.setVisible(bool(report))

    def load_model(self):
        if self.model_combo.currentText():
            self.model_error.clear()
            self._model_error_pending=False
            if self.phase == "title":
                self._startup_model_attempted=True
                self._startup_model_failed=False
                self.title_screen.set_model_state("loading")
                self.ki_dialog.hide()
            self.game.load_model(self.model_combo.currentText(), self.backend_combo.currentData(), self.context_size.value(), self.temperature.value(), self.model_tuning.settings())

    def save_model_tuning(self, settings):
        session_shared.write_profile_settings(self.game._profile_slot(), {'gui_model_tuning': settings})

    def apply_text_size(self, choice):
        from gui.reading_style import TEXT_SIZES, set_reader_size
        if choice not in TEXT_SIZES:
            choice = 'medium'
        size = TEXT_SIZES[choice]
        self.text_size_combo.blockSignals(True)
        self.text_size_combo.setCurrentIndex(self.text_size_combo.findData(choice))
        self.text_size_combo.blockSignals(False)
        for view in (self.journal, self.world_output):
            set_reader_size(view, size)
        self.input.setStyleSheet(f'QLineEdit {{ font-size: {size}px; padding: 14px; }}')
        self.input.setMinimumHeight(size + 40)
        self.text_size_preview.setStyleSheet(f'font-size: {size}px; color: #bac9df;')

    def save_text_size(self):
        choice = self.text_size_combo.currentData() or 'medium'
        self.apply_text_size(choice)
        session_shared.write_profile_settings(self.game._profile_slot(), {'gui_text_size': choice})

    def apply_audio_settings(self):
        settings = session_shared.load_profile_settings(self.game._profile_slot())
        from shared.core.conversation_history import message_limit
        self.history_messages.blockSignals(True)
        self.history_messages.setValue(message_limit(settings))
        self.history_messages.blockSignals(False)
        self.model_tuning.restore(settings.get('gui_model_tuning'))
        from shared.core.hero_classes import selected_class, choice_pending
        saved = session_shared.load_json_file(session_shared.profile_slot_root(self.game._profile_slot()) / 'state/battle_state.json')
        self._class_choice_pending = choice_pending(saved)
        self.apply_hero_class(selected_class(saved))
        if hasattr(self.audio,'select_output'):
            self.audio.select_output(settings.get('gui_audio_output',''))
            self.refresh_audio_outputs()
        self.perspective.blockSignals(True)
        self.perspective.setCurrentIndex(max(0, self.perspective.findData(settings.get('gui_perspective', 'adventure'))))
        self.perspective.blockSignals(False)
        self.apply_perspective()
        self.apply_text_size(settings.get('gui_text_size', 'medium'))
        for widget in [self.music_box, self.sound_box, self.volume]:
            widget.blockSignals(True)
        self.music_box.setChecked(bool(settings.get('music_enabled', False)))
        self.sound_box.setChecked(bool(settings.get('gui_sound_enabled', True)))
        self.volume.setValue(int(settings.get('gui_volume', 35)))
        for widget in [self.music_box, self.sound_box, self.volume]:
            widget.blockSignals(False)
        for key, box in self.dialog_settings.items():
            box.blockSignals(True)
            box.setChecked(bool(settings.get(key, session_shared.SETTINGS_DEFAULTS.get(key, False))))
            box.blockSignals(False)
        self.update_rpg_context_option()
        self.wiki_settings.refresh()
        self.plugin_panel.refresh()
        self.volume_text.setText(self.ui(f'Lautstärke {self.volume.value()} %'))
        self.audio.set_volume(self.volume.value())
        self.audio.location(self.phase in ('menu', 'title', 'title_demo', 'profiles') and not self.game.needs_language_choice, self.game.get_snapshot().language)
        self.audio.set_enabled(self.music_box.isChecked(), self.sound_box.isChecked())

    def update_rpg_context_option(self):
        from shared.core.rpg_generation_context import is_llama_model
        blocked = is_llama_model(architecture=self.loaded_model_architecture, name=self.saved_model or '', family=getattr(self, 'loaded_model_family', ''))
        box = self.dialog_settings['rpg_context_enabled']
        settings = session_shared.load_profile_settings(self.game._profile_slot())
        box.blockSignals(True)
        box.setChecked(blocked or not bool(settings.get('rpg_context_enabled', False)))
        box.setEnabled(not blocked)
        box.setToolTip('Für Llama immer aktiviert: kein Spielkontext. Erinnerungen und Gesprächsverlauf bleiben erhalten.' if blocked else 'An: keine automatischen Spielfakten. Aus: nur Level, HP und Bossfortschritt; keine Dungeon- oder Kampfprotokolle. Erinnerungen bleiben erhalten.')
        box.blockSignals(False)

    def save_history_messages(self, value):
        from shared.core.conversation_history import SETTING, message_limit
        session_shared.write_profile_settings(self.game._profile_slot(), {SETTING: message_limit({SETTING: value})})

    def update_reply_tokens(self):
        from gui.ai_companion import estimate_reply_tokens, MIN_REPLY_TOKENS
        active = self.perspective.currentData() == 'companion'
        self.reply_token_hint.setVisible(active)
        count = estimate_reply_tokens(self.input.text())
        remaining = max(0, MIN_REPLY_TOKENS-count)
        self.reply_token_hint.setText(f'KI-Antwort · ≈ {count} / {MIN_REPLY_TOKENS} Tokens (Mindestlänge, geschätzt) · ' + (f'noch {remaining}' if remaining else 'Mindestlänge erreicht ✓'))

    def save_perspective(self):
        session_shared.write_profile_settings(self.game._profile_slot(), {'gui_perspective': self.perspective.currentData()})
        self.apply_perspective()

    def apply_perspective(self):
        active = self.perspective.currentData() == 'companion'
        self.companion_panel.setVisible(active)
        self.update_reply_tokens()
        self.tactical_input.setVisible(active)
        for heading in self.stack.widget(3).widget().findChildren(QLabel):
            if heading.objectName() == 'title':
                heading.setText('Ich bin die KI' if active else 'MAAT-KI')
        self.arena.stage.update()
        self.input.setPlaceholderText('Schreibe deine Antwort an Maatis …' if active else 'Sprich mit Maatis oder nutze einen Spielbefehl …')

    def reconnect_audio(self):
        if hasattr(self.audio,'_refresh_device'):self.audio._refresh_device()

    def refresh_audio_outputs(self):
        selected=self.audio.output_id
        self.audio_output.blockSignals(True)
        self.audio_output.clear();self.audio_output.addItem('Systemstandard','')
        for identifier,name in self.audio.available_outputs():self.audio_output.addItem(name,identifier)
        index=self.audio_output.findData(selected)
        if index<0:
            self.audio_output.addItem('Gewählter Ausgang nicht verbunden',selected);index=self.audio_output.count()-1
        self.audio_output.setCurrentIndex(index);self.audio_output.blockSignals(False)

    def save_audio_output(self):
        identifier=self.audio_output.currentData() or ''
        session_shared.write_profile_settings(self.game._profile_slot(),{'gui_audio_output':identifier})
        if hasattr(self.audio,'select_output'):self.audio.select_output(identifier)

    def save_audio_settings(self):
        settings = {'music_enabled': self.music_box.isChecked(), 'gui_sound_enabled': self.sound_box.isChecked(), 'gui_volume': self.volume.value()}
        session_shared.write_profile_settings(self.game._profile_slot(), settings)
        self.audio.set_volume(self.volume.value())
        self.audio.set_enabled(self.music_box.isChecked(), self.sound_box.isChecked())
        self.volume_text.setText(self.ui(f'Lautstärke {self.volume.value()} %'))

    def delete_profile(self, slot=None):
        if self.game.busy or (not self.game.ready and not getattr(self, '_startup_profile_pending', False)) or self.game.prompt_id:
            return
        ui = self.profile_screen.ui if getattr(self, 'phase', '') == 'profiles' else self.ui
        language = self.profile_screen.language if getattr(self, 'phase', '') == 'profiles' else self.game.get_snapshot().language
        slots = [slot for slot in range(2, session_shared.PROFILE_SLOT_COUNT + 1) if session_shared.profile_slot_used(slot)]
        if not slots:
            QMessageBox.information(self, ui('Profil löschen'), ui('Keine zusätzlichen Profile vorhanden. Das Standardprofil enthält auch gemeinsame Modelle und bleibt geschützt.'))
            return
        names = [session_shared.profile_slot_label(slot, language) + ' · Level ' + str(session_shared.profile_summary(slot).get('level', 1)) for slot in slots]
        current = slots.index(self.game._profile_slot()) if self.game._profile_slot() in slots else 0
        if slot is None:
            selected, ok = QInputDialog.getItem(self, ui('Profil löschen'), ui('Welches Profil möchtest du löschen?'), names, current, False)
            if not ok or selected not in names:
                return
            slot = slots[names.index(selected)]
        elif type(slot) is not int or slot not in slots:
            return
        else:
            selected = names[slots.index(slot)]
        answer = QMessageBox.question(self, ui('Profil endgültig löschen?'),
            ui('{name} wirklich löschen?\n\nSpielstand, Erinnerungen, Quests und Einstellungen dieses Profils werden endgültig gelöscht. Gemeinsame Modelle und andere Profile bleiben erhalten.', name=selected),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            if slot == self.game._profile_slot():
                old_process = self.game.process
                if getattr(self, '_startup_profile_pending', False):
                    from apps.maat_rpg.session_controller import MaatRpgSession
                    MaatRpgSession.set_profile_index(self.game, 0)
                    self.profile_screen.active_slot = 1
                else:
                    self.change_profile(0)
                from PySide6.QtCore import QProcess
                if old_process and old_process.state() != QProcess.NotRunning:
                    raise RuntimeError('Das Profil wird noch verwendet. Bitte das Spiel neu starten und erneut versuchen.')
            session_shared.delete_profile_slot(slot)
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, ui('Profil konnte nicht gelöscht werden'), str(exc))
            return
        self.footer.setText(ui('Profil {slot} gelöscht. Der Platz ist wieder frei.', slot=slot))
        if getattr(self, 'phase', '') == 'profiles':
            self.profile_screen.refresh()

    def change_profile(self, index):
        if self._active_minigame:return
        if self.game.busy or self.game.prompt_id:
            return
        self._editor_unlocked = False
        self._editor_return = False
        if hasattr(self, 'battle_editor'): self.battle_editor.set_entries([])
        self.editor_button.hide()
        self.chat_activity.reset()
        self._pending_class_event = None
        self._class_timer.stop()
        self._companion_after_class = False
        self.text_stream.clear()
        self.cancel_encounter_intro()
        self._ki_reply_streaming = False
        self._chat_turn_active = False
        self._chat_focus_timer.stop()
        self.reveal_button.hide()
        self._return_to_chat = False
        self._chat_return_timer.stop()
        self._audio_stops.clear()
        self._deferred.clear()
        self._started = False
        self._auto_model_pending = False
        self._startup_model_attempted = self._startup_model_failed = False
        self.saved_model = None
        self._model_safety_report = None
        self.refresh_model_safety()
        self.loaded_model_architecture = ""
        self.loaded_model_family = ""
        self.model_ready = False
        self.phase = 'menu'
        # Align the visible page before the session emits its new snapshot.
        # Otherwise the old profile page briefly looks like a non-menu screen
        # and stops/restarts the menu track while launching the journey.
        self.navigate(0)
        super().change_profile(index)
        self.world_output.clear()
        self.update_wiki_source({})
        self.model_timing.reset()
        self.quest_log.update_data({'groups':{}})
        from shared.core.talents import snapshot as talent_snapshot
        self._talent_data = talent_snapshot({})
        self.talent_tree.update_data(self._talent_data)
        self.achievements.reset()
        self.character_sidebar.reset_statistics()
        journey=saved_journey(self.game._profile_slot())
        self.character_sidebar.terra_map.update_data(journey)
        self.terra_view.update_data(journey)
        self.update_title_artwork(journey)
        self._guide_messages=0
        self._history_unlock_pending=False
        self.maat_guide.reset_profile()
        self.memories.set_profile(session_shared.profile_slot_root(self.game._profile_slot()))
        self.guide_button.setText('🔒   Guide · 0/20')
        self.update_controls()
        self._discovered_games=[]
        self._arcade_highscores={}
        self.game_hall.update_discoveries([])
        self.shop.update_data({})
        self.shop.set_receipt('Wähle deine Vorräte.')
        self.audio.handle_event({'action': 'clear'})
        self.apply_audio_settings()
        self.apply_menu_language()
        if self.game.needs_language_choice:
            self.show_language_choice()

    def restart(self):
        if self._active_minigame:return
        if self.game.busy:
            answer = QMessageBox.question(self, self.ui('Laufende Aktion beenden?'), self.ui('Die aktuelle Aktion wird abgebrochen. Noch ungespeicherter Fortschritt kann verloren gehen. Spielverbindung neu starten?'), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        self.chat_activity.reset()
        self.model_timing.reset()
        self.text_stream.clear()
        self.cancel_encounter_intro()
        self._ki_reply_streaming = False
        self._chat_turn_active = False
        self._chat_focus_timer.stop()
        self.reveal_button.hide()
        self._return_to_chat = False
        self._chat_return_timer.stop()
        self._audio_stops.clear()
        self._deferred.clear()
        self.intro.cancel()
        if hasattr(self, 'story_screen'):
            self.story_screen.cancel()
            self.credits_screen.cancel()
        self.phase = 'menu'
        self._started = False
        self.game.shutdown()
        self.game.start()
        self.navigate(0)

    def closeEvent(self, event):
        diagnostic('window_close_requested', phase=self.phase)
        if self.game.busy and self.game.ready:
            answer = QMessageBox.question(self, self.ui('Spiel verlassen?'), self.ui('Eine Spielaktion läuft noch. Beim Beenden kann ihr noch ungespeicherter Fortschritt verloren gehen. Wirklich schließen?'), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                diagnostic('window_close_cancelled')
                event.ignore()
                return
        self.discard_minigame()
        self.chat_activity.reset()
        self.level_up_notice.dismiss()
        self.model_timing.timer.stop()
        self._chat_focus_timer.stop()
        self._chat_scroll.timer.stop()
        self._world_scroll.timer.stop()
        self._demo_return_timer.stop()
        self._demo_return_pending = False
        if hasattr(self, 'title_idle'):
            self.title_idle.stop()
            self.title_screen.blink.stop()
            self.title_demo.close()
            QApplication.instance().removeEventFilter(self.application_input)
        self.text_stream.clear()
        self.cancel_encounter_intro()
        self._ki_reply_streaming = False
        self.reveal_button.hide()
        self._return_to_chat = False
        self._chat_return_timer.stop()
        self._audio_stops.clear()
        self._deferred.clear()
        self.intro.cancel()
        if hasattr(self, 'story_screen'):
            self.story_screen.cancel()
            self.credits_screen.cancel()
        self.game.shutdown()
        self.audio.close()
        self.audio.status.disconnect(self.show_audio_status)
        event.accept()
        diagnostic('window_close_accepted')


    def present_text(self, text):
        from gui.reply_formatting import reply_text_format
        views = [self.journal, self.world_output]
        if self._presenting_combat_text:
            self.arena.append_text(text)
            # Mirror live combat for the player only. Model conversation,
            # archived dialogue, memory and speech are owned by the worker.
            views = [self.journal]
        for view in views:
            view.moveCursor(QTextCursor.End)
            view.setCurrentCharFormat(reply_text_format())
            view.insertPlainText(text)
            view.ensureCursorVisible()

    def stream_drained(self):
        if self._battle_presenting and self.arena.pending:
            self.battle_log.moveCursor(QTextCursor.End)
            self.battle_log.insertPlainText(self.arena.pending)
            self.arena.pending = ''
        if not self._battle_active:
            self._battle_presenting = False
        pending, self._audio_stops = self._audio_stops, {}
        for event in pending.values():
            self.audio.handle_event(event)
        self.reveal_button.hide()
        deferred, self._deferred = self._deferred, []
        for event in deferred:
            self.receive(event)
        if self._auto_model_pending and self.phase == 'playing' and self.game.ready and not self.game.busy:
            self._auto_model_pending = False
            if not self.model_ready and self.saved_model and not self._startup_model_failed:
                self.load_chat_model()
        self.update_controls()
        self.start_encounter_intro()
        self.confirm_chat_presented()

    def confirm_chat_presented(self):
        if self._chat_generated_id and not self._chat_cancel_requested and not self.text_stream.running:
            identifier, self._chat_generated_id = self._chat_generated_id, None
            self.game.chat_presented(identifier)

    def begin_game(self):
        if not self.game.ready or self.game.busy:
            return
        if self._started:
            self.phase = 'playing'
            self.navigate(3)
            if self.resume_class_selection():
                return
            if self.perspective.currentData() == 'companion':
                self.game.send_text('/ai-start')
        else:
            self.begin_intro()

    def begin_intro(self):
        if not self.game.ready or self.game.busy or self.text_stream.running:
            return
        self.game.stop_speech()
        self.phase = 'intro'
        self.decision.hide()
        self.navigate(6)
        self.footer.setText(self.ui('Prolog · Klick oder Enter: weiter · Esc: Intro überspringen.'))
        self.intro.start(self.game.get_snapshot().language)

    def intro_finished(self):
        self.phase = 'perspective'
        self.stack.setCurrentWidget(self.perspective_screen)
        self.profile_badge.hide()
        self.footer.hide()
        self.audio.location(False, self.game.get_snapshot().language)
        self.audio.handle_event({'action': 'clear'})
        self.perspective_screen.cards[self.perspective.currentData()].setFocus()
        self.update_controls()

    def start_selected_game(self):
        self.profile_badge.show()
        self.footer.show()
        self.phase = 'playing'
        self._started = True
        self._auto_model_pending = bool(self.saved_model and not self.model_ready and not self._startup_model_failed)
        self.navigate(3)
        self.footer.setText(self.ui('Deine Reise beginnt. Sprich mit MAAT-KI.'))
        if self.resume_class_selection():
            return
        if self.perspective.currentData() == 'companion':
            self.game.send_text('/ai-start')
        else:
            self.text_stream.append(self.ui('🌟 MAAT-KI RPG ist bereit.\nDie Welt erinnert sich. Deine Reise beginnt.\n\n'))
        self.reveal_button.show()
        self.update_controls()
        if not self.model_ready:
            self.chat_model_combo.setFocus()
        else:
            self.input.setFocus()

    def load_chat_model(self):
        self.model_combo.setCurrentText(self.chat_model_combo.currentText())
        self.load_model()

    def new_game(self):
        slots = [slot for slot in range(2, session_shared.PROFILE_SLOT_COUNT+1) if not session_shared.profile_slot_used(slot)]
        if not slots:
            QMessageBox.information(self, self.ui('Neues Spiel'), self.ui('Alle Profilplätze sind belegt. Wähle unter Optionen ein vorhandenes Profil.'))
            return
        names = [session_shared.profile_slot_label(slot, self.game.get_snapshot().language) for slot in slots]
        name, ok = QInputDialog.getItem(self, self.ui('Neues Spiel'), self.ui('Freien Profilplatz wählen:'), names, 0, False)
        if ok:
            self._start_on_ready = True
            self.change_profile(slots[names.index(name)]-1)

    def show_info(self):
        QMessageBox.information(self, 'MAAT RPG', self.ui('Die Rückkehr der Prinzipien\n\nStartmenü → Intro → MAAT-KI\n\nHarmonie · Balance · Schöpfungskraft · Verbundenheit · Respekt\n\nOriginalgeschichten und Spielregeln in einer nativen Oberfläche. Musik und KI laufen lokal.'))
