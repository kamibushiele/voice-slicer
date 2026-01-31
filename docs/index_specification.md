# セグメントindex仕様書

## 概要

セグメントのindex, index_subの組み合わせは、ファイル名のソート順を決定するための数字の組み合わせ。
通常は可能な限り連番となるindexを用いて、挿入時はindex_subを使用して挿入を実現する。
可能な限り一致を避けるが、挿入上限によって同じindexが発生することを許容する。

index_subの未定義と0は等価と解釈する。

---

## ワークフロー

### 1. 初回の文字起こし（transcribe.py）

音声ファイルからセグメントを生成し、`transcript_unexported.json`を出力する。

- セグメントには`index`, `index_sub`, `filename`は**未設定**
- `index_digits`はセグメント数から決定

### 2. 編集（GUI）

ユーザーがセグメントの追加・削除・編集を行う。

- 編集中のセグメントは`index`, `filename`が**未設定**のまま
- 保存時は`transcript_unexported.json`に保存

### 3. 書き出し（GUI/split.py）

セグメントを音声ファイルとして書き出す。

1. 時刻順にセグメントをソート
1. 未設定のセグメントに対してindexを決定（既存のindexを基準に計算）
1. ファイル名を生成し、音声ファイルを出力
1. `transcript.json`に確定したindex, filenameを保存
1. `transcript_unexported.json`を削除

```
[編集中]                    [書き出し後]
index: 未設定        →      index: 1
index_sub: 未設定    →      index_sub: 0
filename: 未設定     →      filename: "001_こんにちは.mp3"
```

---

## ファイル名フォーマット

indexは`index_digits`桁の0埋めとする。
index_subは3桁の0埋めとする。

index_subが未定義もしくは0の場合index_subを省略する。

```
{index}_{text}.{ext} ← index_sub省略の場合
{index}-{index_sub}_{text}.{ext}
```

**例 index_digits=3の場合:**

| index | index_sub | text       | ファイル名             |
| ----- | --------- | ---------- | ---------------------- |
| 000   | 500       | 先頭追加   | `000-500_先頭追加.mp3` |
| 001   | 未定義    | こんにちは | `001_こんにちは.mp3`   |
| 001   | 500       | 間に追加   | `001-500_間に追加.mp3` |
| 002   | 未定義    | さようなら | `002_さようなら.mp3`   |
| 003   | 未定義    | 末尾追加   | `003_末尾追加.mp3`     |

### index_digitsの決定

`transcript_unexported.json`の初回生成時のセグメント数の桁数に基づいて桁数を決定し、以降は固定。
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

前のindexがない場合$(N,n)=(0,0)$として扱う。
次のindexがない場合$(M,m)=(+\infty,0)$として扱う。

1. $N+1 < M$ の場合、もしくは $N+1 = M \land m \neq 0$の場合（indexの空きがある）
   1. $(X,x) = (N+1,0)$
2. $N+1 = M \land m=0$の場合（indexの空きがないが次のindex_subが0）
   1. $X=N$
   2. 同じ場所に挿入したいセグメントが$l \geq 1$個並んでいる場合を考え、
   3. $x = n+(1000-n)/(l+1)$
3. $N+1 > M$ つまり $N=M$の場合
   1. $X=N$
   2. 同じ場所に挿入したいセグメントが$l \geq 1$個並んでいる場合を考え、
   3. $x = n+(m-n)/(l+1)$

最後にxは整数にキャストする。また、xが999を超える場合999とする。

---

## 分割不可時の動作

index_subの分割限界に達した場合（例：隣接するindex_subの差が1以下）、
同一の(index, index_sub)を許容する。

> **注意**: 同一indexの場合、ファイル名のソート順は保証されない。

---

## データ構造

### transcript.json / transcript_unexported.json

```json
{
  "source_file": "input.mp3",
  "index_digits": 3,
  "segments": [
    {
      "index": 1,
      "index_sub": 500,
      "start": 0.5,
      "end": 2.3,
      "text": "こんにちは",
      "filename": "001-500_こんにちは.mp3"
    }
  ]
}
```

| フィールド     | 説明                                                           |
| -------------- | -------------------------------------------------------------- |
| `index_digits` | indexの桁数（num Null許容）Null未定義の場合3とする             |
| `index`        | メインindex（num）編集中はNull許容（書き出し前なのでindex未定）|
| `index_sub`    | サブのindex（num Null許容）                                    |
| `filename`     | 書き出し後のファイル名（書き出し前は未設定）                   |
