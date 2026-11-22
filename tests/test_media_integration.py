import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from windows_media_integration import check

class TestMediaIntegration(unittest.TestCase):
    def test_missing_binaries_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                check(folder)

if __name__=='__main__': unittest.main()
