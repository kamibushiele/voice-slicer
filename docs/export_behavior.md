# 書き出し挙動

CLI（split.py）とGUIの書き出しボタンで共通する処理の仕様。

## ワークフロー

```
[文字起こし] → transcript_unexported.json
                        ↓
                   [編集（任意）]
                        ↓
                   [書き出し]
                        ↓
             transcript.json + 音声ファイル
```

## 出力ファイル構造

### 文字起こし直後

```
input_generated/
└── transcript_unexported.json  # 未書き出しセグメント情報
```

### 書き出し後

```
input_generated/
├── transcript.json           # セグメント情報（確定）
├── 001_こんにちは世界.mp3     # 分割音声
├── 002_今日はいい天気ですね.mp3
└── ...
```

### 書き出し後に編集して未反映の状態

```
input_generated/
├── transcript.json             # 前回書き出し時のセグメント情報
├── transcript_unexported.json  # 編集後のセグメント情報
├── 001_こんにちは世界.mp3
├── 002_今日はいい天気ですね.mp3
└── ...
```

## transcript.json と transcript_unexported.json

| ファイル | 役割 |
|---------|------|
| `transcript_unexported.json` | 編集中・未書き出しのセグメント情報 |
| `transcript.json` | 書き出し済みの確定セグメント情報 |

- 文字起こし時: `transcript_unexported.json` のみ生成
- 書き出し時: `transcript.json` に確定、`transcript_unexported.json` は削除
- 起動時: `transcript_unexported.json` が存在すれば優先読み込み

## 差分書き出し処理

書き出し時、変更内容に応じて最小限の処理を行う。

| 変更内容 | 処理 |
|---------|------|
| セグメント追加 | 音声ファイル新規作成 |
| セグメント削除 | 音声ファイル削除 |
| start/end変更 | 旧ファイルを上書き |
| テキストのみ変更 | ファイルリネーム |
| 変更なし | スキップ |

## 全件書き出し

差分ではなく、全セグメントを強制的に再書き出しする。
既存ファイルをすべて削除してから再生成。

## マージン

書き出し時、セグメントの前後にマージンを付加できる。

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--margin-before` | 開始前マージン（秒） | 0.1 |
| `--margin-after` | 終了後マージン（秒） | 0.2 |

## ファイル名生成

詳細は [index_specification.md](index_specification.md) を参照。

```
{index}_{text}.{ext}           # index_sub省略
{index}-{index_sub}_{text}.{ext}
```
