# VoiceSlicer

音声ファイルをWhisperで文字起こしし、各セリフごとに個別の音声ファイルに分割するツールです。

## 機能

- OpenAI Whisperを使用したローカル音声認識
- タイムスタンプベースの音声分割（BGM対応）
- 日本語句読点（。！？）で自動的に文を分割
- 波形を見ながら手動調整できる編集画面
- 差分ベースの書き出し（変更箇所のみ再処理）

## セットアップ

### リリースパッケージ（推奨）

対応プラットフォーム

- Windows x64

[Releases](https://github.com/kamibushiele/voice-slicer/releases)からzipをダウンロードして展開してください。

### ソースから構築

上記対応プラットフォーム以外で動かす場合

```bash
git clone https://github.com/kamibushiele/voice-slicer.git
cd voice-slicer
uv sync
```

uv・ffmpegは別途インストールが必要です。詳細は[docs/tools.md](docs/tools.md)を参照してください。

## 使い方

`voice_slicer.bat` をダブルクリックして起動します。

メニューから実行したい機能を選んでください。

1. **音声ファイルを文字起こしする** — 音声ファイルを読み込み、セリフごとに分割します
2. **文字起こし結果を確認・修正する** — 波形を見ながらセリフの区切りやテキストを調整できます
3. **音声ファイルに書き出す** — 編集結果をもとに個別の音声ファイルを生成します

通常は 1 → 2 または 3 の順に進めます。文字起こし完了後は次のステップへそのまま進むこともできます。

### コマンドラインからの利用

各機能はコマンドラインから直接実行することもできます。モデルサイズや言語指定などの細かい調整が可能です。

詳細は下記のドキュメントを参照してください。

## ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [docs/transcribe.md](docs/transcribe.md) | 文字起こしCLIの詳細 |
| [docs/split.md](docs/split.md) | 分割CLIの詳細 |
| [docs/edit.md](docs/edit.md) | 編集画面の操作ガイド |
| [docs/export_behavior.md](docs/export_behavior.md) | 書き出し処理の仕様 |
| [docs/data_format.md](docs/data_format.md) | JSONデータフォーマット仕様 |
| [docs/index_specification.md](docs/index_specification.md) | セグメントindex仕様 |
| [docs/tools.md](docs/tools.md) | 外部ツール |

## ライセンス

MIT License
