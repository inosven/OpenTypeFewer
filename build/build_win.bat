@echo off
setlocal

set PROJECT_DIR=%~dp0..
cd /d "%PROJECT_DIR%"

echo === OpenTypeFewer Windows Build ===
echo.

echo Cleaning previous build...
if exist dist rmdir /s /q dist 2>nul
if exist build\output rmdir /s /q build\output 2>nul

echo.
echo [1/2] Building CUDA version...
pyinstaller build\voicepad_win.spec --clean --distpath dist --workpath build\output

if %ERRORLEVEL% neq 0 (
    echo.
    echo CUDA build FAILED.
    exit /b 1
)

echo Packaging CUDA version...
if exist dist\OpenTypeFewer-Windows-CUDA.zip del dist\OpenTypeFewer-Windows-CUDA.zip
powershell -Command "Compress-Archive -Path 'dist\OpenTypeFewer' -DestinationPath 'dist\OpenTypeFewer-Windows-CUDA.zip'"

echo Cleaning intermediate files...
if exist dist\OpenTypeFewer rmdir /s /q dist\OpenTypeFewer 2>nul
if exist build\output rmdir /s /q build\output 2>nul

echo.
echo [2/2] Building CPU-only version (no CUDA)...
pyinstaller build\voicepad_win_nocuda.spec --clean --distpath dist --workpath build\output

if %ERRORLEVEL% neq 0 (
    echo.
    echo CPU build FAILED.
    exit /b 1
)

echo Packaging CPU version...
if exist dist\OpenTypeFewer-Windows.zip del dist\OpenTypeFewer-Windows.zip
powershell -Command "Compress-Archive -Path 'dist\OpenTypeFewer' -DestinationPath 'dist\OpenTypeFewer-Windows.zip'"

echo.
echo === Build complete ===
echo   CUDA:     dist\OpenTypeFewer-Windows-CUDA.zip
echo   CPU-only: dist\OpenTypeFewer-Windows.zip
