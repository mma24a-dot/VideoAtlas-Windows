# VideoAtlas 2.0 — frozen application smoke test

Adds `VideoAtlas.exe --self-test` to check a disposable SQLite catalog, bundled FFmpeg and FFprobe, and Qt widget initialization. The Windows build fails before installer creation if the frozen app fails its self-test.

This does not validate actual video playback, full AI inference, or installation on a clean Windows computer. AI models are not bundled.

## Build
On Windows, supply trusted `src\bin\ffmpeg.exe` and `ffprobe.exe`, install Python 3.11 and Inno Setup 6, then run `build_windows.bat`.
