# VideoAtlas v1.4 — Offline model registry

- Added a GUI to register local CLIP, Whisper.cpp and Tesseract model locations.
- Model paths are validated and saved to a local JSON registry with atomic updates.
- Readiness diagnostics show registered models that have gone missing.
- Added tests for registration, validation, and removal.

## Limitations
The registry verifies basic file layout, not that model weights are genuine, compatible, or usable. AI processing screens do not yet automatically use the saved registry. No model weights are included. Windows executable and installer have not been compiled or tested here. The package contains Windows build scripts only.
