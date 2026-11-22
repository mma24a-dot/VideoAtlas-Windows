"""Run on a restored catalog directory while VideoAtlas is closed."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from videoatlas.migration import remap_restored_paths

parser = argparse.ArgumentParser(description='Preview or apply drive-root remapping in a RESTORED VideoAtlas catalog.')
parser.add_argument('restored_directory')
parser.add_argument('old_root')
parser.add_argument('new_root')
parser.add_argument('--apply', action='store_true', help='Actually modify restored catalog (default: preview only)')
args = parser.parse_args()
print(remap_restored_paths(args.restored_directory, args.old_root, args.new_root, dry_run=not args.apply))
