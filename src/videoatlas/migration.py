"""Offline catalog export and safe restore, with no video content copied."""
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path

MAX_FILES = 250000
MAX_UNCOMPRESSED = 8 * 1024**3


def _digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def export_catalog(catalog, data_dir, destination):
    """Create a portable, verified catalog snapshot. Original videos are excluded."""
    base = Path(data_dir).resolve()
    dest = Path(destination).resolve()
    if dest.exists():
        raise FileExistsError(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        snapshot = Path(tmp) / 'catalog.sqlite'
        catalog.backup_to(snapshot)
        items = [snapshot]
        for folder_name in ('thumbnails',):
            folder = base / folder_name
            if folder.is_dir():
                items.extend(p for p in folder.rglob('*') if p.is_file() and not p.is_symlink())
        for filename in ('folders.txt',):
            p = base / filename
            if p.is_file():
                items.append(p)
        if len(items) > MAX_FILES:
            raise ValueError('Too many files to export')
        manifest = {}
        try:
            with zipfile.ZipFile(dest, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3, allowZip64=True) as archive:
                for item in items:
                    name = 'catalog.sqlite' if item == snapshot else item.relative_to(base).as_posix()
                    manifest[name] = {'sha256': _digest(item), 'size': item.stat().st_size}
                    archive.write(item, name)
                archive.writestr('manifest.json', json.dumps({'format': 'videoatlas-backup-v1', 'files': manifest}, sort_keys=True))
        except BaseException:
            dest.unlink(missing_ok=True)
            raise
    return dest


def validate_archive(source):
    """Validate names, sizes, checksums and SQLite integrity before restoration."""
    with zipfile.ZipFile(source) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_FILES + 1:
            raise ValueError('Archive has too many entries')
        names = [i.filename for i in entries]
        if len(set(names)) != len(names) or 'manifest.json' not in names:
            raise ValueError('Missing manifest or duplicate names')
        for entry in entries:
            p = Path(entry.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in entry.filename or ':' in entry.filename:
                raise ValueError('Unsafe archive path')
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Symlinks are not allowed')
        if sum(i.file_size for i in entries) > MAX_UNCOMPRESSED:
            raise ValueError('Archive exceeds size limit')
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('format') != 'videoatlas-backup-v1':
            raise ValueError('Unsupported backup format')
        files = manifest['files']
        if set(files) != set(names) - {'manifest.json'} or 'catalog.sqlite' not in files:
            raise ValueError('Manifest does not match archive')
        with tempfile.TemporaryDirectory() as tmp:
            for name, info in files.items():
                target = Path(tmp) / name
                target.parent.mkdir(parents=True, exist_ok=True)
                h = hashlib.sha256()
                count = 0
                with archive.open(name) as src, open(target, 'wb') as out:
                    while block := src.read(1024 * 1024):
                        count += len(block)
                        if count > info['size']:
                            raise ValueError('Size mismatch')
                        h.update(block)
                        out.write(block)
                if count != info['size'] or h.hexdigest() != info['sha256']:
                    raise ValueError('Backup checksum mismatch: ' + name)
            connection = sqlite3.connect(f'file:{Path(tmp) / "catalog.sqlite"}?mode=ro', uri=True)
            try:
                if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('Database integrity check failed')
            finally:
                connection.close()
    return {'files': len(files), 'bytes': sum(v['size'] for v in files.values())}


def restore_to_new_directory(source, destination):
    """Restore into a new, non-existing directory. Never replace live data."""
    dest = Path(destination).resolve()
    if dest.exists():
        raise FileExistsError('Restore requires a new empty destination path')
    validate_archive(source)
    try:
        dest.mkdir(parents=True)
        with zipfile.ZipFile(source) as archive:
            for name in archive.namelist():
                if name == 'manifest.json':
                    continue
                target = dest / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as src, open(target, 'wb') as out:
                    shutil.copyfileobj(src, out)
        return dest
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)
        raise


def remap_restored_paths(destination, old_root, new_root, dry_run=True):
    """Remap a restored (not live) catalog and folders.txt, preserving video IDs.

    Prefix matching is path-component aware, case-insensitive for Windows paths.
    Does not check file existence: external drives may be disconnected.
    """
    import ntpath
    base = Path(destination).resolve()
    database = base / 'catalog.sqlite'
    if not database.is_file():
        raise FileNotFoundError('No restored catalog.sqlite in destination')
    def normalize(root):
        value = ntpath.normpath(str(root).strip().replace('/', '\\'))
        if not value or value in ('.', '\\') or not ntpath.isabs(value):
            raise ValueError('Use an absolute Windows drive or UNC path')
        return value.rstrip('\\') if len(value) > 3 else value
    old, new = normalize(old_root), normalize(new_root)
    if old.casefold() == new.casefold():
        raise ValueError('Old and new roots are identical')
    def mapped(path):
        path = str(path)
        canonical = ntpath.normpath(path.replace('/', '\\'))
        prefix = old.rstrip('\\') + '\\'
        if canonical.casefold() == old.casefold():
            return new
        if canonical.casefold().startswith(prefix.casefold()):
            return new.rstrip('\\') + canonical[len(old):]
        return None
    conn = sqlite3.connect(str(database))
    try:
        rows = conn.execute('SELECT id,path FROM videos').fetchall()
        changes = [(mapped(path), vid, path) for vid, path in rows]
        changes = [(target, vid, original) for target, vid, original in changes if target is not None]
        existing = {path.casefold(): vid for vid, path in rows}
        targets = set()
        for target, vid, _ in changes:
            key = target.casefold()
            if key in targets or (key in existing and existing[key] != vid):
                raise ValueError('Remapping would produce duplicate video paths')
            targets.add(key)
        folder_path = base / 'folders.txt'
        original_folders = folder_path.read_text(encoding='utf-8').splitlines() if folder_path.exists() else []
        updated_folders = [mapped(p) or p for p in original_folders]
        if not dry_run:
            with conn:
                conn.executemany('UPDATE videos SET path=? WHERE id=?', [(target, vid) for target, vid, _ in changes])
            if folder_path.exists():
                folder_path.write_text('\n'.join(updated_folders), encoding='utf-8')
        return {'videos': len(changes), 'folders': sum(a != b for a,b in zip(original_folders, updated_folders)), 'dry_run': dry_run}
    finally:
        conn.close()
