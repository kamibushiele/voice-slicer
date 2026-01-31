# CLAUDE.md

Claude Code向けの開発ガイド。serenaMCPを活用して効率的に開発を補助する。

## 開発対象プロジェクト概要

音声ファイルをWhisperで文字起こしし、各セリフを個別の音声ファイルに分割するツール。
文字起こしの修正・再分割を行えるようにする。

## 開発・実行環境

CLIとGUIのバックエンドはpython、フロントエンドはjavascriptで実現。

pythonはuvでパッケージ管理を行う。実行は`uv run xxx.py`で行う。

### 動作要件

- Python 3.10-3.12 (3.13+は非対応)
- ffmpeg（システムにインストール必要）
- GPU: オプション（CUDA対応で8-30倍高速化）

### 依存ライブラリ

| パッケージ       | 用途            |
| ---------------- | --------------- |
| `openai-whisper` | 音声認識        |
| `torch`          | GPU対応         |
| `pydub`          | 音声処理        |
| `flask`          | GUIバックエンド |
| `numpy`          | 波形データ処理  |

## システムのワークフロー

1. **文字起こし (CLI)**: 音声ファイル → セグメント情報（`transcript_unexported.json`）
2. **編集 (GUI)**: セグメント情報をブラウザで確認・修正
3. **書き出し (CLI or GUI)**: セグメント情報 → 分割音声ファイル + `transcript.json`

詳細は [docs/export_behavior.md](docs/export_behavior.md) を参照。

## 開発ガイドライン

CLI層とGUI層は共通する処理も多い。このため基本的な動作はCore層(src/)に作成し、各層から呼び出す。

### Core層の原則

- print文を含めない（UI非依存）
- 例外は呼び出し元でハンドリング
- 戻り値でデータを返す

### CLI層の原則

- Core層を呼び出してUI表示を担当
- 進捗表示、エラー表示はここで行う

### GUI層の原則

- Core層を呼び出してAPIレスポンスを返す
- 状態管理はフロントエンド（JavaScript）で行う
