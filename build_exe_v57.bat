@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP=ai_translate_ui_refined_key_maximized_v57_hawaii_default.py"
set "EXE_NAME=AITranslate"
set "ICON=ai_translate_icon.ico"
set "ICON_ABS=%CD%\%ICON%"
set "MANIFEST=AITranslate.manifest"
set "MANIFEST_ABS=%CD%\%MANIFEST%"
set "RELEASE_DIR=release"
set "PACKAGE_NAME=AITranslate_Portable.zip"
set "PACKAGE_PATH=%RELEASE_DIR%\%PACKAGE_NAME%"
set "HASH_PATH=%RELEASE_DIR%\AITranslate_Portable.sha256.txt"

if not exist "%APP%" (
    echo ERROR: %APP% not found.
    pause
    exit /b 1
)

if not exist "%ICON%" (
    echo ERROR: %ICON% not found.
    pause
    exit /b 1
)

if not exist "%MANIFEST%" (
    echo ERROR: %MANIFEST% not found.
    pause
    exit /b 1
)

echo Cleaning old build files...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "%EXE_NAME%.spec" del /f /q "%EXE_NAME%.spec"
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"
if exist "%PACKAGE_PATH%" del /f /q "%PACKAGE_PATH%"
if exist "%HASH_PATH%" del /f /q "%HASH_PATH%"

py -3.11 -m pip install --upgrade openai pyinstaller "httpx[socks]" socksio pypdf

rem Use onedir instead of onefile.
rem This avoids runtime extraction errors such as VCRUNTIME140.dll fseek invalid argument.
py -3.11 -m PyInstaller ^
  --clean ^
  --noconfirm ^
  --onedir ^
  --noconsole ^
  --noupx ^
  --name "%EXE_NAME%" ^
  --icon "%ICON_ABS%" ^
  --add-data "%ICON_ABS%;." ^
  --manifest "%MANIFEST_ABS%" ^
  --hidden-import socksio ^
  --collect-all pypdf ^
  "%APP%"

if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

if not exist "dist\%EXE_NAME%\%EXE_NAME%.exe" (
    echo ERROR: dist\%EXE_NAME%\%EXE_NAME%.exe not found.
    pause
    exit /b 1
)

echo Creating portable package...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Compress-Archive -Path 'dist\%EXE_NAME%' -DestinationPath '%PACKAGE_PATH%' -Force; (Get-FileHash '%PACKAGE_PATH%' -Algorithm SHA256).Hash | Set-Content -Encoding ASCII '%HASH_PATH%'"

if errorlevel 1 (
    echo Package failed.
    pause
    exit /b 1
)

echo Build OK: dist\%EXE_NAME%\%EXE_NAME%.exe
echo Package OK: %PACKAGE_PATH%
echo SHA256 OK: %HASH_PATH%
echo Copy %PACKAGE_PATH% to another computer, unzip it, then run AITranslate\AITranslate.exe.
echo First run on another computer still needs API Key setup.
pause
