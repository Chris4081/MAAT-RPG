"""Setup regression checks without downloading packages or touching real profiles."""
import argparse
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('automatic_setup', ROOT/'packaging/setup/install.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class AutomaticSetupTests(unittest.TestCase):
    def test_macos_build_is_native_and_does_not_inherit_other_backends(self):
        for machine, metal in [('arm64', 'ON'), ('x86_64', 'OFF')]:
            with self.subTest(machine=machine), patch.object(setup.platform, 'machine', return_value=machine), \
                 patch.dict(os.environ, {'CMAKE_ARGS': '-DGGML_CUDA=ON -DGGML_AVX512=ON',
                                        'CFLAGS': '-mavx512f', 'LLAMA_CPP_LIB_PATH': '/wrong',
                                        'CMAKE_TOOLCHAIN_FILE': '/wrong', 'PYTHONPATH': '/wrong'}):
                env = setup.mac_environment(Path('/tmp/Game with spaces/.venv'))
            self.assertIn('-DGGML_NATIVE=ON', env['CMAKE_ARGS'])
            self.assertIn('-DGGML_METAL='+metal, env['CMAKE_ARGS'])
            self.assertIn('-DGGML_BLAS_VENDOR=Apple', env['CMAKE_ARGS'])
            self.assertNotIn('AVX', env['CMAKE_ARGS'])
            for key in ('CFLAGS', 'LLAMA_CPP_LIB_PATH', 'CMAKE_TOOLCHAIN_FILE', 'PYTHONPATH'):
                self.assertNotIn(key, env)

    def test_linux_system_dependencies_are_argument_lists(self):
        for family in ('debian', 'fedora', 'arch', 'suse'):
            with self.subTest(family=family), patch.object(setup.linux, 'distro_family', return_value=family), \
                 patch.object(setup, 'run') as run:
                setup.linux_system_packages(io.StringIO())
                self.assertTrue(run.called)
                for call in run.call_args_list:
                    self.assertEqual(call.args[0][0], 'sudo')
                    self.assertNotIn('shell', call.kwargs)
        with patch.object(setup.linux, 'distro_family', return_value='unknown'), patch.object(setup, 'run') as run:
            with self.assertRaises(RuntimeError):
                setup.linux_system_packages(io.StringIO())
            run.assert_not_called()

    def test_mac_backend_built_once_and_save_preserved(self):
        with tempfile.TemporaryDirectory(prefix='maat setup ') as temporary:
            root = Path(temporary)
            python = root/'.venv/bin/python'
            python.parent.mkdir(parents=True)
            python.touch()
            save = root/'profiles/profile_4/state.json'
            save.parent.mkdir(parents=True)
            save.write_text('{"level":50}')
            args = argparse.Namespace(skip_system_deps=True, rebuild_backend=False, no_wiki=True)
            def probe(command, **kwargs):
                text = str(command)
                output = json.dumps(['x86_64', [3, 11]]) if 'platform.machine' in text else \
                         setup.LLAMA_VERSION if '__version__' in text else 'OK'
                return subprocess.CompletedProcess(command, 0, output, '')
            with patch.object(setup, 'ROOT', root), patch.object(setup, 'environment_folder', return_value=root/'.venv'), \
                 patch.object(setup, 'mac_toolchain'), patch.object(setup.platform, 'machine', return_value='x86_64'), \
                 patch.object(setup, 'mac_backend_signature', return_value={'machine': 'x86_64', 'version': setup.LLAMA_VERSION}), \
                 patch.object(setup, 'probe', side_effect=probe), patch.object(setup, 'run', return_value=True) as run:
                setup.install_macos(io.StringIO(), args)
                self.assertEqual(sum('--no-binary=llama-cpp-python' in c.args[0] for c in run.call_args_list), 1)
                run.reset_mock()
                setup.install_macos(io.StringIO(), args)
                self.assertFalse(any('--no-binary=llama-cpp-python' in c.args[0] for c in run.call_args_list))
                args.rebuild_backend = True
                run.reset_mock()
                setup.install_macos(io.StringIO(), args)
                self.assertEqual(sum('--no-binary=llama-cpp-python' in c.args[0] for c in run.call_args_list), 1)
            self.assertEqual(save.read_text(), '{"level":50}')

    def test_wrong_architecture_environment_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            python = folder/'bin/python'
            python.parent.mkdir(); python.write_text('existing environment')
            args = argparse.Namespace(skip_system_deps=True, rebuild_backend=False, no_wiki=True)
            with patch.object(setup, 'environment_folder', return_value=folder), patch.object(setup, 'mac_toolchain'), \
                 patch.object(setup.platform, 'machine', return_value='arm64'), \
                 patch.object(setup, 'probe', return_value=subprocess.CompletedProcess([], 0, '["x86_64", [3, 11]]', '')), \
                 patch.object(setup, 'run') as run:
                with self.assertRaises(RuntimeError):
                    setup.install_macos(io.StringIO(), args)
                run.assert_not_called()
                self.assertEqual(python.read_text(), 'existing environment')

    def test_failed_setup_never_launches_and_can_be_retried(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            with patch.object(setup.platform, 'system', return_value='Linux'), \
                 patch.object(setup.platform, 'machine', return_value='x86_64'), \
                 patch.object(setup.os, 'geteuid', return_value=1000), \
                 patch.object(setup.linux, 'check_libc'), patch.object(setup.linux, 'game_root'), \
                 patch.object(setup, 'data_root', return_value=folder), \
                 patch.object(setup.linux, 'main', return_value=1), \
                 patch.object(setup.subprocess, 'call') as launch, patch('sys.stderr', new_callable=io.StringIO):
                for _ in range(2):
                    self.assertEqual(setup.main(['--skip-system-deps']), 1)
                launch.assert_not_called()
                self.assertFalse((folder/'linux-env/maat-gui-ready.json').exists())

    def test_plan_is_read_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary)/'not-created'
            with patch.object(setup, 'data_root', return_value=missing), \
                 patch.object(setup, 'linux_system_packages') as packages, \
                 patch.object(setup, 'install_macos') as mac, \
                 patch.object(setup.linux, 'main') as linux, patch('sys.stdout', new_callable=io.StringIO):
                self.assertEqual(setup.main(['--plan']), 0)
                packages.assert_not_called(); mac.assert_not_called(); linux.assert_not_called()
                self.assertFalse(missing.exists())

    def test_shell_entry_preserves_interpreter_path_and_setup_arguments(self):
        with tempfile.TemporaryDirectory(prefix='maat shell path ') as temporary:
            root = Path(temporary)
            record = root/'args.json'
            fake = root/'Python with spaces'
            script = 'import json,sys; from pathlib import Path; Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))'
            fake.write_text('#!/bin/bash\nif [[ "$1" == -c ]]; then exit 0; fi\nexec '+
                            shlex.join([sys.executable, '-c', script, str(record)])+' "$@"\n')
            fake.chmod(0o755)
            env = dict(os.environ, MAAT_SETUP_PYTHON=str(fake), PYTHONDONTWRITEBYTECODE='1')
            result = subprocess.run(['bash', str(ROOT/'setup.sh'), '--no-start', '--skip-system-deps'],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(record.read_text()),
                             [str(ROOT/'packaging/setup/install.py'), '--no-start', '--skip-system-deps'])

    def test_start_bootstraps_once_and_forwards_game_arguments(self):
        with tempfile.TemporaryDirectory(prefix='maat first start ') as temporary:
            root = Path(temporary)
            scripts = root/'packaging/setup'; scripts.mkdir(parents=True)
            shutil.copy2(ROOT/'packaging/setup/start.sh', scripts/'start.sh')
            fakebin = root/'fakebin'; fakebin.mkdir()
            uname = fakebin/'uname'; uname.write_text('#!/bin/sh\nprintf Linux'); uname.chmod(0o755)
            data = root/'user data'
            record = root/'game args.json'
            fake_python = '#!/bin/bash\nif [[ "$1" == -c ]]; then exit 0; fi\nexec '+shlex.join([
                sys.executable, '-c', 'import json,sys; from pathlib import Path; Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))',
                str(record)])+' "$@"\n'
            template = root/'python-template'; template.write_text(fake_python)
            installer = root/'setup.sh'
            installer.write_text('#!/bin/bash\nset -eu\n[[ "$1" == --no-start ]]\n'+
                'mkdir -p "$MAAT_GUI_DATA_ROOT/linux-env/bin"\n'+
                'cp '+shlex.quote(str(template))+' "$MAAT_GUI_DATA_ROOT/linux-env/bin/python"\n'+
                'chmod +x "$MAAT_GUI_DATA_ROOT/linux-env/bin/python"\n'+
                'printf installed >> '+shlex.quote(str(root/'installs'))+'\n')
            env = dict(os.environ, MAAT_GUI_DATA_ROOT=str(data), PATH=str(fakebin)+os.pathsep+os.environ['PATH'])
            env.pop('MAAT_GUI_PYTHON', None)
            for _ in range(2):
                result = subprocess.run(['bash', str(scripts/'start.sh'), '--demo', 'with spaces'], env=env, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root/'installs').read_text(), 'installed')
            self.assertEqual(json.loads(record.read_text()), [str(scripts/'launch.py'), '--demo', 'with spaces'])


if __name__ == '__main__':
    unittest.main()
