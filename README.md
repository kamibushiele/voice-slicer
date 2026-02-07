# VoiceSlicer

音声ファイルをWhisperで文字起こしし、各セリフごとに個別の音声ファイルに分割するツールです。

## 機能

- OpenAI Whisperを使用したローカル音声認識
- タイムスタンプベースの音声分割（BGM対応）
- 日本語句読点（。！？）で自動的に文を分割
- 波形を見ながら手動調整できるGUI
- 差分ベースの書き出し（変更箇所のみ再処理）

## 動作要件

- Python 3.10-3.12（3.13+は非対応）
- [uv](https://docs.astral.sh/uv/)（パッケージ管理）
- [ffmpeg](https://ffmpeg.org/)（音声処理）
- GPU: オプション（CUDA対応で高速化）

## セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/kamibushiele/sound-sozai.git
cd sound-sozai

# 依存パッケージをインストール
uv sync
```

## 使い方

### 1. 文字起こし

音声ファイルからセグメント情報を生成します。

```bash
uv run transcribe.py <音声ファイル> [--model small] [--language ja]
```

出力: `<入力名>_generated/` ディレクトリに `transcript.json` と `edit_segments.json` を生成。

### 2. 編集（GUI）

波形を見ながらセグメントの開始/終了位置やテキストを調整できます。

```bash
uv run edit.py <出力ディレクトリ>
```

ブラウザで http://localhost:5000 が自動で開きます。

### 3. 書き出し（CLI）

セグメント情報をもとに個別の音声ファイルに分割します。

```bash
uv run split.py <出力ディレクトリ>
```

GUIの書き出しボタンからも実行できます。

## ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [docs/transcribe.md](docs/transcribe.md) | 文字起こしCLIの詳細 |
| [docs/split.md](docs/split.md) | 分割CLIの詳細 |
| [docs/edit.md](docs/edit.md) | GUI操作ガイド |
| [docs/export_behavior.md](docs/export_behavior.md) | 書き出し処理の仕様 |
| [docs/data_format.md](docs/data_format.md) | JSONデータフォーマット仕様 |
| [docs/index_specification.md](docs/index_specification.md) | セグメントindex仕様 |

## ライセンス

MIT License
