import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from windows_smoke_test import smoke_test

class SmokeTests(unittest.TestCase):
    def test_missing_assets_fail_without_execution(self):
        with tempfile.TemporaryDirectory() as d:
            with patch('windows_smoke_test.subprocess.run') as run:
                self.assertFalse(smoke_test(d)['ok'])
                run.assert_not_called()

    def test_version_checks_pass_with_mocked_processes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for rel in ('VideoAtlas.exe', '_internal/bin/ffmpeg.exe', '_internal/bin/ffprobe.exe',
                        '_internal/PySide6/Qt6/bin/Qt6Core.dll',
                        '_internal/PySide6/Qt6/plugins/platforms/qwindows.dll'):
                f = root / rel
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(b'fixture')
            class Result:
                returncode = 0
                stdout = 'ffmpeg version 7.0\n'
            def runner(args, **kwargs):
                result = Result()
                result.stdout = Path(args[0]).stem + ' version 7.0\n'
                return result
            with patch('windows_smoke_test.subprocess.run', side_effect=runner) as run:
                result = smoke_test(root)
                self.assertTrue(result['ok'], result)
                self.assertEqual(run.call_count, 2)

    def test_runtime_failure_blocks_release(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for rel in ('VideoAtlas.exe', 'bin/ffmpeg.exe', 'bin/ffprobe.exe',
                        'Qt6Core.dll', 'qwindows.dll'):
                f = root / rel
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(b'fixture')
            with patch('windows_smoke_test.subprocess.run', side_effect=OSError('blocked')):
                self.assertFalse(smoke_test(root)['ok'])
