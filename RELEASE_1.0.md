# VideoAtlas 1.0 — Windows build candidate (source only)

This is **not** a Windows-verified release. A Windows installer must be built on Windows and tested before distribution.

## Changes
- Offline readiness dialog reports FFmpeg, FFprobe, Tesseract and whisper.cpp availability and attempts to run `ffmpeg -version`.
- Deployment checks can detect a local CLIP model folder containing configuration and model weight files (not a complete integrity verification).
- Build script explicitly bundles local FFmpeg and FFprobe executables with PyInstaller. It fails if they are missing.
- Inno Setup version updated to 1.0.0; a portable ZIP build helper was added.
- New isolated deployment unit tests.

## Windows installation build
1. Install Python 3.11+ and Inno Setup 6 on a Windows 10/11 build machine.
2. Copy appropriately licensed Windows `ffmpeg.exe` and `ffprobe.exe` into `src\\bin\\`.
3. Run `build_windows.bat` (requires network access for initial Python package installation unless using a pre-populated offline wheel cache).
4. If Inno Setup is installed, check `installer-output\\VideoAtlas-Setup-1.0.0.exe`.
5. Run `build_portable_windows.bat` to produce `VideoAtlas-Portable-1.0.0.zip`.
6. On a clean offline Windows VM, test install/uninstall, launch, local scanning, thumbnails, playback, external-drive removal, backup and restart.

## AI model dependencies
CLIP requires compatible local Transformers/PyTorch model files and packages. Whisper requires local whisper.cpp binaries and model weights. OCR requires Tesseract plus language data. None of these are included. Do not claim the complete AI edition is ready for air-gapped use until bundled and verified.

## Known issues
- Build requires Python wheels downloaded or cached beforehand.
- Qt Multimedia video codec support must be checked on target Windows systems.
- No signed installer or Windows runtime test.
- No model weight checksums or model-license audit.
- HNSW and CLIP need realistic-scale performance tests.
