"""Native MAAT RPG desktop: visual frontend for the existing alpha session."""
from __future__ import annotations

import math
from gui.qt_runtime import prepare_qt_plugins
prepare_qt_plugins()
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QLinearGradient, QRadialGradient, QPolygonF, QFont
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel,
    QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QStackedWidget,
    QProgressBar, QTextBrowser, QLineEdit, QComboBox, QMessageBox, QScrollArea)
from gui.runtime_paths import configure
configure()
from apps.maat_rpg.session_controller import MaatRpgSession

STYLE = '''
QWidget { background: #080f23; color: #e6e6d8; font-family: "Avenir Next", "Segoe UI", sans-serif; font-size: 14px; }
QFrame#sidebar { background: #060c1c; border-right: 1px solid #233453; }
QFrame#card { background: #101c35; border: 1px solid #2a3e60; border-radius: 12px; }
QFrame#card QLabel { background: transparent; }
QLabel#eyebrow { color: #c6ad73; font-size: 11px; font-weight: 600; }
QLabel#title { font-family: Georgia, serif; font-size: 36px; color: #eee8d3; }
QLabel#heading { font-family: Georgia, serif; font-size: 24px; }
QLabel#muted { color: #a0b1cf; }
QLabel#number { font-size: 32px; color: #dbbd7d; }
QPushButton { background: #142544; border: 1px solid #334d73; border-radius: 7px; padding: 12px 16px; text-align: left; }
QPushButton:hover { background: #20385e; border-color: #b9a16e; }
QPushButton:focus { border: 2px solid #d7be80; }
QPushButton:checked { color: #e3c789; background: #1a3053; border-color: #8f7c51; }
QPushButton:disabled { color: #657697; background: #0c172d; border-color: #263b59; }
QPushButton#primary { background: #cfb67c; color: #0b1830; font-weight: bold; }
QPushButton#primary:hover { background: #e5cc91; }
QPushButton#primary:disabled { background: #162441; color: #8091af; border-color: #304460; }
QProgressBar { background: #081126; border: none; border-radius: 4px; height: 8px; max-height: 8px; }
QProgressBar::chunk { background: #7ca8df; border-radius: 4px; }
QProgressBar#xp::chunk { background: #ceb57c; }
QProgressBar#enemy::chunk { background: #c37f70; }
QTextBrowser, QLineEdit, QComboBox { background: #0b162d; border: 1px solid #304970; border-radius: 7px; padding: 12px; selection-background-color: #365883; }
QTextBrowser { font-size: 15px; }
QScrollArea { border: none; }
QScrollBar:vertical { background: #080f23; width: 8px; }
QScrollBar::handle:vertical { background: #344d76; min-height: 24px; }
'''


def label(text, style=None):
    w = QLabel(text)
    if style:
        w.setObjectName(style)
    w.setWordWrap(True)
    return w


def button(text, callback, primary=False):
    w = QPushButton(text)
    if primary:
        w.setObjectName('primary')
    w.setCursor(Qt.PointingHandCursor)
    w.clicked.connect(callback)
    return w


def card():
    w = QFrame()
    w.setObjectName('card')
    layout = QVBoxLayout(w)
    layout.setContentsMargins(22, 20, 22, 20)
    layout.setSpacing(12)
    return w, layout


