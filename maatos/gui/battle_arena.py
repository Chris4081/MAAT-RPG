"""Shared arena presentation for playable battles and terminal attract-mode replays."""
import hashlib
import math
import re
from collections import deque
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QTimer, QElapsedTimer
from PySide6.QtGui import QColor, QPainter, QPen, QLinearGradient, QRadialGradient, QTextCursor, QFontDatabase, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QProgressBar, QTextBrowser, QPushButton
from gui.maatis_presence import MaatisPresence, SUPPORT
from gui.ui_i18n import LocalizedUI
from shared.core.monster_catalog import canonical_enemy_name, enemy_display_name, regular_enemy_kind, boss_artwork, KIND_ART

ART = Path(__file__).with_name('assets') / 'combat'
ARCHETYPES = [
    ('pharaoh', ('pharao', 'pharaoh')), ('broken_harmony', ('gebrochenen harmonie', 'broken harmony')),
    ('archon', ('archon', 'herr der', 'lord of', 'abgrund', 'abyss')),
    ('time', ('zeit', 'time')), ('sun', ('sonne', 'sun')), ('avatar', ('avatar', 'balance')),
    ('heart', ('schöpfung', 'creation', 'herz', 'heart')), ('crown', ('krone', 'crown')),
    ('axis', ('achse', 'axis', 'äon', 'aeon')), ('light', ('licht', 'light')),
    ('beast', ('bestie', 'beast')), ('phantom', ('phantom', 'geist', 'spirit')),
    ('watcher', ('beobachter', 'watcher')), ('idol', ('idol',)), ('construct', ('konstrukt', 'construct')),
    ('spark', ('funke', 'spark')), ('guardian', ('wächter', 'warden', 'guardian', 'hüter', 'keeper')),
    ('wanderer', ('wanderer',)),
]


def artwork_for(name):
    boss = boss_artwork(name)
    if boss:
        return boss
    kind = regular_enemy_kind(name)
    if kind:
        return KIND_ART[kind]
    lower = canonical_enemy_name(name).casefold()
    return next((kind for kind, words in ARCHETYPES if any(word in lower for word in words)), 'phantom')


PRINCIPLES = {
    'h': ('Harmonie', '#72dfba', ('harmonie', 'harmony')),
    'b': ('Balance', '#79bdff', ('balance',)),
    's': ('Schöpfungskraft', '#e8aeff', ('schöpfung', 'schoepfung', 'creation')),
    'v': ('Verbundenheit', '#ffcd7d', ('verbundenheit', 'connection', 'connectedness')),
    'r': ('Respekt', '#ff9fae', ('respekt', 'respect')),
}


def weakness_key(value):
    value = str(value or '').strip().casefold()
    return next((key for key, (_, _, aliases) in PRINCIPLES.items()
                 if value == key or any(alias in value for alias in aliases)), None)


class CombatActionButton(QPushButton):
    """Paint the hint inside the button without allocating Qt graphics effects.

    Repeated QGraphicsDropShadowEffect construction during round/end updates
    crashed in PySide's SignalManager on macOS. This uses the normal paint path.
    """
    def __init__(self, text):
        super().__init__(text)
        self.weakness_highlight = False
        self._highlight_color = QColor('#dec787')

    def set_weakness_highlight(self, enabled, color):
        color = QColor(color)
        if self.weakness_highlight == bool(enabled) and color == self._highlight_color:
            return
        self.weakness_highlight = bool(enabled)
        self._highlight_color = color
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.weakness_highlight:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.NoBrush)
        # A soft inner halo keeps the label, focus border and click target intact.
        for inset, alpha in ((4, 72), (6, 40), (8, 18)):
            color = QColor(self._highlight_color)
            color.setAlpha(alpha)
            painter.setPen(QPen(color, 2))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(inset, inset, -inset, -inset), 5, 5)
        painter.end()


