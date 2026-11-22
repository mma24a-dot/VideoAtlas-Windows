# VideoAtlas v2.2 — GUI startup verification

Added a disposable-library GUI smoke test to the frozen Windows build pipeline.

## Changes
- `VideoAtlas.exe --gui-smoke` launches the actual Qt main window using an isolated temporary SQLite catalog.
- Tests window construction, light/dark theme switching, library refresh, and database initialization.
- The Windows build aborts before Inno Setup if the frozen GUI smoke test fails.
- Produces `gui-smoke-report.json` in the distribution.
- Updated Inno Setup version and CI artifact name to 2.2.

## Validation
49 Python tests passed in Linux; syntax and ZIP checks passed.
The GUI smoke test is intended for Windows CI and has NOT been run against a Windows binary here.
No installer or bundled AI models are included in the source archive.
