import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from videoatlas.db import Catalog

class BatchQueueTests(unittest.TestCase):
    def test_queue_lifecycle_and_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            db=Catalog(Path(temp)/'catalog.db')
            db.initialize_analysis(); db.initialize_queue()
            path=str(Path(temp)/'sample.mp4')
            db.upsert(dict(path=path,name='sample.mp4',size=100,modified=1.,duration=5.,width=100,height=100,codec='h264',thumbnail=''))
            vid=db.conn.execute('SELECT id FROM videos').fetchone()[0]
            db.enqueue_jobs('scenes',[vid]);db.enqueue_jobs('scenes',[vid])
            self.assertEqual(db.pending_jobs(),1)
            job=db.claim_job();self.assertEqual(job['kind'],'scenes')
            self.assertEqual(db.pending_jobs(),0)
            db.initialize_queue();self.assertEqual(db.pending_jobs(),1)
            job=db.claim_job();db.fail_job(job['id'],'missing')
            self.assertEqual(db.failed_jobs(),1)
            db.enqueue_jobs('scenes',[vid]);job=db.claim_job()
            db.replace_scenes_with_thumbnails(vid,[(1.0,'a.jpg'),(3.0,'b.jpg')])
            db.complete_job(job['id'])
            self.assertEqual(db.conn.execute('SELECT COUNT(*) FROM scenes').fetchone()[0],2)
            self.assertEqual(db.pending_jobs(),0)
            db.conn.close()

if __name__=='__main__':unittest.main()
