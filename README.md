# VideoAtlas v0.7 — Source release

**Not a compiled Windows installer.** Windows GUI and installer have not been verified. The optional AI models and tools are not bundled.

## v0.5 additions
- Scrollable scene-thumbnail gallery, opening playback at the selected timestamp. Scene images appear after batch scene analysis; manually detected scenes may have no cached thumbnail.
- Minimum-duration filter (minutes) and offline/disconnected-file filter. Offline-only filtering checks file existence and may be slow on unavailable NAS paths.
- Direct navigation to video ID from transcription and semantic results, avoiding ambiguity from duplicate filenames.
- Installer metadata updated to 0.5.0. The build requires FFmpeg and FFprobe placed in src/bin, Python, dependencies and Inno Setup. It does not bundle optional AI packages or model weights.

## Validation
Python syntax and SQLite unit tests on Linux only. Windows packaging and actual AI inference not tested.

# VideoAtlas 0.2 — Offline Windows video catalog

**Status:** Source implementation. Syntax and SQLite tests passed on Linux. Windows executable and installer have NOT been compiled or tested here. No AI model weights or third-party executable binaries are included.

## Core capabilities
- Qt desktop application with light/dark themes, internal/external/NAS folder import, incremental background indexing, paginated browsing, searchable filenames/notes/tags, persistent offline drive records, metadata editing, Qt playback.
- FFmpeg/FFprobe thumbnails, codec and duration metadata.
- Scene-change detection and jump-to-scene timeline (FFmpeg scene score).
- JPEG contact sheet export with timestamp labels.
- SHA-256 file hashing and verified duplicate reporting **for files that have been hashed**. Hashing is currently per selected file, not bulk.
- SQLite collections (add selected video; view collection names).
- Offline speech transcription using an **already installed** whisper.cpp `whisper-cli` and **user-provided** GGML model; stored timestamped segments.
- OCR of the currently displayed timestamp using **already installed** Tesseract OCR.
- Search through locally indexed transcripts and OCR text.

## Limitations / not yet implemented
- Semantic image/video embeddings, natural-language visual retrieval, object detection, face clustering, auto-generated video descriptions and true AI scene tagging.
- Batch analysis job scheduling, cancellation and progress reporting for individual AI jobs, robust library path remapping, collection browsing integrated into the main list, automated library-wide verified hashing, scene thumbnails, advanced filter UI, portable database export and synchronisation.
- Whisper model files and Tesseract language packs are not bundled. AI analysis depends on local tools, installed by the user.
- No verified million-file scalability or Windows runtime smoke test. Qt multimedia codec support varies by installed backend.
- Transcription and OCR are optional offline integrations, **not** plug-and-play in the installer.

## Run from source on Windows
1. Install Python 3.11+, FFmpeg and FFprobe (PATH or `src/bin/`).
2. `py -m venv .venv`
3. `.venv\\Scripts\\python.exe -m pip install -r requirements.txt`
4. `.venv\\Scripts\\python.exe run.py`
5. Optional: Install `whisper-cli` and a GGML model locally for transcription; install Tesseract and add it to PATH for OCR.

## Build installer (Windows)
1. Install Python 3.11+ and Inno Setup 6.
2. Place `ffmpeg.exe` and `ffprobe.exe` into `src/bin/`. Verify licensing of your selected FFmpeg distribution.
3. Run `build_windows.bat`.
4. Find executable under `dist/VideoAtlas/`; if Inno Setup was found, installer under `installer-output/VideoAtlas-Setup-0.2.0.exe`.
5. This build script packages FFmpeg but **does not** bundle Whisper, models or Tesseract. For offline AI, install those locally before disconnecting from the internet.

## Tests
From project root: `set PYTHONPATH=src` then `python -m unittest discover -s tests -v`.

## Data and privacy
The SQLite database and thumbnail cache are under `%LOCALAPPDATA%/VideoAtlas`. The scanner does not modify originals. Catalog entries remain after drive disconnection. Hashing reads entire videos; processing huge files can take time. OCR/transcripts remain local. Back up the entire data folder to preserve tags and analyses.

## Version 0.3 — persistent batch analysis

The **Queue batch analysis** toolbar action can queue all catalogued videos or the selected
video for scene detection (with cached scene thumbnails), SHA-256 hashing, OCR sampling,
or offline whisper.cpp transcription. **Run queued jobs**, **Stop batch**, and **Queue status**
manage the persistent SQLite queue. Pending work survives application restarts. Failures
are retained for inspection and can be requeued. A stop request takes effect between jobs,
or between scene thumbnails/OCR samples; FFmpeg scene detection and Whisper transcription
may take time to finish their current process. The queue runs one analysis job at a time
and does not automatically download models or access network services.

The OCR batch samples at 60-second intervals; scene thumbnails are cached in the local
application data directory. Scene thumbnails are currently stored for future timeline UI
integration; the scene picker still shows timestamp labels.

**Not yet included:** CLIP visual embeddings, semantic image search, face recognition,
GPU configuration, a tested Windows executable, a fully self-contained installer, and
fully automatic incremental analysis scheduling. Large collections should be tested on
representative hardware before production use. The batch queue is intentionally serial
and is not a high-throughput distributed scheduler.

