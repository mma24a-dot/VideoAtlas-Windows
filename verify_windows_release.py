"""Verify Windows onedir distribution before installer compilation (offline)."""
import argparse
import hashlib
import json
from pathlib import Path

REQUIRED = ('VideoAtlas.exe', 'bin/ffmpeg.exe', 'bin/ffprobe.exe')

def verify_distribution(folder):
    root = Path(folder).resolve()
    errors = []
    files = {}
    for relative in REQUIRED:
        path = root / relative
        if relative.startswith('bin/') and not path.is_file():
            path = root / '_internal' / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f'Missing or empty: {relative}')
        else:
            files[path.relative_to(root).as_posix()] = {'size': path.stat().st_size,
                               'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    if not any(root.rglob('Qt6Core.dll')):
        errors.append('Qt6Core.dll not found in distribution')
    if not any(root.rglob('qwindows.dll')):
        errors.append('Qt Windows platform plugin qwindows.dll not found')
    return {'ok': not errors, 'errors': errors, 'files': files}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('distribution', nargs='?', default='dist/VideoAtlas')
    parser.add_argument('--manifest', default='')
    args = parser.parse_args()
    result = verify_distribution(args.distribution)
    print(json.dumps(result, indent=2))
    if args.manifest and result['ok']:
        Path(args.manifest).write_text(json.dumps(result, indent=2), encoding='utf-8')
    raise SystemExit(0 if result['ok'] else 1)

if __name__ == '__main__':
    main()
