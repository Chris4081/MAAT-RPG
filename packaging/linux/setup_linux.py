#!/usr/bin/env python3
"""User-local Linux GUI installation. Never modifies a macOS runtime or save.

System packages are printed for the user/admin, never installed using sudo.
llama.cpp is built locally with native CPU detection, not forced AVX2 flags.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).resolve().parent
LLAMA_VERSION = '0.3.34'
BASE_FLAGS = ('-DCMAKE_BUILD_TYPE=Release', '-DGGML_NATIVE=ON',
              '-DGGML_METAL=OFF', '-DGGML_CUDA=OFF', '-DGGML_VULKAN=OFF',
              '-DGGML_OPENMP=ON', '-DLLAMA_CURL=OFF')


def data_root():
    if os.environ.get('MAAT_GUI_DATA_ROOT'):
        return Path(os.environ['MAAT_GUI_DATA_ROOT']).expanduser().resolve()
    base = Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share')))
    if not base.is_absolute():
        raise RuntimeError('XDG_DATA_HOME must be an absolute path.')
    return base/'MAAT-RPG'


def game_root():
    candidates = (ROOT/'maatos', ROOT/'MAAT RPG.app/Contents/Resources/maatos')
    for candidate in candidates:
        if (candidate/'gui/desktop.py').is_file():
            return candidate
    raise RuntimeError('Spieldateien fehlen / Game files missing.')


def distro_family():
    try:
        info = platform.freedesktop_os_release()
    except OSError:
        return 'unknown'
    names = set((info.get('ID','')+' '+info.get('ID_LIKE','')).lower().split())
    for family, aliases in [('debian',{'ubuntu','debian','linuxmint','pop'}),
                            ('fedora',{'fedora','rhel','centos'}),
                            ('arch',{'arch','manjaro'}), ('suse',{'opensuse','suse'})]:
        if names & aliases:
            return family
    return 'unknown'


def system_commands(family):
    return {
        'debian': [
            'sudo apt update',
            'sudo apt install python3 python3-venv python3-dev build-essential cmake pkg-config '
            'libopenblas-dev libgl1 libegl1 libxkbcommon-x11-0 libxcb-cursor0 '
            'libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 '
            'libxcb-xinerama0 libxcb-xkb1 libx11-xcb1 libdbus-1-3 libpulse0 '
            'ffmpeg speech-dispatcher espeak-ng fonts-dejavu-core fonts-noto-color-emoji'],
        'fedora': ['sudo dnf install python3 python3-pip python3-devel gcc gcc-c++ make cmake '
                   'pkgconf-pkg-config openblas-devel mesa-libGL mesa-libEGL libxkbcommon-x11 '
                   'xcb-util-cursor xcb-util-image xcb-util-keysyms xcb-util-renderutil xcb-util-wm '
                   'libX11-xcb pulseaudio-libs ffmpeg-free speech-dispatcher espeak-ng dejavu-sans-fonts'],
        'arch': ['sudo pacman -S --needed python python-pip base-devel cmake pkgconf openblas '
                 'libglvnd libxkbcommon-x11 xcb-util-cursor xcb-util-image xcb-util-keysyms '
                 'xcb-util-renderutil xcb-util-wm libpulse ffmpeg speech-dispatcher espeak-ng ttf-dejavu'],
        'suse': ['sudo zypper install python312 python312-pip python312-devel gcc gcc-c++ make '
                 'cmake pkg-config openblas-devel libGL1 libEGL1 libxkbcommon-x11-0 '
                 'libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 '
                 'libpulse0 speech-dispatcher espeak-ng'],
    }.get(family, ['Install Python 3.10–3.13 + venv + headers, C/C++ compiler, make, cmake, '
                   'pkg-config, OpenBLAS development files, Qt X11/Wayland runtime libraries, '
                   'PulseAudio/PipeWire compatibility libraries and optional speech-dispatcher/espeak-ng.'])


def cmake_flags(openblas):
    return [*BASE_FLAGS, '-DGGML_BLAS='+('ON' if openblas else 'OFF'),
            *(['-DGGML_BLAS_VENDOR=OpenBLAS'] if openblas else [])]


def cpu_identity():
    try:
        return sorted(set(line.strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                          if line.split(':',1)[0].strip() in {'model name','flags','Features','CPU part'}))
    except OSError:
        return [platform.machine(),platform.processor()]


def check_libc():
    name,version=platform.libc_ver()
    minimum=(2,39) if platform.machine().lower() in {'aarch64','arm64'} else (2,28)
    try:current=tuple(int(n) for n in version.split('.')[:2])
    except ValueError:current=()
    if name!='glibc' or current<minimum:
        wanted='.'.join(map(str,minimum))
        raise RuntimeError(f'Qt Linux wheels require glibc {wanted}+ for this architecture; '
                           f'detected {name or "unknown"} {version}. See README-LINUX.md.')


def build_environment(openblas):
    env = dict(os.environ)
    # A macOS preset or a copied CUDA environment must not change this CPU build.
    for key in ('CMAKE_ARGS','CFLAGS','CXXFLAGS','LDFLAGS','ARCHFLAGS','CC','CXX',
                'CMAKE_OSX_ARCHITECTURES','MACOSX_DEPLOYMENT_TARGET','LLAMA_CPP_LIB_PATH'):
        env.pop(key, None)
    env.update(CMAKE_ARGS=' '.join(cmake_flags(openblas)), FORCE_CMAKE='1',
               CMAKE_BUILD_PARALLEL_LEVEL=str(max(1,min(4,os.cpu_count() or 1))),
               PYTHONNOUSERSITE='1', PYTHONUNBUFFERED='1')
    return env


def run(command, log, *, env=None, required=True):
    print('\n+ '+shlex.join(map(str,command)),flush=True)
    log.write('\n+ '+shlex.join(map(str,command))+'\n');log.flush()
    process=subprocess.Popen(list(map(str,command)),stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,text=True,errors='replace',env=env)
    for line in process.stdout:
        print(line,end='',flush=True);log.write(line);log.flush()
    code=process.wait()
    if code and required:
        raise RuntimeError(f'Installation fehlgeschlagen / Installation failed (exit {code}).')
    return code == 0


def desktop_quote(value):
    # Desktop Exec uses its own escaping and % field codes, not shell quoting.
    value=str(value).replace('%','%%')
    for ch in ('\\','"','`','$'):
        value=value.replace(ch,'\\'+ch)
    return '"'+value+'"'


def install_shortcut():
    base=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
    target=base/'applications/maat-rpg.desktop'
    target.parent.mkdir(parents=True,exist_ok=True)
    command='/bin/bash '+desktop_quote(ROOT/'Start Linux.sh')
    if os.environ.get('MAAT_GUI_DATA_ROOT'):
        command='/usr/bin/env '+desktop_quote('MAAT_GUI_DATA_ROOT='+str(data_root()))+' '+command
    target.write_text('[Desktop Entry]\nType=Application\nName=MAAT RPG\n'
                      'Comment=Local AI role-playing game\nComment[de]=Rollenspiel mit lokaler KI\n'
                      'Exec='+command+'\n'
                      'Icon=applications-games\nTerminal=true\nCategories=Game;RolePlaying;\n',encoding='utf-8')
    return target


def main(argv=None):
    parser=argparse.ArgumentParser(description='MAAT RPG · Linux GUI setup (DE/EN)')
    parser.add_argument('--system-deps',action='store_true',help='Show system package commands; do not install')
    parser.add_argument('--rebuild-backend',action='store_true',help='Rebuild after changing CPU or repairing the backend')
    parser.add_argument('--no-shortcut',action='store_true')
    args=parser.parse_args(argv)
    commands=system_commands(distro_family())
    if args.system_deps:
        print('\n'.join(commands));return 0
    if platform.system() != 'Linux':
        print('Nur für Linux / Linux only. macOS: Start GUI.command');return 1
    if hasattr(os,'geteuid') and os.geteuid()==0:
        print('Ohne sudo starten / Run this installer without sudo.');return 1
    if platform.machine().lower() not in {'x86_64','amd64','aarch64','arm64'}:
        print('64-bit Intel/AMD or ARM required.');return 1
    if not ((3,10) <= sys.version_info[:2] < (3,14)):
        print('Python 3.10–3.13 required; choose with MAAT_SETUP_PYTHON.');return 1
    try:
        check_libc()
        game_root()
        missing=[name for name in ('cmake','make','pkg-config') if not shutil.which(name)]
        if not (shutil.which('g++') or shutil.which('clang++')):
            missing.append('C++ compiler')
        if missing:
            raise RuntimeError('Fehlende Build-Werkzeuge / Missing build tools: '+', '.join(missing))
        data=data_root();folder=data/'linux-env';logs=data/'logs';logs.mkdir(parents=True,exist_ok=True)
        logpath=logs/f'linux-setup-{datetime.now():%Y%m%d-%H%M%S}.log'
        print('MAAT RPG · Linux GUI\nDaten / Data: '+str(data)+'\nLog: '+str(logpath),flush=True)
        with logpath.open('w',encoding='utf-8',buffering=1) as log:
            if not (folder/'bin/python').is_file():
                venv.EnvBuilder(with_pip=True).create(folder)
            python=folder/'bin/python'
            probe=subprocess.run([str(python),'-c','import sys; print(sys.version_info.minor)'],
                                 capture_output=True,text=True)
            if probe.returncode or probe.stdout.strip() not in {'10','11','12','13'}:
                raise RuntimeError('linux-env Python incompatible. Use a supported Python; saves are separate from linux-env.')
            pip=[python,'-m','pip','--isolated']
            env=build_environment(False)
            run([*pip,'install','--upgrade','pip','setuptools','wheel'],log,env=env)
            run([*pip,'install','--only-binary=:all:','-r',CONFIG/'requirements.txt'],log,env=env)
            openblas=subprocess.run(['pkg-config','--exists','openblas'],check=False).returncode==0
            if not openblas:
                print('OpenBLAS nicht gefunden: CPU-Fallback / OpenBLAS missing: CPU fallback.',flush=True)
            signature=dict(version=LLAMA_VERSION,machine=platform.machine(),cpu=cpu_identity(),flags=cmake_flags(openblas),
                           python_minor=probe.stdout.strip())
            marker=folder/'maat-backend.json'
            try:previous=json.loads(marker.read_text())
            except (OSError,ValueError):previous={}
            backend_probe=subprocess.run([str(python),'-c','import llama_cpp'],capture_output=True)
            if args.rebuild_backend or previous != signature or backend_probe.returncode:
                marker.unlink(missing_ok=True)
                print('KI-Backend wird für diese CPU gebaut; der erste Aufbau kann mehrere Minuten dauern.\n'
                      'Building AI backend for this CPU; the first build can take several minutes.',flush=True)
                run([*pip,'install','--no-cache-dir','--no-binary=llama-cpp-python','--force-reinstall',
                     '--no-deps',f'llama-cpp-python=={LLAMA_VERSION}'],log,env=build_environment(openblas))
                # Import in a subprocess catches native loader failures/illegal CPU instructions.
                run([python,'-c','import llama_cpp; print(llama_cpp.llama_print_system_info().decode())'],log,env=env)
                marker.write_text(json.dumps(signature,indent=2)+'\n')
            if not run([*pip,'install','--only-binary=:all:','libzim==3.10.0'],log,env=env,required=False):
                print('Offline-Wiki vorerst nicht verfügbar; Spiel läuft weiter.\n'
                      'Offline Wiki unavailable for now; the rest of the game can run.')
            run([python,CONFIG/'launcher.py','--check'],log,env=env)
        if not args.no_shortcut:
            print('Menüeintrag / Menu entry: '+str(install_shortcut()))
        print('\nFertig / Ready. Start: bash '+shlex.quote(str(ROOT/'Start Linux.sh')))
        return 0
    except (OSError,RuntimeError,subprocess.SubprocessError) as exc:
        print('\n'+str(exc)+'\nSystempakete / System packages:\n'+'\n'.join(commands),file=sys.stderr)
        print('Bei Python-venv-Fehlern das passende python3-venv-Paket installieren.\n'
              'For Python venv errors, install the matching python3-venv package.',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
