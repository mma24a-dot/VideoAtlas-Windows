import hashlib
from pathlib import Path
from PySide6.QtCore import QObject,Signal,Slot
from .db import Catalog
from .analysis import sha256_file,detect_scenes,contact_sheet,transcribe_whisper,ocr_frame,frame

class AnalysisJob(QObject):
    finished=Signal(str,str)
    def __init__(self,db_path,video,kind,options=None):
        super().__init__();self.db_path=db_path;self.video=dict(video);self.kind=kind;self.options=options or {}
    @Slot()
    def run(self):
        db=None
        try:
            path=self.video['path'];vid=self.video['id']
            if not Path(path).is_file(): raise RuntimeError('Video is offline or missing')
            db=Catalog(self.db_path);db.initialize_analysis()
            if self.kind=='scenes':
                times=detect_scenes(path)
                cache=Path(self.options.get('scene_cache') or Path.home()/'.videoatlas-scene-cache')
                cache.mkdir(parents=True, exist_ok=True)
                scenes=[]
                failed=0
                for seconds in times:
                    key=hashlib.sha256(f'{path}|{self.video.get("modified", "")}|{seconds}'.encode('utf-8')).hexdigest()
                    thumbnail=cache/(key+'.jpg')
                    if not thumbnail.is_file() or thumbnail.stat().st_size==0:
                        try:
                            frame(path, seconds, thumbnail, 320)
                        except Exception:
                            failed+=1
                            thumbnail=None
                    scenes.append((seconds,str(thumbnail) if thumbnail and thumbnail.is_file() else ''))
                db.replace_scenes_with_thumbnails(vid,scenes)
                result=f'Detected {len(times)} scene changes; generated {len(times)-failed} thumbnails'
                if failed: result+=f' ({failed} frames could not be extracted)'
            elif self.kind=='hash':
                digest=sha256_file(path);db.save_hash(vid,path,digest);result=f'SHA-256: {digest}'
            elif self.kind=='contact':
                output=self.options['output'];contact_sheet(path,self.video['duration'],output,self.options['cache']);result=f'Contact sheet saved: {output}'
            elif self.kind=='transcript':
                segments=transcribe_whisper(path,self.options['model']);db.replace_transcript(vid,segments);result=f'Transcribed {len(segments)} segments'
            elif self.kind=='ocr':
                seconds=self.options['seconds'];content=ocr_frame(path,seconds,self.options.get('tessdata'));db.save_ocr(vid,seconds,content);result=f'OCR at {seconds:.1f}s: {content[:150] or "No text found"}'
            else: raise ValueError('Unknown job')
            self.finished.emit(result,'')
        except Exception as exc:self.finished.emit('',str(exc))
        finally:
            if db:db.conn.close()
