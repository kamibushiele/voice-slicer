# セグメントindex仕様書

## 概要

セグメントのindex, index_subの組み合わせは、ファイル名のソート順を決定するための数字の組み合わせ。
通常は可能な限り連番となるindexを用いて、挿入時はindex_subを使用して挿入を実現する。
可能な限り一致を避けるが、挿入上限によって同じindexが発生することを許容する。

index_subの未定義と0は等価と解釈する。

---

## ワークフロー

### 1. 初回の文字起こし（transcribe.py）

音声ファイルからセグメントを生成し、`transcript.json`と`edit_segments.json`を出力する。

- `transcript.json`: 設定情報のみ（`segments: {}`は空）
- `edit_segments.json`: 全セグメント（ID: 1, 2, 3...）
- セグメントには`index`, `index_sub`は**未設定**

### 2. 編集（GUI）

ユーザーがセグメントの追加・削除・編集を行う。

- 編集中のセグメントは`index`が**未設定**のまま
- 保存時は`edit_segments.json`に変更差分のみ保存

### 3. 書き出し（GUI/split.py）

セグメントを音声ファイルとして書き出す。

1. `transcript.json`と`edit_segments.json`をマージ
2. 時刻順にセグメントをソート
3. 未設定のセグメントに対してindexを決定（既存のindexを基準に計算）
4. ファイル名を生成し、音声ファイルを出力
5. `transcript.json`に確定したindex, セグメント情報を保存
6. `edit_segments.json`は保持

```
[編集中]                    [書き出し後]
index: 未設定        →      index: 1
index_sub: 未設定    →      index_sub: null (0)
```

---

## ファイル名フォーマット

indexは`index_digits`桁の0埋めとする。
index_subは`index_sub_digits`桁の0埋めとする（デフォルト: 3桁）。

index_subが未定義もしくは0の場合index_subを省略する。

```
{index}_{text}.{ext} ← index_sub省略の場合
{index}-{index_sub}_{text}.{ext}
```

**例 index_digits=3, index_sub_digits=3の場合:**

| index | index_sub | text       | ファイル名             |
| ----- | --------- | ---------- | ---------------------- |
| 000   | 500       | 先頭追加   | `000-500_先頭追加.mp3` |
| 001   | 未定義    | こんにちは | `001_こんにちは.mp3`   |
| 001   | 500       | 間に追加   | `001-500_間に追加.mp3` |
| 002   | 未定義    | さようなら | `002_さようなら.mp3`   |
| 003   | 未定義    | 末尾追加   | `003_末尾追加.mp3`     |

### index_digitsの決定

`transcript.json`の初回生成時のセグメント数の桁数に基づいて桁数を決定し、以降は固定。
未指定または3桁未満の場合は3桁とする。

> **注意**: 追加編集で桁数を超えた場合（例：3桁で999の次は1000）、ソート順は保証されない。

---

## index決定ルール

書き出し時、indexが未設定のセグメントに対してindexを決定する。

`(メインindex, index_sub)`で表記する。

挿入したい位置を以下で表すとして挿入決定するindexは以下のルールで決定する。

前のindex = $(N,n)$
後のindex = $(M,m)$
決定index = $(X,x)$
index_sub_digits = $d$（デフォルト: 3）

前のindexがない場合$(N,n)=(0,0)$として扱う。
次のindexがない場合$(M,m)=(+\infty,0)$として扱う。

1. $N+1 < M$ の場合、もしくは $N+1 = M \land m \neq 0$の場合（indexの空きがある）
   1. $(X,x) = (N+1,0)$
2. $N+1 = M \land m=0$の場合（indexの空きがないが次のindex_subが0）
   1. $X=N$
   2. 同じ場所に挿入したいセグメントが$l \geq 1$個並んでいる場合を考え、
   3. $x = n+(10^d-n)/(l+1)$
3. $N+1 > M$ つまり $N=M$の場合
   1. $X=N$
   2. 同じ場所に挿入したいセグメントが$l \geq 1$個並んでいる場合を考え、
   3. $x = n+(m-n)/(l+1)$

最後にxは整数にキャストする。また、xが$10^d - 1$を超える場合$10^d - 1$とする。

---

## 分割不可時の動作

index_subの分割限界に達した場合（例：隣接するindex_subの差が1以下）、
同一の(index, index_sub)を許容する。

> **注意**: 同一indexの場合、ファイル名のソート順は保証されない。

---

## データ構造

### transcript.json（version 2）

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

### edit_segments.json（version 2）

```json
{
  "version": 2,
  "segments": {
    "1": {
      "start": 1.5,
      "end": 2.5
    },
    "2": {
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

### フィールド説明

#### transcript.json

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
| `index_sub` | number \| null | サブインデックス（0の場合null） |

#### edit_segments.json 操作別の記載内容

| 操作 | 記載内容 |
|-----|---------|
| 追加・変更 | 全フィールド（`start`, `end`, `text`） |
| 削除 | セグメント自体の削除 |
