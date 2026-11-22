"""End-to-end media pipeline test against a generated, non-user video.

Run on Windows after packaging; never modifies a user's media library.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def check(distribution):
    root = Path(distribution).resolve()
    def tool(name):
        for candidate in (root/'_internal'/'bin'/f'{name}.exe', root/'bin'/f'{name}.exe'):
            if candidate.is_file(): return str(candidate)
        raise FileNotFoundError(f'Bundled {name}.exe missing')
    ffmpeg, ffprobe = tool('ffmpeg'), tool('ffprobe')
    with tempfile.TemporaryDirectory(prefix='videoatlas-media-') as td:
        folder = Path(td)
        movie = folder/'synthetic.mp4'
        thumb = folder/'thumbnail.jpg'
        commands = [
            [ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-y','-f','lavfi','-i','testsrc2=size=320x240:rate=10:duration=4','-c:v','mpeg4','-q:v','5',str(movie)],
            [ffprobe,'-v','error','-select_streams','v:0','-show_entries','stream=width,height,codec_name:format=duration','-of','json',str(movie)],
            [ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-y','-ss','1','-i',str(movie),'-frames:v','1',str(thumb)],
        ]
        results=[]
        for cmd in commands:
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=45,check=False)
            if result.returncode:
                raise RuntimeError(f'{Path(cmd[0]).name} failed: {result.stderr[-1200:]}')
            results.append(result)
        metadata=json.loads(results[1].stdout)
        stream=metadata['streams'][0]
        duration=float(metadata['format']['duration'])
        if stream['width']!=320 or stream['height']!=240 or not 3.5<=duration<=4.5:
            raise AssertionError(f'Unexpected probe metadata: {metadata}')
        if not movie.is_file() or movie.stat().st_size<1000 or not thumb.is_file() or thumb.stat().st_size<100:
            raise AssertionError('Synthetic video or thumbnail missing')
        return {'ok':True,'resolution':'320x240','duration_seconds':duration,
                'video_bytes':movie.stat().st_size,'thumbnail_bytes':thumb.stat().st_size}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('distribution',nargs='?',default='dist/VideoAtlas')
    parser.add_argument('--report',default='')
    args=parser.parse_args()
    try:
        report=check(args.distribution)
    except Exception as exc:
        report={'ok':False,'error':str(exc)}
    output=json.dumps(report,indent=2)
    print(output)
    if args.report: Path(args.report).write_text(output,encoding='utf-8')
    return 0 if report['ok'] else 1

if __name__=='__main__': sys.exit(main())
