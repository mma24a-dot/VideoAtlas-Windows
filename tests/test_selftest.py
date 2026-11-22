import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from videoatlas import selftest

class SelftestTests(unittest.TestCase):
    def test_selftest_report_schema(self):
        stub = types.ModuleType('videoatlas.scanner')
        stub.binary = lambda name: 'nonexistent-videoatlas-test-binary'
        with patch.dict(sys.modules, {'videoatlas.scanner': stub}):
            result = selftest.run_selftest()
        self.assertTrue(result['database'])
        self.assertFalse(result['ffmpeg'])
        self.assertFalse(result['ffprobe'])
        self.assertFalse(result['ok'])
