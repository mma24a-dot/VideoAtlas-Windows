import tempfile
import unittest
from pathlib import Path
from videoatlas.db import Catalog
from videoatlas.vector_index import _revision

class Version08Tests(unittest.TestCase):
    def test_revision_invalidation(self):
        with tempfile.TemporaryDirectory() as d:
            db=Catalog(Path(d)/'catalog.sqlite'); db.initialize_semantic()
            r=_revision(db)
            db.upsert(dict(path=str(Path(d)/'v.mp4'),name='v.mp4',size=100,modified=1,duration=10,width=640,height=480,codec='h264',thumbnail=''))
            v=db.conn.execute('SELECT id FROM videos').fetchone()[0]
            with db.conn:
                db.conn.execute('INSERT INTO semantic_frames(video_id,seconds,thumbnail,model_id,vector) VALUES(?,?,?,?,?)',(v,1,'','m','[1,0]'))
            self.assertGreater(_revision(db),r)
            db.conn.close()
