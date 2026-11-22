# VideoAtlas v2.1 — Media pipeline integration gate

Adds `windows_media_integration.py`, an end-to-end test for the actual bundled Windows FFmpeg and FFprobe binaries. It generates a synthetic four-second MP4 using FFmpeg, probes duration and resolution, and extracts a thumbnail. All temporary files are deleted after testing. The Windows installer build now fails if any of these checks fail.

This is a build-time integration test, not a guarantee of embedded Qt playback or offline AI inference. Windows build workflow still needs to run on a Windows host; no Windows installer is included in this source archive.

## Run on Windows

`build_windows.bat` (requires Python, Windows FFmpeg/FFprobe in `src\\bin`, and Inno Setup for an installer).

After packaging, run `python windows_media_integration.py dist\\VideoAtlas` to repeat the media test.
