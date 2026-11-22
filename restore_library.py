"""Restore a validated VideoAtlas library into a NEW directory (not the live profile)."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from videoatlas.migration import restore_to_new_directory

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('new_directory', type=Path)
    args = parser.parse_args()
    print('Restored to:', restore_to_new_directory(args.archive, args.new_directory))
