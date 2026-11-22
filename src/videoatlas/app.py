import os
import sys
import subprocess
from pathlib import Path
from PySide6.QtCore import Qt, QThread, QUrl, QTimer
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QSplitter,
 QLineEdit,QPushButton,QLabel,QListWidget,QListWidgetItem,QFileDialog,QTextEdit,QMessageBox,
 QComboBox,QFormLayout,QGroupBox,QScrollArea,QGridLayout,QFrame,QToolBar,QDialog,QInputDialog,QDialogButtonBox,QSpinBox,QCheckBox)
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from .db import Catalog
from .scanner import Scanner, binary
from .jobs import AnalysisJob
from .batch import BatchWorker

BASE=Path(os.getenv('LOCALAPPDATA') or Path.home()/'.local'/'share')/'VideoAtlas'
BASE.mkdir(parents=True,exist_ok=True)
CACHE=BASE/'thumbnails'; CACHE.mkdir(exist_ok=True)
DB=BASE/'catalog.sqlite'

DARK='''QWidget{background:#141820;color:#e7edf6;font-size:13px} QLineEdit,QTextEdit,QListWidget,QComboBox{background:#202734;border:1px solid #364252;border-radius:5px;padding:6px} QPushButton{background:#345d98;border:0;border-radius:5px;padding:9px} QPushButton:hover{background:#4778bd} QGroupBox{border:1px solid #364252;margin-top:12px;padding:10px} QGroupBox::title{subcontrol-origin:margin;left:8px}'''
LIGHT='''QWidget{background:#f5f7fb;color:#1d2939;font-size:13px} QLineEdit,QTextEdit,QListWidget,QComboBox{background:white;border:1px solid #cbd5e1;border-radius:5px;padding:6px} QPushButton{background:#dbeafe;border:1px solid #93b4dd;border-radius:5px;padding:9px} QPushButton:hover{background:#bfdbfe} QGroupBox{border:1px solid #cbd5e1;margin-top:12px;padding:10px} QGroupBox::title{subcontrol-origin:margin;left:8px}'''

