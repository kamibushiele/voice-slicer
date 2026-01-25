# CLAUDE.md

Claude Code向けの開発ガイドです。
serenaMCPを活用して効率的に開発を補助してください。
ソフトウェアの利用方法は[README.md](README.md)を参照してください。

## Project Overview

音声ファイルをWhisperで文字起こしし、各セリフを個別の音声ファイルに分割するツール。BGM付き音声にも対応。

## System Requirements

- **Python**: 3.10-3.12 only (NOT 3.13+)
- **ffmpeg**: システムにインストール必要
- **GPU**: オプション（NVIDIA CUDA対応で8-30倍高速化）

## Architecture

### Three Operating Modes

入力ファイルの拡張子とフラグで自動判定：

1. **Normal Mode** (音声ファイル): Transcribe → Split → Save
2. **Transcribe-Only Mode** (`--transcribe-only`): Transcribe → JSON保存のみ
3. **JSON Mode** (`.json`ファイル): JSON読込 → Split → Save

### Component Structure

```
main.py                    # 3つの処理モードのオーケストレーション
├── src/cli.py            # 引数パース、検証、モード判定
├── src/transcribe.py     # Whisper統合、GPU/CPU検出、句読点分割
├── src/splitter.py       # pydubによる音声切り出し、メタデータ生成
├── src/json_loader.py    # transcript.jsonの読込・検証
└── src/utils.py          # ファイル名サニタイズ、タイムスタンプ整形、文分割ユーティリティ
```

### Data Flow

```
Audio File (mp3/wav/m4a等)
    ↓
[Transcriber]
    • GPU/CPU自動検出
    • 初回実行時にモデルダウンロード
    • 単語レベルタイムスタンプ取得
    • 句読点（。！？）で文分割
    ↓
Segments: [{start, end, text}, ...]
    ↓
[AudioSplitter]
    • マージン追加（前: 0.1s, 後: 0.2s）
    • ファイル名生成: "001_text_here.mp3"
    • pydubで音声切り出し
    • 元フォーマット維持
    ↓
Output:
    • 001_first_line.mp3, 002_second_line.mp3, ...
    • transcript.json
```

## Key Design Decisions

1. **BGM Handling**: VADではなくWhisperの単語レベルタイムスタンプを使用
   - シンプルな実装でBGM付き音声に対応

2. **Japanese Sentence Splitting**: 句読点（。！？）で自動分割
   - 単語レベルタイムスタンプから各文の境界を計算
   - マッチ失敗時は元セグメントのタイムスタンプにフォールバック

3. **Auto-Mode Detection**: 拡張子で処理モード判定
   - `.json` → JSONモード（文字起こしスキップ）
   - その他 → 音声ファイルモード

4. **Output Directory Logic**:
   - 音声入力: `{filename}_generated/`を入力ファイルと同じ場所に作成
   - JSON入力: JSONファイルのディレクトリに出力
   - `--output-dir`で上書き可能

5. **Filename Generation**: `{3桁連番}_{サニタイズ済みテキスト}.{ext}`
   - 禁止文字除去: `\/:*?"<>|`
   - `--max-filename-length`で長さ制限（デフォルト: 制限なし）

6. **Format Preservation**: 出力は入力と同じ音声フォーマット
   - .m4a → 'ipod', .aac → 'adts' の特別処理

## CLI Specification

```bash
python main.py input_file [options]
```

### Arguments

| 引数 | 説明 | デフォルト |
|------|------|------------|
| `input_file` | 音声ファイルまたはJSONファイル（必須） | - |
| `--model` | Whisperモデル（tiny/base/small/medium/large） | base |
| `--language` | 言語コード（ja, en等） | 自動検出 |
| `--output-dir` | 出力ディレクトリ | `{入力名}_generated/` |
| `--max-filename-length` | ファイル名最大長 | 制限なし |
| `--margin-before` | 開始前マージン（秒） | 0.1 |
| `--margin-after` | 終了後マージン（秒） | 0.2 |
| `--transcribe-only` | 文字起こしのみ（分割なし） | - |
| `--from-json` | JSONから分割（明示指定） | - |
| `--device` | デバイス（cuda/cpu） | 自動検出 |

