import tempfile
import unittest
from pathlib import Path
from videoatlas.db import Catalog

class SafetyTests(unittest.TestCase):
    def test_backup_and_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); db=Catalog(root/'live.sqlite')
            db.upsert(dict(path=str(root/'a.mp4'),name='a.mp4',size=4,modified=2.,duration=1.,width=1,height=1,codec='h264',thumbnail=''))
            self.assertTrue(db.integrity_report()['ok'])
            backup=root/'backup.sqlite';db.backup_to(backup)
            copy=Catalog(backup);self.assertEqual(copy.count(),1)
            self.assertTrue(copy.integrity_report()['ok'])
            with self.assertRaises(FileExistsError):db.backup_to(backup)
            with self.assertRaises(ValueError):db.backup_to(root/'live.sqlite')
            copy.conn.close();db.conn.close()

    def test_duplicate_group_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);db=Catalog(root/'live.sqlite');db.initialize_analysis()
            for name in ('a.mp4','b.mp4'):
                file=root/name;file.write_bytes(b'same')
                stat=file.stat()
                db.upsert(dict(path=str(file),name=name,size=stat.st_size,modified=stat.st_mtime,duration=1.,width=1,height=1,codec='',thumbnail=''))
                vid=db.conn.execute('SELECT id FROM videos WHERE path=?',(str(file),)).fetchone()[0]
                db.save_hash(vid,file,'samehash')
            self.assertEqual(len(db.duplicate_groups()),1)
            self.assertEqual(len(db.duplicate_group_files('samehash')),2)
            db.conn.close()
