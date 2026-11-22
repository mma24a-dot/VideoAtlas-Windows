import tempfile
import unittest
from pathlib import Path
from videoatlas.model_registry import save_model, load_registry, check_registry, remove_model, validate_model

class ModelRegistryTests(unittest.TestCase):
    def test_whisper_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp)/'ggml-base.bin'
            model.write_bytes(b'test')
            save_model(tmp, 'whisper', model)
            self.assertEqual(load_registry(tmp)['whisper'], str(model.resolve()))
            self.assertTrue(check_registry(tmp)['whisper']['valid'])
            model.unlink()
            self.assertFalse(check_registry(tmp)['whisper']['valid'])
            remove_model(tmp,'whisper')
            self.assertEqual(load_registry(tmp), {})
    def test_clip_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'config.json').write_text('{}')
            self.assertFalse(validate_model('clip',p)[0])
            (p/'model.safetensors').write_bytes(b'fake')
            self.assertTrue(validate_model('clip',p)[0])
    def test_reject_invalid_kind_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): save_model(tmp,'other',tmp)
            with self.assertRaises(ValueError): save_model(tmp,'whisper',tmp)