## Processing Flow

### Normal Mode
1. 入力ファイル検証
2. 出力ディレクトリ作成
3. Whisper文字起こし（タイムスタンプ付き）
4. 句読点で文分割、タイムスタンプ再計算
5. 音声切り出し・保存
6. transcript.json保存

### Transcribe-Only Mode
1-4は同じ、5-6をスキップしてJSON保存のみ

### JSON Mode
1. JSON読込・検証
2. 元音声ファイル検証
3. 音声切り出し・保存（JSONのテキストをそのまま使用、再分割なし）

## File Formats

### transcript.json
```json
{
  "source_file": "input.mp3",
  "segments": [
    {
      "index": 1,
      "filename": "001_hello_world.mp3",
      "start": 0.5,
      "end": 2.3,
      "text": "hello world"
    }
  ]
}
```

## Code Editing Guidelines

### src/transcribe.py
- 単語レベルタイムスタンプ抽出を維持（分割精度に必要）
- 句読点分割ロジック（`get_segments()`内）を維持
- GPU/CPU両モードでテスト
- 大モデル使用時のメモリ考慮

### src/splitter.py
- フォーマット維持（出力=入力フォーマット）
- マージン計算のエッジケース考慮
- 連番の一貫性（001, 002, ...）
- GUI用メソッド:
  - `export_segment()`: 単一セグメント書き出し
  - `rename_file()`: ファイルリネーム
  - `delete_file()`: ファイル削除
  - `generate_filename()`: ファイル名生成（書き出しなし）

### main.py
- 3モードの明確な分離を維持
- 自動判定ロジック（JSON拡張子）を維持
- 出力ディレクトリ動作の一貫性

## Technical Stack

### Required
- `openai-whisper`: 音声認識
- `torch`: PyTorch（Whisper依存、GPU対応）
- `pydub`: 音声処理
- `tqdm`: プログレスバー
- `ffmpeg`: システム依存（外部）

### GPU Support (CUDA 12.x)
```toml
[[tool.uv.index]]
name = "pytorch-cu124"
url = "https://download.pytorch.org/whl/cu124"
explicit = true

[tool.uv.sources]
torch = { index = "pytorch-cu124" }
torchvision = { index = "pytorch-cu124" }
torchaudio = { index = "pytorch-cu124" }
```

## Performance

| モデル | CPU | GPU (GTX 1660) | 速度比 |
|--------|-----|----------------|--------|
| tiny   | 1x  | 8-10x          | ~8倍   |
| base   | 1x  | 10-15x         | ~12倍  |
| small  | 1x  | 15-20x         | ~17倍  |

## Testing Approach

正式なテストスイートなし。手動テスト：
1. 既知の内容の音声ファイルでテスト
2. 3モード全て（normal, transcribe-only, from-json）をテスト
3. `--device`フラグでGPU/CPU切り替えテスト
4. エッジケース：短い音声、無音、BGMのみ

## GUI Editor

波形を見ながらセグメントを編集できるWebベースのGUIツール。

### 起動方法

```bash
python run_gui.py <output_directory> [--port PORT] [--no-browser]
```

- `transcript.json`が含まれるディレクトリを指定（必須）
- `transcript_unexported.json`があれば優先的に読み込む
- ディレクトリを変更する場合はサーバーを再起動
- ブラウザで http://localhost:5000 が自動で開く

### GUI構成

```
gui/
├── app.py              # Flaskバックエンド（API）
├── audio_handler.py    # 音声処理（波形データ生成）
├── templates/
│   └── index.html      # メインHTML
└── static/
    ├── styles.css      # スタイル
    └── app.js          # JavaScript（Wavesurfer.js統合）
run_gui.py              # 起動スクリプト
```

### 主要機能

