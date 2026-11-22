"""Persistent, resumable local analysis queue. One worker owns its SQLite connection."""
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot
from .db import Catalog
from .analysis import sha256_file, detect_scenes, frame, ocr_frame, transcribe_whisper

class BatchWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(str)

    def __init__(self, database, cache):
        super().__init__()
        self.database = str(database)
        self.cache = Path(cache)
        self.cancelled = False

    @Slot()
    def run(self):
        db = Catalog(self.database)
        db.initialize_analysis()
        db.initialize_queue()
        db.initialize_semantic()
        done = 0
        try:
            total = db.pending_jobs()
            while not self.cancelled:
                job = db.claim_job()
                if job is None:
                    break
                job = dict(job)
                try:
                    video = db.conn.execute('SELECT * FROM videos WHERE id=?', (job['video_id'],)).fetchone()
                    if video is None or not Path(video['path']).is_file():
                        raise FileNotFoundError('Video missing or disconnected')
                    path = video['path']
                    if job['kind'] == 'hash':
                        db.save_hash(job['video_id'], path, sha256_file(path))
                    elif job['kind'] == 'scenes':
                        times = detect_scenes(path)
                        folder = self.cache / 'scenes' / str(job['video_id'])
                        folder.mkdir(parents=True, exist_ok=True)
                        thumbs = []
                        for i, seconds in enumerate(times):
                            if self.cancelled:
                                raise InterruptedError('Cancelled')
                            output = folder / f'{i:06d}.jpg'
                            try:
                                frame(path, seconds, output, 320)
                                thumbs.append((seconds, str(output)))
                            except Exception:
                                thumbs.append((seconds, ''))
                        db.replace_scenes_with_thumbnails(job['video_id'], thumbs)
                    elif job['kind'] == 'ocr':
                        duration = max(float(video['duration'] or 0), 0)
                        for seconds in range(0, max(1, int(duration)), 60):
                            if self.cancelled:
                                raise InterruptedError('Cancelled')
                            content = ocr_frame(path, seconds, job['options'] or None)
                            if content:
                                db.save_ocr(job['video_id'], seconds, content)
                    elif job['kind'] == 'semantic':
                        from .semantic import index_video
                        index_video(db,job['video_id'],path,self.cache,job['options'])
                    elif job['kind'] == 'transcript':
                        model = job['options']
                        db.replace_transcript(job['video_id'], transcribe_whisper(path, model))
                    else:
                        raise ValueError('Unknown analysis job')
                    db.complete_job(job['id'])
                except InterruptedError:
                    db.defer_job(job['id'])
                    break
                except Exception as exc:
                    db.fail_job(job['id'], str(exc))
                done += 1
                self.progress.emit(done, total, f"{job['kind']}: {Path(video['path']).name if video else job['video_id']}")
            self.finished.emit(f'Processed {done} jobs. {db.pending_jobs()} queued; {db.failed_jobs()} failed.')
        except Exception as exc:
            self.finished.emit(f'Batch stopped: {exc}')
        finally:
            db.conn.close()
