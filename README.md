# Audio Transcription and Splitting Tool

音声ファイルを文字起こしし、各セリフごとに個別の音声ファイルに分割するツールです。

## 機能

- OpenAI Whisperを使用したローカル音声認識
- タイムスタンプベースの音声分割（BGM対応）
- 日本語句読点（。！？）で自動的に文を分割
- セリフ内容をファイル名に使用（連番付き）
- Cueシート出力（CSV, TSV, SRT, VTT形式）
- 様々な音声形式に対応（mp3, wav, m4a, aac等）

## 必要要件

- Python 3.10-3.12
- ffmpeg（システムにインストール必要）

### ffmpegのインストール

```bash
# Windows
winget install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

## セットアップ

```bash
# 依存関係のインストール
uv sync

# GPU確認（オプション）
uv run python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

初回実行時、Whisperモデルが自動ダウンロードされます。

## 使い方

### 基本

```bash
# 音声ファイルを文字起こし＆分割
uv run python main.py input.mp3
# → input_generated/ に出力
```

### オプション

```bash
# 高精度モデル使用
uv run python main.py input.mp3 --model small

# 日本語を明示指定
uv run python main.py input.mp3 --language ja

# GPU使用
uv run python main.py input.mp3 --device cuda

# 全Cueシート形式を出力
uv run python main.py input.mp3 --cue-format all
```

### 2段階処理（文字起こし結果を編集したい場合）

```bash
# 1. 文字起こしのみ
uv run python main.py input.mp3 --transcribe-only
# → input_generated/transcript.json が生成

# 2. JSONを編集（テキスト修正、不要セグメント削除など）

# 3. 編集したJSONから音声分割
uv run python main.py input_generated/transcript.json
```

## オプション一覧

| オプション | 説明 | デフォルト |
|----------|------|------------|
| `--model` | Whisperモデル（tiny/base/small/medium/large） | base |
| `--language` | 言語コード（ja, en等） | 自動検出 |
| `--output-dir` | 出力ディレクトリ | `{入力名}_generated/` |
| `--max-filename-length` | ファイル名最大長 | 制限なし |
| `--margin-before` | セグメント開始前マージン（秒） | 0.1 |
| `--margin-after` | セグメント終了後マージン（秒） | 0.2 |
| `--cue-format` | Cueシート形式（csv/tsv/srt/vtt/all） | csv |
| `--transcribe-only` | 文字起こしのみ（音声分割なし） | - |
| `--from-json` | JSONから分割（通常は拡張子で自動判定） | - |
| `--device` | デバイス（cuda/cpu） | 自動検出 |

## 出力ファイル

```
input_generated/
├── 001_こんにちは世界.mp3
├── 002_今日はいい天気ですね.mp3
├── transcript.json      # メタデータ（編集可能）
├── cuesheet.csv         # Cueシート
└── cuesheet.srt         # 字幕ファイル（--cue-format allの場合）
```

## Whisperモデル選択

| モデル | 精度 | 速度 | 推奨用途 |
|--------|------|------|----------|
| tiny   | 低   | 最速 | クイックテスト |
| base   | 中   | 速い | 通常使用 |
| small  | 高   | 普通 | 実用（推奨） |
| medium | 最高 | 遅い | 高品質 |
| large  | 最高 | 最遅 | 最高品質 |

## トラブルシューティング

### ffmpegが見つからない
→ ffmpegをシステムにインストールしてください

### CUDA out of memory
→ 小さいモデルを使用: `--model tiny` または `--model base`

### 音声が検出されない
→ `--language ja` で言語を明示指定、または `--model small` で精度向上

## 開発者向け情報

開発者向けの詳細は [CLAUDE.md](CLAUDE.md) を参照してください。

## ライセンス

MIT License
