"""Persistent, revision-tracked HNSW index for offline scene search.

SQLite remains authoritative. Triggers invalidate saved indexes after any scene edit.
Indexes are rebuilt only when the relevant model's rows change.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile


def _revision(db):
    db.conn.executescript('''
      CREATE TABLE IF NOT EXISTS semantic_index_revision (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL DEFAULT 0);
      INSERT OR IGNORE INTO semantic_index_revision(id,revision) VALUES(1,0);
      CREATE TRIGGER IF NOT EXISTS semantic_index_insert AFTER INSERT ON semantic_frames BEGIN
        UPDATE semantic_index_revision SET revision=revision+1 WHERE id=1; END;
      CREATE TRIGGER IF NOT EXISTS semantic_index_delete AFTER DELETE ON semantic_frames BEGIN
        UPDATE semantic_index_revision SET revision=revision+1 WHERE id=1; END;
      CREATE TRIGGER IF NOT EXISTS semantic_index_update AFTER UPDATE ON semantic_frames BEGIN
        UPDATE semantic_index_revision SET revision=revision+1 WHERE id=1; END;
    ''')
    return db.conn.execute('SELECT revision FROM semantic_index_revision WHERE id=1').fetchone()[0]


def search_hnsw(db, model_id, target, limit=30, cache_dir=None):
    try:
        import numpy as np
        import hnswlib
    except ImportError:
        return None
    if not target or limit < 1:
        return []
    dimension=len(target)
    target=np.asarray(target,dtype=np.float32)
    if not np.isfinite(target).all() or not np.linalg.norm(target):
        return []
    revision=_revision(db)
    key=hashlib.sha256((model_id+'|'+str(dimension)).encode()).hexdigest()
    root=Path(cache_dir) if cache_dir else Path(db.conn.execute('PRAGMA database_list').fetchone()[2]).parent/'vector-index'
    root.mkdir(parents=True,exist_ok=True)
    index_file=root/(key+'.bin'); meta_file=root/(key+'.json')
    records=None; index=None
    if index_file.exists() and meta_file.exists():
        try:
            meta=json.loads(meta_file.read_text(encoding='utf-8'))
            if meta['revision']==revision and meta['dimension']==dimension:
                records=meta['records']
                if records:
                    index=hnswlib.Index(space='cosine',dim=dimension)
                    index.load_index(str(index_file),max_elements=len(records))
        except (ValueError,KeyError,OSError,RuntimeError):
            index=None
    if index is None:
        records=[]; vectors=[]
        for row in db.conn.execute('''SELECT f.video_id,f.seconds,f.thumbnail,f.vector,v.name,v.path
          FROM semantic_frames f JOIN videos v ON v.id=f.video_id WHERE f.model_id=? ORDER BY f.id''',(model_id,)):
            try:
                vec=np.asarray(json.loads(row['vector']),dtype=np.float32)
                if vec.shape!=(dimension,) or not np.isfinite(vec).all() or not np.linalg.norm(vec): continue
                records.append([int(row['video_id']),float(row['seconds']),row['name'],row['path'],row['thumbnail']])
                vectors.append(vec)
            except (ValueError,TypeError): continue
        if not records: return []
        index=hnswlib.Index(space='cosine',dim=dimension)
        index.init_index(max_elements=len(records),ef_construction=150,M=24)
        index.add_items(np.stack(vectors),np.arange(len(records)))
        # Save binary first, metadata last. A crash cannot make stale metadata valid.
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            tmp_index=Path(tmp)/'index.bin';tmp_meta=Path(tmp)/'meta.json'
            index.save_index(str(tmp_index))
            tmp_meta.write_text(json.dumps({'revision':revision,'dimension':dimension,'records':records}),encoding='utf-8')
            os.replace(tmp_index,index_file)
            os.replace(tmp_meta,meta_file)
    count=min(limit,len(records))
    index.set_ef(max(50,count))
    labels,distances=index.knn_query(target,k=count)
    return [(float(1-distance),*records[int(label)]) for label,distance in zip(labels[0],distances[0])]
