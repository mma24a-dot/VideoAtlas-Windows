import tempfile
import unittest
from pathlib import Path
from videoatlas.file_operations import find_duplicates, move_matching_files


class FileOperationsTests(unittest.TestCase):
    def test_duplicates_compare_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            a=root/'a.mp4';b=root/'b.mp4';c=root/'c.mp4'
            a.write_bytes(b'same');b.write_bytes(b'same');c.write_bytes(b'diff')
            groups=find_duplicates([a,b,c])
            self.assertEqual(len(groups),1)
            self.assertEqual(set(groups[0]['paths']),{str(a),str(b)})

    def test_move_matches_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); dest=root/'dest';dest.mkdir()
            a=root/'lesson-one.mp4';b=root/'other.mp4'
            a.write_bytes(b'new');b.write_bytes(b'other')
            (dest/a.name).write_bytes(b'existing')
            moved,skipped=move_matching_files([a,b],'lesson',dest)
            self.assertFalse(moved)
            self.assertEqual(len(skipped),1)
            self.assertEqual((dest/a.name).read_bytes(),b'existing')
            (dest/a.name).unlink()
            moved,skipped=move_matching_files([a,b],'lesson',dest)
            self.assertEqual(len(moved),1)
            self.assertFalse(a.exists())
            self.assertTrue((dest/a.name).exists())


if __name__=='__main__':
    unittest.main()
