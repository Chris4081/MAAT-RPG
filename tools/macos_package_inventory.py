"""Inspect our pkgbuild gzip/odc payload without extracting another app copy."""
import gzip
import hashlib
import plistlib
import stat
import subprocess
import xml.etree.ElementTree as ET


def read_exact(stream, count):
    chunks = []
    while count:
        chunk = stream.read(count)
        if not chunk:
            raise ValueError('Truncated installer payload')
        chunks.append(chunk)
        count -= len(chunk)
    return b''.join(chunks)


def cpio_inventory(stream):
    """Hash old ASCII cpio entries; reject unexpected formats and locations."""
    prefix = 'Applications/MAAT RPG.app/'
    files, captured, hardlinks = {}, {}, {}
    while True:
        header = read_exact(stream, 76)
        if header[:6] != b'070707':
            raise ValueError('Expected pkgbuild old ASCII cpio payload')
        mode = int(header[18:24], 8)
        nlink = int(header[36:42], 8)
        name_size, size = int(header[59:65], 8), int(header[65:76], 8)
        if not 1 <= name_size <= 65536:
            raise ValueError('Invalid payload filename length')
        raw_name = read_exact(stream, name_size)
        if raw_name[-1:] != b'\0':
            raise ValueError('Unterminated payload filename')
        name = raw_name[:-1].decode('utf-8')
        if name == 'TRAILER!!!':
            if size:
                raise ValueError('Nonempty cpio trailer')
            # Read through gzip EOF to verify its CRC as well as the file hashes.
            while chunk := stream.read(1024 * 1024):
                if chunk.strip(b'\0'):
                    raise ValueError('Unexpected data after payload trailer')
            break
        if name.startswith('./'):
            name = name[2:]
        if '..' in name.split('/') or name.startswith('/'):
            raise ValueError('Unsafe installer path')
        if stat.S_ISDIR(mode):
            if size:
                raise ValueError('Nonempty directory entry')
            continue
        # pkgutil restores AppleDouble entries as extended attributes, not
        # separate files. The expanded verifier likewise compares file bytes.
        parent, _, basename = name.rpartition('/')
        if basename.startswith('._'):
            target = (parent + '/' if parent else '') + basename[2:]
            if (not stat.S_ISREG(mode) or not 4 <= size <= 16 * 1024 * 1024
                    or not (target in {'.', 'Applications', prefix[:-1]} or target.startswith(prefix))
                    or read_exact(stream, 4) != b'\x00\x05\x16\x07'):
                raise ValueError(f'Invalid AppleDouble metadata: {name}')
            remaining = size - 4
            while remaining:
                chunk = read_exact(stream, min(remaining, 1024 * 1024))
                remaining -= len(chunk)
            continue
        if not name.startswith(prefix):
            raise ValueError(f'Unexpected installed file: {name}')
        name = name[len(prefix):]
        if name in files:
            raise ValueError(f'Duplicate installed file: {name}')
        if stat.S_ISLNK(mode):
            if size > 65536:
                raise ValueError('Invalid symlink size')
            files[name] = ('symlink', read_exact(stream, size).decode('utf-8'))
            continue
        if not stat.S_ISREG(mode):
            raise ValueError(f'Unexpected file type: {name}')
        collect = name == 'Contents/Info.plist'
        if collect and size > 1024 * 1024:
            raise ValueError('Oversized application plist')
        digest, content, remaining = hashlib.sha256(), [], size
        while remaining:
            chunk = read_exact(stream, min(remaining, 1024 * 1024))
            digest.update(chunk)
            if collect:
                content.append(chunk)
            remaining -= len(chunk)
        files[name] = ('file', digest.hexdigest())
        if collect:
            captured[name] = b''.join(content)
        if nlink > 1:
            inode = (int(header[6:12], 8), int(header[12:18], 8))
            hardlinks.setdefault(inode, []).append((name, size, digest.hexdigest()))
    for group in hardlinks.values():
        hashes = {checksum for _, size, checksum in group if size}
        if len(hashes) > 1:
            raise ValueError('Inconsistent hardlinked payload files')
        checksum = next(iter(hashes), hashlib.sha256(b'').hexdigest())
        for name, _, _ in group:
            files[name] = ('file', checksum)
    return files, captured


def read_installer(package):
    # BSD tar exposes duplicate xar <name> nodes differently from pkgutil;
    # use the names actually listed by the same reader for extraction.
    names = subprocess.check_output(['/usr/bin/tar', '-tf', str(package)], text=True).splitlines()
    def entry(suffix):
        matches = [name for name in names if name == suffix or name.endswith('/' + suffix)]
        if len(matches) != 1:
            raise ValueError(f'Expected one installer {suffix}: {matches}')
        return matches[0]
    if any('Scripts' in name.split('/') for name in names):
        raise ValueError('Unexpected installation scripts')
    def read_metadata(suffix):
        return subprocess.check_output(['/usr/bin/tar', '-xOf', str(package), entry(suffix)])
    distribution = ET.fromstring(read_metadata('Distribution'))
    component = ET.fromstring(read_metadata('PackageInfo'))
    process = subprocess.Popen(['/usr/bin/tar', '-xOf', str(package), entry('Payload')],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        with gzip.GzipFile(fileobj=process.stdout) as stream:
            files, captured = cpio_inventory(stream)
        errors = process.stderr.read().decode('utf-8', errors='replace')
        if process.wait() != 0:
            raise ValueError(f'Cannot read installer payload: {errors}')
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()
        process.stdout.close()
        process.stderr.close()
    info = plistlib.loads(captured['Contents/Info.plist'])
    return info, distribution, component, files
