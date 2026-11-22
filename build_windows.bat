@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 exit /b 1
call .venv\Scripts\activate.bat
python -m pip --version
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1
if not exist "src\bin\ffmpeg.exe" (
 echo ERROR: Place ffmpeg.exe and ffprobe.exe in src\bin before building an offline installer.
 exit /b 1
)
if not exist "src\bin\ffprobe.exe" (
 echo ERROR: Missing src\bin\ffprobe.exe
 exit /b 1
)
set "ICON_ASSETS="
if exist "assets\icons" set "ICON_ASSETS=--add-data assets\icons;assets\icons"
python -m PyInstaller --noconfirm --clean --windowed --name VideoAtlas --paths src --collect-all PySide6 --add-binary "src\bin\ffmpeg.exe;bin" --add-binary "src\bin\ffprobe.exe;bin" %ICON_ASSETS% run.py
if errorlevel 1 exit /b 1
python verify_windows_release.py dist\VideoAtlas --manifest dist\VideoAtlas\release-manifest.json
if errorlevel 1 (
 echo ERROR: Windows distribution verification failed. Installer not built.
 exit /b 1
)
python windows_smoke_test.py dist\VideoAtlas --report dist\VideoAtlas\smoke-report.json
if errorlevel 1 exit /b 1
echo Running frozen application self-test...
set QT_QPA_PLATFORM=offscreen
dist\VideoAtlas\VideoAtlas.exe --self-test --self-test-report dist\VideoAtlas\app-selftest.json
if errorlevel 1 (
 type dist\VideoAtlas\app-selftest.json
 echo ERROR: Frozen application self-test failed.
 exit /b 1
)
echo Running real GUI startup test with a disposable catalog...
set QT_QPA_PLATFORM=offscreen
dist\VideoAtlas\VideoAtlas.exe --gui-smoke --gui-smoke-report=dist\VideoAtlas\gui-smoke-report.json
if errorlevel 1 (
 echo ERROR: Frozen GUI startup test failed.
 exit /b 1
)
python windows_media_integration.py dist\VideoAtlas --report dist\VideoAtlas\media-integration-report.json
if errorlevel 1 (
 echo ERROR: Bundled FFmpeg failed actual video processing.
 exit /b 1
)
python windows_catalog_integration.py dist\VideoAtlas --report dist\VideoAtlas\catalog-integration-report.json
if errorlevel 1 (
 echo ERROR: Bundled media tools failed actual catalog indexing.
 exit /b 1
)
echo Executable and bundled video tools verified at dist\VideoAtlas\VideoAtlas.exe
where iscc >nul 2>&1
if not errorlevel 1 (
 iscc installer\VideoAtlas.iss
 if errorlevel 1 exit /b 1
) else (
 if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\VideoAtlas.iss
  if errorlevel 1 exit /b 1
 ) else (
  echo WARNING: Inno Setup 6 not found. EXE built but no installer produced.
 )
)
if not exist "installer-output\VideoAtlas-Setup-2.4.0.exe" (
 echo ERROR: Installer missing. Inno Setup is required for release.
 exit /b 1
)
echo Done. See dist and installer-output folders.
