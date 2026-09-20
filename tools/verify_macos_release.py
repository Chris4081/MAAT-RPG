#!/usr/bin/env python3
"""Verify the finished installer against the tested stage and current game files."""
from datetime import datetime, timezone
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import plistlib
import runpy
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'build/macos'
DIST = ROOT / 'dist/macos'
STAGE = WORK / 'payload/Applications/MAAT RPG.app'
VERSION = runpy.run_path(str(ROOT / 'tools/build_macos_setup.py'))['VERSION']


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inventory(root):
    result = {}
    for path in root.rglob('*'):
        if path.name == '.DS_Store':
            continue
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[name] = ('symlink', str(path.readlink()))
        elif path.is_file():
            result[name] = ('file', digest(path))
    return result


def main():
    package = DIST / 'MAAT-RPG-macOS-Intel-ARM.pkg'
    package_hash = digest(package)
    assert package_hash == (DIST / 'SHA256.txt').read_text().split()[0]
    regressions = json.loads((WORK / f'test-results/regressions-{VERSION}.json').read_text())
    assert regressions['version'] == VERSION and regressions['passed']
    audit = json.loads((WORK / 'test-results/binary-audit.json').read_text())
    assert audit['architecture_and_linkage'] == 'passed' and not audit['errors']
    runtimes = json.loads((DIST / 'RUNTIME-TESTS.json').read_text())
    assert {r['architecture'] for r in runtimes} == {'arm64', 'x86_64'}
    for runtime in runtimes:
        assert runtime['version'] == VERSION, 'stale runtime report'
        if runtime.get('status') == 'blocked':
            assert '--allow-runtime-blocked' in sys.argv, 'runtime execution is blocked; review the report explicitly'
            assert runtime.get('error') and runtime.get('attempted_at'), 'missing runtime failure evidence'
            runtime_python = STAGE / 'Contents/Resources/runtimes' / runtime['architecture'] / 'bin/python3.11'
            assert runtime['python_sha256'] == digest(runtime_python), 'runtime changed since probe'
            continue
        expected = 'llama_intel' if runtime['architecture'] == 'x86_64' else 'llama'
        assert runtime['gguf_adapter'] == expected
        assert runtime['app_resources_read_only']
        for feature in ('game_worker', 'audio_helper', 'audio_output_switch', 'model_settings',
                        'title_artwork', 'level_up', 'input_filter', 'dungeon_refresh',
                        'chat_response', 'model_timing'):
            assert runtime[feature] == 'ok', (runtime['architecture'], feature)
    streamed = '--stream' in sys.argv
    workspace = nullcontext() if streamed else tempfile.TemporaryDirectory(prefix='package-verification-', dir=WORK)
    with workspace as folder:
        if streamed:
            from macos_package_inventory import read_installer
            print('Reading installer contents without expanding files to disk.', flush=True)
            info, distribution, component, installed_files = read_installer(package)
        else:
            expanded = Path(folder) / 'expanded'
            subprocess.run(['/usr/sbin/pkgutil', '--expand-full', str(package), str(expanded)], check=True)
            installed = next(expanded.glob('*.pkg/Payload/Applications/MAAT RPG.app'))
            component_root = installed.parents[2]
            assert not (component_root / 'Scripts').exists(), 'unexpected installation scripts'
            info = plistlib.loads((installed / 'Contents/Info.plist').read_bytes())
            distribution = ET.parse(expanded / 'Distribution').getroot()
            component = ET.parse(component_root / 'PackageInfo').getroot()
            installed_files = inventory(installed)
        assert info['CFBundleVersion'] == info['CFBundleShortVersionString'] == VERSION
        assert info['LSMinimumSystemVersion'] == '13.3'
        assert set(distribution.find('options').get('hostArchitectures').split(',')) == {'arm64', 'x86_64'}
        assert distribution.find('volume-check/allowed-os-versions/os-version').get('min') == '13.3'
        assert distribution.find('pkg-ref[@version]').get('version') == VERSION
        assert component.get('version') == VERSION and component.get('install-location') == '/'
        print('Checking installer against the tested stage.', flush=True)
        staged_files = inventory(STAGE)
        differences = [name for name in staged_files.keys() | installed_files.keys()
                       if staged_files.get(name) != installed_files.get(name)]
        assert not differences, differences[:20]
        prefix = 'Contents/Resources/maatos/'
        source_hashes = {name[len(prefix):]: value for name, (kind, value) in installed_files.items()
                         if name.startswith(prefix) and kind == 'file'}
        game_source = ROOT / 'maatos'
        expected = {}
        for path in game_source.rglob('*'):
            if not path.is_file():
                continue
            relative = path.relative_to(game_source)
            if relative.parts[0] in {'data', 'logs', 'models', 'state', 'saves', 'cache', 'tools'}:
                continue
            if any(part in {'.DS_Store', '__pycache__', '.git', '.pytest_cache'} for part in relative.parts):
                continue
            if path.suffix in {'.pyc', '.bak', '.gguf', '.zim'}:
                continue
            if relative.as_posix().startswith('apps/maat_rpg/plugins/maat_fields/data/'):
                continue
            expected[relative.as_posix()] = digest(path)
        assert expected == source_hashes, 'source snapshot differs from installer'
        for required in ('gui/game_worker.py', 'gui/runtime_diagnostics.py', 'gui/battle_editor.py',
                         'shared/core/battle_editor.py', 'shared/core/command_i18n.py',
                         'shared/core/monster_catalog.py', 'gui/maat_guide_content.py',
                         'shared/core/boss_art.py',
                         'gui/assets/combat/boss25_ra.svg',
                         'gui/assets/combat/attacks/boss25_ra-impulse.svg',
                         'apps/maat_rpg/plugins/battle/music/credits_en.mp3',
                         'gui/maat_guide.py', 'shared/core/intel_gguf_backend.py',
                         'shared/core/gpt_oss.py', 'gui/plugin_settings.py',
                         'gui/reply_formatting.py', 'gui/chat_response.py',
                         'shared/core/arena_difficulty.py', 'shared/core/ai_plugin_settings.py',
                         'shared/core/maat_reality_layer.py', 'shared/core/reply_style.py',
                         'shared/plugins/maat_reply_style/plugin_main.py',
                         'shared/core/tinyllama.py', 'gui/combat_input.py',
                         'shared/core/repetition_guard.py', 'shared/core/maat_style.py',
                         'shared/plugins/maat_style/plugin_main.py',
                         'apps/maat_rpg/plugins/rpg_identity/plugin_main.py'):
            assert required in source_hashes, required
        assert 'shared/core/minimum_reply.py' not in source_hashes, 'retired hard token minimum must not ship'
        assert 'apps/maat_rpg/plugins/battle/music/credits_theme_en_aac.m4a' not in source_hashes
        assert 'apps/maat_rpg/plugins/battle/music/credits_theme_en.m4a' not in source_hashes
        print(f'PASS: {len(installed_files)} packaged entries and {len(source_hashes)} current game files.', flush=True)
    report = dict(version=VERSION, created_at=datetime.now(timezone.utc).isoformat(),
                  package=package.name, bytes=package.stat().st_size, sha256=package_hash,
                  package_payload='passed', packaged_entries=len(installed_files),
                  payload_verification='streamed gzip CRC and per-file SHA-256' if streamed else 'expanded per-file SHA-256',
                  current_game_files=len(source_hashes), install_destination='/Applications/MAAT RPG.app',
                  minimum_macos='13.3', personal_data='excluded', installation_scripts=False,
                  source_regression_tests=regressions['tests'], source_regression_result='passed',
                  source_regression_modules=regressions['modules'], translations=regressions['translations'],
                  context_default=20000, context_maximum=100000,
                  runtime_execution=('blocked; see per-architecture evidence' if any(r.get('status') == 'blocked' for r in runtimes) else 'passed'),
                  intel_execution=('Blocked in this test environment; no physical Intel test here.' if next(r for r in runtimes if r['architecture'] == 'x86_64').get('status') == 'blocked' else 'Bundled x86_64 runtime tested; no physical Intel test here.'),
                  regression_execution=regressions.get('execution'),
                  intel_avx2='Compiled libraries audited; selection tested; native Intel performance not measured.',
                  real_model_weights_retested=False,
                  model_cleanup='Explicit native close tested, including replacement, EOF and speech teardown failure.',
                  metal_reproduction='Historical 0.4.7 check: development-runtime synthetic 81,760-byte GGUF aborted before the fix and exited 0 after it; not repeated for this package.',
                  developer_id_signed=False, notarized=False, binaries=audit, runtimes=runtimes)
    for field, filename in (('runtime_comparison', f'runtime-comparison-{VERSION}.json'),
                            ('staged_gui', f'staged-gui-{VERSION}.json')):
        evidence = WORK / 'test-results' / filename
        if evidence.is_file():
            details = json.loads(evidence.read_text())
            assert details['version'] == VERSION
            report[field] = details
    (DIST / 'VALIDIERUNG.json').write_text(json.dumps(report, indent=2) + '\n')
    (DIST / 'SOURCE-SNAPSHOT.json').write_text(json.dumps(dict(version=VERSION, sha256=source_hashes), indent=2) + '\n')
    (DIST / 'REGRESSION-TESTS.json').write_text(json.dumps(regressions, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('version', 'bytes', 'sha256', 'packaged_entries', 'current_game_files')}, indent=2))


if __name__ == '__main__':
    main()
