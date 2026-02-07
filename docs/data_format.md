# データフォーマット仕様

本プロジェクトで使用するJSONファイルのデータ構造仕様。

## ファイル一覧

| ファイル | 役割 |
|---------|------|
| `transcript.json` | 元ファイル情報、書き出し設定、書き出し済みセグメント |
| `edit_segments.json` | 編集中の全セグメント情報 |

## transcript.json

### バージョン判定

| version | フォーマット |
|---------|-------------|
| 未定義 | 旧フォーマット（配列ベース） |
| 2 | 新フォーマット（オブジェクトベース） |

旧フォーマット検出時に自動で新フォーマットへ変換する（`transcript_unexported.json` → `edit_segments.json`）。

### 構造（version 2）

```json
{
  "version": 2,
  "source_file": "/path/to/audio.m4a",
  "output_format": {
    "index_digits": 3,
    "index_sub_digits": 3,
    "filename_template": "{index}_{basename}",
    "margin": {
      "before": 0.1,
      "after": 0.2
    }
  },
  "segments": {
    "1": {
      "start": 0,
      "end": 2.16,
      "text": "こんにちは",
      "index": 1,
      "index_sub": null
    },
    "2": {
      "start": 2.21,
      "end": 3.98,
      "text": "ありがとう",
      "index": 2,
      "index_sub": null
    }
  }
}
```

### フィールド説明

#### トップレベル

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `version` | number | スキーマバージョン（現在: 2） |
| `source_file` | string | 元音声ファイルの絶対パス |
| `output_format` | object | 書き出し設定 |
| `segments` | object | 書き出し済みセグメント（IDをキー） |

#### output_format

| フィールド | デフォルト | 説明 |
|-----------|-----------|------|
| `index_digits` | セグメント数から自動計算 | メインインデックス桁数 |
| `index_sub_digits` | 3 | サブインデックス桁数 |
| `filename_template` | `"{index}_{basename}"` | ファイル名テンプレート |
| `margin.before` | 0.1 | 開始前マージン（秒） |
| `margin.after` | 0.2 | 終了後マージン（秒） |

#### segments[id]

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `start` | number | 開始時刻（秒） |
| `end` | number | 終了時刻（秒） |
| `text` | string | セグメントテキスト |
| `index` | number | 書き出し時に確定したインデックス |
| `index_sub` | number &#124; null | サブインデックス（0の場合null） |

## edit_segments.json

### 構造（version 2）

```json
{
  "version": 2,
  "segments": {
    "1": {
      "start": 1.5,
      "end": 2.5,
      "text": "こんにちは"
    },
    "2": {
      "start": 2.21,
      "end": 3.98,
      "text": "変更後テキスト"
    },
    "4": {
      "start": 5.0,
      "end": 6.0,
      "text": "新規追加セグメント"
    }
  }
}
```

### セグメントの記載ルール

| 操作 | 記載内容 |
|-----|---------| 
| 通常 | 全フィールド（`start`, `end`, `text`） |
| 削除 | セグメントを含めない |

### 生成タイミング

- **文字起こし時**: 全セグメントを含む`edit_segments.json`を生成
- **編集保存時**: 現在の全セグメント情報で上書き

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
