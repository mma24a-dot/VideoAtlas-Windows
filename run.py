"""Entry point for source and PyInstaller builds."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

if __name__ == '__main__':
    if '--gui-smoke' in sys.argv:
        from videoatlas.gui_smoke import main
    elif '--self-test' in sys.argv:
        from videoatlas.selftest import main
    else:
        from videoatlas.app import main
    raise SystemExit(main())
