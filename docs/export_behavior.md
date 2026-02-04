# 書き出し挙動

CLI（split.py）とGUIの書き出しボタンで共通する処理の仕様。

## ワークフロー

```
[文字起こし] → transcript.json (設定のみ) + edit_segments.json (全セグメント)
                        ↓
                   [編集（任意）]
                        ↓
               edit_segments.json を更新
                        ↓
                   [書き出し]
                        ↓
             transcript.json (全データ) + 音声ファイル
             edit_segments.json は削除
```

## 出力ファイル構造

### 文字起こし直後

```
input_generated/
├── transcript.json      # 設定情報のみ（segments: {}）
└── edit_segments.json   # 全セグメント情報
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
├── transcript.json      # 前回書き出し時のセグメント情報
├── edit_segments.json   # 変更差分のみ
├── 001_こんにちは世界.mp3
├── 002_今日はいい天気ですね.mp3
└── ...
```

## transcript.json と edit_segments.json

| ファイル | 役割 |
|---------|------|
| `transcript.json` | 元ファイル情報、書き出し設定、書き出し済みセグメント |
| `edit_segments.json` | 未書き出しの変更差分のみ |

- 文字起こし時: 両方を生成（`transcript.json`はセグメント空、`edit_segments.json`に全セグメント）
- 書き出し時: `transcript.json`にマージ済みデータを保存、`edit_segments.json`は削除
- 起動時: 両方を読み込んでマージ

### edit_segments.json の変更差分

| 操作 | 記載内容 |
|-----|---------|
| 追加 | 全フィールド（`start`, `end`, `text`） |
| 変更 | 変更フィールドのみ |
| 削除 | `"deleted": true` のみ |

## マージ処理

読み込み時、`transcript.json`と`edit_segments.json`をマージする。

```python
def merge_segments(transcript_segments, edit_segments):
    result = {}

    # 1. transcript.segmentsをベースにコピー
    for id, seg in transcript_segments.items():
        result[id] = seg.copy()

    # 2. edit_segmentsを適用
    for id, changes in edit_segments.items():
        if changes.get("deleted"):
            # 削除: resultから除去
            result.pop(id, None)
        elif id in result:
            # 変更: 既存セグメントを更新
            result[id].update(changes)
        else:
            # 追加: 新規セグメント
            result[id] = changes.copy()

    return result
```

## 差分書き出し処理

書き出し時、変更内容に応じて最小限の処理を行う。

| 判定 | 条件 | 処理 |
|-----|------|------|
| **追加** | `edit_segments`のみに存在 | index計算 → 音声ファイル作成 |
| **削除** | `"deleted": true` | ファイル名を再計算 → 存在すれば削除 |
| **時間変更** | `start`または`end`が変更 | 音声ファイル再作成（index不変） |
| **テキスト変更** | `text`のみ変更 | ファイル名再計算 → リネームまたは新規作成 |
| **変更なし** | 差分なし | スキップ |

### インデックスの扱い

- 書き出し済みセグメントの`index`/`index_sub`は**不変**
- 新規セグメントのみ書き出し時にインデックスを計算

## 全件書き出し

差分ではなく、全セグメントを強制的に再書き出しする。
`--force`オプションで有効化。

## マージン

書き出し時、セグメントの前後にマージンを付加する。
設定は`transcript.json`の`output_format.margin`に保存される。

| 設定 | 説明 | デフォルト |
|-----------|------|-----------| 
| `margin.before` | 開始前マージン（秒） | 0.1 |
| `margin.after` | 終了後マージン（秒） | 0.2 |

## ファイル名生成

詳細は [index_specification.md](index_specification.md) を参照。

```
{index}_{text}.{ext}           # index_sub省略
{index}-{index_sub}_{text}.{ext}
```

## セグメントID

### 採番ルール

- **連番（最大+1）方式**
- 新規追加時: 既存IDの最大値 + 1
- 欠番は許容（削除後に詰めない）

### 例

```json
// 初期状態
{ "1": {...}, "2": {...}, "3": {...} }

// ID:2を削除
{ "1": {...}, "3": {...} }

// 新規追加（最大3 + 1 = 4）
{ "1": {...}, "3": {...}, "4": {...} }
```

## 後方互換性

### バージョン判定

| version | フォーマット |
|---------|-------------|
| 未定義 | 旧フォーマット（配列ベース） |
| 2 | 新フォーマット（オブジェクトベース） |

### 自動マイグレーション

旧フォーマット検出時に自動で新フォーマットへ変換する。

| 旧ファイル | 変換先 |
|-----------|--------|
| `transcript.json` (旧) | `transcript.json` (新) |
| `transcript_unexported.json` | `edit_segments.json` |
