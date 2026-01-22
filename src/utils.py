"""Utility functions for file handling and text processing."""
import re
from pathlib import Path
from typing import List, Dict, Any


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
