"""JSON file loading and validation for split-from-json mode."""
import json
from pathlib import Path
from typing import Dict, List, Any


def load_transcript_json(json_path: str, auto_migrate: bool = True) -> Dict[str, Any]:
    """
    Load and validate transcript JSON file.
    Supports both old format (version undefined, array-based) and new format (version 2, object-based).

    Args:
        json_path: Path to transcript.json file
        auto_migrate: If True, automatically migrate old format to new format

    Returns:
        Dictionary containing transcript data in new format (version 2)

    Raises:
        FileNotFoundError: If JSON file doesn't exist
        ValueError: If JSON format is invalid
    """
    json_file = Path(json_path)

    if not json_file.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check version
    version = data.get("version")

    if version is None:
        # Old format - migrate if requested
        if auto_migrate:
            return migrate_transcript(data)
        else:
            # Validate old format
            if "source_file" not in data:
                raise ValueError("JSON missing 'source_file' field")
            if "segments" not in data:
                raise ValueError("JSON missing 'segments' field")
            if not isinstance(data["segments"], list):
                raise ValueError("'segments' must be a list")
            return data
    elif version == 2:
        # New format - validate
        validate_transcript_v2(data)
        return data
    else:
        raise ValueError(f"Unsupported JSON version: {version}")


def migrate_transcript(old_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate old format transcript to new format (version 2).

    Args:
        old_data: Old format data (array-based segments)

    Returns:
        New format data (object-based segments with version 2)
    """
    # Convert array to object (ID is 1-indexed)
    segments = {}
    for i, seg in enumerate(old_data.get("segments", []), start=1):
        segments[str(i)] = {
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"],
            "index": seg.get("index"),
            "index_sub": seg.get("index_sub"),
        }
        # filename is not included (will be recalculated)

    return {
        "version": 2,
        "source_file": old_data["source_file"],
        "output_format": {
            "index_digits": old_data.get("index_digits", 3),
            "index_sub_digits": 3,
            "filename_template": "{index}_{basename}",
            "margin": {
                "before": 0.1,
                "after": 0.2
            }
        },
        "segments": segments
    }


def validate_transcript_v2(data: Dict[str, Any]) -> None:
    """
    Validate transcript JSON in new format (version 2).

    Args:
        data: Transcript data to validate

    Raises:
        ValueError: If validation fails
    """
    if data.get("version") != 2:
        raise ValueError("Expected version 2")

    if "source_file" not in data:
        raise ValueError("JSON missing 'source_file' field")

    if "segments" not in data:
        raise ValueError("JSON missing 'segments' field")

    if not isinstance(data["segments"], dict):
        raise ValueError("'segments' must be an object (dict)")

    # Validate output_format if present
    if "output_format" in data:
        output_format = data["output_format"]
        if not isinstance(output_format, dict):
            raise ValueError("'output_format' must be an object")

    # Validate each segment
    for seg_id, seg in data["segments"].items():
        if not isinstance(seg, dict):
            raise ValueError(f"Segment '{seg_id}' must be an object")
        if "start" not in seg:
            raise ValueError(f"Segment '{seg_id}' missing 'start' field")
        if "end" not in seg:
            raise ValueError(f"Segment '{seg_id}' missing 'end' field")
        if "text" not in seg:
            raise ValueError(f"Segment '{seg_id}' missing 'text' field")


def load_edit_segments(json_path: str) -> Dict[str, Any]:
    """
    Load edit_segments.json file.

    Args:
        json_path: Path to edit_segments.json file

    Returns:
        Dictionary containing edit segments data

    Raises:
        FileNotFoundError: If JSON file doesn't exist
        ValueError: If JSON format is invalid
    """
    json_file = Path(json_path)

    if not json_file.exists():
        raise FileNotFoundError(f"edit_segments.json not found: {json_path}")

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Validate version
    version = data.get("version")
    if version is None:
        # Old format (transcript_unexported.json) - migrate
        return migrate_edit_segments(data)
    elif version == 2:
        if "segments" not in data:
            raise ValueError("edit_segments.json missing 'segments' field")
        if not isinstance(data["segments"], dict):
            raise ValueError("'segments' must be an object")
        return data
    else:
        raise ValueError(f"Unsupported edit_segments version: {version}")


def migrate_edit_segments(old_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate old format transcript_unexported.json to new format edit_segments.json.

    Args:
        old_data: Old format data (array-based segments)

    Returns:
        New format data (object-based segments with version 2)
    """
    segments = {}
    for i, seg in enumerate(old_data.get("segments", []), start=1):
        segments[str(i)] = {
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"],
        }

    return {
        "version": 2,
        "segments": segments
    }


def merge_segments(
    transcript_segments: Dict[str, Dict[str, Any]],
    edit_segments: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Merge transcript.segments and edit_segments.segments.

    Args:
        transcript_segments: Segments from transcript.json (exported segments)
        edit_segments: Segments from edit_segments.json (all segments)

    Returns:
        Merged segments dictionary
    """
    # edit_segmentsにセグメントがある場合、edit_segmentsを正として使用
    # （transcript.jsonにあってedit_segmentsにないセグメントは削除されたとみなす）
    if edit_segments:
        result = {}
        for seg_id, seg in edit_segments.items():
            result[seg_id] = seg.copy()
        return result

    # edit_segmentsが空の場合、transcript_segmentsをそのまま使用
    result = {}
    for seg_id, seg in transcript_segments.items():
        result[seg_id] = seg.copy()

    return result


def get_next_segment_id(segments: Dict[str, Dict[str, Any]]) -> str:
    """
    Get next available segment ID (max + 1).

    Args:
        segments: Current segments dictionary

    Returns:
        Next segment ID as string
    """
    if not segments:
        return "1"

    max_id = max(int(seg_id) for seg_id in segments.keys())
    return str(max_id + 1)


def segments_to_whisper_format(segments) -> List[Dict[str, Any]]:
    """
    Convert transcript JSON segments to Whisper-compatible format.
    Supports both old format (list) and new format (dict with ID keys).

    Args:
        segments: List or dict of segment dictionaries from transcript.json

    Returns:
        List of segments in Whisper format (with start, end, text)
    """
    whisper_segments = []

    # Handle both old (list) and new (dict) format
    if isinstance(segments, dict):
        # New format: dict with ID keys
        segment_list = list(segments.values())
    else:
        # Old format: list
        segment_list = segments

    for seg in segment_list:
        # Validate required fields
        if "start" not in seg or "end" not in seg or "text" not in seg:
            raise ValueError(f"Segment missing required fields: {seg}")

        whisper_segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"]
        })

    return whisper_segments
