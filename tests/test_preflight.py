import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from videoatlas.preflight import check_job, check_all

class PreflightTests(unittest.TestCase):
    def test_hash_needs_no_tools(self):
        with tempfile.TemporaryDirectory() as base:
            self.assertTrue(check_job('hash', base)['ready'])

    def test_unknown_job(self):
        with self.assertRaises(ValueError):
            check_job('unknown', '.')

    def test_transcript_missing_model(self):
        with tempfile.TemporaryDirectory() as base:
            with patch('videoatlas.preflight.find_tool', return_value='/fake/exe'):
                result = check_job('transcript', base)
            self.assertFalse(result['ready'])
            self.assertTrue(any('model' in p.lower() for p in result['problems']))

    def test_transcript_with_model(self):
        with tempfile.TemporaryDirectory() as base:
            model = Path(base) / 'ggml-base.bin'
            model.write_bytes(b'test')
            with patch('videoatlas.preflight.find_tool', return_value='/fake/exe'):
                result = check_job('transcript', base, explicit_model=model)
            self.assertTrue(result['ready'])

    def test_ocr_requires_tools(self):
        with tempfile.TemporaryDirectory() as base:
            with patch('videoatlas.preflight.find_tool', return_value=None):
                result = check_job('ocr', base)
            self.assertFalse(result['ready'])
            self.assertEqual(len([x for x in result['problems'] if x.startswith('Missing executable')]), 2)

    def test_all_jobs(self):
        with tempfile.TemporaryDirectory() as base:
            self.assertEqual(len(check_all(base)), 5)

if __name__ == '__main__': unittest.main()
