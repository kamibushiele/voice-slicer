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
├── edit_segments.json   # 全セグメント情報（編集済み）
├── 001_こんにちは世界.mp3
├── 002_今日はいい天気ですね.mp3
└── ...
```

## マージ処理

読み込み時、`transcript.json`と`edit_segments.json`をマージする。

|      項目       | `transcript.json` | `edit_segments.json` |  `edit_segments.json`への反映  |
| --------------- | ----------------- | -------------------- | ------------------------------ |
| セグメント自体  | あり              | なし                 | 削除として扱う               |
| セグメント自体  | なし              | あり                 | 変更なし(次の書き出しで追加)   |
| start,stop,text | あり              | なし                 | transcript.jsonの内容を反映    |
| start,stop,text | 内容が違う        | 内容が違う           | edit_segments.jsonの内容を優先 |

## 差分書き出し処理

書き出し時、変更内容に応じて最小限の処理を行う。
**差分判定は「値の比較」で行う**（キーの存在ではなく、実際の値が変わったかどうかで判定）。

| 判定 | 条件 | 処理 |
|-----|------|------|
| **追加** | `edit_segments`のみに存在 | index計算 → 音声ファイル作成 |
| **削除** | `transcript.json`にあって`edit_segments.json`にない | ファイル名を再計算 → 存在すれば削除 |
| **時間変更** | `start`または`end`の値が変更 | 音声ファイル再作成（index不変） |
| **テキスト変更** | `text`の値のみ変更 | ファイル名再計算 → リネームまたは新規作成 |
| **変更なし** | 値に差分なし | スキップ |

> **注**: `edit_segments.json`に全件データが含まれていても、値が同じであればスキップされる。

### インデックスの扱い

- 書き出し済みセグメントの`index`/`index_sub`は**不変**
- 新規セグメントのみ書き出し時にインデックスを計算
- インデックス決定ルールの詳細は [index_specification.md](index_specification.md) を参照

## 全件書き出し

差分ではなく、全セグメントを強制的に再書き出しする。
`--force`オプションで有効化。

## 手動編集用edit_segments.json生成

`edit_segments.json`が存在しない場合（古い環境など）、手動編集用に`edit_segments.json`を生成する。

```bash
uv run export_edit.py <output_dir>
```

生成される`edit_segments.json`には、`transcript.json`の全セグメント情報が含まれる。
テキストエディタで直接編集し、`split.py`を実行すると差分として処理される。

### 既存edit_segments.jsonがある場合

既に`edit_segments.json`が存在する場合は、以下の動作となる：

1. `transcript.json`の全セグメント情報をベースとしてコピー
2. 既存の`edit_segments.json`の情報で上書き（マージ）

これにより、部分的な編集情報のみが記載された`edit_segments.json`でも、
全セグメント情報を含む形式に更新される。

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

## データフォーマット

各JSONファイルの構造・フィールド仕様は [data_format.md](data_format.md) を参照。
