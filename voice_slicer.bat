@echo off
setlocal

REM VoiceSlicer - Launcher
REM 同梱のuv → 環境変数のuv の順で探索する

set "SCRIPT_DIR=%~dp0"
set "UV=%SCRIPT_DIR%tools\uv\uv.exe"

if exist "%UV%" goto :run

where uv >nul 2>&1
if %errorlevel% equ 0 (
    set "UV=uv"
    goto :run
)

echo [ERROR] uv が見つかりません。
echo リリースパッケージを使用するか、uv を手動でインストールしてください。
echo https://docs.astral.sh/uv/getting-started/installation/
pause
exit /b 1

:run
"%UV%" run python "%SCRIPT_DIR%voice_slicer.py"

echo.
pause
