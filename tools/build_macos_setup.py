#!/usr/bin/env python3
"""Build an offline macOS installer; never installs into the developer's system.

--fetch downloads official, versioned runtime/source archives and PyPI wheels.
--build cross-compiles llama.cpp, assembles both runtimes and builds the .pkg.
Download hashes and package versions are preserved beside the installer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'packaging/macos'
WORK = ROOT / 'build/macos'
CACHE = WORK / 'downloads'
DIST = ROOT / 'dist/macos'
VERSION = '0.4.11'
ARCHES = ('arm64', 'x86_64')
PY_RELEASE = '20260901'
PY_VERSION = '3.11.16'
PY_SHA = {
    'arm64': '768f05cf200273bbdda9a5955a5a6892a4b22f2a0b1e4b0a9160f5c7fce86816',
    'x86_64': '908b381433f78b832c8d64960ced0f85871893cc8779f413f963e0c9e293c258',
}
LLAMA_URL = ('https://files.pythonhosted.org/packages/c1/2f/'
             '46487e949da42b31847853793ddbfd44c7414e94d4364c9a41f91f30af27/'
             'llama_cpp_python-0.3.34.tar.gz')
LLAMA_SHA = 'd849d286d808284f1d3ec1bd6875572430d29d1f9574a010232caa4e9cef0e35'


def run(args, **kwargs):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def download(url, path, expected):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and digest(path) == expected:
        return
    part = path.with_suffix(path.suffix + '.part')
    run(['/usr/bin/curl', '--fail', '--location', '--retry', '3',
         '--connect-timeout', '30', '--max-time', '900', '--output', part, url])
    if digest(part) != expected:
        raise RuntimeError(f'SHA-256 mismatch: {path.name}')
    part.replace(path)


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    manifest = {'python': PY_VERSION, 'llama_cpp_python': '0.3.34', 'archives': []}
    for arch in ARCHES:
        triple = 'aarch64' if arch == 'arm64' else arch
        name = f'cpython-{PY_VERSION}+{PY_RELEASE}-{triple}-apple-darwin-install_only_stripped.tar.gz'
        url = f'https://github.com/astral-sh/python-build-standalone/releases/download/{PY_RELEASE}/{name.replace("+", "%2B")}'
        path = CACHE / f'python-{arch}.tar.gz'
        download(url, path, PY_SHA[arch])
        manifest['archives'].append(dict(file=path.name, url=url, sha256=PY_SHA[arch]))
    download(LLAMA_URL, CACHE / 'llama.tar.gz', LLAMA_SHA)
    manifest['archives'].append(dict(file='llama.tar.gz', url=LLAMA_URL, sha256=LLAMA_SHA))
    for arch in ARCHES:
        dest = CACHE / f'wheels-{arch}'
        run([sys.executable, '-m', 'pip', '--isolated', '--cache-dir', CACHE / 'pip-cache',
             'download', '--index-url', 'https://pypi.org/simple', '--only-binary=:all:',
             '--platform', f'macosx_13_0_{arch}', '--python-version', '311',
             '--implementation', 'cp', '--abi', 'cp311', '--dest', dest,
             '-r', CONFIG / 'requirements.txt'])
        for wheel in sorted(dest.glob('*.whl')):
            manifest['archives'].append(dict(file=str(wheel.relative_to(CACHE)), sha256=digest(wheel),
                                              source='https://pypi.org/simple'))
    (CACHE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def verify_downloads():
    manifest = json.loads((CACHE / 'manifest.json').read_text())
    for item in manifest['archives']:
        path = CACHE / item['file']
        if not path.is_file() or digest(path) != item['sha256']:
            raise RuntimeError(f'Download missing or modified: {path}')
    return manifest


def extract_tar(archive, dest):
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        # data filter prevents absolute paths and escaping symlinks.
        tar.extractall(dest, filter='data')


def unpack_wheel(wheel, target):
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel) as z:
        for entry in z.infolist():
            parts = Path(entry.filename).parts
            if not parts or '..' in parts or Path(entry.filename).is_absolute():
                raise RuntimeError(f'Unsafe wheel entry: {entry.filename}')
            if '.data' in parts[0]:
                if len(parts) < 3 or parts[1] not in ('purelib', 'platlib'):
                    continue  # CLI scripts/headers are not needed by the game.
                parts = parts[2:]
            output = target.joinpath(*parts)
            if entry.is_dir():
                output.mkdir(parents=True, exist_ok=True)
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                with z.open(entry) as source, output.open('wb') as dest:
                    shutil.copyfileobj(source, dest)
                mode = entry.external_attr >> 16
                output.chmod(0o755 if mode & 0o111 else 0o644)


def remove_build_rpaths(libdest):
    for lib in libdest.rglob('*'):
        if not lib.is_file() or lib.suffix not in {'.dylib', '.so'}:
            continue
        commands = subprocess.check_output(['/usr/bin/otool', '-l', lib], text=True)
        lines = commands.splitlines()
        changed = False
        for i, line in enumerate(lines):
            if line.strip() == 'cmd LC_RPATH':
                path = lines[i + 2].strip().removeprefix('path ').split(' (offset ')[0]
                if path.startswith('/') and not path.startswith(('/System/', '/usr/lib/')):
                    run(['/usr/bin/install_name_tool', '-delete_rpath', path, lib])
                    changed = True
        if changed:
            run(['/usr/bin/codesign', '--force', '--sign', '-', lib])


def build_backend(source, arch, optimized=False):
    variant = arch + ('-avx2' if optimized else '')
    build = WORK / f'llama-{variant}'
    libdest = WORK / 'backends' / variant
    cache = build / 'CMakeCache.txt'
    expected = {'GGML_NATIVE': 'OFF', 'GGML_ACCELERATE': 'ON', 'GGML_BLAS': 'ON',
                'GGML_METAL': 'ON' if arch == 'arm64' else 'OFF'}
    if arch == 'x86_64':
        expected.update({f'GGML_{flag}': 'ON' if optimized else 'OFF'
                         for flag in ('AVX', 'AVX2', 'FMA', 'F16C', 'BMI2')})
        expected.update(GGML_AVX512='OFF', GGML_AVX_VNNI='OFF')
    cached = set(cache.read_text().splitlines()) if cache.is_file() else set()
    marker = libdest / '.complete'
    signature = json.dumps(dict(version='0.3.34', architecture=arch, flags=expected), sort_keys=True)
    # A cached library built with different CPU flags must not be reused.
    if marker.is_file() and marker.read_text() == signature and all(f'{key}:BOOL={value}' in cached for key, value in expected.items()):
        remove_build_rpaths(libdest)
        return libdest
    marker.unlink(missing_ok=True)
    args = ['cmake', '-S', source / 'vendor/llama.cpp', '-B', build,
            '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_SHARED_LIBS=ON',
            f'-DCMAKE_OSX_ARCHITECTURES={arch}', '-DCMAKE_OSX_DEPLOYMENT_TARGET=13.0',
            '-DLLAMA_BUILD_TESTS=OFF', '-DLLAMA_BUILD_EXAMPLES=OFF',
            '-DLLAMA_BUILD_TOOLS=OFF', '-DLLAMA_BUILD_SERVER=OFF',
            '-DGGML_NATIVE=OFF', '-DGGML_OPENMP=OFF', '-DGGML_ACCELERATE=ON',
            '-DGGML_BLAS=ON', '-DGGML_BLAS_VENDOR=Apple',
            '-DGGML_METAL=' + ('ON' if arch == 'arm64' else 'OFF'),
            '-DGGML_METAL_EMBED_LIBRARY=ON', '-DLLAMA_CURL=OFF']
    if arch == 'x86_64':
        mode = 'ON' if optimized else 'OFF'
        args += [f'-DGGML_{flag}={mode}' for flag in ('AVX', 'AVX2', 'FMA', 'F16C', 'BMI2')]
        args += ['-DGGML_AVX512=OFF', '-DGGML_AVX_VNNI=OFF']
    run(args)
    run(['cmake', '--build', build, '--config', 'Release', '--target', 'llama', '-j', '4'])
    libdest.mkdir(parents=True, exist_ok=True)
    for path in (build / 'bin').glob('*.dylib*'):
        if path.is_file():
            shutil.copy2(path, libdest / path.name, follow_symlinks=True)
    if not (libdest / 'libllama.dylib').exists():
        raise RuntimeError(f'llama.cpp library missing: {arch}')
    # No references to the build directory or Homebrew may ship.
    for lib in libdest.iterdir():
        if not lib.is_file() or '.dylib' not in lib.name:
            continue
        run(['/usr/bin/install_name_tool', '-id', '@rpath/' + lib.name, lib])
        deps = subprocess.check_output(['/usr/bin/otool', '-L', lib], text=True)
        for line in deps.splitlines()[1:]:
            dep = line.strip().split(' (')[0]
            if Path(dep).name.startswith(('libggml', 'libllama')) and not dep.startswith('@'):
                run(['/usr/bin/install_name_tool', '-change', dep, '@loader_path/' + Path(dep).name, lib])
        for name in sorted(p.name for p in libdest.iterdir() if p.is_file()):
            if '@rpath/' + name in deps:
                run(['/usr/bin/install_name_tool', '-change', '@rpath/' + name, '@loader_path/' + name, lib])
        run(['/usr/bin/codesign', '--force', '--sign', '-', lib])
    remove_build_rpaths(libdest)
    marker.write_text(signature)
    return libdest


def clean_copy_game(dest):
    source = ROOT / 'maatos'
    staged_game = dest / 'Contents/Resources/maatos'
    if staged_game.exists():
        shutil.rmtree(staged_game)
    def ignored(directory, names):
        return [n for n in names if n in {
            '.DS_Store', '__pycache__', '.git', '.pytest_cache', 'data', 'logs',
            'models', 'state', 'saves', 'cache', 'tools', '.venv'
        } or n.endswith(('.pyc', '.bak', '.gguf', '.zim'))]
    shutil.copytree(CONFIG / 'app-template', dest, dirs_exist_ok=True)
    shutil.copytree(source, staged_game, ignore=ignored)
    info_path = dest / 'Contents/Info.plist'
    info = plistlib.loads(info_path.read_bytes())
    info.update(CFBundleVersion=VERSION, CFBundleShortVersionString=VERSION,
                LSMinimumSystemVersion='13.3', NSHighResolutionCapable=True,
                NSRequiresAquaSystemAppearance=False,
                LSArchitecturePriority=['arm64', 'x86_64'])
    info_path.write_bytes(plistlib.dumps(info))
    launcher = dest / 'Contents/MacOS/run.sh'
    launcher.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CONFIG / 'launch.sh', launcher)
    launcher.chmod(0o755)


def assemble():
    manifest = verify_downloads()
    source_root = WORK / 'source'
    if not (source_root / 'llama_cpp_python-0.3.34/llama_cpp').exists():
        extract_tar(CACHE / 'llama.tar.gz', source_root)
    source = source_root / 'llama_cpp_python-0.3.34'
    stage = WORK / 'payload'
    app = stage / 'Applications/MAAT RPG.app'
    clean_copy_game(app)
    resources = app / 'Contents/Resources'
    common = resources / 'runtimes/common'
    common.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CONFIG / 'sitecustomize.py', common / 'sitecustomize.py')
    for arch in ARCHES:
        runtime = resources / 'runtimes' / arch
        if not (runtime / 'bin/python3.11').exists():
            temp = WORK / f'extract-{arch}'
            extract_tar(CACHE / f'python-{arch}.tar.gz', temp)
            temp.joinpath('python').rename(runtime)
        site = runtime / 'lib/python3.11/site-packages'
        for wheel in sorted((CACHE / f'wheels-{arch}').glob('*.whl')):
            is_common = wheel.name.endswith('none-any.whl') or 'universal2.whl' in wheel.name
            if is_common and arch != ARCHES[0]:
                continue
            unpack_wheel(wheel, common if is_common else site)
        remove_build_rpaths(site / 'numpy')
        libs = build_backend(source, arch)
        shutil.copytree(source / 'llama_cpp', site / 'llama_cpp', dirs_exist_ok=True)
        shutil.copytree(libs, site / 'llama_cpp/lib', dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('.complete'))
        if arch == 'x86_64':
            optimized = build_backend(source, arch, optimized=True)
            shutil.copytree(optimized, site / 'llama_cpp/lib/avx2', dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('.complete'))
        metadata = site / 'llama_cpp_python-0.3.34.dist-info'
        metadata.mkdir(exist_ok=True)
        shutil.copy2(source / 'PKG-INFO', metadata / 'METADATA')
        shutil.copy2(source / 'LICENSE.md', metadata / 'LICENSE.md')
    # The game uses QtWidgets, SVG and Multimedia. WebEngine/QML developer
    # tools are deliberately omitted; all dynamically linked runtime libs stay.
    pyside = common / 'PySide6'
    for candidate in [pyside / 'Qt/qml', pyside / 'include', pyside / 'typesystems',
                      pyside / 'Qt/lib/QtWebEngineCore.framework',
                      pyside / 'Qt/lib/QtWebEngineQuick.framework',
                      pyside / 'Qt/lib/QtWebEngineWidgets.framework',
                      pyside / 'Qt/lib/QtWebEngineCore.framework/Helpers']:
        if candidate.is_dir():
            shutil.rmtree(candidate)
    for candidate in pyside.rglob('qtwebengine*'):
        if candidate.is_file():
            candidate.unlink()
    for candidate in pyside.glob('QtWebEngine*'):
        if candidate.is_file():
            candidate.unlink()
    for candidate in (pyside / 'Qt/plugins/sqldrivers').glob('*.dylib'):
        if candidate.name != 'libqsqlite.dylib':
            candidate.unlink()  # External ODBC/Postgres/Mimer drivers aren't used.
    docs = resources / 'Documentation'
    docs.mkdir(exist_ok=True)
    for name in ('LICENSE.txt', 'LICENSE_ADDITIONAL.md', 'QUELLEN_UND_LIZENZEN.md'):
        shutil.copy2(ROOT / name, docs / name)
    shutil.copy2(CONFIG / 'README.md', docs / 'MACOS-SETUP.md')
    shutil.copy2(CONFIG / 'THIRD-PARTY.md', docs / 'THIRD-PARTY.md')
    shutil.copy2(ROOT / 'docs/WIKI_HINWEISE.md', docs / 'WIKI_HINWEISE.md')
    shutil.copy2(ROOT / 'docs/SOFTWARE_LICENSES.md', docs / 'SOFTWARE_LICENSES.md')
    shutil.copytree(ROOT / 'packaging/licenses', docs / 'licenses', dirs_exist_ok=True)
    shutil.copy2(CONFIG / 'smoke_test.py', resources / 'smoke_test.py')
    (resources / 'BUILD-MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    # Sources may live in a private (0700) working directory. An installed app
    # is root-owned and must still be readable by the ordinary player account.
    for path in stage.rglob('*'):
        if path.is_symlink():
            continue
        if path.is_dir():
            path.chmod(0o755)
        else:
            path.chmod(0o755 if path.stat().st_mode & 0o111 else 0o644)
    return stage, app


def package(stage, app):
    audit = subprocess.check_output([sys.executable, ROOT / 'tools/audit_macos_setup.py'], text=True)
    print(audit, flush=True)
    audit_path = WORK / 'test-results/binary-audit.json'
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(json.loads(audit), indent=2) + '\n')
    DIST.mkdir(parents=True, exist_ok=True)
    parts = WORK / 'packages'
    parts.mkdir(exist_ok=True)
    component = parts / 'MAAT-RPG-component.pkg'
    components = WORK / 'components.plist'
    components.write_bytes(plistlib.dumps([dict(
        RootRelativeBundlePath='Applications/MAAT RPG.app',
        BundleIsRelocatable=False, BundleHasStrictIdentifier=True,
        BundleIsVersionChecked=True, BundleOverwriteAction='upgrade')]))
    run(['/usr/bin/pkgbuild', '--root', stage, '--identifier', 'com.maat.rpg.installer',
         '--version', VERSION, '--install-location', '/', '--ownership', 'recommended',
         '--component-plist', components, component])
    target = DIST / 'MAAT-RPG-macOS-Intel-ARM.pkg'
    installer_resources = WORK / 'installer-resources'
    installer_resources.mkdir(exist_ok=True)
    for name in ('Welcome.html', 'Conclusion.html'):
        shutil.copy2(CONFIG / name, installer_resources / name)
    run(['/usr/bin/productbuild', '--distribution', CONFIG / 'Distribution.xml',
         '--resources', installer_resources, '--package-path', parts, target])
    shutil.copy2(CONFIG / 'README.md', DIST / 'BITTE-LESEN.md')
    shutil.copy2(CACHE / 'manifest.json', DIST / 'BUILD-MANIFEST.json')
    report = WORK / 'test-results/runtime-tests.json'
    if report.is_file():
        shutil.copy2(report, DIST / 'RUNTIME-TESTS.json')
    (DIST / 'SHA256.txt').write_text(f'{digest(target)}  {target.name}\n')
    print(f'Installer ready: {target} ({target.stat().st_size / 1024**2:.1f} MiB)', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--assemble-only', action='store_true')
    parser.add_argument('--package-only', action='store_true')
    args = parser.parse_args()
    if not any(vars(args).values()):
        parser.error('Choose --fetch, --build or --assemble-only')
    if args.fetch:
        fetch()
    if args.build or args.assemble_only:
        stage, app = assemble()
        if args.build:
            package(stage, app)
    if args.package_only:
        stage = WORK / 'payload'
        package(stage, stage / 'Applications/MAAT RPG.app')


if __name__ == '__main__':
    main()
