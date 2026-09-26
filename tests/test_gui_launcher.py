"""Guard the native macOS startup path without loading a model or real saves."""
import importlib.util
import io
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gui_startup_launcher', ROOT/'packaging/setup/launch.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class GuiLauncherTests(unittest.TestCase):
    def test_default_check_uses_cocoa_even_with_offscreen_environment(self):
        with patch.object(launcher.platform, 'system', return_value='Darwin'), \
             patch.object(launcher.linux_launcher, 'runtime_environment', return_value={'QT_QPA_PLATFORM': 'offscreen'}), \
             patch.object(launcher, 'check_macos', return_value=True) as check, \
             patch.object(launcher.os, 'execve') as start:
            self.assertEqual(launcher.main(['--check']), 0)
            self.assertEqual(check.call_args.args[1], 'cocoa')
            start.assert_not_called()

    def test_offscreen_is_explicit_and_does_not_launch_game(self):
        with patch.object(launcher.platform, 'system', return_value='Darwin'), \
             patch.object(launcher, 'check_macos', return_value=True) as check, \
             patch.object(launcher.os, 'execve') as start:
            self.assertEqual(launcher.main(['--check-offscreen']), 0)
            self.assertEqual(check.call_args.args[1], 'offscreen')
            start.assert_not_called()

    def test_plugin_visibility_is_repaired_before_qt_import_in_child(self):
        success = subprocess.CompletedProcess([], 0, 'Qt platform cocoa\n', '')
        with patch.object(launcher, 'game_root', return_value=Path('/tmp/Game with spaces/maatos')), \
             patch.object(launcher.subprocess, 'run', return_value=success) as run, \
             patch('sys.stdout', new_callable=io.StringIO):
            self.assertTrue(launcher.check_macos({}))
        command = run.call_args.args[0]
        compile(command[2], '<startup-check>', 'exec')
        self.assertLess(command[2].index('prepare_qt_plugins()'), command[2].index('from PySide6'))
        self.assertIn("'/tmp/Game with spaces/maatos'", command[2])
        self.assertEqual(run.call_args.kwargs['env']['QT_QPA_PLATFORM'], 'cocoa')

    def test_native_failure_never_executes_game(self):
        failure = subprocess.CompletedProcess([], -6, '', 'Could not find the Qt platform plugin "cocoa"')
        with patch.object(launcher.platform, 'system', return_value='Darwin'), \
             patch.object(launcher.subprocess, 'run', return_value=failure), \
             patch.object(launcher.os, 'execve') as start, \
             patch('sys.stderr', new_callable=io.StringIO) as error:
            self.assertEqual(launcher.main([]), 1)
        start.assert_not_called()
        self.assertIn('cocoa', error.getvalue())
        self.assertIn('MAAT cannot start its interface', error.getvalue())

    def test_timeout_is_readable_and_never_executes_game(self):
        with patch.object(launcher.platform, 'system', return_value='Darwin'), \
             patch.object(launcher.subprocess, 'run', side_effect=subprocess.TimeoutExpired('Qt', 25)), \
             patch.object(launcher.os, 'execve') as start, patch('sys.stderr', new_callable=io.StringIO):
            self.assertEqual(launcher.main([]), 1)
        start.assert_not_called()

    def test_success_keeps_game_arguments_and_environment(self):
        game = Path('/tmp/Original app/Contents/Resources/maatos')
        env = {'LANG': 'de_DE.UTF-8'}
        with patch.object(launcher.platform, 'system', return_value='Darwin'), \
             patch.object(launcher.linux_launcher, 'runtime_environment', return_value=env), \
             patch.object(launcher, 'check_macos', return_value=True) as check, \
             patch.object(launcher, 'game_root', return_value=game), \
             patch.object(launcher.os, 'chdir') as chdir, patch.object(launcher.os, 'execve') as start:
            launcher.main(['--demo'])
        check.assert_called_once_with(env, 'cocoa')
        chdir.assert_called_once_with(game)
        self.assertEqual(start.call_args.args[1][1:], ['-m', 'gui.desktop', '--demo'])
        self.assertEqual(start.call_args.args[2], env)

    def test_linux_keeps_existing_launcher_and_display_detection(self):
        with patch.object(launcher.platform, 'system', return_value='Linux'), \
             patch.object(launcher.linux_launcher, 'main', return_value=0) as linux, \
             patch.object(launcher, 'check_macos') as mac:
            self.assertEqual(launcher.main(['--check']), 0)
        linux.assert_called_once_with(['--check'])
        mac.assert_not_called()


if __name__ == '__main__':
    unittest.main()
