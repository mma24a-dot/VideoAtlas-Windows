import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class GuiSmokePackagingTests(unittest.TestCase):
    def test_entrypoint_has_gui_smoke_mode(self):
        entry = (ROOT / 'run.py').read_text(encoding='utf-8')
        self.assertIn("'--gui-smoke'", entry)
        self.assertIn('videoatlas.gui_smoke', entry)

    def test_windows_build_blocks_on_gui_failure(self):
        build = (ROOT / 'build_windows.bat').read_text(encoding='utf-8')
        self.assertIn('VideoAtlas.exe --gui-smoke', build)
        self.assertIn('ERROR: Frozen GUI startup test failed.', build)
        self.assertLess(build.index('VideoAtlas.exe --gui-smoke'), build.index('iscc installer'))

    def test_smoke_uses_disposable_catalog(self):
        smoke = (ROOT / 'src/videoatlas/gui_smoke.py').read_text(encoding='utf-8')
        self.assertIn('TemporaryDirectory(', smoke)
        self.assertIn("os.environ['LOCALAPPDATA'] = directory", smoke)
