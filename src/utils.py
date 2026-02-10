"""Utility functions for file handling and text processing."""
import math
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional


# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def setup_ffmpeg() -> None:
    """Configure pydub to use local ffmpeg if available in tools/ffmpeg/."""
    import sys
    from pydub import AudioSegment

    ffmpeg_dir = PROJECT_ROOT / "tools" / "ffmpeg"
    ext = ".exe" if sys.platform == "win32" else ""
    ffmpeg_path = ffmpeg_dir / f"ffmpeg{ext}"
    ffprobe_path = ffmpeg_dir / f"ffprobe{ext}"

    if ffmpeg_path.exists():
        AudioSegment.converter = str(ffmpeg_path)
    if ffprobe_path.exists():
        AudioSegment.ffprobe = str(ffprobe_path)


def get_audio_segment_class():
    """pydubのAudioSegmentをローカルffmpeg設定済みで返す。

    pydubを使う箇所はこの関数経由でAudioSegmentを取得すること。
    """
    setup_ffmpeg()
    from pydub import AudioSegment
    return AudioSegment


def split_sentences_with_positions(text: str) -> List[tuple]:
    """
    Split Japanese text by punctuation marks and return with character positions.

    Args:
        text: Original text

    Returns:
        List of tuples: (sentence_text, start_pos, end_pos)
    """
    sentences = []
    current_pos = 0

    # Find all punctuation positions
    punctuation_pattern = re.compile(r'(。|！|？)')

    for match in punctuation_pattern.finditer(text):
        punct_pos = match.start()
        sentence_text = text[current_pos:punct_pos + 1]

        if sentence_text.strip():
            sentences.append((sentence_text, current_pos, punct_pos + 1))

        current_pos = punct_pos + 1

    # Add remaining text if any
    if current_pos < len(text):
        remaining = text[current_pos:]
        if remaining.strip():
            sentences.append((remaining, current_pos, len(text)))

    return sentences


def split_sentences_by_punctuation(text: str) -> List[str]:
    """
    Split Japanese text by punctuation marks (。！？).

    Args:
        text: Original text

    Returns:
        List of sentences split by punctuation
    """
    # Split by Japanese punctuation marks (。！？)
    # Keep the punctuation with the sentence
    sentences = re.split(r'(。|！|？)', text)

    # Reconstruct sentences with punctuation
    result = []
    for i in range(0, len(sentences), 2):
        if i < len(sentences):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]  # Add punctuation

            # Only include non-empty sentences
            if sentence.strip():
                result.append(sentence)

    return result


def sanitize_filename(text: str, max_length: int = None) -> str:
    """
    Convert text to a safe filename.

    Args:
        text: Original text
        max_length: Maximum length of filename (None for no limit, respects OS limit)

    Returns:
        Sanitized filename string
    """
    # Remove or replace invalid filename characters
    invalid_chars = r'[\\/:*?"<>|]'
    sanitized = re.sub(invalid_chars, '', text)

    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')

    # Replace multiple underscores with single underscore
    sanitized = re.sub(r'_+', '_', sanitized)

    # Strip leading/trailing underscores
    sanitized = sanitized.strip('_')

    # Limit length if specified
    if max_length is not None and len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip('_')

    # Ensure we have something (fallback)
    if not sanitized:
        sanitized = "untitled"

    return sanitized


def generate_segment_filename(
    index: int,
    text: str,
    extension: str,
    max_text_length: int = None
) -> str:
    """
    Generate a filename for an audio segment.
    
    Args:
        index: Segment index (1-based)
        text: Segment text content
        extension: File extension (with or without leading dot)
        max_text_length: Maximum length of text part (None for no limit)
    
    Returns:
        Generated filename like "001_hello_world.mp3"
    """
    # Ensure extension has leading dot
    if not extension.startswith('.'):
        extension = '.' + extension
    
    # Generate filename parts
    file_number = f"{index:03d}"
    text_part = sanitize_filename(text, max_text_length)
    
    return f"{file_number}_{text_part}{extension}"


