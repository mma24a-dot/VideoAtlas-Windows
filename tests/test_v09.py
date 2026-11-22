import tempfile
import unittest
from pathlib import Path
from videoatlas.db import Catalog

class UnifiedFilteringTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.db=Catalog(self.root/'db.sqlite')
        for i in range(6):
            path=self.root/f'video{i}.mp4'
            if i%2==0: path.write_bytes(b'video')
            self.db.upsert(dict(path=str(path),name=f'video{i}.mp4',size=200+i,
                modified=float(i),duration=60+i,width=1920,height=1080,
                codec='h264',thumbnail=''))
        self.db.save_details(2,'special notes','wildlife, nature')
    def tearDown(self):
        self.db.conn.close();self.temp.cleanup()
    def test_tag_search_and_metadata(self):
        rows=self.db.advanced_filter(term='wildlife',min_width=1280,codec='h264')
        self.assertEqual(len(rows),1)
        self.assertIn('wildlife',rows[0]['tags'])
    def test_offline_pagination(self):
        first=self.db.advanced_filter(offline_only=True,limit=1,offset=0)
        second=self.db.advanced_filter(offline_only=True,limit=1,offset=1)
        self.assertEqual(len(first),1)
        self.assertEqual(len(second),1)
        self.assertNotEqual(first[0]['id'],second[0]['id'])
        self.assertEqual(len(self.db.advanced_filter(offline_only=True,limit=5,offset=3)),0)
    def test_literal_wildcards(self):
        self.assertEqual(self.db.advanced_filter(term='%'),[])
        matches=self.db.advanced_filter(term='_')
        self.assertTrue(all('_' in r['path'] or '_' in r['name'] or '_' in (r['notes'] or '') for r in matches))
    def test_combined_filters(self):
        self.assertEqual(len(self.db.advanced_filter(min_width=2000)),0)
        self.assertEqual(len(self.db.advanced_filter(max_size=202)),3)
        self.assertEqual(len(self.db.advanced_filter(max_duration=62)),3)

if __name__=='__main__': unittest.main()
