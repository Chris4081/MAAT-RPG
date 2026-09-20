#!/usr/bin/env python3
"""Linux launcher with child-process Qt checks and readable startup failures."""
from __future__ import annotations
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from setup_linux import data_root, game_root, system_commands, distro_family


QT_CHECK = '''from PySide6.QtWidgets import QApplication
from PySide6 import QtCore, QtMultimedia, QtSvg, QtSvgWidgets
import colorama, yaml, requests, numpy, jinja2
app=QApplication([])
print('Qt', QtCore.qVersion(), 'platform', app.platformName())
'''


def runtime_environment():
    env=dict(os.environ)
    env.update(PYTHONNOUSERSITE='1',PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1')
    # Native libraries must come from the Linux venv, not copied macOS paths
    # or Qt plugins injected by another Python distribution (e.g. OpenCV).
    for key in ('PYTHONHOME','PYTHONPATH','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH',
                'LLAMA_CPP_LIB_PATH'):
        env.pop(key,None)
    # QApplication chooses the display backend. Do not force X11 over Wayland;
    # a user-provided QT_QPA_PLATFORM remains an explicit troubleshooting option.
    return env


def check_qt(env, log):
    try:
        probe=subprocess.run([sys.executable,'-c',QT_CHECK],env=env,
                             capture_output=True,text=True,errors='replace',timeout=25)
        log.write(probe.stdout+probe.stderr);log.flush()
    except subprocess.TimeoutExpired:
        print('Qt-Startprüfung hängt / Qt startup check timed out.',file=sys.stderr)
        return False
    if probe.returncode:
        print(probe.stdout+probe.stderr,file=sys.stderr)
        print('Grafikbibliotheken oder Desktop-Sitzung fehlen / Check graphics libraries and desktop session.\n'
              +'\n'.join(system_commands(distro_family())),file=sys.stderr)
        return False
    print(probe.stdout.strip())
    return True


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if platform.system()!='Linux':
        print('Linux launcher only. macOS: Start GUI.command',file=sys.stderr);return 1
    check='--check' in args
    if check:args.remove('--check')
    env=runtime_environment()
    if not (env.get('DISPLAY') or env.get('WAYLAND_DISPLAY') or
            env.get('QT_QPA_PLATFORM') in {'offscreen','minimal'}):
        if not check:
            print('Bitte in einer grafischen Linux-Sitzung starten.\n'
                  'Please start inside a graphical Linux desktop session.',file=sys.stderr);return 1
        env['QT_QPA_PLATFORM']='offscreen'
    try:
        game=game_root();data=data_root();logs=data/'logs';logs.mkdir(parents=True,exist_ok=True)
        if env.get('MAAT_GUI_DATA_ROOT'):
            env['MAAT_GUI_DATA_ROOT']=str(data)
        path=logs/f'linux-start-{datetime.now():%Y%m%d-%H%M%S}-{os.getpid()}.log'
        print('MAAT RPG · Log: '+str(path),flush=True)
        with path.open('w',encoding='utf-8',buffering=1) as log:
            log.write(json.dumps(dict(platform=platform.platform(),machine=platform.machine(),
                                      python=sys.version.split()[0],check_only=check))+'\n')
            if not check_qt(env,log):return 1
            if check:
                # No model loaded; import is isolated from both installer and GUI.
                probe=subprocess.run([sys.executable,'-c','import llama_cpp; print(llama_cpp.llama_print_system_info().decode())'],
                                     env=env,capture_output=True,text=True,errors='replace',timeout=30)
                log.write(probe.stdout+probe.stderr);print(probe.stdout.strip())
                if probe.returncode:
                    print('KI-Backend fehlgeschlagen / AI backend failed.\n'
                          'bash "Install Linux.sh" --rebuild-backend',file=sys.stderr)
                    return 1
                return 0
            # Keep game stdout in the terminal, never save chat content here.
            result=subprocess.call([sys.executable,'-m','gui.desktop',*args],cwd=game,env=env)
            log.write(f'game_exit={result}\n')
        if result:
            print('MAAT wurde beendet / MAAT exited unexpectedly. Logs: '+str(logs),file=sys.stderr)
            if sys.stdin.isatty():
                try:input('Enter zum Schließen / Press Enter to close … ')
                except EOFError:pass
        return result if result>=0 else 128-result
    except (OSError,RuntimeError,subprocess.SubprocessError) as exc:
        print('MAAT Linux: '+str(exc),file=sys.stderr);return 1


if __name__=='__main__':
    raise SystemExit(main())
