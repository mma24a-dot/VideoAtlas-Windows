import tempfile
import unittest
from pathlib import Path
from verify_windows_release import verify_distribution

class ReleaseVerifierTests(unittest.TestCase):
    def test_missing_assets_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = verify_distribution(tmp)
            self.assertFalse(result['ok'])
            self.assertTrue(any('ffmpeg.exe' in x for x in result['errors']))

    def test_complete_mock_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ('VideoAtlas.exe','bin/ffmpeg.exe','bin/ffprobe.exe',
                        '_internal/PySide6/Qt6/bin/Qt6Core.dll',
                        '_internal/PySide6/Qt6/plugins/platforms/qwindows.dll'):
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b'fixture')
            result = verify_distribution(root)
            self.assertTrue(result['ok'])
            self.assertEqual(len(result['files']), 3)

    def test_pyinstaller_internal_binary_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ('VideoAtlas.exe', '_internal/bin/ffmpeg.exe',
                        '_internal/bin/ffprobe.exe',
                        '_internal/PySide6/Qt6/bin/Qt6Core.dll',
                        '_internal/PySide6/Qt6/plugins/platforms/qwindows.dll'):
                f = root / rel
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(b'fixture')
            result = verify_distribution(root)
            self.assertTrue(result['ok'], result['errors'])
            self.assertIn('_internal/bin/ffmpeg.exe', result['files'])

    def test_empty_executable_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'VideoAtlas.exe').touch()
            self.assertFalse(verify_distribution(root)['ok'])
