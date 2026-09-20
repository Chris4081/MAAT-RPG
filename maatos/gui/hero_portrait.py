"""Approved class portraits and locally extracted combat poses."""
from pathlib import Path
from functools import lru_cache
from math import ceil
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPixmap, QPainter, QImage
from PySide6.QtWidgets import QLabel
from shared.core.hero_classes import CLASSES

ART = Path(__file__).parent / 'assets/classes/transparent-v1'
ACTION_ART = ART.parent / 'actions-v1'
POSES = frozenset(('ready', 'blink', 'tired', 'wave', 'balance', 'creation',
    'connection', 'respect', 'slash', 'claw', 'sand', 'spark', 'impulse',
    'focus', 'heal', 'hurt', 'guard', 'victory', 'charged'))


def normalize_class(value):
    return value if isinstance(value, str) and value in CLASSES else 'normal'


def class_name(value, language='de'):
    value = normalize_class(value)
    from shared.core.gameplay_i18n import tr
    return tr(CLASSES[value][0] if value in CLASSES else 'Normal · noch keine Klasse', language)


def portrait_path(value):
    return ART / f'maatis-{normalize_class(value)}.png'


@lru_cache(maxsize=6)
def portrait_pixmap(value):
    return QPixmap(str(portrait_path(value)))


@lru_cache(maxsize=6)
def portrait_vertical_bounds(value):
    """Visible top and foot line in the approved portrait's padded canvas.

    Action sheets were registered to this same foot line when extracted. Use
    the standard portrait for every pose: waves, particles and raised hands
    must not move the registration point from one animation frame to another.
    """
    image = portrait_pixmap(value).toImage().convertToFormat(QImage.Format_Alpha8)
    if image.isNull():
        return 0., 1.
    pixels, width, stride = image.constBits(), image.width(), image.bytesPerLine()
    def visible(row):
        return any(pixels[row*stride:row*stride+width])
    top = next((y for y in range(image.height()) if visible(y)), None)
    if top is None:
        return 0., 1.
    bottom = next(y+1 for y in range(image.height()-1, top-1, -1) if visible(y))
    return top/image.height(), bottom/image.height()


def pose_path(value, pose):
    return ACTION_ART / normalize_class(value) / f'{pose}.png' if pose in POSES else portrait_path(value)


@lru_cache(maxsize=24)
def pose_pixmap(value, pose):
    return QPixmap(str(pose_path(value, pose)))


class PortraitRenderer:
    def __init__(self, value='normal'):
        self.set_class(value)

    def set_class(self, value):
        value = normalize_class(value)
        if getattr(self, 'class_id', None) == value:
            return
        self.class_id = value
        self.visible_top, self.foot_line = portrait_vertical_bounds(value)
        self.pose_id = None
        self.set_pose('standard')

    def set_pose(self, pose):
        pose = pose if pose in POSES else 'standard'
        if self.pose_id == pose:
            return
        pixmap = portrait_pixmap(self.class_id) if pose == 'standard' else pose_pixmap(self.class_id, pose)
        if pixmap.isNull():
            pose, pixmap = 'standard', portrait_pixmap(self.class_id)
        self.pose_id, self.pixmap = pose, pixmap
        self.asset = pose_path(self.class_id, pose)
        self._scaled_key = None
        self._scaled_pixmap = None

    def bounds(self, rect):
        # Extracted action frames add 48 pixels around the 320-pixel body frame.
        # Keep the feet/body size aligned with the approved standard portrait.
        if self.pose_id != 'standard':
            return rect.adjusted(-rect.width()*.15, -rect.height()*.15,
                                  rect.width()*.15, rect.height()*.15)
        return rect

    def grounded_bounds(self, rect):
        """Place visible feet on rect.bottom(), excluding transparent padding."""
        return rect.translated(0, (1-self.foot_line)*rect.height())

    def isValid(self):
        return not self.pixmap.isNull()

    def render(self, painter, rect):
        if self.pixmap.isNull():
            return
        # Prefilter large PNGs before rotating/swaying them. Directly sampling the
        # full image at battle size makes the thin gold outline shimmer.
        pixels = max(rect.width(), rect.height()) * painter.device().devicePixelRatioF()
        pixels = min(self.pixmap.width(), max(32, ceil(pixels / 32) * 32))
        if self._scaled_key != pixels:
            self._scaled_pixmap = self.pixmap.scaled(pixels, pixels, Qt.KeepAspectRatio,
                                                     Qt.SmoothTransformation)
            self._scaled_key = pixels
        painter.save()
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(rect, self._scaled_pixmap, QRectF(self._scaled_pixmap.rect()))
        painter.restore()


class HeroPortrait(QLabel):
    def __init__(self, size=110, parent=None):
        super().__init__(parent)
        self.side = size
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        # The shared QWidget theme otherwise paints a navy tile behind the image.
        self.setStyleSheet('background: transparent; border: none;')
        self.set_class('normal')

    def set_class(self, value):
        self.class_id = normalize_class(value)
        self.setPixmap(portrait_pixmap(self.class_id).scaled(self.side, self.side,
                       Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.setAccessibleName('Maatis · ' + class_name(self.class_id))
