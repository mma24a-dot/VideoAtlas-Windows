"""CLI: python verify_offline_bundle.py verify ROOT MANIFEST.json
         python verify_offline_bundle.py create ROOT MANIFEST.json relative/path ...
"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent / "src"))
import json
from pathlib import Path
from videoatlas.offline_bundle import create_manifest, verify_manifest

p=argparse.ArgumentParser(description='Offline asset integrity tool')
p.add_argument('action', choices=['create','verify'])
p.add_argument('root')
p.add_argument('manifest')
p.add_argument('paths', nargs='*')
a=p.parse_args()
if a.action == 'create':
    if not a.paths: p.error('create requires one or more relative file paths')
    Path(a.manifest).write_text(json.dumps(create_manifest(a.root,a.paths),indent=2),encoding='utf-8')
    print('Manifest written:',a.manifest)
else:
    result=verify_manifest(a.root,a.manifest)
    for entry in result: print(entry['status'],entry['path'])
    if any(x['status']!='ok' for x in result): raise SystemExit(1)
    print('All',len(result),'assets verified')
