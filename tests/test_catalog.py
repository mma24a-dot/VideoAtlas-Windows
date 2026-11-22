import tempfile
import unittest
from pathlib import Path
from videoatlas.db import Catalog
from videoatlas.analysis import sha256_file

class CatalogTests(unittest.TestCase):
    def test_index_and_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Catalog(Path(tmp)/'db.sqlite');db.initialize_analysis();db.initialize_queue()
            video=Path(tmp)/'video.mp4';video.write_bytes(b'test video data')
            db.upsert(dict(path=str(video),name=video.name,size=video.stat().st_size,modified=video.stat().st_mtime,duration=10,width=100,height=100,codec='h264',thumbnail=''))
            self.assertEqual(db.count(),1)
            db.replace_scenes(1,[1.5,4.0]);self.assertEqual(len(db.get_scenes(1)),2)
            db.replace_transcript(1,[(0,2,'hello video world')]);self.assertEqual(len(db.search_analysis('hello')),1)
            db.save_ocr(1,2,'heart ultrasound');self.assertEqual(len(db.search_analysis('ultrasound')),1)
            db.save_hash(1,video,sha256_file(video))
            db.add_to_collection('medical',1);self.assertEqual(len(db.collection_items('medical')),1)
            db.conn.close()

if __name__=='__main__':unittest.main()
