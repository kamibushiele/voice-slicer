# 文字起こしCLI

OpenAI Whisperを使用した音声認識で、音声ファイルをセリフごとに分割します。
句読点（。！？）で自動分割。単語レベルタイムスタンプから各文の境界を計算。

## 使い方

```bash
uv run transcribe.py <音声ファイル> [オプション]
```

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--model` | Whisperモデル (tiny/base/small/medium/large) | base |
| `--language` | 言語コード (ja, en等) | 自動検出 |
| `--output-dir` | 出力ディレクトリ | `{入力名}_generated/` |
| `--device` | デバイス (cuda/cpu) | 自動検出 |
| `--index-digits` | インデックスの桁数 | セグメント数から自動計算 |
| `--index-sub-digits` | サブインデックスの桁数 | 3 |
| `--filename-template` | ファイル名テンプレート | `{index}_{basename}` |
| `--margin-before` | 開始前マージン（秒） | 0.1 |
| `--margin-after` | 終了後マージン（秒） | 0.2 |

これらの書き出し設定は`transcript.json`の`output_format`に保存される。詳細は [data_format.md](data_format.md) を参照。

## Whisperモデル

| モデル | 精度 | 速度 | 推奨用途 |
|--------|------|------|----------|
| tiny   | 低   | 最速 | クイックテスト |
| base   | 中   | 速い | 通常使用 |
| small  | 高   | 普通 | 実用（推奨） |
| medium | 最高 | 遅い | 高品質 |
| large  | 最高 | 最遅 | 最高品質 |

## 出力

`{出力ディレクトリ}/` に `transcript.json`（設定情報）と `edit_segments.json`（全セグメント）を生成。

```
input_generated/
├── transcript.json      # 設定情報のみ
└── edit_segments.json   # 全セグメント情報
```

この時点では音声ファイルは生成されない。
書き出しは [split.py](split.md) または [GUI](edit.md) で行う。
