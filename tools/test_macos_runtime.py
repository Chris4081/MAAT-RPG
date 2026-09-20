#!/usr/bin/env python3
"""Test both staged runtimes with read-only app resources and temporary profiles."""
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'build/macos/payload/Applications/MAAT RPG.app'
OUT = ROOT / 'build/macos/test-results'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    modes = [(p, p.stat().st_mode & 0o777) for p in [APP, *APP.rglob('*')] if not p.is_symlink()]
    try:
        for path, mode in modes:
            path.chmod(mode & ~0o222)
        reports = []
        for arch in ('arm64', 'x86_64'):
            env = dict(os.environ, MAAT_TEST_ARCH=arch)
            env.pop('LLAMA_CPP_LIB_PATH', None)
            env.pop('MAAT_CPU_VARIANT', None)
            result = subprocess.run([str(APP / 'Contents/MacOS/run.sh'), '--self-test'],
                                    env=env, capture_output=True, text=True, timeout=180)
            (OUT / f'{arch}.log').write_text(result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError(f'{arch} test failed ({result.returncode}); see {OUT / (arch + ".log")}')
            match = re.search(r'\{\s*"architecture".*\}', result.stdout, re.S)
            report = json.loads(match.group()) if match else {}
            if report.get('gguf_adapter') != ('llama_intel' if arch == 'x86_64' else 'llama'):
                raise RuntimeError(f'Wrong GGUF adapter for {arch}: {report}')
            if report.get('architecture') != arch or any(report.get(key) != 'ok' for key in
                    ('game_worker', 'audio_helper', 'audio_output_switch', 'model_settings', 'title_artwork', 'level_up', 'input_filter', 'dungeon_refresh', 'chat_response', 'model_timing')):
                raise RuntimeError(f'Invalid runtime result: {report}')
            report['app_resources_read_only'] = True
            reports.append(report)
            print(f'PASS: {arch}, read-only app, language, worker, battle, wiki, model settings, audio helper, title artwork, level-up, input filter, chat response, model timing', flush=True)
        if (APP / 'Contents/Resources/maatos/data').exists():
            raise RuntimeError('A plugin created a data folder inside the app')
        (OUT / 'runtime-tests.json').write_text(json.dumps(reports, indent=2) + '\n')
    finally:
        for path, mode in modes:
            if path.exists():
                path.chmod(mode)


if __name__ == '__main__':
    main()
