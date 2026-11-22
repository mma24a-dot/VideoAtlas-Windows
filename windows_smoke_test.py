"""Read-only smoke test of a frozen VideoAtlas Windows distribution.

Runs on Windows build agents; does not require launching the GUI or opening videos.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from verify_windows_release import verify_distribution


def smoke_test(folder, timeout=20):
    root = Path(folder).resolve()
    report = verify_distribution(root)
    report['runtime'] = {}
    if not report['ok']:
        return report
    for name in ('ffmpeg', 'ffprobe'):
        binary = next((root / rel for rel in (f'bin/{name}.exe', f'_internal/bin/{name}.exe') if (root / rel).is_file()), None)
        try:
            result = subprocess.run([str(binary), '-version'], capture_output=True, text=True,
                                    timeout=timeout, check=False, env=os.environ.copy())
            success = result.returncode == 0 and name in result.stdout.lower()
            report['runtime'][name] = {'ok': success, 'returncode': result.returncode,
                                        'first_line': result.stdout.splitlines()[0] if result.stdout else ''}
            if not success:
                report['errors'].append(f'{name} failed version smoke test')
        except (OSError, subprocess.TimeoutExpired) as exc:
            report['runtime'][name] = {'ok': False, 'error': str(exc)}
            report['errors'].append(f'{name} could not run: {exc}')
    report['ok'] = not report['errors']
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('distribution', nargs='?', default='dist/VideoAtlas')
    parser.add_argument('--report', default='')
    args = parser.parse_args()
    result = smoke_test(args.distribution)
    output = json.dumps(result, indent=2)
    print(output)
    if args.report:
        Path(args.report).write_text(output, encoding='utf-8')
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
