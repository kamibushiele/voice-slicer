# AI文字起こし

OpenAI Whisperを使用した音声認識で、音声ファイルをセリフごとに分割します。

## 基本的な使い方

```bash
# 音声ファイルを文字起こし＆分割
uv run python main.py input.mp3
# → input_generated/ に出力
```

## オプション

| オプション | 説明 | デフォルト |
|----------|------|------------|
| `--model` | Whisperモデル（tiny/base/small/medium/large） | base |
| `--language` | 言語コード（ja, en等） | 自動検出 |
| `--output-dir` | 出力ディレクトリ | `{入力名}_generated/` |
| `--max-filename-length` | ファイル名最大長 | 制限なし |
| `--margin-before` | セグメント開始前マージン（秒） | 0.1 |
| `--margin-after` | セグメント終了後マージン（秒） | 0.2 |
| `--transcribe-only` | 文字起こしのみ（音声分割なし） | - |
| `--from-json` | JSONから分割（通常は拡張子で自動判定） | - |
| `--device` | デバイス（cuda/cpu） | 自動検出 |

## Whisperモデル

| モデル | 精度 | 速度 | 推奨用途 |
|--------|------|------|----------|
| tiny   | 低   | 最速 | クイックテスト |
| base   | 中   | 速い | 通常使用 |
| small  | 高   | 普通 | 実用（推奨） |
| medium | 最高 | 遅い | 高品質 |
| large  | 最高 | 最遅 | 最高品質 |

```bash
# 高精度モデル使用
uv run python main.py input.mp3 --model small

# GPU使用
uv run python main.py input.mp3 --device cuda
```

## 2段階処理

文字起こし結果を編集してから分割する場合：

```bash
# 1. 文字起こしのみ
uv run python main.py input.mp3 --transcribe-only
# → input_generated/transcript.json が生成

# 2. JSONを編集（テキスト修正、不要セグメント削除など）

# 3. 編集したJSONから音声分割
uv run python main.py input_generated/transcript.json
```

## 出力ファイル

```
input_generated/
├── 001_こんにちは世界.mp3
├── 002_今日はいい天気ですね.mp3
└── transcript.json      # メタデータ（編集可能）
```

## トラブルシューティング

### ffmpegが見つからない
→ ffmpegをシステムにインストールしてください

### CUDA out of memory
→ 小さいモデルを使用: `--model tiny` または `--model base`

### 音声が検出されない
→ `--language ja` で言語を明示指定、または `--model small` で精度向上
