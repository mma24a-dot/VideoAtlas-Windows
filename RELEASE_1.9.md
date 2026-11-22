# VideoAtlas v1.9 — Windows build smoke tests

Adds `windows_smoke_test.py` to execute the packaged FFmpeg and FFprobe binaries and fail the installer build if either cannot run. Adds Windows GitHub Actions build automation and publishes artifacts only after checks pass. This does not validate GUI launch, playback, GPU inference, or clean-machine installation.

## Windows build
Run `build_windows.bat` on Windows with Python, FFmpeg binaries in `src\bin`, and Inno Setup 6 installed. A Windows CI workflow can generate the installer as an artifact when run on GitHub. Building may require internet to install build dependencies; installed application is designed for offline use.
