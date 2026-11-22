"""Offline-only model registry. Stores paths, never downloads models."""
import json
import os
import tempfile
from pathlib import Path
from .offline_bundle import verify_manifest

KINDS = ('clip', 'whisper', 'tesseract')

def registry_path(base):
    return Path(base) / 'models.json'

def load_registry(base):
    path = registry_path(base)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('Invalid model registry')
    return {k: v for k, v in data.items() if k in KINDS and isinstance(v, str)}

def validate_model(kind, path):
    if kind not in KINDS:
        raise ValueError('Unsupported model type')
    p = Path(path).expanduser().resolve()
    if kind == 'clip':
        valid = p.is_dir() and (p / 'config.json').is_file() and any(
            (p / name).is_file() for name in ('model.safetensors', 'pytorch_model.bin', 'model.safetensors.index.json', 'pytorch_model.bin.index.json'))
    elif kind == 'whisper':
        valid = p.is_file() and p.suffix.lower() == '.bin'
    else:
        valid = p.is_dir() and any(p.glob('*.traineddata'))
    return valid, str(p)

def save_model(base, kind, path):
    valid, resolved = validate_model(kind, path)
    if not valid:
        raise ValueError(f'Invalid {kind} model location: {resolved}')
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    data = load_registry(base)
    data[kind] = resolved
    target = registry_path(base)
    fd, temp = tempfile.mkstemp(prefix='.models-', suffix='.json', dir=base)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return resolved

def remove_model(base, kind):
    if kind not in KINDS:
        raise ValueError('Unsupported model type')
    data = load_registry(base)
    data.pop(kind, None)
    target = registry_path(base)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2), encoding='utf-8')

def check_registry(base):
    result = {}
    for kind, path in load_registry(base).items():
        valid, resolved = validate_model(kind, path)
        result[kind] = {'valid': valid, 'path': resolved}
    return result

def verify_model_manifest(root, manifest):
    return verify_manifest(root, manifest)