class Sanctum(QWidget):
    """Resolution-independent landscape and sigil; no external assets needed."""
    def __init__(self, battle=False):
        super().__init__()
        self.battle = battle
        self.setMinimumHeight(170 if battle else 230)
        self.setAccessibleName('Kampfarena mit Resonanzsiegel' if battle else 'Tempel der fünf Prinzipien')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0, QColor('#152c52' if not self.battle else '#262344'))
        bg.setColorAt(1, QColor('#080f23'))
        p.fillRect(self.rect(), bg)
        glow = QRadialGradient(QPointF(w*.57, h*.4), h*.7)
        glow.setColorAt(0, QColor(102, 146, 230, 60))
        glow.setColorAt(1, QColor(15, 30, 63, 0))
        p.fillRect(self.rect(), glow)
        for i in range(54):
            x, y = ((i*137+41) % 997)/997*w, ((i*73+17) % 293)/400*h
            p.setPen(QColor(194, 183, 140, 70+i%4*25))
            p.drawPoint(QPointF(x, y))
        for layer in range(3):
            points = [QPointF(0, h)]
            for i in range(13):
                points.append(QPointF(i*w/12, h*(.64+layer*.09)-math.sin(i*1.9+layer)*h*.11))
            points.append(QPointF(w, h))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(['#263f66', '#182c4c', '#0c1c36'][layer]))
            p.drawPolygon(QPolygonF(points))
        if not self.battle:
            # Two stone faces share an apex and ridge; geometry scales with the window.
            apex = QPointF(w*.53, h*.12)
            left = QPointF(w*.22, h*.83)
            ridge = QPointF(w*.57, h*.87)
            right = QPointF(w*.82, h*.79)
            face = QLinearGradient(apex, left)
            face.setColorAt(0, QColor('#bba36a'))
            face.setColorAt(1, QColor('#4b5266'))
            p.setPen(Qt.NoPen)
            p.setBrush(face)
            p.drawPolygon(QPolygonF([apex, left, ridge]))
            shade = QLinearGradient(apex, right)
            shade.setColorAt(0, QColor('#6c725f'))
            shade.setColorAt(1, QColor('#182d4d'))
            p.setBrush(shade)
            p.drawPolygon(QPolygonF([apex, ridge, right]))
            p.setPen(QPen(QColor(225, 209, 159, 60), 1))
            for step in range(1, 14):
                t = step / 14
                a = apex + (left-apex)*t
                b = apex + (ridge-apex)*t
                c = apex + (right-apex)*t
                p.drawLine(a, b)
                p.drawLine(b, c)
                for block in range(1, step):
                    start = a + (b-a)*(block/step)
                    p.drawLine(start, start + QPointF(0, h*.022))
            p.setPen(QPen(QColor('#d3bd7f'), 1.4))
            p.drawLine(left, apex)
            p.drawLine(apex, ridge)
            glow = QRadialGradient(QPointF(w*.49, h*.79), h*.18)
            glow.setColorAt(0, QColor(240, 190, 91, 110))
            glow.setColorAt(1, QColor(240, 190, 91, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(glow)
            p.drawEllipse(QPointF(w*.49, h*.79), h*.18, h*.18)
            p.setBrush(QColor('#efd18c'))
            p.drawPolygon(QPolygonF([QPointF(w*.472, h*.81), QPointF(w*.478, h*.67),
                                    QPointF(w*.500, h*.67), QPointF(w*.512, h*.825)]))
        cx, cy, r = (w*.57, h*.43, min(h*.27, w*.18)) if self.battle else (w*.86, h*.25, min(h*.13, w*.075))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor('#af9e69'), 1))
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.drawEllipse(QPointF(cx, cy), r*.85, r*.85)
        points = [QPointF(cx+math.sin(i*math.tau/5)*r, cy-math.cos(i*math.tau/5)*r) for i in range(5)]
        for i in range(5):
            p.drawLine(points[i], points[(i+2)%5])
            p.setBrush(QColor('#d5be82'))
            p.drawEllipse(points[i], 4, 4)
            p.setBrush(Qt.NoBrush)
        p.setPen(QColor('#e1d5ae'))
        p.setFont(QFont('Georgia', 22))
        p.drawText(QRectF(cx-r, cy-22, 2*r, 44), Qt.AlignCenter, '◆' if self.battle else 'M')
        p.setFont(QFont('Georgia', 11))
        p.setPen(QColor('#a6b8d8'))
        caption = ('THE ECHO OF THE RIFT' if self.battle else 'THE WORLD REMEMBERS') if self.property('language') == 'en' else ('DAS ECHO DES RISSES' if self.battle else 'DIE WELT ERINNERT SICH')
        p.drawText(QRectF(0, h-35, w, 25), Qt.AlignCenter, ' '.join(caption))
        p.end()


