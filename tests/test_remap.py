import sqlite3
import tempfile
import unittest
from pathlib import Path
from videoatlas.migration import remap_restored_paths

class RemapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.db = sqlite3.connect(self.base/'catalog.sqlite')
        self.db.execute('CREATE TABLE videos(id INTEGER PRIMARY KEY,path TEXT UNIQUE)')
        self.db.executemany('INSERT INTO videos(path) VALUES(?)', [('E:\\Movies\\one.mp4',), ('E:\\MoviesExtra\\two.mp4',)])
        self.db.commit(); self.db.close()
        (self.base/'folders.txt').write_text('E:\\Movies\nE:\\MoviesExtra', encoding='utf-8')

    def test_preview_and_apply(self):
        preview = remap_restored_paths(self.base,'E:\\Movies','Z:\\Archive',dry_run=True)
        self.assertEqual(preview['videos'],1)
        conn=sqlite3.connect(self.base/'catalog.sqlite')
        self.assertEqual(conn.execute('SELECT path FROM videos WHERE id=1').fetchone()[0], 'E:\\Movies\\one.mp4')
        conn.close()
        result=remap_restored_paths(self.base,'E:\\Movies','Z:\\Archive',dry_run=False)
        self.assertEqual(result['folders'],1)
        conn=sqlite3.connect(self.base/'catalog.sqlite')
        self.assertEqual(conn.execute('SELECT path FROM videos WHERE id=1').fetchone()[0], 'Z:\\Archive\\one.mp4')
        self.assertEqual(conn.execute('SELECT path FROM videos WHERE id=2').fetchone()[0], 'E:\\MoviesExtra\\two.mp4')
        conn.close()

    def test_collision_refused(self):
        conn=sqlite3.connect(self.base/'catalog.sqlite')
        conn.execute('INSERT INTO videos(path) VALUES(?)',('Z:\\Archive\\one.mp4',))
        conn.commit();conn.close()
        with self.assertRaises(ValueError):
            remap_restored_paths(self.base,'E:\\Movies','Z:\\Archive',dry_run=False)
