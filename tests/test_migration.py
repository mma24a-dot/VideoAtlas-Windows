import tempfile
import unittest
import zipfile
from pathlib import Path
from videoatlas.db import Catalog
from videoatlas.migration import export_catalog, validate_archive, restore_to_new_directory

class MigrationTests(unittest.TestCase):
    def test_export_and_restore(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=root/'data'; data.mkdir(); (data/'thumbnails').mkdir()
            (data/'thumbnails'/'sample.jpg').write_bytes(b'jpeg'); (data/'folders.txt').write_text('D:/Videos')
            db=Catalog(data/'catalog.sqlite')
            package=export_catalog(db,data,root/'backup.zip')
            self.assertEqual(validate_archive(package)['files'],3)
            restored=restore_to_new_directory(package,root/'restored')
            self.assertEqual((restored/'thumbnails'/'sample.jpg').read_bytes(),b'jpeg')
            with self.assertRaises(FileExistsError): restore_to_new_directory(package,restored)
            db.conn.close()

    def test_reject_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'evil.zip'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('../evil.txt','bad')
                z.writestr('manifest.json','{}')
            with self.assertRaises(ValueError): validate_archive(p)

    def test_reject_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=root/'data';data.mkdir()
            db=Catalog(data/'catalog.sqlite');package=export_catalog(db,data,root/'backup.zip')
            modified=root/'bad.zip'
            with zipfile.ZipFile(package) as source,zipfile.ZipFile(modified,'w') as target:
                for name in source.namelist():
                    target.writestr(name,b'bad' if name=='catalog.sqlite' else source.read(name))
            with self.assertRaises(ValueError): validate_archive(modified)
            db.conn.close()
