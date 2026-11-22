"""Read-only installation self-test using a disposable catalog and synthetic video.

Does not access the user's library or download models.
"""
import json
import sys
import subprocess
import tempfile
from pathlib import Path
from .db import Catalog


def run_selftest():
    report = {'database': False, 'ffmpeg': False, 'ffprobe': False, 'qt': False, 'errors': []}
    try:
        with tempfile.TemporaryDirectory(prefix='videoatlas-selftest-') as temp:
            db = Catalog(Path(temp) / 'test.sqlite')
            db.upsert(dict(path=str(Path(temp)/'sample.mp4'), name='sample.mp4', size=10,
                           modified=1.0, duration=1.0, width=64, height=64,
                           codec='h264', thumbnail=''))
            report['database'] = len(db.search('sample')) == 1
            db.conn.close()
    except Exception as exc:
        report['errors'].append('database: ' + str(exc))
    for tool in ('ffmpeg', 'ffprobe'):
        try:
            from .scanner import binary
            path = binary(tool)
            result = subprocess.run([str(path), '-version'], capture_output=True,
                                    text=True, timeout=15)
            report[tool] = result.returncode == 0 and tool in result.stdout.lower()
        except Exception as exc:
            report['errors'].append(tool + ': ' + str(exc))
    try:
        from PySide6.QtWidgets import QApplication, QWidget
        app = QApplication.instance() or QApplication(['VideoAtlas-selftest', '-platform', 'offscreen'])
        widget = QWidget()
        report['qt'] = widget is not None
        widget.close()
    except Exception as exc:
        report['errors'].append('qt: ' + str(exc))
    report['ok'] = all(report[key] for key in ('database', 'ffmpeg', 'ffprobe', 'qt'))
    return report


def main():
    report = run_selftest()
    payload = json.dumps(report, indent=2)
    if "--self-test-report" in sys.argv:
        idx = sys.argv.index("--self-test-report")
        if idx + 1 < len(sys.argv):
            Path(sys.argv[idx + 1]).write_text(payload, encoding="utf-8")
    elif sys.stdout is not None:
        print(payload)
    return 0 if report['ok'] else 1
