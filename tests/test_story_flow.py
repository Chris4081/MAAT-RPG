from PySide6.QtCore import QCoreApplication, QEvent
import unittest
from test_desktop import APP
from gui.text_stream import TextStream
from gui.intro_screen import IntroScreen
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest


class PresentationTest(unittest.TestCase):
    def test_stream_preserves_chunk_order_and_finishes_once(self):
        stream = TextStream()
        output, finished = [], []
        stream.chunk.connect(output.append)
        stream.drained.connect(lambda: finished.append(True))
        stream.append('Maatis: ')
        stream.append('Hallo 🌌!')
        self.assertEqual(output, [])
        stream.advance()
        self.assertEqual(''.join(output), 'M')
        stream.finish()
        self.assertEqual(''.join(output), 'Maatis: Hallo 🌌!')
        self.assertEqual(finished, [True])
        self.assertFalse(stream.running)
        stream.append('Nicht mehr anzeigen')
        stream.clear()
        stream.advance()
        self.assertEqual(''.join(output), 'Maatis: Hallo 🌌!')

    def test_intro_click_pacing_finish_and_keyboard_skip(self):
        intro = IntroScreen()
        done, audio = [], []
        intro.completed.connect(lambda: done.append(True))
        intro.audio_requested.connect(audio.append)
        try:
            intro.show()
            intro.start('de')
            APP.processEvents()
            intro.text.clear()
            intro.offset = intro.next_character = 0
            intro.tick()
            self.assertGreater(len(intro.text.toPlainText()), 0)
            self.assertIn('Vor langer Zeit', ' '.join(intro.segments))
            self.assertFalse(intro.artwork.pixmap.isNull())
            self.assertTrue(audio[-1]['loop'])
            QTest.mouseClick(intro.text.viewport(), Qt.LeftButton)
            self.assertEqual(intro.text.toPlainText(), intro.segments[0])
            self.assertFalse(intro.timer.isActive())
            intro.tick()
            self.assertEqual(intro.segment, 0)
            QTest.keyClick(intro.text, Qt.Key_Return)
            self.assertEqual(intro.segment, 1)
            self.assertEqual(intro.text.toPlainText(), '')
            self.assertTrue(intro.running)
            self.assertIn('Das Licht verstummte.', intro.segments)
            while intro.running:
                intro.advance()
            self.assertEqual(done, [True])
            self.assertFalse(intro.timer.isActive())
            intro.start('en')
            APP.processEvents()
            QTest.keyClick(intro.text, Qt.Key_Escape)
            APP.processEvents()
            self.assertFalse(intro.running)
            self.assertEqual(len(done), 2)
            self.assertEqual(audio[-1]['action'], 'stop')
        finally:
            intro.cancel()
            intro.close()
            intro.deleteLater()
            QCoreApplication.sendPostedEvents(intro, QEvent.DeferredDelete)
            APP.processEvents()
