# 外部ツール

実行に必要なツール一覧です。

- [uv](https://docs.astral.sh/uv/)（パッケージ管理）
- [ffmpeg](https://ffmpeg.org/)（音声処理）

pythonのバージョンについては[.python-version](../.python-version)を、
pythonの依存パッケージについては [pyproject.toml](../pyproject.toml)を参照してください。
Pythonパッケージは初回実行時に自動でインストールされます。

配布版はバイナリを同梱しているため、個別のインストールは不要です。
依存外部ツールはプロジェクト内の `tools/` ディレクトリに配置されており、各スクリプトの実行時にのみPATHに追加されます。
システムの環境変数は変更しません。既にuv・ffmpegがシステムにインストールされている場合でも同梱版が優先されます。
