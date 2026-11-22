"""Download and bundle MIT-licensed Tabler PNG toolbar icons."""
import json
import shutil
import zipfile
from pathlib import Path

root=Path(__file__).resolve().parent
source=root/'node_modules'/'@tabler'/'icons-png'/'icons'/'outline'
destination=root/'assets'/'icons'
destination.mkdir(parents=True,exist_ok=True)
mapping={
 'add-folder':'folder-plus','rescan':'refresh','stop-scan':'player-stop',
 'scenes':'movie','timeline':'timeline','gallery':'photo','contact-sheet':'layout-grid',
 'sha-256':'fingerprint','duplicates':'files','find-duplicates':'file-search',
 'transcribe':'microphone','ocr-frame':'scan','ai-search':'search',
 'visual-search':'photo-search','add-collection':'folder-plus','view-collection':'folder-open',
 'queue-batch':'list-check','run-jobs':'player-play','stop-batch':'player-stop',
 'queue-status':'list-details','possible-dupes':'files','move-files':'folder-symlink',
 'backup':'database-export','export':'file-export','validate':'shield-check',
 'restore':'restore','db-health':'database','dupe-details':'file-search',
 'offline-status':'wifi-off','ai-models':'brain',
}
missing=[]
for label,icon in mapping.items():
    file=source/(icon+'.png')
    if not file.is_file():
        missing.append(icon)
        continue
    shutil.copyfile(file,destination/(label+'.png'))
if missing:
    raise RuntimeError('Missing Tabler icons: '+', '.join(missing))
license_file=root/'node_modules'/'@tabler'/'icons-png'/'LICENSE'
if not license_file.is_file():
    license_file=root/'node_modules'/'@tabler'/'icons-png'/'LICENSE.md'
if not license_file.is_file():
    raise RuntimeError('Tabler license not found')
shutil.copyfile(license_file,destination/'TABLER-LICENSE.txt')
with zipfile.ZipFile(root/'VideoAtlas-Toolbar-Icons.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(destination.glob('*.png')):
        archive.write(path,'icons/'+path.name)
    archive.write(destination/'TABLER-LICENSE.txt','icons/TABLER-LICENSE.txt')
print('Packaged',len(mapping),'icons')
