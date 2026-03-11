@echo off
setlocal

set PROJECT_DIR=%~dp0..
cd /d "%PROJECT_DIR%"

echo === VoicePad Windows Build ===
echo.

echo Cleaning previous build...
if exist dist rmdir /s /q dist 2>nul
if exist build\output rmdir /s /q build\output 2>nul

echo.
echo Building with PyInstaller...
pyinstaller build\voicepad_win.spec --clean --distpath dist --workpath build\output

if %ERRORLEVEL% neq 0 (
    echo.
    echo Build FAILED.
    exit /b 1
)

echo.
echo Build complete: dist\VoicePad\VoicePad.exe
