@echo off
setlocal
cd /d "%~dp0"
call build_windows.bat
if errorlevel 1 exit /b 1
powershell -NoProfile -Command "Compress-Archive -Path 'dist\VideoAtlas\*' -DestinationPath 'VideoAtlas-Portable-1.9.0.zip' -Force"
if errorlevel 1 exit /b 1
echo Portable archive created: VideoAtlas-Portable-1.9.0.zip
