import tempfile
import unittest
from pathlib import Path
from videoatlas.db import Catalog

class SemanticSchemaTests(unittest.TestCase):
    def test_semantic_schema_and_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Catalog(Path(tmp)/'test.sqlite')
            db.initialize_analysis();db.initialize_queue();db.initialize_semantic()
            db.upsert({'path':str(Path(tmp)/'movie.mp4'),'name':'movie.mp4','size':123,'modified':1,'duration':10,'width':1280,'height':720,'codec':'h264','thumbnail':''})
            vid=db.conn.execute('SELECT id FROM videos').fetchone()[0]
            db.enqueue_jobs('semantic',[vid],str(Path(tmp)/'clip'))
            self.assertEqual(db.pending_jobs(),1)
            db.conn.execute('INSERT INTO semantic_frames(video_id,seconds,thumbnail,model_id,vector) VALUES(?,?,?,?,?)',(vid,1,'frame.jpg','local-model','[0.1,0.2]'))
            self.assertEqual(db.conn.execute('SELECT count(*) FROM semantic_frames').fetchone()[0],1)
            db.conn.close()

if __name__=='__main__':unittest.main()
