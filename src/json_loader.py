"""JSON file loading and validation for split-from-json mode."""
import json
from pathlib import Path
from typing import Dict, List, Any


def load_transcript_json(json_path: str) -> Dict[str, Any]:
    """
    Load and validate transcript JSON file.

    Args:
        json_path: Path to transcript.json file

    Returns:
        Dictionary containing transcript data

    Raises:
        FileNotFoundError: If JSON file doesn't exist
        ValueError: If JSON format is invalid
    """
    json_file = Path(json_path)

    if not json_file.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Validate required fields
    if "source_file" not in data:
        raise ValueError("JSON missing 'source_file' field")
    if "segments" not in data:
        raise ValueError("JSON missing 'segments' field")
    if not isinstance(data["segments"], list):
        raise ValueError("'segments' must be a list")

    return data


def segments_to_whisper_format(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert transcript JSON segments to Whisper-compatible format.

    Args:
        segments: List of segment dictionaries from transcript.json

    Returns:
        List of segments in Whisper format (with start, end, text)
    """
    whisper_segments = []

    for seg in segments:
        # Validate required fields
        if "start" not in seg or "end" not in seg or "text" not in seg:
            raise ValueError(f"Segment missing required fields: {seg}")

        whisper_segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"]
        })

    return whisper_segments
