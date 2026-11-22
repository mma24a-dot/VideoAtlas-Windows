"""Exercise the real main window in a disposable, offline catalog.

Run with QT_QPA_PLATFORM=offscreen for unattended Windows CI.
"""
import json
import os
import sys
import tempfile
from pathlib import Path


def main():
    # The application defines its data directory at import time. Isolate it first.
    with tempfile.TemporaryDirectory(prefix='videoatlas-gui-smoke-') as directory:
        os.environ['LOCALAPPDATA'] = directory
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        from .app import Window
        app = QApplication.instance() or QApplication(['VideoAtlas GUI smoke'])
        app.setApplicationName('VideoAtlas GUI Smoke')
        report = {'ok': False, 'window_created': False, 'database_created': False,
                  'theme_switch': False, 'library_refresh': False}
        window = None
        try:
            window = Window()
            report['window_created'] = True
            window.show()
            app.processEvents()
            window.set_theme('Light')
            window.set_theme('Dark')
            report['theme_switch'] = True
            window.refresh()
            report['library_refresh'] = True
            report['database_created'] = (Path(directory) / 'VideoAtlas' / 'catalog.sqlite').is_file()
            if not report['database_created']:
                raise RuntimeError('SQLite catalog was not created')
            QTimer.singleShot(100, app.quit)
            app.exec()
            report['ok'] = True
        except Exception as exc:
            report['error'] = f'{type(exc).__name__}: {exc}'
        finally:
            if window is not None:
                window.close()
            output = json.dumps(report, indent=2)
            print(output)
            for arg in sys.argv[1:]:
                if arg.startswith('--gui-smoke-report='):
                    Path(arg.split('=', 1)[1]).write_text(output, encoding='utf-8')
        return 0 if report['ok'] else 1
