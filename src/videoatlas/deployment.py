"""Offline deployment diagnostics; never downloads or executes untrusted content."""
import os
import shutil
import subprocess
import sys
from pathlib import Path


def application_root():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))


def find_tool(name, root=None):
    root = Path(root) if root is not None else application_root()
    names = [name + '.exe', name] if os.name == 'nt' else [name, name + '.exe']
    for folder in (root / 'bin', root / 'src' / 'bin'):
        for candidate in names:
            path = folder / candidate
            if path.is_file():
                return str(path)
    return shutil.which(name) or (shutil.which(name + '.exe') if os.name != 'nt' else None)


def model_directory_valid(path):
    p = Path(path).expanduser()
    return p.is_dir() and (p / 'config.json').is_file() and any(
        (p / f).is_file() for f in ('model.safetensors', 'pytorch_model.bin', 'model.safetensors.index.json', 'pytorch_model.bin.index.json')
    )


def diagnostics(model_dir=None, root=None):
    checks = {}
    for name in ('ffmpeg', 'ffprobe', 'tesseract', 'whisper-cli'):
        path = find_tool(name, root)
        checks[name] = {'available': bool(path), 'path': path or ''}
    if model_dir:
        checks['clip_model'] = {'available': model_directory_valid(model_dir), 'path': str(model_dir)}
    return checks


def probe_ffmpeg(root=None):
    tool = find_tool('ffmpeg', root)
    if not tool:
        return False, 'FFmpeg not found'
    try:
        result = subprocess.run([tool, '-version'], capture_output=True, text=True, timeout=8)
        return result.returncode == 0, (result.stdout or result.stderr).splitlines()[0][:250]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
