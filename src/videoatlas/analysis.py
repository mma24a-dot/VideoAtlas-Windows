"""Offline optional media analysis; original videos are never modified."""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
import shutil
import sys

from .deployment import find_tool

def binary(name):
    return find_tool(name) or ''

FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

def sha256_file(path, chunk=4*1024*1024):
    digest=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(chunk),b''):
            digest.update(block)
    return digest.hexdigest()

def detect_scenes(path, threshold=0.35, timeout=900):
    """Return scene timestamps based on FFmpeg's scene-change score."""
    exe=binary('ffmpeg')
    if not exe: raise RuntimeError('FFmpeg is required for scene detection')
    cmd=[exe,'-hide_banner','-nostdin','-i',str(path),'-vf',f"select='gt(scene,{threshold})',showinfo",'-an','-f','null','-']
    proc=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,creationflags=FLAGS)
    if proc.returncode: raise RuntimeError(proc.stderr[-800:])
    return sorted(set(round(float(x),3) for x in re.findall(r'pts_time:([0-9.]+)',proc.stderr)))

def frame(path,seconds,output,width=480):
    exe=binary('ffmpeg')
    if not exe: raise RuntimeError('FFmpeg not found')
    proc=subprocess.run([exe,'-hide_banner','-loglevel','error','-nostdin','-y','-ss',str(seconds),'-i',str(path),'-frames:v','1','-vf',f'scale={width}:-2',str(output)],capture_output=True,timeout=60,creationflags=FLAGS)
    if proc.returncode or not Path(output).is_file(): raise RuntimeError('Could not extract frame')
    return str(output)

def contact_sheet(path,duration,output,cache,columns=4,count=16):
    from PIL import Image,ImageDraw
    cache=Path(cache); cache.mkdir(parents=True,exist_ok=True)
    images=[]
    for index in range(count):
        timestamp=max(0,(index+0.5)*max(duration,1)/count)
        filename=cache/f'contact-{index}.jpg'
        try:
            frame(path,timestamp,filename,320)
            with Image.open(filename) as image: images.append((timestamp,image.convert('RGB').copy()))
        except (RuntimeError,OSError,subprocess.TimeoutExpired): continue
    if not images: raise RuntimeError('No video frames could be extracted')
    cell_w,cell_h=320,210
    sheet=Image.new('RGB',(columns*cell_w,((len(images)+columns-1)//columns)*cell_h),'#111827')
    draw=ImageDraw.Draw(sheet)
    for i,(seconds,img) in enumerate(images):
        x=(i%columns)*cell_w;y=(i//columns)*cell_h
        img.thumbnail((cell_w,180));sheet.paste(img,(x,y))
        draw.text((x+8,y+183),f'{int(seconds)//3600:02d}:{int(seconds)%3600//60:02d}:{int(seconds)%60:02d}',fill='white')
    sheet.save(output,quality=90)
    return output

def transcribe_whisper(path, model_path):
    """Uses a locally installed whisper.cpp executable and a local model; no downloads."""
    import shutil
    exe=binary('whisper-cli') or shutil.which('main')
    if not exe: raise RuntimeError('Install whisper.cpp and add whisper-cli to PATH')
    if not Path(model_path).is_file(): raise RuntimeError('Select a local whisper.cpp GGML model')
    ffmpeg=binary('ffmpeg')
    if not ffmpeg: raise RuntimeError('FFmpeg required')
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        wav=Path(temp)/'audio.wav'
        p=subprocess.run([ffmpeg,'-nostdin','-y','-i',str(path),'-vn','-ac','1','-ar','16000','-c:a','pcm_s16le',str(wav)],capture_output=True,creationflags=FLAGS)
        if p.returncode: raise RuntimeError('Audio extraction failed')
        p=subprocess.run([exe,'-m',str(model_path),'-f',str(wav),'-oj','-of',str(Path(temp)/'transcript')],capture_output=True,text=True,creationflags=FLAGS)
        output=Path(temp)/'transcript.json'
        if p.returncode or not output.exists(): raise RuntimeError((p.stderr or 'Transcription failed')[-500:])
        data=json.loads(output.read_text(encoding='utf-8'))
        return [(int(s['offsets']['from'])/1000,int(s['offsets']['to'])/1000,s['text'].strip()) for s in data.get('transcription',[])]

def ocr_frame(path,seconds,tessdata=None):
    import shutil,tempfile
    exe=binary('tesseract')
    if not exe: raise RuntimeError('Install Tesseract OCR locally')
    with tempfile.TemporaryDirectory() as temp:
        jpg=Path(temp)/'frame.jpg';frame(path,seconds,jpg,1280)
        env=os.environ.copy()
        if tessdata: env['TESSDATA_PREFIX']=str(Path(tessdata).resolve())
        p=subprocess.run([exe,str(jpg),'stdout'],capture_output=True,text=True,creationflags=FLAGS,env=env)
        if p.returncode: raise RuntimeError(p.stderr[-500:])
        return p.stdout.strip()