class ResonanceBar(LocalizedUI, QProgressBar):
    def __init__(self):
        super().__init__()
        self.setRange(0, 100)
        self.setMinimumHeight(32)
        self.setStyleSheet('QProgressBar {background:#152740; border:1px solid #746442; border-radius:7px; text-align:center; color:#fff0c4; font-size:17px; font-weight:700;} QProgressBar::chunk {background:#bd964d; border-radius:6px;}')
        self.pulse_clock = QElapsedTimer()
        self.pulse_timer = QTimer(self)
        self.pulse_timer.setInterval(40)
        self.pulse_timer.timeout.connect(self.update)
        self.valueChanged.connect(self.refresh_pulse)
        self.setValue(0)

    def retranslate(self):
        self.refresh_pulse()

    def refresh_pulse(self):
        full = self.value() >= 100
        self.setFormat(self.ui('✦ RESONANZ VOLL · 100 % ✦' if full else 'Resonanz · %v %'))
        if full and self.isVisible():
            if not self.pulse_timer.isActive():
                self.pulse_clock.start()
                self.pulse_timer.start()
        else:
            self.pulse_timer.stop()
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_pulse()

    def hideEvent(self, event):
        self.pulse_timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.value() < 100:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        seconds = self.pulse_clock.elapsed()/1000 if self.pulse_clock.isValid() else 0
        alpha = round(130 + 100*(.5 + .5*math.sin(seconds*3)))
        painter.setPen(QPen(QColor(255, 223, 134, alpha), 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(2, 2, -2, -2), 6, 6)
        painter.end()


class CombatStage(LocalizedUI, QWidget):
    effect_started = Signal(dict)
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(150)
        from gui.hero_portrait import PortraitRenderer
        self.hero = PortraitRenderer()
        self.presence = MaatisPresence(self)
        self.enemy = QSvgRenderer(self)
        self.attack_sprite = QSvgRenderer(self)
        self.attack_asset = None
        self.name = None
        self.enemy_visual = {}
        self.enemy_art = "beast"
        self.custom_portrait = False
        self.tint = QColor('#c69ce9')
        self.effects = deque()
        self.effect = None
        self.effect_frame = 0
        self.effect_kind = ''
        self.effect_clock = QElapsedTimer()
        self.effect_timer = QTimer(self)
        self.effect_timer.setInterval(225)
        self.effect_timer.timeout.connect(self.advance_effect)
        self.hit_clock = QElapsedTimer()
        self.hit_duration = 720
        self.hit_target = None
        self.hit_damage = 0
        self.hit_label = None
        self.hit_timer = QTimer(self)
        self.hit_timer.setInterval(25)
        self.hit_timer.timeout.connect(self.advance_hit)
        self._hit_masks = {}
        self.sway_clock = QElapsedTimer()
        self.sway_timer = QTimer(self)
        self.sway_timer.setInterval(33)
        self.sway_timer.timeout.connect(self.update)

    def set_hero_class(self, value):
        from gui.hero_portrait import normalize_class
        value = normalize_class(value)
        if self.hero.class_id != value:
            self.clear_effects()
            self.hero.set_class(value)
            self._hit_masks.clear()
            self.update()

    def clear_enemy(self):
        self.clear_effects()
        self.name=None
        self.enemy_visual={}
        self.custom_portrait=False
        self.presence.reset()
        self.enemy.load(b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>')
        self._hit_masks.clear()
        self.setAccessibleName(self.ui('Maatis · Noch kein Gegner'))
        self.update()

    def set_enemy(self, name, visual=None):
        if not name:
            self.clear_enemy()
            return
        name = canonical_enemy_name(name)
        self.setAccessibleName(self.ui('Maatis gegenüber {name}', name=enemy_display_name(name, self.language)))
        visual = dict(visual or {})
        if name == self.name and visual == self.enemy_visual:
            return
        self.clear_effects()
        self.enemy_visual = visual
        from shared.core.battle_editor import ARTS
        self.enemy_art = visual.get("art") if visual.get("art") in ARTS else artwork_for(name)
        self.custom_portrait = False
        self.name = name
        self.presence.set_victory(False)
        if hasattr(self, '_hit_masks'):
            self._hit_masks.clear()
        digest = hashlib.sha256(name.encode()).digest()
        self.tint = QColor.fromHsv(175 + digest[0] % 150, 90 + digest[1] % 65, 225)
        svg = (ART/(self.enemy_art+'.svg')).read_text()
        from shared.core.battle_editor import portrait_path
        import base64
        encoded = visual.get('portrait_png')
        image_path = portrait_path(visual.get('image'))
        if not encoded and image_path and image_path.is_file() and image_path.stat().st_size <= 2_100_000:
            encoded = base64.b64encode(image_path.read_bytes()).decode('ascii')
        if isinstance(encoded, str) and len(encoded) <= 2_800_000:
            try:
                raw = base64.b64decode(encoded, validate=True)
            except ValueError:
                raw = b''
            if raw.startswith(b'\x89PNG\r\n\x1a\n'):
                svg = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 720 720"><image width="720" height="720" preserveAspectRatio="xMidYMax meet" xlink:href="data:image/png;base64,' + encoded + '"/></svg>'
                self.custom_portrait = True
        svg = svg.replace('#c69ce9', self.tint.name()).replace('#535b83', self.tint.darker(245).name())
        self.enemy.load(svg.encode())
        self.setAccessibleName(self.ui('Maatis gegenüber {name}', name=enemy_display_name(name, self.language)))
        self.update()

    def show_effect(self, event):
        self.effects.append(dict(event))
        if self.effect is None:
            self.next_effect()

    def next_effect(self):
        from gui.ascii_effects import FRAMES, SUPPORT_FRAMES, effect_kind
        if not self.effects:
            self.effect = None
            self.attack_asset = None
            self.effect_kind = ''
            self.effect_timer.stop()
            self.hero.set_pose('standard')
            self.update()
            return
        self.effect = self.effects.popleft()
        kind = effect_kind(self.effect, self.enemy_art)
        if self.effect.get('attacker') == 'enemy' and self.enemy_visual.get('effect') in FRAMES:
            kind = self.enemy_visual['effect']
        self.effect_kind = kind
        self.effect_clock.start()
        self.frames = (SUPPORT_FRAMES if kind in SUPPORT else FRAMES)[kind]
        character = 'maatis' if self.effect.get('attacker') == 'player' else self.enemy_art
        if character == 'maatis':
            self.hero.set_pose(kind)
            self.attack_asset = self.hero.asset if self.hero.pose_id != 'standard' else None
        else:
            path = ART/'attacks'/f'{character}-{kind}.svg'
            self.attack_asset = path if path.is_file() and not self.custom_portrait else None
            if self.attack_asset:
                svg = path.read_text()
                svg = svg.replace('#c69ce9', self.tint.name()).replace('#535b83', self.tint.darker(245).name())
                self.attack_sprite.load(svg.encode())
                self._hit_masks = {k:v for k,v in self._hit_masks.items() if k[0] != id(self.attack_sprite)}
        self.effect_frame = 0
        self.effect_timer.start()
        self.hit_target = 'enemy' if self.effect.get('attacker') == 'player' else 'player'
        self.hit_damage = max(0, int(self.effect.get('damage', 0)))
        self.hit_label = None
        if character == 'maatis' and kind in SUPPORT:
            self.hit_target = 'player'
            self.hit_damage = 0
            healed = max(0, int(self.effect.get('heal', 0)))
            self.hit_label = self.ui('+{hp} KP', hp=healed) if healed else self.ui('FOKUS' if kind == 'focus' else 'HEILUNG')
        self.hit_clock.start()
        self.hit_timer.start()
        self.effect_started.emit(self.effect)
        self.update()

    def advance_effect(self):
        if self.effect is None:
            self.effect_timer.stop()
            return
        self.effect_frame += 1
        if self.effect_frame >= len(self.frames):
            self.next_effect()
        else:
            self.update()

    def advance_hit(self):
        if self.hit_clock.elapsed() >= self.hit_duration:
            self.hit_target = None
            self.hit_timer.stop()
        self.update()

    def hit_progress(self):
        return min(1., self.hit_clock.elapsed()/self.hit_duration) if self.hit_clock.isValid() else 1.

    def hit_mask(self, renderer, size):
        pixels = max(1, int(size))
        # One hero renderer swaps images: a previous pose must never be reused
        # as the red hit silhouette of a different pose or class.
        revision = renderer.pixmap.cacheKey() if renderer is self.hero else 0
        key = (id(renderer), pixels, revision)
        if key not in self._hit_masks:
            mask = QPixmap(pixels, pixels)
            mask.fill(Qt.transparent)
            paint = QPainter(mask)
            renderer.render(paint, QRectF(0, 0, pixels, pixels))
            paint.setCompositionMode(QPainter.CompositionMode_SourceIn)
            paint.fillRect(mask.rect(), QColor('#ff354d'))
            paint.end()
            # Bound the cache across poses and window sizes.
            if len(self._hit_masks) >= 6:
                self._hit_masks.clear()
            self._hit_masks[key] = mask
        return self._hit_masks[key]

    def clear_effects(self):
        self.hit_timer.stop()
        self.hit_target = None
        self.hit_label = None
        self.effect_timer.stop()
        self.effects.clear()
        self.effect = None
        self.attack_asset = None
        self.effect_kind = ''
        self.effect_clock.invalidate()
        self.hero.set_pose('standard')
        self.update()

    def showEvent(self, event):
        self.sway_clock.start()
        self.sway_timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.sway_timer.stop()
        self.clear_effects()
        super().hideEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0, QColor('#102646'))
        gradient.setColorAt(1, QColor('#080f23'))
        painter.fillRect(self.rect(), gradient)
        size = min(h*.92, w*.32)
        seconds = self.sway_clock.elapsed()/1000 if self.sway_clock.isValid() else 0
        action_progress = min(1., self.effect_clock.elapsed() / (len(self.frames)*self.effect_timer.interval())) if self.effect and self.effect_clock.isValid() else 0.
        hero_pose = self.presence.pose(seconds, self.effect, self.hit_target, self.hit_damage)
        hero_kind = self.effect_kind if self.effect and self.effect.get('attacker') == 'player' else hero_pose
        self.hero.set_pose(hero_kind if self.name or self.effect else 'standard')
        for cx, renderer, color in [(w*.25, self.hero, QColor('#ddc587')), (w*.75, self.enemy, self.tint)]:
            if renderer is self.enemy and self.name is None:continue
            glow = QRadialGradient(QPointF(cx, h*.6), size*.65)
            soft = QColor(color); soft.setAlpha(60)
            glow.setColorAt(0, soft)
            glow.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setPen(Qt.NoPen); painter.setBrush(glow)
            painter.drawEllipse(QPointF(cx, h*.58), size*.65, size*.55)
            painter.setPen(QPen(color.darker(160), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(cx, h*.92), size*.55, size*.075)
            attacking = self.effect and ((renderer is self.hero and self.effect.get('attacker') == 'player') or (renderer is self.enemy and self.attack_asset and self.effect.get('attacker') == 'enemy'))
            shown = self.attack_sprite if attacking and renderer is self.enemy else renderer
            phase = 0 if renderer is self.hero else math.pi
            wave = math.sin(seconds*1.7 + phase)
            # Pivot around the feet. Only the figures sway, never the HUD or text.
            painter.save()
            target = 'player' if renderer is self.hero else 'enemy'
            hit = self.hit_target == target and self.hit_damage > 0
            progress = self.hit_progress()
            shake = math.sin(progress*math.pi*10)*min(10, size*.035)*(1-progress) if hit else 0
            hero = renderer is self.hero
            lunge = math.sin(action_progress*math.pi)*size*.055 if hero and attacking and self.effect_kind not in SUPPORT else 0
            breath = math.sin(seconds*2)*size*.004 if hero else 0
            lift = math.sin(action_progress*math.pi)*size*.02 if hero and hero_kind in {'focus','impulse'} else 0
            painter.translate(cx + wave*min(5, size*.018) + shake + lunge, h*.92 - lift)
            painter.rotate(wave*1.4)
            rect = QRectF(-size/2, h*.02-size-breath, size, size+breath)
            if hero:
                # The PNG canvas includes transparent space below the feet.
                # Anchor the body to the floor/pivot, then apply the same
                # breathing, sway, lunge and lift to portraits and effects.
                rect = self.hero.grounded_bounds(QRectF(-size/2, -size-breath, size, size+breath))
                presence_rect = self.presence.aligned_bounds(rect, self.hero.visible_top, self.hero.foot_line)
                self.presence.paint(painter, presence_rect, seconds, hero_kind, action_progress)
            sprite_rect = shown.bounds(rect) if hero else rect
            shown.render(painter, sprite_rect)
            if hero:
                self.presence.paint(painter, presence_rect, seconds, hero_kind, action_progress, front=True)
            if hit and progress < .55:
                painter.setOpacity(.72*(1-progress/.55))
                mask_size = sprite_rect.width()
                painter.drawPixmap(sprite_rect, self.hit_mask(shown, mask_size), QRectF(0, 0, int(mask_size), int(mask_size)))
            painter.restore()
        if self.hit_target is not None:
            progress = self.hit_progress()
            cx = w*(.25 if self.hit_target == 'player' else .75)
            font = painter.font()
            font.setPixelSize(max(24, min(44, int(w*.034))))
            font.setBold(True)
            painter.setFont(font)
            damage = self.hit_label or (f'−{self.hit_damage}' if self.hit_damage else 'BLOCK')
            area = QRectF(cx-size*.5, max(8, h*.24)-progress*24, size, 60)
            painter.setOpacity(min(1., (1-progress)*3))
            painter.setPen(QPen(QColor('#080f23')))
            painter.drawText(area.translated(2, 3), Qt.AlignCenter, damage)
            painter.setPen(QColor('#72dfba') if self.hit_label else QColor('#ffb5be') if self.hit_damage else QColor('#bcd2eb'))
            painter.drawText(area, Qt.AlignCenter, damage)
            painter.setOpacity(1.)
        painter.setPen(QColor('#8e9fb9'))
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPixelSize(23)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, '⚔')
        if self.effect and self.effect_kind not in SUPPORT:
            from gui.ascii_effects import directional_frame
            attacker = self.effect.get('attacker', 'player')
            fraction = self.effect_frame / max(1, len(self.frames)-1)
            center = w * ((.41 + .18*fraction) if attacker == 'player' else (.59 - .18*fraction))
            font.setPixelSize(max(12, min(22, int(w*.025))))
            font.setBold(True)
            painter.setFont(font)
            color = QColor('#f5d488') if attacker == 'player' else self.tint.lighter(130)
            painter.setPen(color)
            text = directional_frame(self.frames[self.effect_frame], attacker)
            # The two effect lanes sit just above the central sword, between figures.
            painter.drawText(QRectF(center-w*.09, h*.37, w*.18, 38), Qt.AlignCenter, text)
        painter.end()


class BattleArena(LocalizedUI, QWidget):
    action_requested = Signal(str)
    def __init__(self, demo=False):
        super().__init__()
        self.demo = demo
        self._display_state = {}
        self.setObjectName('battleArena')
        self.setStyleSheet('QWidget#battleArena {background: #0b162d; border: 1px solid #345171; border-radius: 12px;}')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(8)
        title = QLabel('⚔  MAAT BATTLE  ⚔' + ('   ·   DEMO' if demo else ''))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 22px; color: #dec68b; font-weight: 600;')
        layout.addWidget(title)
        self.difficulty_badge = QLabel()
        self.difficulty_badge.setAlignment(Qt.AlignCenter)
        self.difficulty_badge.hide()
        layout.addWidget(self.difficulty_badge)
        names = QHBoxLayout()
        self.hero_name = QLabel('MAATIS · LVL 1')
        self._difficulty = None
        self.enemy_name = QLabel('Schattenwächter')
        self.enemy_name.setAlignment(Qt.AlignCenter)
        self.hero_name.setAlignment(Qt.AlignCenter)
        self._fight_type = None
        self._enemy_level = None
        for widget in (self.hero_name, self.enemy_name):
            widget.setWordWrap(True)
            widget.setStyleSheet('font-size: 18px;')
            names.addWidget(widget, 1)
        layout.addLayout(names)
        self.stage = CombatStage()
        layout.addWidget(self.stage, 1)
        bars = QHBoxLayout()
        self.hero_hp = self.bar('#72c7c4')
        self.enemy_hp = self.bar('#cb8399')
        bars.addWidget(self.hero_hp, 1); bars.addSpacing(45); bars.addWidget(self.enemy_hp, 1)
        layout.addLayout(bars)
        self.resonance = ResonanceBar()
        self.resonance.setRange(0, 100)
        self.resonance.setValue(0)
        layout.addWidget(self.resonance)
        self.details = QLabel('Finde den Rhythmus deines Gegners.')
        self.details.setWordWrap(True)
        self.details.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.details)
        self.log = QTextBrowser()
        self.log.setStyleSheet('QTextBrowser { font-size: 18px; padding: 6px; border: none; background: #0a1428; }')
        font = self.log.font(); font.setPixelSize(18)
        self.log.setFont(font); self.log.document().setDefaultFont(font)
        from PySide6.QtGui import QTextOption
        self.log.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.log.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.log.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.log.setFixedHeight(self.log.fontMetrics().lineSpacing()*3 + 22)
        self.log.document().setMaximumBlockCount(150)
        layout.addWidget(self.log)
        self._advance_mode = None
        self.advance_hint = QLabel()
        self.advance_hint.setWordWrap(True)
        self.advance_hint.setAlignment(Qt.AlignCenter)
        self.advance_hint.setStyleSheet('font-size:13px; color:#d8c18a; padding:2px;')
        self.advance_hint.hide()
        layout.addWidget(self.advance_hint)
        self.actions = {}
        self.weakness = None
        self._round = 0
        self._battle_running = False
        self._hint_ready = False
        self._hint_usable = False
        self._hint_elapsed = QElapsedTimer()
        self.weakness_timer = QTimer(self)
        self.weakness_timer.setSingleShot(True)
        self.weakness_timer.setTimerType(Qt.PreciseTimer)
        self.weakness_timer.setInterval(30000)
        self.weakness_timer.timeout.connect(self.reveal_weakness)
        row = QGridLayout()
        self.action_grid = row
        self.action_columns = 5
        for i, (key, title) in enumerate([('h','H'),('b','B'),('s','S'),('v','V'),('r','R'),('skill','Skill'),('focus','Fokus'),('potion','Heiltrank'),('impulse','Impuls'),('escape','Wegrennen')]):
            btn = CombatActionButton(title)
            btn.setMinimumHeight(50)
            btn.setMinimumWidth(52 if key in PRINCIPLES else 62)
            btn.setToolTip(PRINCIPLES[key][0] if key in PRINCIPLES else title)
            btn.setAccessibleName(PRINCIPLES[key][0] if key in PRINCIPLES else title)
            btn.clicked.connect(lambda checked=False, k=key: self.action_requested.emit(k))
            btn.setEnabled(False)
            self.actions[key] = btn
            row.addWidget(btn, i//5, i%5)
        layout.addLayout(row)
        self.pending = ''
        self.clear_opponent()

    def retranslate(self):
        self.stage.language = self.language
        self.resonance.set_language(self.language)
        self.set_advance_hint(self._advance_mode)
        self.style_actions()
        if self._display_state:
            self.update_state(dict(self._display_state))

    def set_advance_hint(self, mode):
        self._advance_mode = mode
        text = ('Klick ins Kampfbild oder den Text · Leertaste · Enter: Text vervollständigen'
                if mode == 'reading' else 'Klick · Leertaste · Enter: weiter')
        self.advance_hint.setText(self.ui(text))
        self.advance_hint.setVisible(mode is not None and not self.demo)

    def set_combat_visible(self, visible):
        for widget in (self.stage, self.hero_name, self.enemy_name, self.hero_hp,
                       self.enemy_hp, self.resonance, self.details, *self.actions.values()):
            widget.setVisible(visible)

    def reset_weakness_hint(self):
        self.weakness_timer.stop()
        self._hint_elapsed.invalidate()
        self._hint_ready = False
        self._hint_usable = False

    def set_hint_waiting(self, usable):
        if self.demo:
            return
        was_usable = self._hint_usable
        self._hint_usable = bool(usable and self._battle_running and self._round > 0)
        if not self._hint_usable:
            self.weakness_timer.stop()
        elif not self._hint_ready:
            if not self._hint_elapsed.isValid():
                self._hint_elapsed.start()
            remaining = max(0, 30000 - self._hint_elapsed.elapsed())
            if remaining == 0:
                self.reveal_weakness()
            elif not self.weakness_timer.isActive():
                self.weakness_timer.start(remaining)
        if was_usable != self._hint_usable:
            self.style_actions()

    def reveal_weakness(self):
        if self._hint_usable and self._battle_running:
            self._hint_ready = True
            self.style_actions()

    def clear_opponent(self):
        self._display_state.clear()
        self.set_advance_hint(None)
        self.reset_weakness_hint()
        self._round = 0
        self._battle_running = False
        self.set_combat_visible(False)
        self.stage.clear_enemy()
        self.enemy_name.clear()
        self.enemy_hp.setRange(0,1);self.enemy_hp.setValue(0);self.enemy_hp.setFormat('')
        self.enemy_hp.setVisible(False)
        self.difficulty_badge.hide()
        self._difficulty=None;self._fight_type=None;self._enemy_level=None
        self.weakness=None;self.details.clear();self.resonance.setValue(0)
        self.pending='';self.log.clear()
        self.style_actions()

    def style_actions(self):
        for key, btn in self.actions.items():
            color = PRINCIPLES[key][1] if key in PRINCIPLES else '#93adc9'
            weak = key == self.weakness and (self.demo or (self._hint_ready and self._hint_usable))
            size = 24 if key in PRINCIPLES else 16
            bg = QColor(color).darker(340).name() if key in PRINCIPLES else '#152b46'
            btn.setText(key.upper() + (' ✦' if weak else '') if key in PRINCIPLES else self.ui({'skill':'Skill','focus':'Fokus','potion':'Heiltrank','impulse':'Impuls','escape':'Wegrennen'}[key]))
            btn.setStyleSheet(f"QPushButton {{font-size:{size}px; font-weight:700; text-align:center; padding:6px 4px; background:{bg}; color:{color}; border:{3 if weak else 1}px solid {color}; border-radius:8px;}} QPushButton:hover {{background:{QColor(bg).lighter(145).name()};}} QPushButton:pressed {{background:{QColor(bg).lighter(185).name()};}} QPushButton:disabled {{color:{color if weak or self.demo else '#758298'}; border-color:{color if weak else '#354861'}; background:{bg};}} QPushButton:focus {{border:3px solid #fff1c1;}}")
            btn.set_weakness_highlight(weak, color)
            if key in PRINCIPLES:
                btn.setToolTip(self.ui(PRINCIPLES[key][0]) + (' · ' + self.ui('Schwäche des Gegners') if weak else ''))
            else:
                btn.setToolTip(btn.text())
            btn.setAccessibleName(self.ui(PRINCIPLES[key][0]) if key in PRINCIPLES else btn.text())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        columns = 10 if self.width() >= 1000 else 5
        if columns != self.action_columns:
            self.action_columns = columns
            for i, btn in enumerate(self.actions.values()):
                self.action_grid.addWidget(btn, i//columns, i%columns)

    def bar(self, color):
        bar = QProgressBar()
        bar.setMinimumHeight(22)
        bar.setStyleSheet(f'QProgressBar {{background: #152740; border: none; border-radius: 4px; text-align: center; font-size: 14px;}} QProgressBar::chunk {{background: {color}; border-radius: 4px;}}')
        return bar

    def update_state(self, data):
        self._display_state.update(data)
        new_round = int(data.get('round_number', self._round) or 0)
        if new_round != self._round or data.get('active') is False:
            self.reset_weakness_hint()
            self._round = new_round
            self.style_actions()
        if 'active' in data:
            self._battle_running = bool(data['active'])
        if 'enemy_name' in data and not data['enemy_name']:
            self.clear_opponent()
            data={k:v for k,v in data.items() if k.startswith('player_')}
        if 'arena_difficulty' in data:
            from shared.core.arena_difficulty import TIERS
            tier = self._difficulty = TIERS.get(data['arena_difficulty'])
            self.difficulty_badge.setVisible(tier is not None)
            color = tier['color'] if tier else '#eee5ce'
            self.enemy_name.setStyleSheet(f'font-size: 18px; color: {color};')
            if tier:
                source = self.ui("Zufallskampf-EP" if data.get("combat_source") == "random" else "Arena-EP")
                caption = f"DEMO · {self.ui(tier['label']).upper()}" if data.get('combat_source') == 'demo' else f"{self.ui(tier['label']).upper()} · {tier['xp']:.0%} {source}"
                self.difficulty_badge.setText(caption)
                self.difficulty_badge.setStyleSheet(f'font-size: 18px; font-weight: 600; color: {color};')
        if 'enemy_name' in data:
            name = data['enemy_name']
            self.stage.set_enemy(name, self._display_state.get("enemy_visual"))
            self.set_combat_visible(True)
        if 'fight_type' in data:
            self._fight_type = data['fight_type']
        if 'enemy_level' in data:
            self._enemy_level = data['enemy_level']
        if any(key in data for key in ('enemy_name', 'arena_difficulty', 'fight_type', 'enemy_level')):
            badge = ' · ♛ ' + self.ui('FINALBOSS') if self._fight_type == 'final' else ' · ♛ BOSS' if self._fight_type == 'boss' else ''
            level = f' · LVL {self._enemy_level}' if self._enemy_level is not None else ''
            self.enemy_name.setText(('● ' if self._difficulty else '') + (enemy_display_name(self.stage.name, self.language) if self.stage.name else self.ui('Unbekannter Gegner')) + level + badge)
        if 'player_level' in data:
            self.hero_name.setText(f"MAATIS · LVL {data['player_level']}")
        for prefix, bar in [('player',self.hero_hp),('enemy',self.enemy_hp)]:
            if prefix+'_max_hp' in data:
                bar.setRange(0, max(1,int(data[prefix+'_max_hp'])))
            if prefix+'_hp' in data:
                bar.setValue(int(data[prefix+'_hp']))
                bar.setFormat(f'HP {bar.value()} / {bar.maximum()}')
        if 'resonance' in data:
            self.resonance.setValue(int(data['resonance']))
        self.stage.presence.hp_fraction = max(0., self.hero_hp.value()/max(1, self.hero_hp.maximum()))
        self.stage.presence.resonance = self.resonance.value()
        if data.get('active') is True:
            self.stage.presence.set_victory(False)
        elif data.get('active') is False and self.stage.name:
            self.stage.presence.set_victory(self.enemy_hp.value() == 0 and self.hero_hp.value() > 0)
        if 'weakness' in data:
            weak = weakness_key(data['weakness'])
            if weak != self.weakness:
                self.weakness = weak
                self.style_actions()
            hint = self.ui('Schwäche: {weakness}   ·   ', weakness=self.ui(PRINCIPLES[weak][0]) if weak else data['weakness']) if self.demo or (self._round > 0 and self._round % 3 == 0) else ''
            auras = {'none':'Keine','shatter':'Zersplitterung','counter':'Konter','wildfire':'Wildfeuer','silence':'Schweigen','sealed':'Siegel','judgment':'Urteil'}
            aura = str(data.get('aura','—'))
            aura = self.ui(auras.get(aura,aura))
            self.details.setText(f"{hint}Aura: {aura}   ·   Phase {data.get('phase','1')}")

    def append_text(self, text):
        self.pending += text
        if '\n' not in self.pending:
            return
        complete, self.pending = self.pending.rsplit('\n', 1)
        lines = [re.sub(r'\*\*(.*?)\*\*', r'\1', line) for line in complete.splitlines()
                 if line.strip() and not re.match(r'^(?:[-─]{3,}|[1-6][).]|.*HP:|Resonanz:|Resonance:|Schwäche:|Schwaeche:|Schwachstelle:|Weakness:|Aktion:|Action:)', line.strip())]
        if lines:
            self.log.moveCursor(QTextCursor.End)
            self.log.insertPlainText('\n'.join(lines)+'\n')
            self.log.ensureCursorVisible()
