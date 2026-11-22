import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot
from .db import Catalog

EXTENSIONS = {'.mp4','.mkv','.avi','.mov','.wmv','.flv','.webm','.m4v','.mpg','.mpeg','.mts','.m2ts','.ts','.3gp','.vob'}

from .deployment import find_tool

def binary(name):
    return find_tool(name) or ''


def probe(path):
    result = {'duration':0.0,'width':0,'height':0,'codec':''}
    exe = binary('ffprobe')
    if not exe: return result
    try:
        proc = subprocess.run([exe,'-v','error','-show_entries','format=duration:stream=codec_name,width,height,codec_type',
            '-of','json',str(path)], capture_output=True,text=True,timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        data=json.loads(proc.stdout)
        result['duration']=float(data.get('format',{}).get('duration') or 0)
        stream=next((s for s in data.get('streams',[]) if s.get('codec_type')=='video'),{})
        result.update(width=int(stream.get('width') or 0),height=int(stream.get('height') or 0),codec=stream.get('codec_name') or '')
    except (OSError,ValueError,subprocess.TimeoutExpired,json.JSONDecodeError): pass
    return result

def thumbnail(path, cache, modified=None):
    exe=binary('ffmpeg')
    if not exe: return ''
    target=cache / (hashlib.sha256((str(path)+str(modified or '')).encode('utf-8')).hexdigest()+'.jpg')
    if target.is_file(): return str(target)
    try:
        subprocess.run([exe,'-nostdin','-y','-ss','00:00:02','-i',str(path),'-frames:v','1',
            '-vf','scale=320:-2','-q:v','5',str(target)],stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,timeout=35,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        return str(target) if target.is_file() else ''
    except (OSError,subprocess.TimeoutExpired): return ''

class Scanner(QObject):
    progress=Signal(int,str)
    finished=Signal(int,str)
    def __init__(self, db_path, cache, folders):
        super().__init__(); self.db_path=db_path; self.cache=Path(cache); self.folders=folders; self.cancelled=False
    @Slot()
    def run(self):
        catalog=None; count=0; error=''
        try:
            catalog=Catalog(self.db_path)
            for folder in self.folders:
                if self.cancelled: break
                def onerror(err): self.progress.emit(count, f'Cannot read: {err.filename}')
                for root, dirs, files in os.walk(folder, onerror=onerror):
                    if self.cancelled: break
                    for filename in files:
                        if self.cancelled: break
                        path=Path(root)/filename
                        if path.suffix.lower() not in EXTENSIONS: continue
                        try:
                            stat=path.stat()
                            old=catalog.existing(path)
                            if old and old['size']==stat.st_size and old['modified']==stat.st_mtime: continue
                            metadata=probe(path)
                            item=dict(path=str(path),name=filename,size=stat.st_size,modified=stat.st_mtime,
                                      thumbnail=thumbnail(path,self.cache,stat.st_mtime),**metadata)
                            catalog.upsert(item); count+=1
                            if count%5==0: self.progress.emit(count,filename)
                        except (OSError,ValueError) as exc:
                            self.progress.emit(count,f'Skipped {filename}: {exc}')
        except Exception as exc: error=str(exc)
        finally:
            if catalog: catalog.conn.close()
            self.finished.emit(count,error)
