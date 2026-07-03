@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP=ai_translate_ui_refined_key_maximized_v23.py"
set "EXE_NAME=AITranslate"
set "ICON=ai_translate_icon.ico"
set "ICON_ABS=%CD%\%ICON%"

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

echo Cleaning old build files...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "%EXE_NAME%.spec" del /f /q "%EXE_NAME%.spec"

py -3.11 -m pip install --upgrade openai pyinstaller
py -3.11 -m PyInstaller ^
  --clean ^
  --noconfirm ^
  --onefile ^
  --noconsole ^
  --name "%EXE_NAME%" ^
  --icon "%ICON_ABS%" ^
  --add-data "%ICON_ABS%;." ^
  "%APP%"

if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

echo Build OK: dist\%EXE_NAME%.exe
echo If Explorer still shows the old icon, rename the exe or restart Explorer.
pause
