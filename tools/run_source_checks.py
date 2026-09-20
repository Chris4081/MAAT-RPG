#!/usr/bin/env python3
"""Run representative existing tests with separate Qt processes and disposable data."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = (
    'test_linux_distribution', 'test_qt_runtime', 'test_desktop', 'test_backend_route',
    'test_intel_adapter', 'test_gguf_chat', 'test_mistral_compatibility',
    'test_gpt_oss', 'test_class_actions', 'test_boss_art', 'test_monster_variety',
    'test_prompt_prefix', 'test_history_settings', 'test_offline_wiki',
    'test_combat_sounds', 'test_music_free_source', 'test_maat_coil', 'test_temple_circles',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modules', nargs='*', help='Optional existing test module names')
    args = parser.parse_args()
    modules = args.modules or DEFAULTS
    for module in modules:
        if not module.startswith('test_') or not (ROOT / 'tests' / f'{module}.py').is_file():
            parser.error(f'Unknown test module: {module}')
    failed = []
    for module in modules:
        start = time.monotonic()
        with tempfile.TemporaryDirectory(prefix='maat-source-check-') as temporary:
            base = Path(temporary)
            env = dict(os.environ)
            env.update(
                QT_QPA_PLATFORM='offscreen', PYTHONDONTWRITEBYTECODE='1',
                PYTHONPATH=os.pathsep.join((str(ROOT/'maatos'), str(ROOT/'tests'))),
                MAAT_GUI_DATA_ROOT=str(base/'game'), MAAT_APP_SUPPORT_DIR=str(base/'game'),
                XDG_DATA_HOME=str(base/'xdg-data'), XDG_CONFIG_HOME=str(base/'xdg-config'),
                XDG_CACHE_HOME=str(base/'xdg-cache'),
            )
            env['APPDATA'] = str(base/'appdata')
            env['LOCALAPPDATA'] = str(base/'localappdata')
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'unittest', module, '-v'], cwd=ROOT,
                    env=env, capture_output=True, text=True, errors='replace', timeout=90,
                )
                ok = result.returncode == 0
                output = result.stdout + result.stderr
                summary = next((line for line in output.splitlines() if line.startswith('Ran ')), 'No test summary')
                status = next((line for line in reversed(output.splitlines()) if line.startswith(('OK', 'FAILED'))), '')
                print(f'{module}: {"PASS" if ok else "FAIL"} — {summary}; {status} ({time.monotonic()-start:.1f}s)', flush=True)
                if not ok:
                    failed.append(module)
                    print(output[-16000:], flush=True)
            except subprocess.TimeoutExpired:
                failed.append(module)
                print(f'{module}: TIMEOUT', flush=True)
    print(f'{len(modules)-len(failed)}/{len(modules)} test modules passed.', flush=True)
    return bool(failed)


if __name__ == '__main__':
    raise SystemExit(main())