class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.db=Catalog(DB); self.page=0; self.term=''; self.current=None; self.worker=None; self.thread=None
        self.setWindowTitle('VideoAtlas — Offline Video Catalog'); self.resize(1370,820)
        self.player=QMediaPlayer(self); self.audio=QAudioOutput(self); self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.65)
        self.db.initialize_analysis(); self.db.initialize_queue(); self.db.initialize_semantic(); self.analysis_thread=None; self.analysis_worker=None
        self.batch_thread=None; self.batch_worker=None
        self.setup_ui(); self.set_theme('Dark'); self.refresh()

    def setup_ui(self):
        bar=QToolBar('Library'); self.addToolBar(bar)
        add=QAction('Add folder',self); add.triggered.connect(self.add_folder); bar.addAction(add)
        rescan=QAction('Rescan folders',self); rescan.triggered.connect(self.scan_folders); bar.addAction(rescan)
        stop=QAction('Stop scan',self); stop.triggered.connect(self.stop_scan); bar.addAction(stop)
        bar.addSeparator(); bar.addWidget(QLabel(' Theme: '))
        self.theme=QComboBox(); self.theme.addItems(['Dark','Light']); self.theme.currentTextChanged.connect(self.set_theme); bar.addWidget(self.theme)
        bar.addSeparator()
        for title,handler in [('Detect scenes',self.detect_selected_scenes),('Scene timeline',self.scene_timeline),('Scene gallery',self.scene_gallery),('Contact sheet',self.make_contact_sheet),('SHA-256',self.hash_selected),('Verified duplicates',self.show_verified_duplicates),('Transcribe audio',self.transcribe_selected),('OCR current frame',self.ocr_selected),('AI text search',self.search_ai),('Visual semantic search',self.semantic_search),('Add to collection',self.add_collection),('View collection',self.view_collection)]:
            action=QAction(title,self);action.triggered.connect(handler);bar.addAction(action)
        bar.addSeparator()
        for title,handler in [('Queue batch analysis',self.queue_batch),('Run queued jobs',self.run_batch),('Stop batch',self.stop_batch),('Queue status',self.show_queue)]:
            action=QAction(title,self); action.triggered.connect(handler); bar.addAction(action)
        bar.addSeparator(); duplicates=QAction('Possible duplicates',self); duplicates.triggered.connect(self.show_duplicates); bar.addAction(duplicates)
        for title, handler in [('Backup catalog', self.backup_catalog), ('Export library package', self.export_library_package), ('Validate backup package', self.validate_backup_package), ('Restore to new folder', self.restore_library_gui), ('Database health', self.check_database), ('Duplicate details', self.duplicate_details)]:
            action=QAction(title,self); action.triggered.connect(handler); bar.addAction(action)
        check=QAction('Offline readiness',self); check.triggered.connect(self.offline_readiness); bar.addAction(check)
        models=QAction('Local AI models',self); models.triggered.connect(self.manage_models); bar.addAction(models)
        self.statusBar().showMessage('Ready — all catalog data remains on this computer')
        split=QSplitter(Qt.Horizontal); self.setCentralWidget(split)
        left=QWidget(); lv=QVBoxLayout(left); lv.addWidget(QLabel('LIBRARY FOLDERS'))
        self.folders=QListWidget(); self.folders.setMaximumHeight(230); lv.addWidget(self.folders)
        remove=QPushButton('Remove selected folder'); remove.clicked.connect(self.remove_folder); lv.addWidget(remove)
        lv.addWidget(QLabel('SEARCH VIDEOS / TAGS'))
        self.search=QLineEdit(); self.search.setPlaceholderText('Filename, notes, path, tag…'); self.search.textChanged.connect(self.debounce_search); lv.addWidget(self.search)
        self.timer=QTimer(self); self.timer.setSingleShot(True); self.timer.setInterval(250); self.timer.timeout.connect(self.search_now)
        filters=QHBoxLayout()
        self.min_duration=QSpinBox(); self.min_duration.setRange(0,100000); self.min_duration.setSuffix(' min+')
        self.min_duration.setToolTip('Minimum video duration in minutes')
        self.offline_only=QCheckBox('Offline only')
        self.min_duration.valueChanged.connect(lambda _:self.apply_filters())
        self.offline_only.toggled.connect(lambda _:self.apply_filters())
        filters.addWidget(self.min_duration); filters.addWidget(self.offline_only); lv.addLayout(filters)
        lv.addWidget(QLabel('ADVANCED FILTERS'))
        advanced=QGridLayout()
        self.min_width=QSpinBox(); self.min_width.setRange(0,16384); self.min_width.setSuffix(' px width+')
        self.min_height=QSpinBox(); self.min_height.setRange(0,16384); self.min_height.setSuffix(' px height+')
        self.min_size=QSpinBox(); self.min_size.setRange(0,1000000); self.min_size.setSuffix(' MB+')
        self.codec_filter=QLineEdit(); self.codec_filter.setPlaceholderText('Codec (e.g. h264)')
        for i,widget in enumerate((self.min_width,self.min_height,self.min_size,self.codec_filter)):
            advanced.addWidget(widget,i//2,i%2)
            if isinstance(widget,QSpinBox): widget.valueChanged.connect(lambda _:self.apply_filters())
            else: widget.textChanged.connect(self.debounce_search)
        lv.addLayout(advanced)
        lv.addWidget(QLabel('VIDEOS'))
        self.items=QListWidget(); self.items.setIconSize(__import__('PySide6.QtCore',fromlist=['QSize']).QSize(112,64))
        self.items.currentItemChanged.connect(self.select_video); lv.addWidget(self.items,1)
        paging=QHBoxLayout(); prev=QPushButton('◀ Previous'); nxt=QPushButton('Next ▶')
        prev.clicked.connect(lambda:self.change_page(-1)); nxt.clicked.connect(lambda:self.change_page(1))
        paging.addWidget(prev); paging.addWidget(nxt); lv.addLayout(paging)
        self.counter=QLabel(''); lv.addWidget(self.counter)
        split.addWidget(left)
        right=QWidget(); rv=QVBoxLayout(right)
        self.video=QVideoWidget(); self.video.setMinimumHeight(280); self.player.setVideoOutput(self.video); rv.addWidget(self.video,3)
        playback=QHBoxLayout(); play=QPushButton('▶ Play'); pause=QPushButton('Ⅱ Pause'); openfile=QPushButton('Open externally')
        play.clicked.connect(self.player.play); pause.clicked.connect(self.player.pause); openfile.clicked.connect(self.open_external)
        for b in (play,pause,openfile): playback.addWidget(b)
        rv.addLayout(playback)
        from PySide6.QtWidgets import QSlider
        self.seek=QSlider(Qt.Horizontal); self.seek.setRange(0,1000); self.seek.sliderMoved.connect(self.seek_to)
        self.player.positionChanged.connect(self.position_changed); rv.addWidget(self.seek)
        self.info=QLabel('Select a video'); self.info.setWordWrap(True); rv.addWidget(self.info)
        group=QGroupBox('Catalog metadata'); form=QFormLayout(group)
        self.tags=QLineEdit(); self.tags.setPlaceholderText('Comma-separated tags'); self.notes=QTextEdit(); self.notes.setMaximumHeight(100)
        form.addRow('Tags',self.tags); form.addRow('Notes',self.notes)
        save=QPushButton('Save tags and notes'); save.clicked.connect(self.save_details); form.addRow(save)
        rv.addWidget(group,2); split.addWidget(right); split.setSizes([500,870])
        self.load_folders()

    def manage_models(self):
        from .model_registry import load_registry, save_model, remove_model, check_registry
        dialog=QDialog(self); dialog.setWindowTitle('Local AI models — offline'); dialog.resize(680,320)
        layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Select models already on this computer. Nothing is downloaded or uploaded.'))
        rows={}
        for kind, description in [('clip','CLIP visual search folder'),('whisper','Whisper.cpp .bin file'),('tesseract','Tesseract tessdata folder')]:
            line=QHBoxLayout(); label=QLabel(description); label.setMinimumWidth(190)
            location=QLineEdit(load_registry(BASE).get(kind,'')); location.setReadOnly(True)
            choose=QPushButton('Select'); clear=QPushButton('Clear')
            def select_model(checked=False, kind=kind, location=location):
                if kind=='whisper':
                    path,_=QFileDialog.getOpenFileName(dialog,'Select local Whisper model','','Binary model (*.bin)')
                else:
                    path=QFileDialog.getExistingDirectory(dialog,'Select local '+kind+' model folder')
                if not path:return
                try: location.setText(save_model(BASE,kind,path))
                except (ValueError,OSError) as exc: QMessageBox.warning(dialog,'Invalid model',str(exc))
            def clear_model(checked=False, kind=kind, location=location):
                remove_model(BASE,kind); location.clear()
            choose.clicked.connect(select_model); clear.clicked.connect(clear_model)
            for widget in (label,location,choose,clear):line.addWidget(widget)
            layout.addLayout(line); rows[kind]=location
        status=QTextEdit(); status.setReadOnly(True); layout.addWidget(status)
        def refresh_status():
            checks=check_registry(BASE)
            status.setPlainText('\n'.join(f"{kind}: {'READY' if checks.get(kind,{}).get('valid') else 'Not configured / missing'}" for kind in ('clip','whisper','tesseract')))
        refresh=QPushButton('Check configured models'); refresh.clicked.connect(refresh_status)
        layout.addWidget(refresh)
        close=QPushButton('Close'); close.clicked.connect(dialog.accept); layout.addWidget(close)
        dialog.exec()

    def offline_readiness(self):
        from .deployment import diagnostics, probe_ffmpeg
        checks=diagnostics()
        lines=[f"{name}: {'Available' if value['available'] else 'Not installed'}" + (f" — {value['path']}" if value['path'] else '') for name,value in checks.items()]
        ok, detail=probe_ffmpeg()
        lines.append(f"FFmpeg execution: {'OK' if ok else 'FAILED'} — {detail}")
        from .model_registry import check_registry
        for kind, info in check_registry(BASE).items():
            lines.append(f"{kind} model: {'READY' if info['valid'] else 'MISSING'} — {info['path']}")
        lines.append('Optional AI models are not bundled; configure them using Local AI models.')
        QMessageBox.information(self,'Offline readiness', '\n'.join(lines))

    def folder_file(self): return BASE/'folders.txt'
    def load_folders(self):
        if self.folder_file().exists():
            for line in self.folder_file().read_text(encoding='utf-8').splitlines():
                if line.strip(): self.folders.addItem(line.strip())
    def persist_folders(self):
        self.folder_file().write_text('\n'.join(self.folders.item(i).text() for i in range(self.folders.count())),encoding='utf-8')
    def add_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'Choose video library folder')
        if folder and not any(self.folders.item(i).text()==folder for i in range(self.folders.count())):
            self.folders.addItem(folder); self.persist_folders(); self.scan_folders()
    def remove_folder(self):
        for item in self.folders.selectedItems(): self.folders.takeItem(self.folders.row(item))
        self.persist_folders()
    def scan_folders(self):
        if self.thread is not None: return
        folders=[self.folders.item(i).text() for i in range(self.folders.count())]
        if not folders: QMessageBox.information(self,'VideoAtlas','Add a library folder first.'); return
        self.thread=QThread(self); self.worker=Scanner(DB,CACHE,folders); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.progress.connect(lambda n,s:self.statusBar().showMessage(f'Indexed {n} videos — {s}'))
        self.worker.finished.connect(self.scan_finished); self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.clear_thread)
        self.thread.start(); self.statusBar().showMessage('Scanning video folders in background…')
    def stop_scan(self):
        if self.worker: self.worker.cancelled=True
    def scan_finished(self,n,error):
        self.statusBar().showMessage(f'Scan completed: {n} new/changed videos. '+(f'Error: {error}' if error else ''))
        self.refresh()
    def clear_thread(self): self.worker=None; self.thread=None
    def debounce_search(self): self.timer.start()
    def search_now(self): self.page=0; self.term=self.search.text(); self.refresh()
    def change_page(self,d): self.page=max(0,self.page+d); self.refresh()
    def apply_filters(self):
        self.page=0; self.refresh()
    def refresh(self):
        self.items.clear()
        rows=self.db.advanced_filter(term=self.term,min_width=self.min_width.value(),
            min_height=self.min_height.value(),min_size=self.min_size.value()*1048576,
            codec=self.codec_filter.text(),min_duration=self.min_duration.value()*60,
            offline_only=self.offline_only.isChecked(),limit=150,offset=self.page*150)
        for row in rows:
            duration=int(row['duration'] or 0); label=f"{row['name']}\n{duration//60}:{duration%60:02d}  ·  {row['size']/1048576:.1f} MB  ·  {row['tags']}"
            item=QListWidgetItem(label); item.setData(Qt.UserRole,dict(row))
            if row['thumbnail'] and Path(row['thumbnail']).exists(): item.setIcon(QIcon(QPixmap(row['thumbnail'])))
            self.items.addItem(item)
        self.counter.setText(f'{self.db.count():,} catalogued videos · page {self.page+1} · {len(rows)} shown')
    def select_video(self,item,previous=None):
        if not item: return
        self.current=item.data(Qt.UserRole)
        r=self.current; available=Path(r['path']).is_file()
        self.info.setText(f"{r['name']}\n{r['width']}×{r['height']} · {r['codec']} · {r['size']/1073741824:.2f} GB\n{r['path']}"+('' if available else '\nOFFLINE / DRIVE DISCONNECTED'))
        self.tags.setText(r['tags']); self.notes.setPlainText(r['notes'])
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(r['path']) if available else QUrl())
    def save_details(self):
        if not self.current: return
        self.db.save_details(self.current['id'],self.notes.toPlainText(),self.tags.text())
        self.refresh(); self.statusBar().showMessage('Metadata saved')
    def open_external(self):
        if self.current and Path(self.current['path']).exists():
            if sys.platform=='win32': os.startfile(self.current['path'])
            elif sys.platform=='darwin': subprocess.Popen(['open',self.current['path']])
            else: subprocess.Popen(['xdg-open',self.current['path']])
    def seek_to(self,value):
        if self.player.duration(): self.player.setPosition(int(self.player.duration()*value/1000))
    def position_changed(self,pos):
        if self.player.duration():
            self.seek.blockSignals(True); self.seek.setValue(int(pos*1000/self.player.duration())); self.seek.blockSignals(False)
    def set_theme(self,name): QApplication.instance().setStyleSheet(DARK if name=='Dark' else LIGHT)
    def backup_catalog(self):
        from datetime import datetime
        suggestion='VideoAtlas-catalog-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.sqlite'
        destination,_=QFileDialog.getSaveFileName(self,'Save database backup',str(Path.home()/suggestion),'SQLite database (*.sqlite)')
        if not destination:return
        try:
            saved=self.db.backup_to(destination)
            QMessageBox.information(self,'Backup complete',f'Database saved to:\n{saved}\n\nAlso back up your thumbnail cache and folders.txt for a complete migration.')
        except Exception as exc:
            QMessageBox.critical(self,'Backup failed',str(exc))

    def export_library_package(self):
        from .migration import export_catalog
        destination, _ = QFileDialog.getSaveFileName(self, 'Export library package', str(Path.home() / 'VideoAtlas-library.zip'), 'ZIP archives (*.zip)')
        if not destination:
            return
        try:
            saved = export_catalog(self.db, BASE, destination)
            QMessageBox.information(self, 'Export complete', f'Catalog, folder settings and thumbnails saved to:\n{saved}\n\nOriginal video files are NOT included.')
        except Exception as exc:
            QMessageBox.critical(self, 'Export failed', str(exc))

    def validate_backup_package(self):
        from .migration import validate_archive
        source, _ = QFileDialog.getOpenFileName(self, 'Validate library package', str(Path.home()), 'ZIP archives (*.zip)')
        if not source:
            return
        try:
            info = validate_archive(source)
            QMessageBox.information(self, 'Valid backup', f"Validated {info['files']} files and {info['bytes']:,} bytes.\nRestore into a NEW directory using the migration utility; never overwrite a running catalog.")
        except Exception as exc:
            QMessageBox.critical(self, 'Invalid backup', str(exc))

    def restore_library_gui(self):
        from .migration import restore_to_new_directory
        source, _ = QFileDialog.getOpenFileName(self, 'Choose VideoAtlas backup', str(Path.home()), 'ZIP archives (*.zip)')
        if not source:
            return
        parent = QFileDialog.getExistingDirectory(self, 'Choose parent folder for restored catalog')
        if not parent:
            return
        name, ok = QInputDialog.getText(self, 'New restoration folder', 'Name for NEW folder (must not exist):', text='VideoAtlas-Restored')
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in ('.', '..') or '/' in name or "\\" in name or ':' in name:
            QMessageBox.warning(self, 'Invalid folder', 'Enter a single folder name, not a path.')
            return
        destination = Path(parent) / name
        if QMessageBox.question(self, 'Confirm safe restore',
            f'Restore to a NEW folder?\n{destination}\n\nYour active library will NOT be changed.\nOriginal videos are NOT included.') != QMessageBox.Yes:
            return
        try:
            restored = restore_to_new_directory(source, destination)
            QMessageBox.information(self, 'Restore complete',
                f'Restored to:\n{restored}\n\nThe running catalog was NOT replaced.\nUse the offline path-remapping utility if your drive letters changed.')
        except Exception as exc:
            QMessageBox.critical(self, 'Restore failed', str(exc))

    def check_database(self):
        try:
            report=self.db.integrity_report()
            QMessageBox.information(self,'Database health',('Database integrity: OK' if report['ok'] else 'Database integrity problems detected')+'\n'+str(report))
        except Exception as exc:
            QMessageBox.critical(self,'Database health check failed',str(exc))

    def duplicate_details(self):
        groups=self.db.duplicate_groups()
        if not groups:
            QMessageBox.information(self,'Verified duplicates','No matching SHA-256 groups found. Queue SHA-256 analysis first.');return
        dialog=QDialog(self);dialog.setWindowTitle('Verified duplicate groups (read-only)');dialog.resize(900,540)
        layout=QVBoxLayout(dialog);selector=QComboBox();details=QTextEdit();details.setReadOnly(True)
        for group in groups:
            selector.addItem(f"{group['copies']} copies · {group['file_bytes']/1048576:.1f} MB each · {group['sha256'][:18]}…",group['sha256'])
        def display(_=None):
            digest=selector.currentData()
            lines=[f'SHA-256: {digest}', 'These files matched their stored size and modification time at the last scan.', 'Original files will not be modified.', '']
            lines.extend(r['path'] for r in self.db.duplicate_group_files(digest))
            details.setPlainText('\n'.join(lines))
        selector.currentIndexChanged.connect(display);layout.addWidget(selector);layout.addWidget(details);display();dialog.exec()

    def show_duplicates(self):
        rows=self.db.duplicates(); msg='\n'.join(f"{r['n']} files of {r['size']/1048576:.1f} MB" for r in rows)
        QMessageBox.information(self,'Potential duplicate sizes',msg or 'No matching file sizes found.\nThis is a size-based candidate check, not a verified content hash.')
    def start_analysis(self,kind,options=None):
        if not self.current: QMessageBox.information(self,'Select video','Select a video first.');return
        if self.analysis_thread is not None: QMessageBox.information(self,'Busy','An analysis task is already running.');return
        self.analysis_thread=QThread(self);self.analysis_worker=AnalysisJob(DB,self.current,kind,options)
        self.analysis_worker.moveToThread(self.analysis_thread)
        self.analysis_thread.started.connect(self.analysis_worker.run)
        self.analysis_worker.finished.connect(self.analysis_finished)
        self.analysis_worker.finished.connect(self.analysis_thread.quit)
        self.analysis_thread.finished.connect(self.analysis_worker.deleteLater)
        self.analysis_thread.finished.connect(self.analysis_thread.deleteLater)
        self.analysis_thread.finished.connect(self.clear_analysis)
        self.analysis_thread.start();self.statusBar().showMessage(f'Running offline {kind} analysis…')

    def analysis_finished(self,result,error):
        self.statusBar().showMessage(error or result)
        if error: QMessageBox.warning(self,'Analysis error',error)
        elif result: QMessageBox.information(self,'Analysis complete',result)

    def clear_analysis(self): self.analysis_thread=None;self.analysis_worker=None
    def detect_selected_scenes(self):self.start_analysis('scenes')
    def hash_selected(self):self.start_analysis('hash')
    def open_video_id(self, video_id, seconds=0):
        # Search by primary key rather than filename: duplicate names are common.
        self.search.blockSignals(True); self.search.setText(''); self.search.blockSignals(False)
        self.term=''; self.page=0
        row=self.db.conn.execute('SELECT id FROM videos WHERE id=?',(video_id,)).fetchone()
        if row is None:return False
        self.min_duration.setValue(0); self.offline_only.setChecked(False)
        rank=self.db.conn.execute('SELECT COUNT(*) FROM videos WHERE modified>(SELECT modified FROM videos WHERE id=?) OR (modified=(SELECT modified FROM videos WHERE id=?) AND id>?)', (video_id,video_id,video_id)).fetchone()[0]
        self.page=rank//150; self.refresh()
        for i in range(self.items.count()):
            item=self.items.item(i)
            if item.data(Qt.UserRole)['id']==video_id:
                self.items.setCurrentItem(item)
                self.player.setPosition(int(seconds*1000))
                return True
        return False

    def scene_gallery(self):
        if not self.current:return
        scenes=self.db.get_scenes(self.current['id'])
        if not scenes:
            QMessageBox.information(self,'Scene gallery','Detect scenes first.');return
        dialog=QDialog(self);dialog.setWindowTitle('Scene gallery — '+self.current['name']);dialog.resize(900,650)
        layout=QVBoxLayout(dialog); scroll=QScrollArea(); scroll.setWidgetResizable(True)
        content=QWidget();grid=QGridLayout(content)
        for i,scene in enumerate(scenes[:300]):
            seconds=float(scene['seconds']); thumbnail=Path(scene['thumbnail'] or '')
            # Use existing cached images only; gallery never blocks on FFmpeg.
            button=QPushButton(f'{int(seconds//3600):02d}:{int(seconds%3600//60):02d}:{int(seconds%60):02d}')
            button.setMinimumSize(160,100)
            if scene['thumbnail'] and thumbnail.is_file():
                button.setIcon(QIcon(str(thumbnail)))
                from PySide6.QtCore import QSize
                button.setIconSize(QSize(145,75))
            button.clicked.connect(lambda checked=False,t=seconds:(self.player.setPosition(int(t*1000)),dialog.accept()))
            grid.addWidget(button,i//4,i%4)
        scroll.setWidget(content);layout.addWidget(scroll)
        layout.addWidget(QLabel(f'{len(scenes)} indexed scenes; displaying first {min(len(scenes),300)}. Click to jump.'))
        dialog.exec()

    def scene_timeline(self):
        if not self.current:return
        scenes=self.db.get_scenes(self.current['id'])
        if not scenes: QMessageBox.information(self,'Scenes','No scenes indexed. Run Detect scenes first.');return
        values=[f'{int(s["seconds"])//3600:02d}:{int(s["seconds"])%3600//60:02d}:{int(s["seconds"])%60:02d} — {s["seconds"]:.2f}s' for s in scenes]
        selected,ok=QInputDialog.getItem(self,'Scene timeline','Jump to scene',values,0,False)
        if ok:
            idx=values.index(selected);self.player.setPosition(int(scenes[idx]['seconds']*1000))
    def make_contact_sheet(self):
        if not self.current:return
        output,_=QFileDialog.getSaveFileName(self,'Export contact sheet',str(Path.home()/(Path(self.current['name']).stem+'-contact.jpg')),'JPEG (*.jpg)')
        if output:self.start_analysis('contact',{'output':output,'cache':str(CACHE/'contact-temp')})
    def show_verified_duplicates(self):
        rows=self.db.verified_duplicates()
        QMessageBox.information(self,'Verified duplicates','\n\n'.join(f'{r["n"]} copies, SHA-256 {r["sha256"][:16]}…\n{r["paths"]}' for r in rows)[:10000] or 'No verified duplicates. Hash matching-size videos first using SHA-256.')
    def transcribe_selected(self):
        from .model_resolution import resolve_model
        try: model=resolve_model(BASE,'whisper')
        except RuntimeError as exc: QMessageBox.warning(self,'Local AI model',str(exc));return
        self.start_analysis('transcript',{'model':model})
    def ocr_selected(self):
        from .model_resolution import resolve_model
        try: tessdata=resolve_model(BASE,'tesseract')
        except RuntimeError as exc: QMessageBox.warning(self,'Local AI model',str(exc));return
        self.start_analysis('ocr',{'seconds':self.player.position()/1000,'tessdata':tessdata})
    def search_ai(self):
        term,ok=QInputDialog.getText(self,'Transcript and OCR search','Search indexed speech or onscreen text:')
        if not ok or not term.strip():return
        try:rows=self.db.search_analysis(term)
        except Exception as exc:QMessageBox.warning(self,'Search error',str(exc));return
        if not rows:QMessageBox.information(self,'Search','No matches. Analyze videos first.');return
        labels=[f'{r["name"]} · {r["kind"]} · {r["seconds"]:.1f}s · {r["excerpt"]}' for r in rows]
        chosen,ok=QInputDialog.getItem(self,'Search results','Select a match',labels,0,False)
        if ok:
            row=rows[labels.index(chosen)]
            self.open_video_id(row['video_id'],row['seconds'])
    def semantic_search(self):
        from .semantic import search
        from .model_resolution import resolve_model
        try: model=resolve_model(BASE,'clip')
        except RuntimeError as exc: QMessageBox.warning(self,'Local AI model',str(exc));return
        term,ok=QInputDialog.getText(self,'Visual search','Describe the scene you want to find:')
        if not ok or not term.strip():return
        try:results=search(self.db,term,model)
        except Exception as exc:
            QMessageBox.warning(self,'Visual search',f'Local CLIP model could not run: {exc}')
            return
        if not results:
            QMessageBox.information(self,'Visual search','No indexed scenes for this model. Queue semantic analysis first.')
            return
        labels=[f'{score:.3f} | {name} | {seconds:.1f}s' for score,vid,seconds,name,path,thumb in results]
        selected,ok=QInputDialog.getItem(self,'Visual matches','Select scene:',labels,0,False)
        if ok:
            score,vid,seconds,name,path,thumb=results[labels.index(selected)]
            if not self.open_video_id(vid,seconds):
                QMessageBox.information(self,'Scene location',f'{path}\nTimestamp: {seconds:.1f}s')

    def add_collection(self):
        if not self.current:return
        name,ok=QInputDialog.getText(self,'Add to collection','Collection name:')
        if ok and name.strip():self.db.add_to_collection(name.strip(),self.current['id']);self.statusBar().showMessage('Added to collection')
    def view_collection(self):
        names=[r['name'] for r in self.db.collections_list()]
        if not names:QMessageBox.information(self,'Collections','No collections created yet.');return
        name,ok=QInputDialog.getItem(self,'Collections','Collection:',names,0,False)
        if ok:
            rows=self.db.collection_items(name)
            QMessageBox.information(self,name,'\n'.join(r['name'] for r in rows)[:12000] or 'Empty collection')
    def queue_batch(self):
        kinds=['scenes','hash','ocr','transcript','semantic']
        kind,ok=QInputDialog.getItem(self,'Batch analysis','Task:',kinds,0,False)
        if not ok:return
        scope,ok=QInputDialog.getItem(self,'Batch analysis','Videos:', ['Entire catalog','Current video'],0,False)
        if not ok:return
        options=''
        if kind=='semantic':
            from .model_resolution import resolve_model
            try: options=resolve_model(BASE,'clip')
            except RuntimeError as exc: QMessageBox.warning(self,'Local AI model',str(exc));return
        if kind=='transcript':
            from .model_resolution import resolve_model
            try: options=resolve_model(BASE,'whisper')
            except RuntimeError as exc: QMessageBox.warning(self,'Local AI model',str(exc));return
        if kind=='ocr':
            from .model_resolution import resolve_model
            try: options=resolve_model(BASE,'tesseract')
            except RuntimeError as exc: QMessageBox.warning(self,'Local AI model',str(exc));return
        if scope=='Current video':
            if not self.current:return
            ids=[self.current['id']]
        else:
            ids=[r[0] for r in self.db.conn.execute('SELECT id FROM videos')]
        if not ids:return
        self.db.enqueue_jobs(kind,ids,options)
        self.statusBar().showMessage(f'Queued {len(ids)} {kind} tasks; click Run queued jobs')

    def run_batch(self):
        if self.batch_thread is not None:return
        if not self.db.pending_jobs():
            QMessageBox.information(self,'Queue','No pending jobs.');return
        self.batch_thread=QThread(self)
        self.batch_worker=BatchWorker(DB,CACHE)
        self.batch_worker.moveToThread(self.batch_thread)
        self.batch_thread.started.connect(self.batch_worker.run)
        self.batch_worker.progress.connect(lambda done,total,name:self.statusBar().showMessage(f'Batch {done}/{total}: {name}'))
        self.batch_worker.finished.connect(self.batch_finished)
        self.batch_worker.finished.connect(self.batch_thread.quit)
        self.batch_thread.finished.connect(self.batch_worker.deleteLater)
        self.batch_thread.finished.connect(self.batch_thread.deleteLater)
        self.batch_thread.finished.connect(self.clear_batch)
        self.batch_thread.start()

    def stop_batch(self):
        if self.batch_worker:self.batch_worker.cancelled=True

    def batch_finished(self,message):
        self.statusBar().showMessage(message)
        QMessageBox.information(self,'Batch analysis',message)

    def clear_batch(self):
        self.batch_thread=None;self.batch_worker=None

    def show_queue(self):
        summary=', '.join(f'{r["status"]}: {r["n"]}' for r in self.db.queue_summary())
        failures='\n'.join(f'{r["name"]} ({r["kind"]}): {r["error"]}' for r in self.db.queue_failures())
        QMessageBox.information(self,'Analysis queue', (summary or 'Empty queue')+'\n\n'+failures[:7000])

    def closeEvent(self,event):
        if self.batch_thread is not None:
            self.stop_batch()
            QMessageBox.information(self,'Batch running','Stopping after the current task. Please wait before exiting.')
            event.ignore();return

        if self.analysis_thread is not None:
            QMessageBox.information(self,'Analysis running','Wait for the current analysis to finish before exiting.');event.ignore();return

        if self.thread is not None:
            self.stop_scan(); self.thread.quit(); self.thread.wait(30000)
            if self.thread.isRunning(): event.ignore(); return
        self.player.stop(); self.db.conn.close(); event.accept()

def main():
    app=QApplication(sys.argv); app.setApplicationName('VideoAtlas'); window=Window(); window.show(); return app.exec()
