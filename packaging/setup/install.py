#!/usr/bin/env python3
"""Automatic GUI setup for macOS/Linux; profiles and models are never modified."""
from __future__ import annotations

import argparse
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
import sys
import time
import venv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'packaging/linux'))
import setup_linux as linux

LLAMA_VERSION = linux.LLAMA_VERSION


def data_root():
    if platform.system() == 'Linux':
        return linux.data_root()
    return Path(os.environ.get('MAAT_GUI_DATA_ROOT') or
                Path.home() / 'Library/Application Support/MAAT-RPG').expanduser().resolve()


def environment_folder():
    return data_root() / 'linux-env' if platform.system() == 'Linux' else ROOT / '.venv'


def mac_flags(machine):
    return ['-DCMAKE_BUILD_TYPE=Release', '-DGGML_NATIVE=ON',
            '-DGGML_METAL=' + ('ON' if machine == 'arm64' else 'OFF'),
            '-DGGML_ACCELERATE=ON', '-DGGML_BLAS=ON', '-DGGML_BLAS_VENDOR=Apple',
            '-DGGML_OPENMP=OFF', '-DGGML_CUDA=OFF', '-DGGML_VULKAN=OFF', '-DLLAMA_CURL=OFF']


def mac_environment(folder):
    env = linux.build_environment(False)
    env['CMAKE_ARGS'] = ' '.join(mac_flags(platform.machine()))
    env['PATH'] = str(folder / 'bin') + os.pathsep + os.environ.get('PATH', '')
    for key in ('PYTHONHOME', 'PYTHONPATH', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH',
                'CMAKE_GENERATOR', 'CMAKE_TOOLCHAIN_FILE', 'SDKROOT', 'CMAKE_PREFIX_PATH'):
        env.pop(key, None)
    return env


def run(command, log, **kwargs):
    return linux.run(command, log, **kwargs)


def probe(command, *, env=None):
    return subprocess.run(list(map(str, command)), env=env, capture_output=True,
                          text=True, errors='replace', timeout=30)


def linux_system_packages(log):
    family = linux.distro_family()
    if family == 'unknown':
        raise RuntimeError('Distribution nicht automatisch unterstützt / Distribution not automatically supported. '
                           'Install system packages from SETUP.md, then use --skip-system-deps.')
    for text in linux.system_commands(family):
        command = shlex.split(text)
        # Commands come only from our static package list, never from shell input.
        if command[1] in {'apt', 'dnf'} and 'install' in command:
            command.insert(3, '-y')
        elif command[1] == 'pacman':
            command.insert(2, '--noconfirm')
        elif command[1] == 'zypper':
            command.insert(2, '--non-interactive')
        run(command, log)


def mac_toolchain(skip):
    if probe(['xcrun', '--find', 'clang']).returncode == 0:
        return
    if skip:
        raise RuntimeError('Xcode Command Line Tools fehlen / missing: xcode-select --install')
    subprocess.run(['xcode-select', '--install'], check=False)
    print('Bitte Apples Installationsdialog abschließen; danach geht es automatisch weiter.\n'
          'Complete the Apple installer dialog; setup continues automatically. (Ctrl+C: stop)', flush=True)
    deadline = time.monotonic() + 3600
    while time.monotonic() < deadline:
        if probe(['xcrun', '--find', 'clang']).returncode == 0:
            return
        time.sleep(5)
    raise RuntimeError('Apple-Installation nicht abgeschlossen / Apple installation not completed. Run setup again.')


def mac_backend_signature():
    cpu = probe(['sysctl', '-n', 'machdep.cpu.brand_string']).stdout.strip()
    return dict(version=LLAMA_VERSION, machine=platform.machine(), cpu=cpu,
                flags=mac_flags(platform.machine()), python=list(sys.version_info[:2]))


