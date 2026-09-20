#!/usr/bin/env python3
"""Read-only source check. No model, network, GUI or installed runtime required."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {'.git', '.venv', '__pycache__', '.pytest_cache', 'build', 'dist', 'output', 'tmp'}
FORBIDDEN = {'data', 'logs', 'saves', 'models', 'state', 'cache', 'runtimes'}
BANNED_EXTENSIONS = {'.gguf', '.zim', '.safetensors', '.pyc', '.bak', '.log', '.sqlite', '.db', '.dylib', '.so', '.dll', '.pkg', '.dmg', '.whl'}
PROJECT_MP3_CUES = {
    'maatos/apps/maat_rpg/plugins/battle/sounds/levelup.mp3',
    'maatos/apps/maat_rpg/plugins/battle/music/victory.mp3',
}
TEXT = {'.py', '.json', '.yaml', '.yml', '.md', '.txt', '.sh', '.command', '.ps1', '.html', '.xml'}


def source_files():
    if (ROOT / '.git').is_dir():
        names = subprocess.check_output(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT
        ).decode().split('\0')
        return sorted({ROOT / name for name in names if name and (ROOT / name).is_file()})
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and not set(p.relative_to(ROOT).parts) & IGNORED)


def main():
    errors = []
    files = source_files()
    folded = {}
    python_count = 0
    json_count = 0
    for path in files:
        rel = path.relative_to(ROOT)
        label = rel.as_posix()
        if path.suffix.lower() in {'.mp3', '.m4a'} and label not in PROJECT_MP3_CUES:
            errors.append(f'Background music is not part of the source edition: {label}')
        if path.is_symlink():
            errors.append(f'Unexpected symlink: {label}')
        if set(rel.parts) & FORBIDDEN or path.suffix in BANNED_EXTENSIONS or path.name in {'.DS_Store', 'SUNO_NACHWEISE.csv', 'RUNTIME_AUDIT.json'}:
            errors.append(f'Private/generated/binary runtime file: {label}')
        if path.stat().st_size >= 100 * 1024 * 1024:
            errors.append(f'File exceeds repository size budget: {label}')
        if label.casefold() in folded and folded[label.casefold()] != label:
            errors.append(f'Case-conflicting path: {label}')
        folded[label.casefold()] = label
        if path.suffix not in TEXT:
            continue
        try:
            text = path.read_text(encoding='utf-8-sig')
            if path.suffix == '.py':
                ast.parse(text, filename=label)
                python_count += 1
            if path.suffix == '.json':
                json.loads(text)
                json_count += 1
        except (UnicodeError, SyntaxError, ValueError) as exc:
            errors.append(f'Invalid source: {label}: {exc}')
            continue
        # Deliberately report filenames only, never potential credential values.
        private_path = r'/(?:Users|Volumes)/[^\s"\'<>]+'
        credential = r'(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-proj-[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)'
        if re.search(private_path, text):
            errors.append(f'Personal absolute path: {label}')
        if re.search(credential, text):
            errors.append(f'Possible credential: {label}')
        if path.suffix == '.md':
            # Only inline Markdown destinations, outside fenced code examples.
            prose = re.sub(r'```.*?```', '', text, flags=re.S)
            for match in re.finditer(r'!?\[[^\]\n]*\]\((<[^>]+>|[^)\n]+)\)', prose):
                target = match.group(1).strip()
                target = target[1:-1] if target.startswith('<') else target.split(' "', 1)[0]
                parsed = urlsplit(target)
                if parsed.scheme or target.startswith(('#', '//')):
                    continue
                destination = unquote(parsed.path)
                if destination and not (path.parent / destination).exists():
                    errors.append(f'Broken local Markdown link: {label} -> {destination}')
    total = sum(p.stat().st_size for p in files)
    largest = max(files, key=lambda p: p.stat().st_size)
    print(f'{len(files)} files; {total / 1024**2:.1f} MiB; {python_count} Python and {json_count} JSON files parsed.')
    print(f'Largest: {largest.relative_to(ROOT)} ({largest.stat().st_size / 1024**2:.2f} MiB).')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('Source checks passed. Heuristic checks are not a full security or license audit.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
