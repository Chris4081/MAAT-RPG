#!/usr/bin/env python3
"""Export the current GUI as a clean, architecture-neutral Linux test archive."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[1]
GAME=ROOT/'maatos'
NAME='MAAT-RPG-Linux'
SKIP={'__pycache__','.git','.DS_Store','data','logs','cache','state','saves','models'}
ALLOWED={'.py','.json','.yaml','.yml','.txt','.png','.svg','.wav','.mp3','.m4a','.md'}


def sources():
    # profiles contains shipped system prompts, not the user's save slots.
    for top in ('apps','shared','gui','profiles'):
        for source in sorted((GAME/top).rglob('*')):
            rel=source.relative_to(GAME)
            if any(part in SKIP or part.startswith('.') for part in rel.parts):continue
            if source.is_symlink():raise ValueError(f'Unexpected symlink: {source}')
            if source.is_file() and source.suffix in ALLOWED:
                yield source,Path('maatos')/rel
    for name in ('Install Linux.sh','Start Linux.sh','setup.sh','Install.command',
                 'Start GUI.command','SETUP.md','requirements-gui.txt','requirements-wiki.txt'):
        yield ROOT/name,Path(name)
    for source in sorted((ROOT/'packaging/linux').iterdir()):
        if source.is_file() and source.suffix in {'.py','.txt','.md'}:
            yield source,Path('packaging/linux')/source.name
    for source in sorted((ROOT/'packaging/setup').iterdir()):
        if source.is_file() and source.suffix in {'.py','.sh'}:
            yield source,Path('packaging/setup')/source.name
    yield ROOT/'packaging/linux/ARCHIVE-README.md',Path('README-LINUX.md')
    yield ROOT/'docs/INSTALL_LINUX.md',Path('docs/INSTALL_LINUX.md')
    yield ROOT/'docs/WIKI_HINWEISE.md',Path('WIKI_HINWEISE.md')
    yield ROOT/'docs/SOFTWARE_LICENSES.md',Path('SOFTWARE_LICENSES.md')
    yield ROOT/'packaging/linux/THIRD-PARTY.md',Path('THIRD-PARTY.md')
    for source in sorted((ROOT/'packaging/licenses').iterdir()):
        if source.is_file() and source.suffix in {'.txt','.md','.json'}:
            yield source,Path('licenses')/source.name
    for name in ('LICENSE','LICENSE.md','LICENSE.txt','LICENSE_ADDITIONAL.md','QUELLEN_UND_LIZENZEN.md'):
        if (ROOT/name).is_file():yield ROOT/name,Path(name)


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def build(output):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),
                  release='linux-gui-test-2026-09-20',
                  runtime='Installed locally by Install Linux.sh; CPU backend',files={})
    entries=list(sources())
    names=[str(rel) for _,rel in entries]
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError('Duplicate/case-conflicting archive names')
    for source,rel in entries:
        manifest['files'][rel.as_posix()]=dict(bytes=source.stat().st_size,sha256=digest(source))
    temporary=output.with_suffix(output.suffix+'.part')
    with tarfile.open(temporary,'w:gz',compresslevel=6) as tar:
        for source,rel in entries:
            info=tar.gettarinfo(str(source),arcname=f'{NAME}/{rel.as_posix()}')
            info.uid=info.gid=0;info.uname=info.gname='';info.pax_headers={}
            info.mode=0o755 if source.suffix in {'.sh','.command'} else 0o644
            with source.open('rb') as stream:tar.addfile(info,stream)
        raw=(json.dumps(manifest,indent=2)+'\n').encode()
        info=tarfile.TarInfo(f'{NAME}/manifest.json');info.size=len(raw);info.mode=0o644
        tar.addfile(info,io.BytesIO(raw))
    # Re-open and compare every member, not only the archive's checksum.
    with tarfile.open(temporary) as tar:
        for member in tar:
            if member.name==f'{NAME}/manifest.json':continue
            rel=member.name.removeprefix(NAME+'/')
            h=hashlib.sha256()
            with tar.extractfile(member) as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
            if h.hexdigest()!=manifest['files'][rel]['sha256']:raise ValueError(rel)
    temporary.replace(output)
    output.with_name(output.name+'.sha256').write_text(digest(output)+'  '+output.name+'\n')
    output.with_name('manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'{output}\n{len(entries)} files, {output.stat().st_size/1024/1024:.1f} MiB; all hashes verified.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'dist/linux/MAAT-RPG-Linux-Test.tar.gz')
    build(parser.parse_args().output)
