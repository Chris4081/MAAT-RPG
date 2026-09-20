#!/usr/bin/env python3
"""Read-only runtime inspection; writes an evidence inventory, not legal clearance."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from email.parser import Parser
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / 'build/macos/payload/Applications/MAAT RPG.app/Contents/Resources'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def record(path, base):
    return dict(path=path.relative_to(base).as_posix(), bytes=path.stat().st_size, sha256=digest(path))


def native_kind(path):
    """Recognize library files, including extensionless macOS framework binaries."""
    if path.suffix in {'.dylib', '.so'}:
        return 'python_extension' if path.suffix == '.so' else 'dynamic_library'
    if path.name + '.framework' in path.parts:
        return 'framework'
    return None


def inspect(resources):
    runtime = resources / 'runtimes'
    if not runtime.is_dir():
        raise ValueError(f'Runtime folder missing: {runtime}')
    report = dict(schema_version=2, checked_utc=datetime.now(timezone.utc).isoformat(),
                  scope='Prepared macOS payload; not a newly extracted installer; static inspection only.',
                  legal_clearance=False, packages=[], native_libraries=[], notices=[], warnings=[])
    manifest = resources / 'BUILD-MANIFEST.json'
    if manifest.is_file():
        report['build_manifest'] = record(manifest, resources)
    # Include notices stored outside dist-info too (e.g. CPython and vendored code).
    for path in sorted(runtime.rglob('*')):
        if path.is_file() and any(word in path.name.lower() for word in ('license', 'copying', 'copyright', 'notice')):
            report['notices'].append(record(path, runtime))
    for directory in sorted(runtime.rglob('*.dist-info')):
        metadata = directory / 'METADATA'
        if not metadata.is_file():
            report['warnings'].append('No METADATA: ' + directory.relative_to(runtime).as_posix())
            continue
        info = Parser().parsestr(metadata.read_text(errors='replace'))
        prefix = directory.relative_to(runtime).as_posix() + '/'
        notices = [item['path'] for item in report['notices'] if item['path'].startswith(prefix)]
        package = dict(name=info.get('Name', directory.name), version=info.get('Version'),
                       location=directory.relative_to(runtime).as_posix(),
                       metadata_sha256=digest(metadata),
                       license_expression=info.get('License-Expression'),
                       license_field=info.get('License'),
                       license_classifiers=[s for s in info.get_all('Classifier', []) if s.startswith('License ::')],
                       declared_license_files=info.get_all('License-File', []), notice_files=notices,
                       source_status='Not established by metadata alone')
        report['packages'].append(package)
        if not notices:
            report['warnings'].append('No license text found inside dist-info: ' + prefix.rstrip('/'))
    seen = set()
    for path in sorted(runtime.rglob('*')):
        kind = native_kind(path)
        if not kind or not path.is_file():
            continue
        # Only unique physical libraries; aliases still remain in the original payload.
        real = path.resolve()
        if real in seen:
            continue
        seen.add(real)
        item = record(path, runtime)
        item['kind'] = kind
        if path.name.startswith('libavutil'):
            strings = subprocess.run(['/usr/bin/strings', '-n', '3', str(path)],
                                     text=True, errors='replace', capture_output=True, check=True).stdout.splitlines()
            item['embedded_ffmpeg_configurations'] = list(dict.fromkeys(s for s in strings if '--disable-programs' in s))
            item['source_status'] = 'Configuration strings are evidence, not verification of exact corresponding source.'
        report['native_libraries'].append(item)
    report['warnings'].extend([
        'Standard license supplements do not replace component-specific notices or corresponding-source obligations.',
        'Vendored/static dependencies require further component-level review.',
        'Native coverage includes .dylib, .so and framework binaries; standalone executables are not inventoried.',
        'Bundled Qt add-on frameworks require module-specific license and source mapping, even if unused by the game.',
        'No inference of native libzim source version from Python package version or ABI filename.',
        'Archive contents, model weights and private user data are outside this runtime audit.',
    ])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resources', type=Path, default=PAYLOAD)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/licensing/RUNTIME_AUDIT.json')
    args = parser.parse_args()
    report = inspect(args.resources)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"{len(report['packages'])} package records, {len(report['notices'])} notices, "
          f"{len(report['native_libraries'])} native libraries. Complete legal clearance: no.")
    print(args.output)


if __name__ == '__main__':
    main()