def install_macos(log, args):
    mac_toolchain(args.skip_system_deps)
    folder = environment_folder()
    python = folder / 'bin/python'
    if not python.is_file():
        if folder.exists():
            raise RuntimeError('Unvollständige .venv / Incomplete .venv. Rename that environment and retry; keep your saves.')
        venv.EnvBuilder(with_pip=True).create(folder)
    env = mac_environment(folder)
    identity = probe([python, '-c', 'import json,platform,sys; print(json.dumps([platform.machine(),list(sys.version_info[:2])]))'], env=env)
    try:
        machine, version = json.loads(identity.stdout)
    except (ValueError, TypeError):
        raise RuntimeError('Die .venv lässt sich nicht starten / Cannot start .venv. See SETUP.md.') from None
    if identity.returncode or machine != platform.machine() or not ((3, 10) <= tuple(version) < (3, 14)):
        raise RuntimeError('Die .venv gehört zu einer anderen Architektur/Python-Version.\n'
                           'The .venv has an incompatible architecture/Python version. Rename .venv and run setup again.')
    pip = [python, '-m', 'pip', '--isolated']
    run([*pip, 'install', '--upgrade', 'pip', 'setuptools', 'wheel'], log, env=env)
    run([*pip, 'install', '--only-binary=:all:', '-r', ROOT/'requirements-gui.txt', 'cmake', 'ninja'], log, env=env)
    signature = mac_backend_signature()
    signature['python'] = version
    marker = folder / 'maat-backend.json'
    try:
        previous = json.loads(marker.read_text())
    except (OSError, ValueError):
        previous = {}
    backend = probe([python, '-c', 'import llama_cpp; print(llama_cpp.__version__)'], env=env)
    if args.rebuild_backend or previous != signature or backend.returncode or backend.stdout.strip() != LLAMA_VERSION:
        marker.unlink(missing_ok=True)
        print('KI-Backend wird für diesen Mac gebaut / Building AI backend for this Mac …', flush=True)
        run([*pip, 'install', '--no-cache-dir', '--no-binary=llama-cpp-python', '--force-reinstall',
             '--no-deps', f'llama-cpp-python=={LLAMA_VERSION}'], log, env=env)
        result = probe([python, '-c', 'import llama_cpp; print(llama_cpp.llama_print_system_info().decode())'], env=env)
        log.write(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError('KI-Backend startet nicht / AI backend cannot start. See setup log.')
        marker.write_text(json.dumps(signature, indent=2)+'\n')
    if not args.no_wiki:
        if not run([*pip, 'install', '--only-binary=:all:', '-r', ROOT/'requirements-wiki.txt'], log, env=env, required=False):
            print('Offline-Wiki optional nicht verfügbar / Optional offline Wiki unavailable; game remains usable.')
    check = probe([python, ROOT/'packaging/setup/launch.py', '--check'], env=env)
    log.write(check.stdout + check.stderr)
    print(check.stdout + check.stderr, end='')
    if check.returncode:
        raise RuntimeError('GUI-Startprüfung fehlgeschlagen / GUI startup check failed.')
    return python


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('no-start', 'skip-system-deps', 'rebuild-backend', 'no-shortcut', 'no-wiki', 'plan', 'system-deps'):
        parser.add_argument('--'+flag, action='store_true')
    args = parser.parse_args(argv)
    system = platform.system()
    if args.plan or args.system_deps:
        print(f'System: {system} / {platform.machine()}\nPython: {sys.executable}\nEnvironment: {environment_folder()}')
        print('\n'.join(linux.system_commands(linux.distro_family())) if system == 'Linux' else
              'Xcode Command Line Tools; Python.org if Python is missing; Qt; native GGUF (Metal on ARM / Accelerate on Intel).')
        print('No profiles, models or settings are changed. No model or music downloads.')
        return 0
    logpath = None
    try:
        if system not in {'Darwin', 'Linux'}:
            raise RuntimeError('macOS/Linux only.')
        if os.geteuid() == 0:
            raise RuntimeError('Ohne sudo starten / Run setup without sudo.')
        if platform.machine().lower() not in {'arm64', 'aarch64', 'x86_64', 'amd64'}:
            raise RuntimeError('64-bit Intel/AMD or ARM required.')
        if system == 'Darwin' and tuple(map(int, platform.mac_ver()[0].split('.')[:2])) < (13, 3):
            raise RuntimeError('macOS 13.3 oder neuer benötigt / macOS 13.3 or newer required.')
        if system == 'Linux':
            linux.check_libc()
        linux.game_root()
        logs = data_root() / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        logpath = logs / f'setup-{datetime.now():%Y%m%d-%H%M%S}-{os.getpid()}.log'
        with (logs/'setup.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('Setup läuft bereits / Setup is already running.') from None
            print(f'MAAT RPG · Setup\nLog: {logpath}', flush=True)
            with logpath.open('w', encoding='utf-8', buffering=1) as log:
                if system == 'Linux':
                    if not args.skip_system_deps:
                        linux_system_packages(log)
                    options = [flag for flag in ('--rebuild-backend', '--no-shortcut', '--no-wiki')
                               if getattr(args, flag[2:].replace('-', '_'))]
                    if linux.main(options):
                        raise RuntimeError('Linux-Einrichtung fehlgeschlagen / Linux setup failed. See linux-setup log.')
                    python = environment_folder() / 'bin/python'
                else:
                    python = install_macos(log, args)
                # Only mark ready after the native backend and Qt probes have succeeded.
                (environment_folder()/'maat-gui-ready.json').write_text(json.dumps({
                    'system': system, 'machine': platform.machine(), 'backend': LLAMA_VERSION,
                    'requirements': hashlib.sha256((ROOT/'requirements-gui.txt').read_bytes()).hexdigest(),
                }, indent=2)+'\n')
        print('Fertig! / Ready! Start: Start GUI.command (Mac) / Start Linux.sh (Linux)', flush=True)
        if not args.no_start:
            return subprocess.call([str(python), str(ROOT/'packaging/setup/launch.py')])
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(f'\nSetup nicht abgeschlossen / Setup incomplete: {exc}', file=sys.stderr)
        if logpath:
            print(f'Log: {logpath}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nSetup abgebrochen; erneut startbar / Setup cancelled; you can run it again.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
