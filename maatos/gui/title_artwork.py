"""Profile-driven Terra landscapes, shared by the title screen and main menu."""
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPixmap
from gui.desktop import Sanctum
from shared.core.terra_journey import REGIONS, snapshot

ART = Path(__file__).with_name('assets') / 'title-worlds'
REGION_KEYS = ('desert', 'gardens', 'coast', 'mountains', 'terra')
REGIONS_EN = ('The Scales of the Desert', 'Gardens of Creation',
              'Crystal Coast of Resonance', "Aeon's Star Mountains", 'The Light of Terra')


def artwork_key(journey):
    """Use the same region and unlock gate as the real map, including final retries."""
    if not isinstance(journey, dict) or journey.get('kind') not in ('battle', 'final', 'complete'):
        return 'pyramid'
    region = journey.get('region')
    if type(region) is not int or not 0 <= region < len(REGION_KEYS):
        return 'pyramid'
    return REGION_KEYS[region]


def saved_journey(slot):
    """Read the last active profile before a worker/model exists; never alter its save."""
    from apps.maat_rpg import session_shared as shared
    root = shared.profile_slot_root(slot) / 'state'
    settings = shared.load_profile_settings(slot)
    story = 'companion_story_state.json' if settings.get('gui_perspective') == 'companion' else 'story_state.json'
    battle = shared.load_json_file(root / 'battle_state.json')
    # A partially damaged save must not make the new title renderer block startup.
    state = {key: battle[key] if isinstance(battle.get(key), dict) else {}
             for key in ('stats', 'world')}
    return snapshot(state, shared.load_json_file(root / story))


@lru_cache(maxsize=2)
def landscape(key):
    # QPixmaps share storage between title/menu. Keep only the current and previous
    # region cached, rather than retaining every full-resolution picture alongside a GGUF.
    return QPixmap(str(ART / (key + '.png')))


class JourneyArtwork(Sanctum):
    """Original vector pyramid first; fitted, navy-feathered artwork after unlocking combat."""
    def __init__(self):
        super().__init__()
        self.key = 'pyramid'
        self.image = QPixmap()
        self.journey = snapshot({})

    def set_journey(self, journey):
        self.journey = dict(journey or snapshot({}))
        key = artwork_key(self.journey)
        if key != self.key:
            self.key = key
            self.image = QPixmap() if key == 'pyramid' else landscape(key)
        self.set_language(self.property('language') or 'de')

    def set_language(self, language):
        self.setProperty('language', 'en' if language == 'en' else 'de')
        self.setAccessibleName(self.caption())
        self.update()

    def caption(self):
        english = self.property('language') == 'en'
        if self.key == 'pyramid' or self.image.isNull():
            return 'The world remembers' if english else 'Die Welt erinnert sich'
        return (REGIONS_EN if english else REGIONS)[REGION_KEYS.index(self.key)]

    def paintEvent(self, event):
        if self.image.isNull():
            # The built-in pyramid also covers absent or damaged optional artwork.
            return super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor('#080f23'))
        bounds = QRectF(self.rect())
        scale = min(bounds.width() / self.image.width(), bounds.height() / self.image.height())
        w, h = self.image.width() * scale, self.image.height() * scale
        target = QRectF((bounds.width()-w)/2, (bounds.height()-h)/2, w, h)
        # Contain the whole illustration: neither narrow windows nor ultrawide
        # displays cut off its landmark. Feather into the actual GUI background.
        p.drawPixmap(target, self.image, QRectF(self.image.rect()))
        fade = min(w, h) * .13
        x, y, right, bottom = target.left(), target.top(), target.right(), target.bottom()
        for rect, start, end in (
            (QRectF(x, y, fade, h), (x, y), (x+fade, y)),
            (QRectF(right-fade, y, fade, h), (right, y), (right-fade, y)),
            (QRectF(x, y, w, fade), (x, y), (x, y+fade)),
            (QRectF(x, bottom-fade, w, fade), (x, bottom), (x, bottom-fade)),
        ):
            gradient = QLinearGradient(*start, *end)
            gradient.setColorAt(0, QColor('#080f23'))
            gradient.setColorAt(1, QColor(8, 15, 35, 0))
            p.fillRect(rect, gradient)
        # Keep the region name translated, sharp and readable at every window size.
        footer = QLinearGradient(0, self.height()-62, 0, self.height())
        footer.setColorAt(0, QColor(8, 15, 35, 0))
        footer.setColorAt(1, QColor('#080f23'))
        p.fillRect(QRectF(0, self.height()-62, self.width(), 62), footer)
        font = QFont('Georgia'); font.setPixelSize(14)
        p.setFont(font); p.setPen(QColor('#d8c38c'))
        p.drawText(QRectF(12, self.height()-35, self.width()-24, 25), Qt.AlignCenter, self.caption())
        p.end()
