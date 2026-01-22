@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo Audio Transcription and Splitting Tool - Launcher
echo ============================================================
echo.

echo 入力ファイルのパスを入力してください:
set /p INPUT_FILE=">> "

REM パスから前後のダブルクォートを削除
if defined INPUT_FILE (
    if "!INPUT_FILE:~0,1!"=="" (
        set INPUT_FILE=!INPUT_FILE:~1!
    )
    if "!INPUT_FILE:~-1!"=="" (
        set INPUT_FILE=!INPUT_FILE:~0,-1!
    )
)

if not exist "!INPUT_FILE!" (
    echo.
    echo [ERROR] ファイルが見つかりません: !INPUT_FILE!
    echo.
    pause
    exit /b 1
)

echo.
echo モデルサイズを選択してください:
echo   1. tiny   (最速・最低精度)
echo   2. base   (標準)
echo   3. small  (やや高精度)
echo   4. medium (高精度・遅い)
echo   5. large  (最高精度・最も遅い)
echo.
set /p MODEL_CHOICE="選択 (1-5) [デフォルト: 2]: "

if "%MODEL_CHOICE%"=="" set MODEL_CHOICE=2

if "%MODEL_CHOICE%"=="1" set MODEL=tiny
if "%MODEL_CHOICE%"=="2" set MODEL=base
if "%MODEL_CHOICE%"=="3" set MODEL=small
if "%MODEL_CHOICE%"=="4" set MODEL=medium
if "%MODEL_CHOICE%"=="5" set MODEL=large

if not defined MODEL (
    echo.
    echo [ERROR] 無効な選択です
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo 実行設定:
echo   入力ファイル: !INPUT_FILE!
echo   モデルサイズ: !MODEL!
echo ============================================================
echo.
echo 実行を開始します...
echo.

uv run python main.py "!INPUT_FILE!" --model !MODEL!

echo.
echo ============================================================
echo 処理が完了しました
echo ============================================================
pause
