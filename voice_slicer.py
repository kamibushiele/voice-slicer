"""VoiceSlicer - Interactive CLI launcher."""
import subprocess
import sys
from pathlib import Path

import questionary

SCRIPT_DIR = Path(__file__).parent

MODELS = [
    ("tiny", "最速・精度低め"),
    ("base", "標準（おすすめ）"),
    ("small", "やや高精度"),
    ("medium", "高精度・処理が遅い"),
    ("large", "最高精度・処理がとても遅い"),
]


# ── ユーティリティ ─────────────────────────────


def ask_path(message: str) -> str | None:
    """対話的にパスを取得する。"""
    raw = questionary.path(message).ask()
    if raw is None:
        return None
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    return raw


def run_script(name: str, args: list[str]) -> int:
    """プロジェクト内のスクリプトを実行する。"""
    script = SCRIPT_DIR / name
    result = subprocess.run([sys.executable, str(script)] + args)
    return result.returncode


def run_script_capture(name: str, args: list[str]) -> tuple[int, str]:
    """プロジェクト内のスクリプトを実行し、出力を表示しつつキャプチャする。"""
    script = SCRIPT_DIR / name
    proc = subprocess.Popen(
        [sys.executable, "-u", str(script)] + args,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout_lines = []
    for line in proc.stdout:
        print(line, end="")
        stdout_lines.append(line)
    proc.wait()
    return proc.returncode, "".join(stdout_lines)


def parse_output_dir(stdout: str) -> str | None:
    """stdoutからOUTPUT_DIR=行を解析する。"""
    for line in stdout.splitlines():
        if line.startswith("OUTPUT_DIR="):
            return line[len("OUTPUT_DIR="):]
    return None


# ── 1. 文字起こし ──────────────────────────────


def do_transcribe() -> int:
    """音声ファイルを文字起こしする。"""
    file_path = ask_path("音声ファイルをドラッグ＆ドロップ、またはパスを入力:")
    if file_path is None:
        return 1
    if not Path(file_path).exists():
        print(f"\n[ERROR] ファイルが見つかりません: {file_path}", file=sys.stderr)
        return 1

    model_choices = [
        questionary.Choice(f"{name:<8} - {desc}", value=name)
        for name, desc in MODELS
    ]
    model = questionary.select(
        "認識精度を選んでください（精度が高いほど処理に時間がかかります）:",
        choices=model_choices,
        default="base",
    ).ask()
    if model is None:
        return 1

    desc = dict(MODELS)[model]
    print()
    print("=" * 60)
    print("実行設定:")
    print(f"  音声ファイル: {file_path}")
    print(f"  認識精度:     {model} ({desc})")
    print("=" * 60)
    print()

    ret, stdout = run_script_capture("transcribe.py", [file_path, "--model", model])
    if ret != 0:
        return ret

    # 文字起こし後の次のアクション
    output_dir = parse_output_dir(stdout)
    if output_dir is None:
        print("\n[ERROR] 出力ディレクトリの取得に失敗しました。", file=sys.stderr)
        return 1

    next_action = questionary.select(
        "文字起こしが完了しました。次に何をしますか？",
        choices=[
            questionary.Choice("文字起こし結果を確認・修正する（編集画面を開く）", value="edit"),
            questionary.Choice("音声ファイルに書き出す", value="split"),
            questionary.Choice("終了", value=None),
        ],
    ).ask()

    if next_action == "edit":
        return run_script("edit.py", [output_dir])
    elif next_action == "split":
        return run_script("split.py", [output_dir])
    return 0


# ── 2. 編集 ───────────────────────────────────


def do_edit() -> int:
    """編集画面を開く。"""
    dir_path = ask_path("文字起こし済みフォルダをドラッグ＆ドロップ、またはパスを入力:")
    if dir_path is None:
        return 1
    if not Path(dir_path).is_dir():
        print(f"\n[ERROR] フォルダが見つかりません: {dir_path}", file=sys.stderr)
        return 1

    return run_script("edit.py", [dir_path])


# ── 3. 書き出し ───────────────────────────────


def do_split() -> int:
    """音声ファイルを書き出す。"""
    dir_path = ask_path("文字起こし済みフォルダをドラッグ＆ドロップ、またはパスを入力:")
    if dir_path is None:
        return 1
    if not Path(dir_path).is_dir():
        print(f"\n[ERROR] フォルダが見つかりません: {dir_path}", file=sys.stderr)
        return 1

    return run_script("split.py", [dir_path])


# ── メインメニュー ─────────────────────────────

ACTIONS = [
    ("音声ファイルを文字起こしする", do_transcribe),
    ("文字起こし結果を確認・修正する（編集画面を開く）", do_edit),
    ("音声ファイルに書き出す", do_split),
    ("終了", None),
]


def main() -> int:
    print("=" * 60)
    print("VoiceSlicer")
    print("=" * 60)
    print()

    choices = [
        questionary.Choice(label, value=action)
        for label, action in ACTIONS
    ]
    action = questionary.select(
        "何をしますか？",
        choices=choices,
    ).ask()

    if action is None:
        return 0

    return action()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n操作がキャンセルされました。")
        sys.exit(1)
