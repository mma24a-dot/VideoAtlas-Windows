# VideoAtlas 1.8 — Packaging consistency release

- Fixed Windows distribution verification for PyInstaller 6 `onedir` layout, where bundled FFmpeg/FFprobe reside in `_internal/bin` rather than the executable directory.
- Unified scanner and analysis FFmpeg discovery with the application deployment helper, which understands frozen executable layouts.
- Updated Inno Setup and portable ZIP version labels to 1.8.0.
- Added regression test for the actual PyInstaller 6 directory structure.

## Limitations
Source tests can run on Linux; the executable, Windows installer, Qt playback and offline AI inference still require validation on Windows. FFmpeg and AI model binaries are not distributed in this source archive.