1. **波形表示**: Wavesurfer.jsによる波形表示・ズーム・タイムライン
2. **セグメント編集**: ドラッグ操作または数値入力で時刻調整（即座に反映）
3. **テキスト編集**: 文字起こしテキストの修正（即座に反映）
4. **音声再生**: セグメント単位の再生・ループ再生・再生速度変更
5. **自動選択**: 再生カーソル位置のセグメントを自動選択（ループ再生中は無効）
6. **保存**: `transcript_unexported.json`として保存（編集中の状態）
7. **差分書き出し**: 変更/追加/削除/リネームを差分ベースで処理
8. **全件書き出し**: 強制的に全セグメントを再書き出し
9. **ファイル名自動生成**: 書き出し時にテキストから自動生成

### 波形エディタの操作

波形エディタは上部（20%）と下部（80%）で操作が分離されています：

| 領域 | 操作 |
|------|------|
| 上部（タイムライン・波形の上20%） | クリックでカーソル移動 |
| 下部（セグメント表示領域・波形の下80%） | クリックでセグメント選択、ドラッグで時刻調整 |

- タイムラインは5秒ごとにメインラベル、1秒ごとにサブラベルを表示
- Ctrl+ホイールで波形をズームイン/アウト

### キーボードショートカット

| キー | 機能 |
|------|------|
| Space | 再生/停止 |
| L | ループ再生ON/OFF |
| ←/→ | 前/次のセグメント選択 |
| ↑/↓ | 0.1秒移動 |
| ,/. | 5秒移動 |
| >/<  | 再生速度変更 |
| +/- | ズームイン/アウト |
| Ctrl+ホイール | ズームイン/アウト |
| Delete | セグメント削除 |
| Ctrl+S | 保存 |
| ? | ヘルプ表示 |

### セグメントのindex

- `index`は各セグメントの固有ID
- セグメントの追加・削除で他のセグメントのindexは変更されない
- 新規追加時は最大index + 1が割り当てられる
- セグメントは開始時刻順にソートして表示
- ファイル名は書き出し時に`{index:03d}_{text}.{ext}`形式で自動生成（GUIでは非表示）

### ワークフロー

```
[編集] → [保存] → transcript_unexported.json（編集中の状態）
                         ↓
                    [書き出し]
                         ↓
              transcript.json（書き出し済み）
              + 音声ファイル生成/リネーム/削除
              + transcript_unexported.json削除
```

### 書き出し処理（差分ベース）

| 状況 | 処理 |
|------|------|
| 削除されたセグメント | 音声ファイル削除 |
| 新規セグメント | 音声ファイル書き出し |
| start/end変更 | 旧ファイル削除 + 再書き出し |
| テキストのみ変更 | ファイルリネームのみ |
| 変更なし | 何もしない |

- **書き出しボタン**: 差分のみ処理（効率的）
- **全件書き出しボタン**: 全セグメントを強制的に再書き出し

### 起動時の動作

- `transcript_unexported.json`が存在する場合は優先的に読み込み
- 「未書き出しの変更あり」と通知される
- 書き出しを実行すると`transcript.json`が更新され、`_unexported.json`は削除される

### JSON形式

**transcript.json**（書き出し済み）:
```json
{
  "source_file": "input.mp3",
  "segments": [
    {
      "index": 1,
      "filename": "001_hello_world.mp3",
      "start": 0.5,
      "end": 2.3,
      "text": "hello world"
    }
  ]
}
```

**transcript_unexported.json**（編集中）:
- 保存時に自動生成される
- 書き出し後に自動削除される
- 起動時に存在すれば優先的に読み込まれる

### GUI追加依存関係

- `flask>=3.0.0`: Webフレームワーク
- `numpy>=1.24.0`: 波形データ処理

## Future Enhancements

- [x] GUI版
- [ ] バッチ処理（複数ファイル）
- [ ] 話者分離
- [ ] VAD併用オプション
- [ ] 出力フォーマット変換（mp3, wav等）
- [ ] クラウドAPI版（OpenAI Whisper API）
- [ ] セグメント自動マージ

## Windows: run.bat

対話式バッチファイル（非技術者向け）。Shift-JIS CRLF。
編集時は UTF-8一時ファイル経由で編集後、Shift-JISに変換。
