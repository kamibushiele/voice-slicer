# Audio Transcription and Splitting Tool

音声ファイルを文字起こしし、各セリフごとに個別の音声ファイルに分割するツールです。

## 機能

- OpenAI Whisperを使用したローカル音声認識
- タイムスタンプベースの音声分割（BGM対応）
- 日本語句読点（。！？）で自動的に文を分割
- 波形を見ながら手動調整できるGUI

## 必要要件

- Python 3.10-3.12
- ffmpeg

```bash
# ffmpegのインストール（Windows）
winget install ffmpeg
```

## セットアップ

```bash
uv sync
```

## 使い方

### AI文字起こし

```bash
# 音声ファイルを文字起こし＆分割
uv run python main.py input.mp3
```

詳細は **[AI文字起こしドキュメント](docs/Transcription.md)** を参照してください。

### 手動調整GUI

```bash
# 波形を見ながらセグメントを編集
uv run python run_gui.py input_generated/
```

詳細は **[手動調整GUIドキュメント](docs/GUI.md)** を参照してください。

## 出力ファイル

```
input_generated/
├── 001_こんにちは世界.mp3
├── 002_今日はいい天気ですね.mp3
└── transcript.json
```

## 開発者向け情報

[CLAUDE.md](CLAUDE.md) を参照してください。

## ライセンス

MIT License
