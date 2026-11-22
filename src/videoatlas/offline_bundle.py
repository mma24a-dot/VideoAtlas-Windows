"""Deterministic, offline verification of local runtime/model assets.

Manifest files are user-provided trust anchors; checksums detect accidental changes,
not authenticity of an untrusted manifest. No network calls are made.
"""
import hashlib
import json
from pathlib import Path


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b''):
            digest.update(chunk)
    return digest.hexdigest()


def create_manifest(root, relative_paths):
    root = Path(root).resolve()
    files = []
    for relative in sorted(set(relative_paths)):
        target = _safe_path(root, relative)
        if not target.is_file():
            raise FileNotFoundError(relative)
        files.append({'path': relative.replace('\\', '/'), 'size': target.stat().st_size,
                      'sha256': sha256_file(target)})
    return {'schema': 1, 'files': files}


def _safe_path(root, relative):
    path = Path(relative)
    if path.is_absolute() or not path.parts or '..' in path.parts:
        raise ValueError('Unsafe relative path')
    target = (root / path).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Path escapes bundle root')
    return target


def verify_manifest(root, manifest):
    root = Path(root).resolve()
    if isinstance(manifest, (str, Path)):
        manifest = json.loads(Path(manifest).read_text(encoding='utf-8'))
    if manifest.get('schema') != 1 or not isinstance(manifest.get('files'), list):
        raise ValueError('Unsupported bundle manifest')
    results = []
    seen = set()
    for entry in manifest['files']:
        relative = entry['path']
        if relative in seen:
            raise ValueError('Duplicate manifest entry')
        seen.add(relative)
        target = _safe_path(root, relative)
        if not target.is_file():
            status = 'missing'
        elif target.stat().st_size != entry['size']:
            status = 'size_mismatch'
        elif sha256_file(target).lower() != entry['sha256'].lower():
            status = 'hash_mismatch'
        else:
            status = 'ok'
        results.append({'path': relative, 'status': status})
    return results
