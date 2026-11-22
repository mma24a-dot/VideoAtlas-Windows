import tempfile
import unittest
from pathlib import Path
from videoatlas.model_registry import save_model
from videoatlas.model_resolution import resolve_model, tesseract_environment

class ResolutionTests(unittest.TestCase):
    def test_saved_and_explicit_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'a.bin'; b=Path(tmp)/'b.bin'
            a.write_bytes(b'a'); b.write_bytes(b'b')
            save_model(tmp,'whisper',a)
            self.assertEqual(resolve_model(tmp,'whisper'),str(a.resolve()))
            self.assertEqual(resolve_model(tmp,'whisper',b),str(b.resolve()))
    def test_missing_or_invalid_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError): resolve_model(tmp,'clip')
            with self.assertRaises(RuntimeError): resolve_model(tmp,'whisper',Path(tmp)/'missing.bin')
            self.assertIsNone(resolve_model(tmp,'clip',required=False))
    def test_tessdata_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(tesseract_environment(tmp)['TESSDATA_PREFIX'],str(Path(tmp).resolve()))
            self.assertEqual(tesseract_environment(None),{})
