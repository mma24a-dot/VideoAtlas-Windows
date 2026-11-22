import tempfile
import unittest
from pathlib import Path
from videoatlas.deployment import diagnostics, find_tool, model_directory_valid

class DeploymentTests(unittest.TestCase):
    def test_bundled_binary_priority(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/'bin'; folder.mkdir()
            tool=folder/'ffmpeg.exe'; tool.write_bytes(b'test')
            self.assertEqual(find_tool('ffmpeg', d),str(tool))
    def test_model_requires_weights(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'config.json').write_text('{}')
            self.assertFalse(model_directory_valid(p))
            (p/'model.safetensors').write_bytes(b'placeholder')
            self.assertTrue(model_directory_valid(p))
    def test_diagnostics_missing_model(self):
        self.assertFalse(diagnostics('/nonexistent/model')['clip_model']['available'])

