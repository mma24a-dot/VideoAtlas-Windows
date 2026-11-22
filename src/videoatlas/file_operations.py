"""Safe file operations and content-verified duplicate discovery."""
import hashlib
import shutil
from collections import defaultdict
from pathlib import Path


def sha256(path, chunk_size=4 * 1024 * 1024):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b''):
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicates(paths):
    """Only return files whose contents match, never size-only candidates."""
    by_size = defaultdict(list)
    for entry in paths:
        path = Path(entry)
        try:
            if path.is_file():
                by_size[path.stat().st_size].append(path)
        except OSError:
            continue
    groups = []
    for size, candidates in by_size.items():
        if len(candidates) < 2:
            continue
        by_hash = defaultdict(list)
        for path in candidates:
            try:
                by_hash[sha256(path)].append(str(path))
            except OSError:
                continue
        groups.extend({'size': size, 'sha256': digest, 'paths': matches}
                      for digest, matches in by_hash.items() if len(matches) > 1)
    return sorted(groups, key=lambda item: (-len(item['paths']), -item['size']))


def move_matching_files(paths, needle, destination):
    """Move exact file paths with a case-insensitive filename substring match.

    Never overwrite existing files, never move a file into itself, and only
    operate on the explicit list of source paths supplied by the caller.
    """
    needle = needle.strip().casefold()
    if not needle:
        raise ValueError('Enter a nonempty filename search term.')
    destination = Path(destination).resolve()
    if not destination.is_dir():
        raise ValueError('Choose an existing destination folder.')
    moved, skipped = [], []
    for entry in paths:
        source = Path(entry)
        if needle not in source.name.casefold():
            continue
        try:
            if not source.is_file():
                skipped.append((str(source), 'File unavailable'))
                continue
            target = destination / source.name
            if source.resolve() == target.resolve() or target.exists():
                skipped.append((str(source), 'Destination exists or is the source'))
                continue
            shutil.move(str(source), str(target))
            moved.append((str(source), str(target)))
        except OSError as exc:
            skipped.append((str(source), str(exc)))
    return moved, skipped
