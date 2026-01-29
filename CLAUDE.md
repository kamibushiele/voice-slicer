# CLAUDE.md

Claude Code向けの開発ガイド。serenaMCPを活用して効率的に開発を補助してください。

## 概要

音声ファイルをWhisperで文字起こしし、各セリフを個別の音声ファイルに分割するツール。
BGM付き音声にも対応。

## ワークフロー

1. **文字起こし (CLI)**: 音声ファイル → transcript.json
2. **編集 (GUI)**: transcript.jsonをブラウザで確認・修正
3. **書き出し (CLI or GUI)**: transcript.json → 分割音声ファイル

```bash
# Step 1: 文字起こし
uv run python transcribe.py input.mp3

# Step 2: GUIで編集・書き出し
uv run python edit.py input_generated/

# または: CLIで直接書き出し（編集不要の場合）
uv run python split.py input_generated/
```

### 出力

文字起こし直後:
```
input_generated/
└── transcript_unexported.json  # 未書き出しセグメント情報
```

書き出し後:
```
input_generated/
├── transcript.json           # セグメント情報（確定）
├── 001_こんにちは世界.mp3     # 分割音声
├── 002_今日はいい天気ですね.mp3
└── ...
```

---

## アーキテクチャ

### 層構成

| 層 | 役割 | UI依存 |
|----|------|--------|
| **Core層** | データ処理・ビジネスロジック | なし |
| **CLI層** | コマンドライン操作 | あり（print） |
| **GUI層** | Webブラウザ操作 | あり（Flask） |

### Core層（src/）

UI非依存の純粋な処理ロジック。CLI/GUIどちらからも利用可能。

| モジュール | 責務 |
|-----------|------|
| `transcribe.py` | Whisper文字起こし、句読点分割 |
| `splitter.py` | 音声分割、ファイル操作 |
| `json_loader.py` | transcript.json読み書き |
| `utils.py` | ファイル名生成、テキスト処理 |

### CLI層

| ファイル | 責務 |
|----------|------|
| `transcribe.py` | 文字起こしCLI |
| `split.py` | 書き出しCLI |
| `edit.py` | GUI起動 |

### GUI層（gui/）

| ファイル | 責務 |
|----------|------|
| `app.py` | Flaskルーティング、API |
| `audio_handler.py` | 波形データ生成 |
| `templates/index.html` | UI |
| `static/app.js` | Wavesurfer.js統合 |

---

## データ形式

### transcript.json

```json
{
  "source_file": "input.mp3",
  "segments": [
    {
      "index": 1,
      "filename": "001_こんにちは.mp3",
      "start": 0.5,
      "end": 2.3,
      "text": "こんにちは"
    }
  ]
}
```

### セグメントのindex

詳細は [docs/index_specification.md](docs/index_specification.md) を参照。

- `index` + `index_sub` の組み合わせでソート順を決定
- 書き出し時にindexが確定し、ファイル名が生成される
- ファイル名: `{index}_{text}.{ext}` または `{index}-{index_sub}_{text}.{ext}`

### transcript_unexported.json

- GUI編集中の一時保存ファイル
- 書き出し完了時に自動削除
- 起動時に存在すれば優先読み込み

---

## CLI リファレンス

### transcribe.py（文字起こし）

```bash
python transcribe.py <音声ファイル> [オプション]
```

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--model` | Whisperモデル (tiny/base/small/medium/large) | base |
| `--language` | 言語コード (ja, en等) | 自動検出 |
| `--output-dir` | 出力ディレクトリ | `{入力名}_generated/` |
| `--device` | デバイス (cuda/cpu) | 自動検出 |

### split.py（書き出し）

```bash
python split.py <出力ディレクトリ> [オプション]
```

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--margin-before` | 開始前マージン（秒） | 0.1 |
| `--margin-after` | 終了後マージン（秒） | 0.2 |
| `--max-filename-length` | ファイル名最大長 | 制限なし |

---

## GUI リファレンス

### 起動

```bash
python edit.py <出力ディレクトリ> [--port PORT] [--no-browser]
```

### キーボードショートカット

| キー | 機能 |
|------|------|
| `Space` | 再生/停止 |
| `L` | ループ再生ON/OFF |
| `←` / `→` | 前/次のセグメント |
| `↑` / `↓` | 0.1秒移動 |
| `,` / `.` | 5秒移動 |
| `<` / `>` | 再生速度変更 |
| `+` / `-` | ズームイン/アウト |
| `Delete` | セグメント削除 |
| `Ctrl+S` | 保存 |

### 書き出し処理（差分ベース）

| 変更内容 | 処理 |
|---------|------|
| セグメント削除 | 音声ファイル削除 |
| セグメント追加 | 音声ファイル新規作成 |
| start/end変更 | 旧ファイル削除 → 再作成 |
| テキストのみ変更 | ファイルリネーム |
| 変更なし | スキップ |

---

## 技術情報

### 動作要件

- Python 3.10-3.12 (3.13+は非対応)
- ffmpeg（システムにインストール必要）
- GPU: オプション（CUDA対応で8-30倍高速化）

### 依存ライブラリ

| パッケージ | 用途 |
|-----------|------|
| `openai-whisper` | 音声認識 |
| `torch` | GPU対応 |
| `pydub` | 音声処理 |
| `flask` | GUIバックエンド |
| `numpy` | 波形データ処理 |

### GPU設定 (CUDA 12.x)

```toml
[[tool.uv.index]]
name = "pytorch-cu124"
url = "https://download.pytorch.org/whl/cu124"
explicit = true

[tool.uv.sources]
torch = { index = "pytorch-cu124" }
```

---

## 設計方針

### BGM対応
VADではなくWhisperの単語レベルタイムスタンプを使用。シンプルな実装でBGM付き音声に対応。

### 日本語文分割
句読点（。！？）で自動分割。単語レベルタイムスタンプから各文の境界を計算。

### 出力フォーマット
入力と同じ音声フォーマットを維持。`.m4a` → `ipod`, `.aac` → `adts` の特別処理あり。

---

## 開発ガイドライン

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

---

## 今後の拡張予定

- [ ] バッチ処理（複数ファイル）
- [ ] 話者分離
- [ ] 出力フォーマット変換
- [ ] セグメント自動マージ
