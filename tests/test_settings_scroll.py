"""Wheel/trackpad scrolling must not edit or save settings under the pointer."""
import unittest
from unittest.mock import patch
from test_desktop import APP
from test_gui_language import LanguageTests, shared
from PySide6.QtCore import Qt, QPoint, QPointF, QCoreApplication, QEvent
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QComboBox, QSpinBox, QDoubleSpinBox,
    QSlider, QStyle, QStyleOptionSlider,
)
from gui.settings_scroll import protect_settings_scroll


def wheel(widget, *, trackpad=False):
    point = widget.rect().center()
    event = QWheelEvent(QPointF(point), QPointF(widget.mapToGlobal(point)),
        QPoint(0, -24) if trackpad else QPoint(), QPoint(0, -120),
        Qt.NoButton, Qt.NoModifier,
        Qt.ScrollUpdate if trackpad else Qt.NoScrollPhase, False)
    APP.sendEvent(widget, event)
    APP.processEvents()


class SettingsScrollTests(unittest.TestCase):
    setUp = LanguageTests.setUp
    close_windows = LanguageTests.close_windows
    window = LanguageTests.window
    ready = LanguageTests.ready

    def test_wheel_scrolls_page_and_preserves_focused_and_unfocused_values(self):
        area = QScrollArea(); area.setWidgetResizable(True)
        body = QWidget(); layout = QVBoxLayout(body)
        layout.addSpacing(300)
        combo = QComboBox(); combo.addItems(['Small', 'Medium', 'Large']); combo.setCurrentIndex(1)
        integer = QSpinBox(); integer.setRange(0, 100); integer.setValue(50)
        decimal = QDoubleSpinBox(); decimal.setRange(0, 2); decimal.setValue(.8)
        slider = QSlider(Qt.Horizontal); slider.setValue(50)
        controls = (combo, integer, decimal, slider)
        changes = []
        for control in controls:
            layout.addWidget(control)
            (control.currentIndexChanged if control is combo else control.valueChanged).connect(changes.append)
        layout.addSpacing(1200)
        area.setWidget(body); area.resize(600, 450); area.show()
        protect_settings_scroll(body); APP.processEvents()
        try:
            for focused in (False, True):
                for trackpad in (False, True):
                    for control in (*controls, integer.lineEdit(), decimal.lineEdit()):
                        with self.subTest(focused=focused, trackpad=trackpad, widget=type(control).__name__):
                            area.ensureWidgetVisible(control)
                            (control if focused else area).setFocus()
                            before = area.verticalScrollBar().value()
                            wheel(control, trackpad=trackpad)
                            self.assertGreater(area.verticalScrollBar().value(), before)
                            self.assertEqual((combo.currentIndex(), integer.value(), decimal.value(), slider.value()), (1, 50, .8, 50))
                            self.assertEqual(changes, [])
            # Explicit selection, keyboard editing and dragging still work.
            combo.showPopup(); QTest.keyClick(combo, Qt.Key_Down); QTest.keyClick(combo, Qt.Key_Return)
            self.assertEqual(combo.currentIndex(), 2)
            QTest.keyClick(integer, Qt.Key_Up); self.assertEqual(integer.value(), 51)
            QTest.keyClick(decimal, Qt.Key_Up); self.assertGreater(decimal.value(), .8)
            area.ensureWidgetVisible(slider); APP.processEvents()
            option = QStyleOptionSlider(); slider.initStyleOption(option)
            handle = slider.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, slider).center()
            destination = QPoint(slider.width()-20, handle.y())
            QTest.mousePress(slider, Qt.LeftButton, pos=handle)
            QTest.mouseMove(slider, destination)
            QTest.mouseRelease(slider, Qt.LeftButton, pos=destination)
            self.assertGreater(slider.value(), 50)
        finally:
            area.close(); area.deleteLater()
            QCoreApplication.sendPostedEvents(area, QEvent.DeferredDelete)

    def test_real_settings_and_model_fields_scroll_without_saving(self):
        shared.write_application_language('de')
        shared.set_profile_name(1, 'Scroll test')
        window = self.window(); self.ready(window)
        window.enter_menu(); window.resize(900, 650); window.navigate(4)
        with patch.object(shared, 'write_profile_settings') as save:
            for control in (window.text_size_combo, window.volume, window.audio_output):
                window.general_settings.ensureWidgetVisible(control); APP.processEvents()
                before = window.general_settings.verticalScrollBar().value()
                wheel(control)
                self.assertGreater(window.general_settings.verticalScrollBar().value(), before)
            save.assert_not_called()
        window.open_models(); window.ki_dialog.resize(700, 600)
        window.model_tuning.mode.setCurrentIndex(1); APP.processEvents()
        fields = [window.model_tuning.mode, window.context_size, window.temperature,
                  *window.model_tuning.fields.values(), window.model_tuning.flash]
        def value(field):
            return field.currentIndex() if isinstance(field, QComboBox) else field.value()
        before_values = [value(field) for field in fields]
        with patch.object(shared, 'write_profile_settings') as save:
            for field in fields:
                window.model_scroll.ensureWidgetVisible(field); APP.processEvents()
                field.setFocus(); wheel(field, trackpad=True)
            self.assertEqual([value(field) for field in fields], before_values)
            save.assert_not_called()
