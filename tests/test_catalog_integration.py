import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from windows_catalog_integration import bundled_tool

class CatalogIntegrationTests(unittest.TestCase):
    def test_missing_bundled_tool_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                bundled_tool(folder, 'ffprobe')

    def test_resolves_pyinstaller_six_layout(self):
        with tempfile.TemporaryDirectory() as folder:
            binary = Path(folder) / '_internal' / 'bin' / 'ffmpeg.exe'
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b'fixture')
            self.assertEqual(bundled_tool(folder, 'ffmpeg'), str(binary))
