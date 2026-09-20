#!/usr/bin/env python3
"""Check the staged installer for architecture, portability and private data."""
import concurrent.futures
import json
from pathlib import Path
import plistlib
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'build/macos/payload/Applications/MAAT RPG.app'
GAME = APP / 'Contents/Resources/maatos'
MAGIC = {b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xcf',
         b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca'}


def check_binary(path):
    relative = path.relative_to(APP).as_posix()
    required = ['arm64'] if '/runtimes/arm64/' in relative else ['x86_64'] if '/runtimes/x86_64/' in relative else ['arm64', 'x86_64']
    arches = subprocess.check_output(['/usr/bin/lipo', '-archs', path], text=True).split()
    errors = []
    if not all(arch in arches for arch in required):
        errors.append(f'Wrong architecture {arches}: {relative}')
    commands = subprocess.check_output(['/usr/bin/otool', '-l', path], text=True)
    lines = commands.splitlines()
    identities = set()
    versions = []
    for i, line in enumerate(lines):
        if line.strip() == 'cmd LC_ID_DYLIB':
            identities.add(lines[i + 2].strip().removeprefix('name ').split(' (offset ')[0])
        elif line.strip() == 'cmd LC_BUILD_VERSION':
            versions.append(lines[i + 3].strip().removeprefix('minos '))
        elif line.strip() == 'cmd LC_VERSION_MIN_MACOSX':
            versions.append(lines[i + 2].strip().removeprefix('version '))
    linked = subprocess.check_output(['/usr/bin/otool', '-L', path], text=True)
    for line in linked.splitlines():
        if not line.startswith('\t'):
            continue
        dep = line.strip().split(' (')[0]
        if dep in identities:
            continue
        if dep.startswith('/') and not dep.startswith(('/System/Library/', '/usr/lib/')):
            errors.append(f'External library: {relative} -> {dep}')
        if dep.startswith('@loader_path/'):
            resolved = path.parent / dep[len('@loader_path/'):]
            if not resolved.exists():
                errors.append(f'Missing linked library: {relative} -> {dep}')
    for i, line in enumerate(lines):
        if line.strip() == 'cmd LC_RPATH':
            rpath = lines[i + 2].strip().removeprefix('path ').split(' (offset ')[0]
            if rpath.startswith('/') and not rpath.startswith(('/System/', '/usr/lib/')):
                errors.append(f'External runtime path: {relative} -> {rpath}')
    for version in versions:
        if tuple(map(int, version.split('.')))[:2] > (13, 3):
            errors.append(f'Requires newer macOS {version}: {relative}')
    return errors


def main():
    errors, binaries = [], []
    # Verify the shipped CPU libraries themselves, including the versioned
    # filename actually referenced by libllama. A portable-only payload must
    # never silently pass the Intel performance check.
    intel = APP/'Contents/Resources/runtimes/x86_64/lib/python3.11/site-packages/llama_cpp/lib'
    variants = {}
    for variant, folder, enabled in [('portable', intel, False), ('avx2', intel/'avx2', True)]:
        library = folder/'libggml-cpu.0.dylib'
        if not library.is_file():
            errors.append(f'Missing Intel CPU library: {library.relative_to(APP)}')
            continue
        assembly = subprocess.check_output(['/usr/bin/otool', '-tvV', library], text=True)
        flags = {}
        for feature in ('avx', 'avx2', 'fma', 'f16c', 'bmi2'):
            block = re.search(r'^_ggml_cpu_has_' + feature + r':\n(.*?\bretq)', assembly, re.M | re.S)
            body = block.group(1) if block else ''
            pattern = r'movl\s+\$0x1,\s*%eax' if enabled else r'xorl\s+%eax,\s*%eax'
            flags[feature] = bool(re.search(pattern, body))
            if not flags[feature]:
                errors.append(f'Intel {variant}: compiled {feature} capability does not match expected {enabled}')
        variants[variant] = dict(expected_enabled=enabled, compiled_flags_verified=flags)
    for name in ('data', 'logs', 'models', 'state', 'saves', 'cache', 'tools'):
        if (GAME / name).exists():
            errors.append(f'Unexpected development/user directory: {name}')
    for path in APP.rglob('*'):
        if path.is_symlink():
            if not path.resolve().is_relative_to(APP.resolve()):
                errors.append(f'Escaping symlink: {path}')
            continue
        if path.is_dir():
            if path.stat().st_mode & 0o005 != 0o005:
                errors.append(f'Directory not readable/traversable by player: {path}')
            continue
        if not path.is_file():
            continue
        if path.stat().st_mode & 0o004 == 0:
            errors.append(f'File not readable by player: {path}')
        if path.is_relative_to(GAME) and path.suffix in {'.gguf', '.zim', '.db', '.sqlite', '.bak', '.log'}:
            errors.append(f'Private/development payload: {path.relative_to(GAME)}')
        with path.open('rb') as f:
            if f.read(4) in MAGIC:
                binaries.append(path)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for result in pool.map(check_binary, binaries):
            errors.extend(result)
    info = plistlib.loads((APP / 'Contents/Info.plist').read_bytes())
    if info['LSMinimumSystemVersion'] != '13.3':
        errors.append('App minimum macOS does not match installer')
    result = dict(macho_binaries=len(binaries), architecture_and_linkage='passed' if not errors else 'failed',
                  intel_cpu_variants=variants,
                  personal_data='excluded', minimum_macos=info['LSMinimumSystemVersion'], errors=errors)
    print(json.dumps(result, indent=2))
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