## v0.4: Offline CLIP semantic search (experimental)

The **Visual semantic search** toolbar action searches scene-frame embeddings using a text description. **Queue batch analysis → semantic** generates embeddings using a CLIP model already stored locally. This optional feature requires installing `torch` and `transformers` (plus compatible tokenization/image dependencies) and providing a local Hugging Face-format CLIP model directory with `config.json`, processor/tokenizer files, and weights. No model is downloaded by VideoAtlas; model loading uses `local_files_only=True`. You must provision all Python packages and model files before disconnecting from the internet. GPU is used when CUDA is available; CPU fallback is supported but slower.

The standard Windows build does **not** bundle PyTorch, Transformers, CLIP model weights, or OCR/transcription binaries. To include these in a truly offline installer, extend the build environment and installer payload and test on an offline Windows machine. For very large collections, the current JSON-vector search is linear-time and will need an approximate-nearest-neighbor index. Visual-search result navigation currently searches by filename and may require manual opening if the result is not on the current page.

Suggested setup on the development PC: `pip install torch transformers` and download a compatible CLIP model folder ahead of time. For offline operation, point the app to that local folder. The application itself does not contact any API for inference.


## v0.6: Catalog safety and duplicate inspection

- **Backup catalog** uses SQLite's online backup API to create a consistent `.sqlite` snapshot, including committed data from WAL mode. Existing backup files are never overwritten. For complete migration, also copy `%LOCALAPPDATA%/VideoAtlas/thumbnails/` and `folders.txt`.
- **Database health** checks SQLite quick integrity and foreign-key consistency.
- **Duplicate details** provides a read-only group selector with full file paths for matching SHA-256 hashes. It never deletes files. Hash freshness is checked against the *catalogued* size and modification time; if files have changed on disk since the last scan, rescan and rehash before acting.
- No Windows installer has been compiled or tested in this Linux development environment. Optional AI models, Whisper, and OCR tools are still not bundled.

## Version 0.7 — indexed search option and advanced SQL filters
- Optional in-memory HNSW approximate-nearest-neighbor index for CLIP scene search, using locally installed `hnswlib` and `numpy`. If either is absent, the original exact SQLite vector scan remains available. Install with `pip install numpy hnswlib` on a supported Python/Windows build.
- HNSW is built from SQLite at search time, so this is a first indexing integration **not yet a persistent, high-scale index**. For very large libraries, index rebuilding can be slow; persisted incremental indexing is a future task.
- New `Catalog.advanced_filter` API filters dimensions, file size, codec, duration and text with SQL parameters. GUI controls for these additional filters are not yet connected.
- AI models, FFmpeg binaries and optional dependencies are **not bundled**. A fully self-contained Windows installer is not yet produced or tested.


## Version 0.8 — persistent ANN cache and GUI filters
- HNSW indexes are persisted beside the catalog in `vector-index/` and loaded on later searches. SQLite triggers increment a revision after semantic-frame edits, invalidating saved indexes. Each model and embedding dimension gets a separate index. The index is a rebuildable cache; delete it safely to recover from corruption.
- Advanced search UI adds minimum width, height, file size, and codec fields. The default search retains tag matching; advanced-filter search currently matches names, paths, and notes only. Offline-only combined with advanced filters filters the current SQL page rather than globally, so pagination may be sparse.
- Optional `numpy` and `hnswlib` are still required; without them semantic search uses the existing exact fallback.
- No Windows runtime or standalone installer has been verified. Offline AI weights are not bundled.

## Version 0.9 — unified library filtering and Windows build hygiene

- Advanced search now applies **all filters in one query**, including tags, codec, dimensions, size and duration.
- Offline-only results are filtered **before pagination**, avoiding sparse or misleading pages.
- LIKE wildcard characters in user input are treated literally, and SQL values are parameterized.
- Installer version updated to 0.9.0; Windows build now invokes PyInstaller through the active virtual environment.
- New regression tests exercise tag searches, offline pagination and combined filters.

### Building and distributing offline

Run `build_windows.bat` on a **Windows** computer with Python, pip and Inno Setup already installed. It installs Python packages during the build, so a build machine without network access must provide a local wheelhouse and adjust pip installation accordingly. Place licensed Windows `ffmpeg.exe` and `ffprobe.exe` binaries in `src/bin/` before building. The resulting packaged application does not require an internet connection for cataloguing, but optional AI components (PyTorch/CLIP model, Whisper, Tesseract) remain separate and must be provisioned locally. This is not yet a verified complete offline AI installer.

## Version 1.4 update
Use **Local AI models** on the toolbar to register locally installed CLIP, Whisper.cpp and Tesseract data. The registry is stored in the user's VideoAtlas application-data folder. These settings are currently diagnostic and do not automatically replace model-selection dialogs in processing tools. See RELEASE_1.4.md.


## v1.9 Windows build validation

The GitHub Actions workflow `.github/workflows/windows-build.yml` builds on Windows and uploads the compiled distribution and installer as CI artifacts. `windows_smoke_test.py` executes packaged FFmpeg/FFprobe version checks before allowing the installer build. This source archive itself contains no Windows executable or bundled AI models.
