"""Windows end-to-end catalog ingestion test using bundled FFmpeg binaries.
Runs against disposable synthetic media and never touches a user's library.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))


def bundled_tool(distribution, name):
    root = Path(distribution).resolve()
    for candidate in (root / '_internal' / 'bin' / (name + '.exe'), root / 'bin' / (name + '.exe')):
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(f'Missing bundled {name}.exe')


def check(distribution):
    from videoatlas.db import Catalog
    from videoatlas.scanner import Scanner
    ffmpeg = bundled_tool(distribution, 'ffmpeg')
    ffprobe = bundled_tool(distribution, 'ffprobe')
    with tempfile.TemporaryDirectory(prefix='videoatlas-catalog-') as temp:
        root = Path(temp)
        media = root / 'media'
        cache = root / 'thumbnails'
        media.mkdir()
        cache.mkdir()
        movie = media / 'integration-sample.mp4'
        result = subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
            '-f', 'lavfi', '-i', 'testsrc2=size=320x240:rate=10:duration=5',
            '-c:v', 'mpeg4', '-q:v', '5', str(movie)], capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError('Failed generating test video: ' + result.stderr[-800:])
        database = root / 'catalog.sqlite3'
        events = []
        scanner = Scanner(str(database), str(cache), [str(media)])
        scanner.finished.connect(lambda count, error: events.append((count, error)))
        def local_binary(name):
            return {'ffmpeg': ffmpeg, 'ffprobe': ffprobe}.get(name, '')
        with patch('videoatlas.scanner.binary', side_effect=local_binary):
            scanner.run()
            if not events or events[-1][0] != 1 or events[-1][1]:
                raise AssertionError(f'Initial scan failed: {events}')
            scanner.run()
            if events[-1] != (0, ''):
                raise AssertionError(f'Incremental rescan should skip unchanged files: {events}')
        db = Catalog(str(database))
        try:
            matches = db.search('integration-sample')
            if len(matches) != 1 or db.count() != 1:
                raise AssertionError('Video missing or duplicated in catalog')
            entry = matches[0]
            if entry['width'] != 320 or entry['height'] != 240 or not 4.5 <= entry['duration'] <= 5.5:
                raise AssertionError('Incorrect indexed metadata')
            thumb = Path(entry['thumbnail'])
            if not thumb.is_file() or thumb.stat().st_size < 100:
                raise AssertionError('Scanner did not generate a valid thumbnail')
            return {'ok': True, 'catalog_count': db.count(), 'resolution': '320x240',
                    'duration_seconds': entry['duration'], 'thumbnail_bytes': thumb.stat().st_size,
                    'incremental_rescan_skipped': True}
        finally:
            db.conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('distribution', nargs='?', default='dist/VideoAtlas')
    parser.add_argument('--report', default='')
    args = parser.parse_args()
    try:
        output = check(args.distribution)
    except Exception as exc:
        output = {'ok': False, 'error': str(exc)}
    data = json.dumps(output, indent=2)
    print(data)
    if args.report:
        Path(args.report).write_text(data, encoding='utf-8')
    return 0 if output['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
