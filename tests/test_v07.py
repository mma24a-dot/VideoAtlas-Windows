import tempfile
import unittest
from pathlib import Path
from videoatlas.db import Catalog
from videoatlas.vector_index import search_hnsw

class Version07Tests(unittest.TestCase):
    def test_advanced_filter(self):
        with tempfile.TemporaryDirectory() as d:
            db=Catalog(Path(d)/'catalog.sqlite')
            for name, width, codec in [('a.mp4',1920,'h264'),('b.mp4',640,'vp9')]:
                db.upsert(dict(path=str(Path(d)/name),name=name,size=100,modified=1,
                               duration=60,width=width,height=1080,codec=codec,thumbnail=''))
            self.assertEqual([x['name'] for x in db.advanced_filter(min_width=1000)],['a.mp4'])
            self.assertEqual([x['name'] for x in db.advanced_filter(codec='vp9')],['b.mp4'])
            self.assertEqual(db.advanced_filter(max_duration=20),[])
            db.conn.close()

    def test_vector_search_empty(self):
        with tempfile.TemporaryDirectory() as d:
            db=Catalog(Path(d)/'catalog.sqlite');db.initialize_semantic()
            self.assertIn(search_hnsw(db,'none',[1.,0.],3), (None,[]))
            db.conn.close()
