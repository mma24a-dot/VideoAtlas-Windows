from pathlib import Path
from PySide6.QtCore import QObject,Signal,Slot
from .db import Catalog
from .analysis import sha256_file,detect_scenes,contact_sheet,transcribe_whisper,ocr_frame

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
                times=detect_scenes(path);db.replace_scenes(vid,times);result=f'Detected {len(times)} scene changes'
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
