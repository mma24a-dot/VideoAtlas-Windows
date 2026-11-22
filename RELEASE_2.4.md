# VideoAtlas 2.4 — Installer smoke-test gate

- Windows GitHub Actions workflow installs runtime dependencies before Python tests.
- Build fails if Inno Setup does not produce `VideoAtlas-Setup-2.4.0.exe`.
- A new PowerShell test silently installs the actual installer into a disposable directory and runs the installed executable self-test.
- Installer smoke report is uploaded alongside Windows release artifacts.

**Not yet verified:** Windows GitHub Actions execution, clean-machine UI/playback, GPU/AI inference, and complete offline model bundling. Do not describe this source release as a tested Windows installer.
