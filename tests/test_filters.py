import tempfile,unittest
from pathlib import Path
from videoatlas.db import Catalog
class FilterTests(unittest.TestCase):
 def test_filters(self):
  with tempfile.TemporaryDirectory() as d:
   db=Catalog(Path(d)/'test.sqlite')
   for name,duration,exists in [('short.mp4',10,True),('long.mp4',700,True),('missing.mp4',900,False)]:
    path=Path(d)/name
    if exists:path.write_bytes(b'video')
    db.upsert(dict(path=str(path),name=name,size=5,modified=duration,duration=duration,width=1,height=1,codec='test',thumbnail=''))
   self.assertEqual(len(db.search_filtered(min_duration=600)),2)
   self.assertEqual(len(db.search_filtered(offline_only=True)),1)
   self.assertEqual(db.search_filtered(term='long')[0]['name'],'long.mp4')
   self.assertEqual(len(db.search_filtered(term='missing',offline_only=True)),1)
   db.conn.close()
