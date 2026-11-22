# VideoAtlas 1.6 — offline job readiness and packaging fixes

- New `videoatlas.preflight` module checks requirements for each processing job without internet access.
- Checks availability of FFmpeg, Tesseract, whisper-cli and locally registered model files.
- Whisper and OCR now look for bundled binaries as well as system-installed ones.
- Fixed Windows installer build script so Inno Setup is not invoked twice when both locations are available; errors now propagate.
- Updated Inno Setup version to 1.6.0.
- Added six isolated readiness tests.

## Known limitations

This release contains Windows build scripts and source code, **not** a compiled or verified Windows installer. Local AI models are not included. Windows UI, playback, GPU inference and real-video performance have not been tested here. Preflight reports existence, not proof that executables or models work correctly.