def format_timestamp(seconds: float) -> str:
    """
    Format seconds to HH:MM:SS.mmm format.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


# =============================================================================
# Index関連関数
# =============================================================================

def calculate_index_digits(count: int) -> int:
    """
    セグメント数から必要なindex桁数を計算する。

    Args:
        count: セグメント数

    Returns:
        桁数（最小3桁）
    """
    if count <= 999:
        return 3
    return len(str(count))


def determine_index(
    before: Optional[Tuple[int, int]],
    after: Optional[Tuple[int, int]],
    l: int = 1,
    index_sub_digits: int = 3
) -> Tuple[int, int]:
    """
    挿入位置からindexを決定する。

    Args:
        before: 前のセグメントの(index, index_sub)、なければNone
        after: 後のセグメントの(index, index_sub)、なければNone
        l: 同じ場所に挿入するセグメント数（>=1）
        index_sub_digits: サブインデックスの桁数（デフォルト: 3）

    Returns:
        (index, index_sub) のタプル
    """
    # 最大値を計算: 10^d - 1
    max_index_sub = (10 ** index_sub_digits) - 1

    # 前のindexがない場合は(0, 0)として扱う
    N, n = before if before else (0, 0)

    # 後のindexがない場合は(+inf, 0)として扱う
    if after is None:
        M, m = float('inf'), 0
    else:
        M, m = after

    # ルール1: indexの空きがある場合
    if N + 1 < M or (N + 1 == M and m != 0):
        return (N + 1, 0)

    # ルール2: indexの空きがないが次のindex_subが0
    if N + 1 == M and m == 0:
        X = N
        x = n + (max_index_sub - n) // (l + 1)
        x = min(int(x), max_index_sub)
        return (X, x)

    # ルール3: N = M の場合（同一index内）
    X = N
    x = n + (m - n) // (l + 1)
    x = min(int(x), max_index_sub)
    return (X, x)


def format_index_filename(
    index: int,
    index_sub: Optional[int],
    text: str,
    extension: str,
    index_digits: int = 3,
    index_sub_digits: int = 3,
    max_text_length: int = None
) -> str:
    """
    index, index_subからファイル名を生成する。

    Args:
        index: メインindex
        index_sub: サブindex（0またはNoneの場合は省略）
        text: セグメントのテキスト
        extension: ファイル拡張子
        index_digits: indexの桁数
        index_sub_digits: index_subの桁数
        max_text_length: テキスト部分の最大長

    Returns:
        生成されたファイル名
    """
    # Ensure extension has leading dot
    if not extension.startswith('.'):
        extension = '.' + extension

    # indexを桁数に合わせてフォーマット
    index_str = str(index).zfill(index_digits)

    # index_subが0またはNoneの場合は省略
    if index_sub and index_sub != 0:
        index_sub_str = str(index_sub).zfill(index_sub_digits)
        index_part = f"{index_str}-{index_sub_str}"
    else:
        index_part = index_str

    # テキスト部分をサニタイズ
    text_part = sanitize_filename(text, max_text_length)

    return f"{index_part}_{text_part}{extension}"


def format_index_string(
    index: int,
    index_sub: Optional[int],
    index_digits: int = 3,
    index_sub_digits: int = 3
) -> str:
    """
    indexとindex_subをフォーマットされた文字列に変換する。
    テンプレート変数{index}の展開に使用する。

    Args:
        index: メインindex
        index_sub: サブindex（0またはNoneの場合は省略）
        index_digits: indexの桁数
        index_sub_digits: index_subの桁数

    Returns:
        フォーマットされたindex文字列（例: "001", "001-500"）
    """
    # indexを桁数に合わせてフォーマット
    index_str = str(index).zfill(index_digits)

    # index_subが0またはNoneの場合は省略
    if index_sub and index_sub != 0:
        index_sub_str = str(index_sub).zfill(index_sub_digits)
        return f"{index_str}-{index_sub_str}"
    else:
        return index_str


def expand_filename_template(
    template: str,
    index: int,
    index_sub: Optional[int],
    text: str,
    extension: str,
    index_digits: int = 3,
    index_sub_digits: int = 3,
    max_text_length: int = None
) -> str:
    """
    ファイル名テンプレートを展開する。

    Args:
        template: ファイル名テンプレート（例: "{index}_{basename}"）
        index: メインindex
        index_sub: サブindex（0またはNoneの場合は省略）
        text: セグメントのテキスト
        extension: ファイル拡張子（先頭のドットあり）
        index_digits: indexの桁数
        index_sub_digits: index_subの桁数
        max_text_length: テキスト部分の最大長

    Returns:
        展開されたファイル名
    """
    # Ensure extension has leading dot
    if not extension.startswith('.'):
        extension = '.' + extension

    # {index}を展開
    index_str = format_index_string(index, index_sub, index_digits, index_sub_digits)

    # {basename}を展開（サニタイズ済みtext + 拡張子）
    text_part = sanitize_filename(text, max_text_length)
    basename = f"{text_part}{extension}"

    # テンプレートを展開
    result = template.replace("{index}", index_str)
    result = result.replace("{basename}", basename)

    # テンプレートに拡張子が含まれていない場合は追加
    if not result.endswith(extension):
        result += extension

    return result


def migrate_old_index(old_index: int) -> Tuple[int, int]:
    """
    旧形式のindex（整数のみ）を新形式に変換する。

    Args:
        old_index: 旧形式のindex

    Returns:
        (index, index_sub) のタプル
    """
    return (old_index, 0)


def find_available_port(start_port: int = 5000, max_attempts: int = 100) -> int:
    """指定ポートから順に空きポートを探索して返す。

    Args:
        start_port: 探索開始ポート番号
        max_attempts: 最大試行回数

    Returns:
        利用可能なポート番号

    Raises:
        RuntimeError: 空きポートが見つからない場合
    """
    import socket
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"ポート {start_port}〜{start_port + max_attempts - 1} は全て使用中です"
    )
