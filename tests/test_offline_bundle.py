import json
import tempfile
import unittest
from pathlib import Path
from videoatlas.offline_bundle import create_manifest, verify_manifest

class BundleTests(unittest.TestCase):
    def test_valid_and_modified(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'model').mkdir(); (p/'model'/'weights.bin').write_bytes(b'weights')
            m=create_manifest(p,['model/weights.bin'])
            self.assertEqual(verify_manifest(p,m)[0]['status'],'ok')
            (p/'model'/'weights.bin').write_bytes(b'changed')
            self.assertEqual(verify_manifest(p,m)[0]['status'],'hash_mismatch')
    def test_missing(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'a').write_bytes(b'a'); m=create_manifest(p,['a']); (p/'a').unlink()
            self.assertEqual(verify_manifest(p,m)[0]['status'],'missing')
    def test_reject_escape(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): create_manifest(d,['../outside'])
    def test_reject_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'a').write_bytes(b'a'); m=create_manifest(p,['a']); m['files'].append(dict(m['files'][0]))
            with self.assertRaises(ValueError): verify_manifest(p,m)
