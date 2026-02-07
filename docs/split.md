# 分割CLI

セグメント情報を音声ファイルに書き出す。

## 使い方

```bash
uv run split.py <ディレクトリ> [オプション]
```

- `<ディレクトリ>`: `transcript.json` と `edit_segments.json` を含むディレクトリ（書き出し先でもある）

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--margin-before` | 開始前マージン（秒） | 0.1 |
| `--margin-after` | 終了後マージン（秒） | 0.2 |
| `--max-filename-length` | ファイル名最大長 | 制限なし |

## 書き出し挙動

差分ベースで書き出しを行う。詳細は [export_behavior.md](export_behavior.md) を参照。
