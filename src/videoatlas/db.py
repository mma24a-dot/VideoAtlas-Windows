import sqlite3
from pathlib import Path

class Catalog:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA busy_timeout=5000')
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS videos (
          id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
          size INTEGER NOT NULL, modified REAL NOT NULL, duration REAL DEFAULT 0,
          width INTEGER DEFAULT 0, height INTEGER DEFAULT 0, codec TEXT DEFAULT '',
          thumbnail TEXT DEFAULT '', notes TEXT DEFAULT '', added TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS tags(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS video_tags(video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
          tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE, PRIMARY KEY(video_id, tag_id));
        CREATE TABLE IF NOT EXISTS collections(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS collection_videos(collection_id INTEGER, video_id INTEGER,
          PRIMARY KEY(collection_id, video_id));
        CREATE INDEX IF NOT EXISTS ix_video_name ON videos(name);
        CREATE INDEX IF NOT EXISTS ix_video_size ON videos(size);
        CREATE INDEX IF NOT EXISTS ix_video_modified ON videos(modified);
        ''')
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS video_search USING fts5(name, notes, content='videos', content_rowid='id')")
        self.conn.executescript('''
        CREATE TRIGGER IF NOT EXISTS videos_ai AFTER INSERT ON videos BEGIN
          INSERT INTO video_search(rowid,name,notes) VALUES(new.id,new.name,new.notes); END;
        CREATE TRIGGER IF NOT EXISTS videos_ad AFTER DELETE ON videos BEGIN
          INSERT INTO video_search(video_search,rowid,name,notes) VALUES('delete',old.id,old.name,old.notes); END;
        CREATE TRIGGER IF NOT EXISTS videos_au AFTER UPDATE OF name,notes ON videos BEGIN
          INSERT INTO video_search(video_search,rowid,name,notes) VALUES('delete',old.id,old.name,old.notes);
          INSERT INTO video_search(rowid,name,notes) VALUES(new.id,new.name,new.notes); END;
        ''')
        self.conn.commit()

    def upsert(self, item):
        self.conn.execute('''INSERT INTO videos(path,name,size,modified,duration,width,height,codec,thumbnail)
          VALUES(:path,:name,:size,:modified,:duration,:width,:height,:codec,:thumbnail)
          ON CONFLICT(path) DO UPDATE SET name=excluded.name,size=excluded.size,
          modified=excluded.modified,duration=excluded.duration,width=excluded.width,
          height=excluded.height,codec=excluded.codec,thumbnail=excluded.thumbnail''', item)
        self.conn.commit()

    def existing(self, path):
        return self.conn.execute('SELECT size,modified FROM videos WHERE path=?',(str(path),)).fetchone()

    def search(self, term='', limit=150, offset=0):
        if term.strip():
            # LIKE deliberately supports partial filenames and notes without requiring FTS syntax.
            q = '%' + term.strip().replace('\\','\\\\').replace('%','\\%').replace('_','\\_') + '%'
            return self.conn.execute('''SELECT v.*, COALESCE(group_concat(t.name, ', '),'') tags
                FROM videos v LEFT JOIN video_tags vt ON vt.video_id=v.id
                LEFT JOIN tags t ON t.id=vt.tag_id
                WHERE (v.name LIKE ? ESCAPE '\\' OR v.notes LIKE ? ESCAPE '\\' OR v.path LIKE ? ESCAPE '\\'
                OR EXISTS(SELECT 1 FROM video_tags x JOIN tags y ON y.id=x.tag_id WHERE x.video_id=v.id AND y.name LIKE ? ESCAPE '\\'))
                GROUP BY v.id ORDER BY v.modified DESC LIMIT ? OFFSET ?''',(q,q,q,q,limit,offset)).fetchall()
        return self.conn.execute('''SELECT v.*, COALESCE(group_concat(t.name, ', '),'') tags
            FROM videos v LEFT JOIN video_tags vt ON vt.video_id=v.id
            LEFT JOIN tags t ON t.id=vt.tag_id GROUP BY v.id
            ORDER BY v.modified DESC LIMIT ? OFFSET ?''',(limit,offset)).fetchall()

    def search_filtered(self, term='', limit=150, offset=0, min_duration=0, offline_only=False):
        import os
        if offline_only:
            result=[]; skipped=0
            cursor=self.conn.execute("""SELECT v.*,COALESCE((SELECT group_concat(t.name, ', ') FROM video_tags vt JOIN tags t ON t.id=vt.tag_id WHERE vt.video_id=v.id),'') tags FROM videos v WHERE v.duration>=? ORDER BY v.modified DESC,v.id DESC""",(min_duration,))
            needle=term.strip().casefold()
            for r in cursor:
                if os.path.isfile(r['path']):continue
                if needle and needle not in (r['name']+' '+r['path']+' '+r['notes']+' '+r['tags']).casefold():continue
                if skipped<offset:skipped+=1;continue
                result.append(r)
                if len(result)>=limit:break
            return result
        needle='%'+term.strip().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        return self.conn.execute("""SELECT v.*,COALESCE((SELECT group_concat(t.name, ', ') FROM video_tags vt JOIN tags t ON t.id=vt.tag_id WHERE vt.video_id=v.id),'') tags
            FROM videos v WHERE v.duration>=? AND (?='' OR v.name LIKE ? ESCAPE char(92) OR v.notes LIKE ? ESCAPE char(92) OR v.path LIKE ? ESCAPE char(92) OR EXISTS
            (SELECT 1 FROM video_tags vt JOIN tags t ON t.id=vt.tag_id WHERE vt.video_id=v.id AND t.name LIKE ? ESCAPE char(92)))
            ORDER BY v.modified DESC,v.id DESC LIMIT ? OFFSET ?""",(min_duration,term.strip(),needle,needle,needle,needle,limit,offset)).fetchall()

    def count(self):
        return self.conn.execute('SELECT COUNT(*) FROM videos').fetchone()[0]

    def save_details(self, video_id, notes, tags):
        with self.conn:
            self.conn.execute('UPDATE videos SET notes=? WHERE id=?',(notes,video_id))
            self.conn.execute('DELETE FROM video_tags WHERE video_id=?',(video_id,))
            for tag in sorted(set(x.strip() for x in tags.split(',') if x.strip())):
                self.conn.execute('INSERT OR IGNORE INTO tags(name) VALUES(?)',(tag,))
                self.conn.execute('INSERT OR IGNORE INTO video_tags(video_id,tag_id) VALUES(?,(SELECT id FROM tags WHERE name=?))',(video_id,tag))

    def duplicates(self):
        return self.conn.execute('''SELECT size, COUNT(*) n FROM videos WHERE size>0
            GROUP BY size HAVING COUNT(*)>1 ORDER BY n DESC LIMIT 100''').fetchall()

    def initialize_analysis(self):
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS scenes(id INTEGER PRIMARY KEY,video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,seconds REAL NOT NULL,notes TEXT DEFAULT '',UNIQUE(video_id,seconds));
        CREATE TABLE IF NOT EXISTS transcripts(id INTEGER PRIMARY KEY,video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,start REAL,end REAL,text TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ocr_results(id INTEGER PRIMARY KEY,video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,seconds REAL,text TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS hashes(video_id INTEGER PRIMARY KEY REFERENCES videos(id) ON DELETE CASCADE,sha256 TEXT NOT NULL,size INTEGER NOT NULL,modified REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS ix_scenes_video ON scenes(video_id,seconds);
        CREATE INDEX IF NOT EXISTS ix_transcripts_video ON transcripts(video_id,start);
        CREATE INDEX IF NOT EXISTS ix_hashes_digest ON hashes(sha256);
        CREATE VIRTUAL TABLE IF NOT EXISTS analysis_search USING fts5(text,video_id UNINDEXED,kind UNINDEXED,seconds UNINDEXED);
        ''')
        self.conn.commit()

    def replace_scenes(self,vid,times):
        with self.conn:
            self.conn.execute('DELETE FROM scenes WHERE video_id=?',(vid,))
            self.conn.executemany('INSERT INTO scenes(video_id,seconds) VALUES(?,?)',[(vid,t) for t in times])

    def get_scenes(self,vid):
        return self.conn.execute('SELECT seconds,notes,thumbnail FROM scenes WHERE video_id=? ORDER BY seconds',(vid,)).fetchall()

    def replace_transcript(self,vid,segments):
        with self.conn:
            self.conn.execute('DELETE FROM transcripts WHERE video_id=?',(vid,))
            self.conn.execute("DELETE FROM analysis_search WHERE video_id=? AND kind='transcript'",(vid,))
            self.conn.executemany('INSERT INTO transcripts(video_id,start,end,text) VALUES(?,?,?,?)',[(vid,*s) for s in segments])
            self.conn.executemany('INSERT INTO analysis_search(text,video_id,kind,seconds) VALUES(?,?,?,?)',[(s[2],vid,'transcript',s[0]) for s in segments])

    def save_ocr(self,vid,seconds,content):
        with self.conn:
            self.conn.execute('INSERT INTO ocr_results(video_id,seconds,text) VALUES(?,?,?)',(vid,seconds,content))
            self.conn.execute('INSERT INTO analysis_search(text,video_id,kind,seconds) VALUES(?,?,?,?)',(content,vid,'ocr',seconds))

    def save_hash(self,vid,path,digest):
        stat=Path(path).stat()
        with self.conn:
            self.conn.execute('INSERT OR REPLACE INTO hashes(video_id,sha256,size,modified) VALUES(?,?,?,?)',(vid,digest,stat.st_size,stat.st_mtime))

    def verified_duplicates(self):
        return self.conn.execute('''SELECT h.sha256,COUNT(*) n,group_concat(v.path,char(10)) paths FROM hashes h JOIN videos v ON v.id=h.video_id WHERE h.size=v.size AND h.modified=v.modified GROUP BY h.sha256 HAVING COUNT(*)>1 ORDER BY n DESC''').fetchall()

    def search_analysis(self,query,limit=100):
        terms=' '.join('"'+word.replace('"','')+'"' for word in query.split() if word.strip('"'))
        if not terms: return []
        return self.conn.execute('''SELECT a.video_id,a.kind,a.seconds,snippet(analysis_search,0,'[',']','…',12) excerpt,v.name FROM analysis_search a JOIN videos v ON v.id=CAST(a.video_id AS INTEGER) WHERE analysis_search MATCH ? LIMIT ?''',(terms,limit)).fetchall()

    def collections_list(self):
        return self.conn.execute('SELECT id,name FROM collections ORDER BY name').fetchall()

    def add_to_collection(self,name,vid):
        with self.conn:
            self.conn.execute('INSERT OR IGNORE INTO collections(name) VALUES(?)',(name,))
            self.conn.execute('INSERT OR IGNORE INTO collection_videos(collection_id,video_id) VALUES((SELECT id FROM collections WHERE name=?),?)',(name,vid))

    def collection_items(self,name):
        return self.conn.execute('''SELECT v.name,v.path FROM collection_videos cv JOIN collections c ON c.id=cv.collection_id JOIN videos v ON v.id=cv.video_id WHERE c.name=? ORDER BY v.name''',(name,)).fetchall()

    def initialize_queue(self):
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS analysis_jobs (
            id INTEGER PRIMARY KEY, video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
            kind TEXT NOT NULL, options TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'pending',
            error TEXT NOT NULL DEFAULT '', created TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(video_id,kind,options));
        CREATE INDEX IF NOT EXISTS ix_jobs_status ON analysis_jobs(status,id);
        ''')
        columns = {r['name'] for r in self.conn.execute('PRAGMA table_info(scenes)')}
        if 'thumbnail' not in columns:
            self.conn.execute("ALTER TABLE scenes ADD COLUMN thumbnail TEXT DEFAULT ''")
        # Recover interrupted jobs from previous application sessions.
        self.conn.execute("UPDATE analysis_jobs SET status='pending' WHERE status='running'")
        self.conn.commit()

    def initialize_semantic(self):
        self.conn.executescript('''CREATE TABLE IF NOT EXISTS semantic_frames (
          id INTEGER PRIMARY KEY, video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
          seconds REAL NOT NULL, thumbnail TEXT NOT NULL, model_id TEXT NOT NULL,
          vector TEXT NOT NULL);
          CREATE INDEX IF NOT EXISTS ix_semantic_model ON semantic_frames(model_id);
          CREATE INDEX IF NOT EXISTS ix_semantic_video ON semantic_frames(video_id);''')
        self.conn.commit()

    def enqueue_jobs(self, kind, video_ids, options=''):
        if kind not in ('hash', 'scenes', 'ocr', 'transcript', 'semantic'):
            raise ValueError('Unsupported job kind')
        with self.conn:
            self.conn.executemany('''INSERT INTO analysis_jobs(video_id,kind,options) VALUES(?,?,?)
                ON CONFLICT(video_id,kind,options) DO UPDATE SET status='pending',error='' ''',
                [(int(vid),kind,options) for vid in video_ids])

    def pending_jobs(self):
        return self.conn.execute("SELECT COUNT(*) FROM analysis_jobs WHERE status='pending'").fetchone()[0]

    def failed_jobs(self):
        return self.conn.execute("SELECT COUNT(*) FROM analysis_jobs WHERE status='failed'").fetchone()[0]

    def claim_job(self):
        with self.conn:
            row = self.conn.execute("SELECT * FROM analysis_jobs WHERE status='pending' ORDER BY id LIMIT 1").fetchone()
            if row:
                self.conn.execute("UPDATE analysis_jobs SET status='running' WHERE id=?", (row['id'],))
            return row

    def complete_job(self, job_id):
        with self.conn:
            self.conn.execute("UPDATE analysis_jobs SET status='done',error='' WHERE id=?", (job_id,))

    def defer_job(self, job_id):
        with self.conn:
            self.conn.execute("UPDATE analysis_jobs SET status='pending' WHERE id=?", (job_id,))

    def fail_job(self, job_id, error):
        with self.conn:
            self.conn.execute("UPDATE analysis_jobs SET status='failed',error=? WHERE id=?", (error[:2000], job_id))

    def replace_scenes_with_thumbnails(self, vid, scenes):
        with self.conn:
            self.conn.execute('DELETE FROM scenes WHERE video_id=?', (vid,))
            self.conn.executemany('INSERT INTO scenes(video_id,seconds,thumbnail) VALUES(?,?,?)',
                                  [(vid, float(t), thumb) for t,thumb in scenes])

    def queue_summary(self):
        return self.conn.execute('SELECT status,COUNT(*) AS n FROM analysis_jobs GROUP BY status').fetchall()

    def queue_failures(self, limit=30):
        return self.conn.execute('''SELECT j.kind,v.name,j.error FROM analysis_jobs j
            JOIN videos v ON v.id=j.video_id WHERE j.status='failed' ORDER BY j.id DESC LIMIT ?''', (limit,)).fetchall()

    def integrity_report(self):
        """Check SQLite structure and foreign keys without altering the catalog."""
        quick = [row[0] for row in self.conn.execute('PRAGMA quick_check')]
        foreign = [tuple(row) for row in self.conn.execute('PRAGMA foreign_key_check')]
        return {'ok': quick == ['ok'] and not foreign, 'quick_check': quick, 'foreign_key_violations': foreign}

    def backup_to(self, destination):
        """Consistent snapshot even when the catalog is in WAL mode."""
        dest = Path(destination).expanduser().resolve()
        source = Path(self.conn.execute('PRAGMA database_list').fetchone()[2]).resolve()
        if dest == source:
            raise ValueError('Backup destination must differ from the live database')
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            raise FileExistsError('Choose a new backup filename to avoid overwriting existing backups')
        # SQLite backup API produces a transactionally consistent database copy.
        target = sqlite3.connect(str(dest))
        try:
            self.conn.backup(target, pages=256, sleep=0.05)
            check = target.execute('PRAGMA quick_check').fetchone()[0]
            if check != 'ok':
                raise RuntimeError('Backup integrity check failed: ' + check)
        except Exception:
            target.close()
            dest.unlink(missing_ok=True)
            raise
        else:
            target.close()
        return dest

    def duplicate_groups(self, limit=100):
        """Only hashes still matching the recorded file size and modification time."""
        return self.conn.execute("""SELECT h.sha256,COUNT(*) AS copies,SUM(v.size) AS total_bytes,
          MIN(v.size) AS file_bytes FROM hashes h JOIN videos v ON v.id=h.video_id
          WHERE h.size=v.size AND h.modified=v.modified
          GROUP BY h.sha256 HAVING COUNT(*)>1 ORDER BY copies DESC LIMIT ?""", (limit,)).fetchall()

    def duplicate_group_files(self, sha256):
        return self.conn.execute("""SELECT v.id,v.name,v.path,v.size FROM hashes h
          JOIN videos v ON v.id=h.video_id WHERE h.sha256=?
          AND h.size=v.size AND h.modified=v.modified ORDER BY v.path""", (sha256,)).fetchall()

    def advanced_filter(self, *, term='', min_width=0, min_height=0, min_size=0,
                        max_size=None, codec='', min_duration=0, max_duration=None,
                        offline_only=False, limit=150, offset=0, extensions=None):
        #Consistent filters, including tags, before pagination.

        import os
        clauses=['v.width>=?', 'v.height>=?', 'v.size>=?', 'v.duration>=?']
        params=[min_width,min_height,min_size,min_duration]
        if extensions is not None:
            extensions=sorted(set(extensions))
            if not extensions:
                return []
            clauses.append('('+' OR '.join('lower(v.path) LIKE ?' for _ in extensions)+')')
            params.extend('%'+ext.lower() for ext in extensions)
        if max_size is not None:
            clauses.append('v.size<=?'); params.append(max_size)
        if max_duration is not None:
            clauses.append('v.duration<=?'); params.append(max_duration)
        if codec.strip():
            clauses.append('v.codec LIKE ? ESCAPE char(92)')
            params.append('%'+self._escape_like(codec.strip())+'%')
        if term.strip():
            needle='%'+self._escape_like(term.strip())+'%'
            clauses.append('''(v.name LIKE ? ESCAPE char(92) OR v.path LIKE ? ESCAPE char(92)
                OR v.notes LIKE ? ESCAPE char(92) OR EXISTS
                (SELECT 1 FROM video_tags vt JOIN tags t ON t.id=vt.tag_id
                 WHERE vt.video_id=v.id AND t.name LIKE ? ESCAPE char(92)))''')
            params.extend([needle]*4)
        sql='''SELECT v.*,COALESCE((SELECT group_concat(t.name, ', ') FROM video_tags vt
               JOIN tags t ON t.id=vt.tag_id WHERE vt.video_id=v.id),'') tags
               FROM videos v WHERE '''+' AND '.join(clauses)+' ORDER BY v.modified DESC,v.id DESC'
        limit=max(1,int(limit)); offset=max(0,int(offset))
        if not offline_only:
            return self.conn.execute(sql+' LIMIT ? OFFSET ?',params+[limit,offset]).fetchall()
        result=[]; skipped=0
        for row in self.conn.execute(sql,params):
            if os.path.isfile(row['path']): continue
            if skipped<offset:
                skipped+=1; continue
            result.append(row)
            if len(result)==limit: break
        return result

    @staticmethod
    def _escape_like(value):
        return value.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
