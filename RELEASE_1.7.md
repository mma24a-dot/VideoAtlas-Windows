# VideoAtlas v1.7 — Windows release verification

This release adds a **fail-closed Windows distribution verifier**. The build script now refuses to invoke Inno Setup unless the PyInstaller output contains a nonempty `VideoAtlas.exe`, `ffmpeg.exe`, `ffprobe.exe`, the Qt Core DLL, and the Qt Windows platform plugin. It records SHA-256 hashes and sizes for the executable and video tools in `release-manifest.json`.

## Build on Windows

1. Install Python 3.11+ and Inno Setup 6.
2. Supply trusted, license-compliant Windows FFmpeg binaries at `src\\bin\\ffmpeg.exe` and `src\\bin\\ffprobe.exe`.
3. Run `build_windows.bat` on Windows 10/11 with an internet connection for Python dependencies, or with dependencies preinstalled/cached.
4. Inspect `dist\\VideoAtlas\\release-manifest.json` and run a real installation smoke test on a clean Windows machine.

**Not a verified installer release.** The verifier checks presence and hashes, not executable authenticity, correct codec behavior, working playback, Qt startup, or real AI inference. AI model weights and optional runtimes are not included. Building from source may require downloads; running the resulting application is intended to be offline.
