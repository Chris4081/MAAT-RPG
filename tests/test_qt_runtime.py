"""Regression checks for macOS plugin visibility; no real model or saves."""
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'maatos'))
from gui import qt_runtime


class QtRuntimeTests(unittest.TestCase):
    def test_other_platforms_do_not_modify_packages(self):
        for system in ('linux', 'win32'):
            with self.subTest(system=system), patch.object(qt_runtime.sys, 'platform', system), \
                    patch.object(qt_runtime, '_plugin_roots') as roots:
                self.assertEqual(qt_runtime.prepare_qt_plugins(), 0)
                roots.assert_not_called()

    def test_missing_optional_package_is_left_to_normal_import_error(self):
        with patch.object(qt_runtime.importlib.util, 'find_spec', return_value=None):
            self.assertEqual(list(qt_runtime._plugin_roots()), [])

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS file flags')
    def test_hidden_plugins_become_discoverable_without_changing_other_attributes(self):
        from PySide6.QtCore import QDir
        with tempfile.TemporaryDirectory(prefix='maat qt visibility ') as temporary:
            env = Path(temporary) / '.venv'
            root = env / 'Qt/plugins'
            platforms = root / 'platforms'
            platforms.mkdir(parents=True)
            plugin = platforms / 'libqtest.dylib'
            plugin.write_bytes(b'unchanged plugin content')
            outside = env / 'unrelated.dylib'
            outside.write_bytes(b'unrelated')
            link = platforms / 'external.dylib'
            link.symlink_to(outside)
            for path in (env, root, platforms, plugin, outside):
                os.chflags(path, path.stat().st_flags | stat.UF_HIDDEN)
            os.chflags(plugin, plugin.stat().st_flags | stat.UF_NODUMP)
            before = plugin.stat()
            self.assertNotIn(plugin.name, QDir(str(platforms)).entryList(QDir.Files))
            with patch.object(qt_runtime, '_plugin_roots', return_value=[root]):
                self.assertEqual(qt_runtime.prepare_qt_plugins(), 3)
                self.assertEqual(qt_runtime.prepare_qt_plugins(), 0)
            self.assertIn(plugin.name, QDir(str(platforms)).entryList(QDir.Files))
            self.assertEqual(plugin.stat().st_flags, before.st_flags & ~stat.UF_HIDDEN)
            self.assertEqual(plugin.stat().st_mode, before.st_mode)
            self.assertEqual(plugin.read_bytes(), b'unchanged plugin content')
            self.assertTrue(env.stat().st_flags & stat.UF_HIDDEN)
            self.assertTrue(outside.stat().st_flags & stat.UF_HIDDEN)

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS file flags')
    def test_unwritable_hidden_plugin_reports_a_clear_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plugin = root / 'libqtest.dylib'
            plugin.touch()
            os.chflags(plugin, plugin.stat().st_flags | stat.UF_HIDDEN)
            with patch.object(qt_runtime, '_plugin_roots', return_value=[root]), \
                    patch.object(qt_runtime.os, 'chflags', side_effect=PermissionError('test')):
                with self.assertRaisesRegex(RuntimeError, 'Qt plugin cannot be made visible'):
                    qt_runtime.prepare_qt_plugins()


if __name__ == '__main__':
    unittest.main()
