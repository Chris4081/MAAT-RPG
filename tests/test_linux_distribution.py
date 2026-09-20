"""Linux packaging, startup isolation and preservation of macOS dispatch."""
import importlib.util
import io
import json
import os
import shlex
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packaging/linux'))
import setup_linux as setup
import launcher
spec=importlib.util.spec_from_file_location('linux_builder',ROOT/'tools/build_linux_test.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


class LinuxDistributionTests(unittest.TestCase):
    def test_paths_with_spaces_and_xdg(self):
        with patch.dict(os.environ,{'XDG_DATA_HOME':'/tmp/Maat Linux Data'},clear=True):
            self.assertEqual(setup.data_root(),Path('/tmp/Maat Linux Data/MAAT-RPG'))
            with patch.dict(os.environ,{'MAAT_GUI_DATA_ROOT':'/tmp/Custom Profile Root'}):
                self.assertEqual(setup.data_root(),Path('/tmp/Custom Profile Root').resolve())
        with patch.dict(os.environ,{'XDG_DATA_HOME':'relative'},clear=True):
            with self.assertRaises(RuntimeError):setup.data_root()

    def test_repo_and_archive_layout(self):
        self.assertTrue((setup.game_root()/'gui/desktop.py').is_file())
        with tempfile.TemporaryDirectory(prefix='maat-linux-layout-') as tmp:
            game=Path(tmp)/'maatos/gui';game.mkdir(parents=True);(game/'desktop.py').touch()
            with patch.object(setup,'ROOT',Path(tmp)):
                self.assertEqual(setup.game_root(),Path(tmp)/'maatos')

    def test_native_cpu_build_does_not_inherit_mac_or_forced_avx(self):
        with patch.dict(os.environ,{'CMAKE_ARGS':'-DGGML_AVX2=ON -DGGML_METAL=ON',
                                    'CXXFLAGS':'-mavx512f','LLAMA_CPP_LIB_PATH':'/mac/lib'}), \
             patch.object(os,'cpu_count',return_value=32):
            env=setup.build_environment(True)
        self.assertNotIn('CXXFLAGS',env);self.assertNotIn('LLAMA_CPP_LIB_PATH',env)
        self.assertIn('-DGGML_NATIVE=ON',env['CMAKE_ARGS'])
        self.assertIn('-DGGML_METAL=OFF',env['CMAKE_ARGS'])
        self.assertIn('-DGGML_BLAS_VENDOR=OpenBLAS',env['CMAKE_ARGS'])
        self.assertNotIn('-DGGML_AVX',env['CMAKE_ARGS'])
        self.assertEqual(env['CMAKE_BUILD_PARALLEL_LEVEL'],'4')
        self.assertIn('-DGGML_BLAS=OFF',setup.build_environment(False)['CMAKE_ARGS'])

    def test_supported_qt_libc_checked_before_installing(self):
        for cpu,libc,ok in [('x86_64','2.28',True),('x86_64','2.27',False),
                            ('aarch64','2.39',True),('aarch64','2.35',False)]:
            with patch.object(setup.platform,'machine',return_value=cpu), \
                 patch.object(setup.platform,'libc_ver',return_value=('glibc',libc)):
                if ok:setup.check_libc()
                else:
                    with self.assertRaises(RuntimeError):setup.check_libc()
        with patch.object(setup.platform,'libc_ver',return_value=('musl','1.2')):
            with self.assertRaises(RuntimeError):setup.check_libc()

    def test_shortcut_quotes_paths_and_does_not_touch_profiles(self):
        with tempfile.TemporaryDirectory(prefix='maat-linux-shortcut-') as tmp:
            data=Path(tmp)/'xdg';save=data/'MAAT-RPG/profiles/profile_4/state.json'
            save.parent.mkdir(parents=True);save.write_text('{"keep": true}')
            with patch.dict(os.environ,{'XDG_DATA_HOME':str(data)},clear=True), \
                 patch.object(setup,'ROOT',Path(tmp)/'Game % Name'):
                shortcut=setup.install_shortcut()
            text=shortcut.read_text()
            self.assertIn('Exec=/bin/bash "',text);self.assertIn('Game %% Name/Start Linux.sh"',text)
            self.assertEqual(save.read_text(),'{"keep": true}')

    def test_bad_qt_plugin_does_not_start_the_game(self):
        failure=subprocess.CompletedProcess([], -6, '', 'xcb plugin cannot be loaded')
        with tempfile.TemporaryDirectory(prefix='maat-linux-start-') as tmp, \
             patch.object(launcher.platform,'system',return_value='Linux'), \
             patch.object(launcher,'data_root',return_value=Path(tmp)), \
             patch.object(launcher.subprocess,'run',return_value=failure), \
             patch.object(launcher.subprocess,'call') as start, \
             patch.dict(os.environ,{'DISPLAY':':0'}), patch('sys.stderr',new_callable=io.StringIO):
            self.assertEqual(launcher.main([]),1)
            start.assert_not_called()
            self.assertIn('xcb plugin',next((Path(tmp)/'logs').glob('*')).read_text())

    def test_runtime_keeps_wayland_choice_and_isolates_foreign_libraries(self):
        with patch.dict(os.environ,{'WAYLAND_DISPLAY':'wayland-0','QT_QPA_PLATFORM':'wayland',
                                    'PYTHONPATH':'/bad/python','QT_PLUGIN_PATH':'/bad/qt',
                                    'LLAMA_CPP_LIB_PATH':'/bad/lib'},clear=True):
            env=launcher.runtime_environment()
        self.assertEqual(env['QT_QPA_PLATFORM'],'wayland')
        self.assertEqual(env['WAYLAND_DISPLAY'],'wayland-0')
        for key in ('PYTHONPATH','QT_PLUGIN_PATH','LLAMA_CPP_LIB_PATH'):self.assertNotIn(key,env)

    def test_export_contains_both_languages_assets_but_no_personal_data_or_native_mac_files(self):
        names={str(target) for _,target in builder.sources()}
        for name in ('maatos/profiles/maat_rpg.yaml','maatos/profiles/maat_rpg_en.yaml',
                     'maatos/gui/assets/combat/beast.svg','maatos/gui/assets/combat/attacks/beast-claw.svg',
                     'maatos/apps/maat_rpg/plugins/battle/music/victory.mp3',
                     'Install Linux.sh','packaging/linux/launcher.py'):
            self.assertIn(name,names)
        for name in names:
            if Path(name).suffix in {'.mp3', '.m4a'}:
                self.assertIn(name, {'maatos/apps/maat_rpg/plugins/battle/music/victory.mp3',
                                     'maatos/apps/maat_rpg/plugins/battle/sounds/levelup.mp3'})
            self.assertFalse(set(Path(name).parts)&{'data','logs','saves','models','__pycache__'})
            self.assertNotIn(Path(name).suffix,{'.dylib','.so','.gguf','.zim','.pyc','.bak'})

    def test_macos_launcher_still_uses_explicit_python_and_arguments(self):
        with tempfile.TemporaryDirectory(prefix='maat mac launch ') as tmp:
            target=Path(tmp)/'args.json';fake=Path(tmp)/'Python with spaces'
            command=[sys.executable, '-c',
                'import sys,json; from pathlib import Path; Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))',
                str(target)]
            fake.write_text('#!/bin/sh\nexec '+shlex.join(command)+' "$@"\n');fake.chmod(0o755)
            # Mock only uname via PATH; do not import platform-specific native libraries.
            uname=Path(tmp)/'uname';uname.write_text('#!/bin/sh\nprintf Darwin');uname.chmod(0o755)
            env=dict(os.environ,MAAT_GUI_PYTHON=str(fake),PATH=tmp+':'+os.environ['PATH'])
            result=subprocess.run(['bash',str(setup.game_root()/'start_gui.sh'),'--demo'],env=env,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(target.read_text()),['-m','gui.desktop','--demo'])

    def test_setup_installs_cpu_backend_once_and_preserves_save(self):
        with tempfile.TemporaryDirectory(prefix='maat-linux-install-') as tmp:
            root=Path(tmp);python=root/'linux-env/bin/python';python.parent.mkdir(parents=True);python.touch()
            save=root/'profiles/profile_4/state.json';save.parent.mkdir(parents=True);save.write_text('{"level":50}')
            def probe(command,**kwargs):
                return subprocess.CompletedProcess(command,0,'11' if 'sys.version_info.minor' in str(command) else '', '')
            with patch.object(setup.platform,'system',return_value='Linux'), \
                 patch.object(setup.platform,'machine',return_value='x86_64'), \
                 patch.object(setup,'check_libc'),patch.object(setup,'cpu_identity',return_value=['old Intel CPU']), \
                 patch.object(setup.os,'geteuid',return_value=1000), \
                 patch.object(setup.shutil,'which',return_value='/usr/bin/tool'), \
                 patch.object(setup,'data_root',return_value=root), \
                 patch.object(setup.subprocess,'run',side_effect=probe), \
                 patch.object(setup,'run',return_value=True) as run:
                self.assertEqual(setup.main(['--no-shortcut']),0)
                builds=[c for c in run.call_args_list if '--no-binary=llama-cpp-python' in c.args[0]]
                self.assertEqual(len(builds),1)
                self.assertIn('GGML_NATIVE=ON',builds[0].kwargs['env']['CMAKE_ARGS'])
                self.assertEqual(save.read_text(),'{"level":50}')
                run.reset_mock()
                self.assertEqual(setup.main(['--no-shortcut']),0)
                self.assertFalse(any('--no-binary=llama-cpp-python' in c.args[0] for c in run.call_args_list))
                self.assertEqual(save.read_text(),'{"level":50}')


if __name__=='__main__':unittest.main()
