# CLAUDE.md

Claude Code向けの開発ガイドです。利用方法は[README.md](README.md)を参照してください。

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
├── src/cuesheet.py       # マルチフォーマット出力（CSV/TSV/SRT/VTT）
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
    • cuesheet.csv/tsv/srt/vtt
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
| `--cue-format` | Cueシート形式（csv/tsv/srt/vtt/all） | csv |
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
7. Cueシート出力

### Transcribe-Only Mode
1-4は同じ、5-7をスキップしてJSON保存のみ

### JSON Mode
1. JSON読込・検証
2. 元音声ファイル検証
3. 音声切り出し・保存（JSONのテキストをそのまま使用、再分割なし）
4. Cueシート出力

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

### Cue Sheet Formats
- **CSV/TSV**: `Index,Start,End,Duration,Text,Filename`
- **SRT**: `00:00:00,000 --> 00:00:03,580` 形式
- **VTT**: `00:00:00.000 --> 00:00:03.580` 形式

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

### src/cuesheet.py
- 既存フォーマットジェネレータパターンに従う
- タイムスタンプをフォーマット固有記法に変換
- 新フォーマット追加時はCLI引数も更新

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
5. Cueシートを対象アプリ（動画編集ソフト等）で検証

## Future Enhancements

- [ ] GUI版
- [ ] バッチ処理（複数ファイル）
- [ ] 話者分離
- [ ] VAD併用オプション
- [ ] 出力フォーマット変換（mp3, wav等）
- [ ] クラウドAPI版（OpenAI Whisper API）
- [ ] セグメント自動マージ

## Windows: run.bat

対話式バッチファイル（非技術者向け）。Shift-JIS CRLF。
編集時は UTF-8一時ファイル経由で編集後、Shift-JISに変換。