class MaatWindow(QMainWindow):
    def __init__(self, session=None):
        super().__init__()
        self.session = session or MaatRpgSession()
        self.setWindowTitle('MAAT RPG · Astratest')
        self.resize(1220, 840)
        self.setMinimumSize(880, 650)
        self.setStyleSheet(STYLE)
        root = QWidget()
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(210)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(22, 30, 22, 25)
        nav.setSpacing(12)
        nav.addWidget(label('M A A T', 'title'))
        nav.addWidget(label('RETURN OF THE PRINCIPLES', 'eyebrow'))
        nav.addSpacing(30)
        self.nav_buttons = []
        for i, text in enumerate(['◇   Heiligtum', '◈   Charakter', '⚔   Kampfarena', '≡   Reisetagebuch', '⚙   Einstellungen']):
            callback = lambda checked=False, n=i: self.navigate(n)
            if i == 3:
                from gui.navigation import ChatNavigationButton
                b = ChatNavigationButton(text, callback)
            else:
                b = button(text, callback)
            b.setCheckable(True)
            nav.addWidget(b)
            self.nav_buttons.append(b)
        nav.addStretch()
        nav.addWidget(label('H · B · S · V · R', 'eyebrow'))
        nav.addWidget(label('Fünf Prinzipien.\nDein eigener Weg.', 'muted'))
        nav.addSpacing(18)
        nav.addWidget(label('Created by GPT6 Astra', 'eyebrow'))
        shell.addWidget(sidebar)
        content = QVBoxLayout()
        content.setContentsMargins(30, 24, 30, 20)
        content.setSpacing(16)
        top = QHBoxLayout()
        era = label('DAS ZEITALTER DER RESONANZ', 'eyebrow')
        self.era = era
        era.setWordWrap(False)
        top.addWidget(era)
        top.addStretch()
        self.profile_badge = label('Profil', 'muted')
        self.profile_badge.setWordWrap(False)
        top.addWidget(self.profile_badge)
        content.addLayout(top)
        self.stack = QStackedWidget()
        content.addWidget(self.stack, 1)
        self.footer = label('Testmodus · Chat ohne KI · Kämpfe und Belohnungen nur für diese Sitzung', 'muted')
        content.addWidget(self.footer)
        shell.addLayout(content, 1)
        self._build_home()
        self._build_character()
        self._build_battle()
        self._build_journal()
        self._build_settings()
        self._build_extensions()
        self.session.on_snapshot(self.apply_snapshot)
        self.session.on_token(self._token)
        self.session.on_done(self._done)
        self.session.on_event(lambda e: self.journal.append(e.message))
        self._reply = ''
        self._battle_active = False
        self.start_session()
        self.navigate(0)

    def start_session(self):
        self.session.start()

    def _build_extensions(self):
        pass

    def page(self, eyebrow, title, subtitle):
        area = QScrollArea()
        area.setWidgetResizable(True)
        w = QWidget()
        area.setWidget(w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(12)
        layout.addWidget(label(eyebrow, 'eyebrow'))
        layout.addWidget(label(title, 'title'))
        layout.addWidget(label(subtitle, 'muted'))
        self.stack.addWidget(area)
        return layout

    def _build_home(self):
        l = self.page('01 / HEILIGTUM', 'Deine Reise beginnt im Inneren.', 'Ein Spiel über Bedeutung, Erinnerung und die Rückkehr der Prinzipien.')
        l.addWidget(Sanctum(), 1)
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
        c.addWidget(label('Welchen Weg wählst du?', 'heading'))
        c.addWidget(label('Erkunde deinen Charakter oder stelle dich dem Echo in einer Übungsbegegnung.', 'muted'))
        actions = QHBoxLayout()
        actions.addWidget(button('Kampfarena betreten  →', lambda: self.navigate(2), True))
        actions.addWidget(button('Mit Maatis sprechen  →', lambda: self.navigate(3)))
        c.addLayout(actions)
        l.addWidget(w)

    def _build_character(self):
        l = self.page('02 / CHARAKTER', 'Dein Weg hinterlässt Spuren.', 'Level und Werte aus deinem ausgewählten MAAT-Spielprofil.')
        w, c = card()
        self.path_name = label('', 'heading')
        self.motive = label('', 'muted')
        self.level_name = label('', 'number')
        self.xp_text = label('')
        self.xp_bar = QProgressBar()
        self.xp_bar.setObjectName('xp')
        self.xp_bar.setTextVisible(False)
        for item in [self.path_name, self.motive, self.level_name, self.xp_text, self.xp_bar]:
            c.addWidget(item)
        l.addWidget(w)
        w, c = card()
        self.character_values = label('', 'heading')
        c.addWidget(self.character_values)
        l.addWidget(w)
        w, c = card()
        c.addWidget(label('Die fünf Prinzipien', 'heading'))
        c.addWidget(label('H  Harmonie     ·     B  Balance     ·     S  Schöpfung\nV  Verbundenheit     ·     R  Respekt', 'muted'))
        c.addWidget(label('Orientierung für deine Reise — hier werden keine ungemessenen Feldwerte angezeigt.', 'muted'))
        l.addWidget(w)
        l.addStretch()

    def _build_battle(self):
        l = self.page('03 / KAMPFARENA', 'Begegne dem Echo.', 'Sammle Resonanz. Nutze deine Fähigkeiten. Finde deinen Rhythmus.')
        self.enemy_title = label('Die Arena wartet auf dich.', 'heading')
        l.addWidget(self.enemy_title)
        self.enemy_bar = QProgressBar()
        self.enemy_bar.setObjectName('enemy')
        self.enemy_bar.setTextVisible(False)
        l.addWidget(self.enemy_bar)
        l.addWidget(Sanctum(True), 1)
        self.battle_info = label('', 'muted')
        l.addWidget(self.battle_info)
        self.hp_text = label('')
        self.hp_bar = QProgressBar()
        self.hp_bar.setTextVisible(False)
        l.addWidget(self.hp_text)
        l.addWidget(self.hp_bar)
        self.battle_log = label('Starte einen Übungskampf. Dein gespeicherter Fortschritt bleibt erhalten.')
        l.addWidget(self.battle_log)
        grid = QGridLayout()
        self.action_buttons = {}
        for i, (action, title) in enumerate([('attack', 'Angriff'), ('skills', 'Fähigkeit'), ('focus', 'Fokus +20'), ('potion', 'Heiltrank'), ('impulse', 'Impuls −35'), ('escape', 'Rückzug')]):
            b = button(title, lambda checked=False, a=action: self.session.handle_battle_action(a))
            self.action_buttons[action] = b
            grid.addWidget(b, i//3, i%3)
        l.addLayout(grid)
        self.start_battle = button('Übungskampf starten  →', lambda: self.session.send_command('/fight'), True)
        l.addWidget(self.start_battle)

    def _build_journal(self):
        l = self.page('04 / REISETAGEBUCH', 'Worte werden zu Erinnerung.', 'Demo-Dialog und Ereignisse dieser Sitzung. Noch keine lokale KI verbunden.')
        self.journal = QTextBrowser()
        from gui.reading_style import large_transcript
        large_transcript(self.journal)
        self.journal.document().setMaximumBlockCount(500)
        l.addWidget(self.journal, 1)
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setStyleSheet("font-size: 36px; padding: 14px;")
        self.input.setMinimumHeight(76)
        self.input.setPlaceholderText('Schreibe etwas … oder /help, /quests, /fight')
        self.input.returnPressed.connect(self.send)
        row.addWidget(self.input, 1)
        self.send_button = button('Senden  →', self.send, True)
        row.addWidget(self.send_button)
        l.addLayout(row)

    def _build_settings(self):
        l = self.page('05 / EINSTELLUNGEN', 'Dein Ort. Dein Profil.', 'Die Oberfläche läuft lokal als eigenständiges Programmfenster.')
        w, c = card()
        c.addWidget(label('Spielprofil', 'heading'))
        self.profiles = QComboBox()
        self.profiles.currentIndexChanged.connect(self.change_profile)
        c.addWidget(self.profiles)
        c.addWidget(label('Ein Profilwechsel setzt den laufenden Übungskampf zurück. Die Profilwahl wird gespeichert.', 'muted'))
        l.addWidget(w)
        w, c = card()
        c.addWidget(label('Über diesen Test', 'heading'))
        c.addWidget(label('Native Python-/Qt-Oberfläche für macOS, Linux und perspektivisch Windows.\n\nDie GUI nutzt die vorhandene Alpha-Session. KI-Antworten, Musik und das vollständige Plugin-Kampfsystem werden in dieser Oberfläche noch nicht ausgeführt.\n\nMenüsprache: Deutsch. Spieltexte folgen der Sprache des ausgewählten Profils.', 'muted'))
        l.addWidget(w)
        l.addStretch()

    def navigate(self, index):
        self.stack.setCurrentIndex(index)
        for i, b in enumerate(self.nav_buttons):
            b.setChecked(i == index)

    def change_profile(self, index):
        if index >= 0:
            self.journal.clear()
            self.session.set_profile_index(index)

    def apply_snapshot(self, s):
        from shared.core.gameplay_i18n import tr
        p, b = s.player, s.battle
        self.profile_badge.setText(f'{s.profile_name}   /   LVL {p.level}')
        for widget, value in zip(self.home_stats, [p.level, p.gold, p.boss_victories]):
            widget.setText(str(value))
        self.path_name.setText(p.path_profile)
        self.motive.setText(f'{p.rank} · {p.motive}')
        self.level_name.setText(f'Level {p.level:02d}')
        self.xp_text.setText(tr('{xp} / {next_xp} XP · noch {remaining} bis zum nächsten Level', s.language,xp=f'{p.xp:,}',next_xp=f'{p.next_xp:,}',remaining=f'{max(0,p.next_xp-p.xp):,}'))
        self.xp_bar.setRange(0, max(1, p.next_xp))
        self.xp_bar.setValue(p.xp)
        self.character_values.setText(tr('{hp} / {max_hp} LP   ·   {gold} Gold   ·   {potions} Heiltränke\n{wins} Boss-Siege   ·   {principles} Prinzipien wiederhergestellt',s.language,hp=p.hp,max_hp=p.max_hp,gold=p.gold,potions=p.potions,wins=p.boss_victories,principles=p.principles_restored))
        from shared.core.monster_catalog import enemy_display_name
        self.enemy_title.setText(f'{enemy_display_name(b.enemy_name,s.language)}  ·  {b.enemy_hp} / {b.enemy_max_hp} '+('HP' if s.language=='en' else 'LP') if b.enemy_name else 'Die Arena wartet auf dich.')
        self.enemy_bar.setRange(0, max(1, b.enemy_max_hp))
        self.enemy_bar.setValue(b.enemy_hp)
        self.hp_text.setText(f'DEINE LEBENSKRAFT   {p.hp} / {p.max_hp} LP')
        self.hp_bar.setRange(0, max(1, p.max_hp))
        self.hp_bar.setValue(p.hp)
        weakness_hint = f'Schwäche: {b.weakness}   ·   ' if b.round_number > 0 and b.round_number % 3 == 0 else ''
        self.battle_info.setText(f'Resonanz {b.resonance}/100   ·   {weakness_hint}Aura: {b.aura}   ·   Phase {b.phase}   ·   Ladung {b.charge}/{b.charge_max}')
        if b.last_log:
            self.battle_log.setText(b.last_log)
        for action, btn in self.action_buttons.items():
            btn.setEnabled(b.active and (action != 'potion' or p.potions > 0) and (action != 'impulse' or b.resonance >= 35))
        self.start_battle.setEnabled(not b.active)
        if hasattr(self, 'profiles'):
            self.profiles.blockSignals(True)
            self.profiles.clear()
            self.profiles.addItems(s.profile_labels)
            self.profiles.setCurrentText(s.profile_name)
            self.profiles.blockSignals(False)
        if b.active and not self._battle_active:
            self.navigate(2)
        self._battle_active = b.active

    def send(self):
        text = self.input.text().strip()
        if not text:
            return
        from html import escape
        from shared.core.gameplay_i18n import tr
        speaker = tr('Du · ', self.session.get_snapshot().language)
        self.journal.append(f'<p style="color:#dac48e">{escape(speaker)}{escape(text)}</p>')
        self.input.clear()
        if text.lower() in ('/clear', '/cls'):
            self.journal.clear()
        else:
            self.session.send_text(text)

    def _token(self, chunk):
        self._reply += str(chunk or '')

    def _done(self):
        from html import escape
        self.journal.append('<p style="color:#ffffff">' + escape(self._reply).replace('\n', '<br>') + '</p>')
        self._reply = ''

    def closeEvent(self, event):
        self.session.shutdown()
        event.accept()


def main():
    from gui import runtime_diagnostics as diagnostics
    diagnostics.configure()
    app = QApplication.instance() or QApplication([])
    app.aboutToQuit.connect(lambda: diagnostics.event('qt_about_to_quit'))
    app.lastWindowClosed.connect(lambda: diagnostics.event('qt_last_window_closed'))
    app.setApplicationName('MAAT RPG Astratest')
    app.setStyle('Fusion')
    try:
        if "--demo" in __import__("sys").argv:
            window = MaatWindow()
        else:
            from gui.live_window import LiveWindow
            window = LiveWindow()
    except Exception as exc:
        QMessageBox.critical(None, 'MAAT RPG – Startfehler', str(exc))
        return 1
    window.showMaximized()
    result = app.exec()
    diagnostics.event('qt_event_loop_finished', code=result)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
