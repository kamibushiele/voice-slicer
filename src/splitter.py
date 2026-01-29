"""Audio file splitting based on transcription segments."""
from pathlib import Path
from typing import List, Dict, Any
from pydub import AudioSegment
from tqdm import tqdm
import json

from .utils import (
    format_index_filename,
    determine_index,
    calculate_index_digits,
)


class AudioSplitter:
    """Handles splitting audio files into segments."""

    def __init__(
        self,
        audio_path: str,
        output_dir: str = "output",
        margin_before: float = 0.1,
        margin_after: float = 0.2,
        max_filename_length: int = None,
    ):
        """
        Initialize audio splitter.

        Args:
            audio_path: Path to input audio file
            output_dir: Directory for output files
            margin_before: Seconds to add before segment start
            margin_after: Seconds to add after segment end
            max_filename_length: Maximum filename length (None for no limit)
        """
        self.audio_path = Path(audio_path)
        self.output_dir = Path(output_dir)
        self.margin_before = margin_before * 1000  # Convert to milliseconds
        self.margin_after = margin_after * 1000
        self.max_filename_length = max_filename_length

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load audio file
        self.audio = AudioSegment.from_file(str(self.audio_path))
        self.audio_duration = len(self.audio)  # in milliseconds  # in milliseconds

    def split_and_save(
        self,
        segments: List[Dict[str, Any]],
        index_digits: int = None
    ) -> List[Dict[str, Any]]:
        """
        Split audio into segments and save as separate files.
        Assigns sequential indices (1, 2, 3, ...) to all segments.

        Args:
            segments: List of segment dictionaries with start, end, text
            index_digits: Number of digits for index (calculated from segment count if None)

        Returns:
            List of output file metadata
        """
        # Calculate index_digits if not provided
        if index_digits is None:
            index_digits = calculate_index_digits(len(segments))

        output_metadata = []
        file_extension = self.audio_path.suffix

        # Map file extensions to ffmpeg format names
        format_map = {
            '.m4a': 'ipod',
            '.mp4': 'mp4',
            '.aac': 'adts',
        }

        # Get the correct format name for ffmpeg
        export_format = format_map.get(file_extension.lower(), file_extension.lstrip('.'))

        for i, segment in enumerate(tqdm(segments, desc="Processing segments")):
            # Calculate start and end times in milliseconds
            start_ms = max(0, segment["start"] * 1000 - self.margin_before)
            end_ms = min(self.audio_duration, segment["end"] * 1000 + self.margin_after)

            # Extract audio segment
            audio_segment = self.audio[start_ms:end_ms]

            # Generate filename with sequential index
            index = i + 1
            filename = format_index_filename(
                index=index,
                index_sub=None,
                text=segment["text"],
                extension=file_extension,
                index_digits=index_digits,
                max_text_length=self.max_filename_length,
            )
            output_path = self.output_dir / filename

            # Save audio segment
            audio_segment.export(
                str(output_path),
                format=export_format,
            )

            # Store metadata
            metadata = {
                "index": index,
                "filename": filename,
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
            }
            output_metadata.append(metadata)

        return output_metadata

    def generate_metadata_only(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate metadata without splitting audio (for transcribe-only mode).
        index, index_sub, filename are not set (will be determined at export time).

        Args:
            segments: List of segment dictionaries with start, end, text

        Returns:
            List of output file metadata (without index/filename)
        """
        output_metadata = []

        for segment in segments:
            # Store metadata without index/filename (determined at export time)
            metadata = {
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
            }
            output_metadata.append(metadata)

        return output_metadata

    def save_metadata(
        self,
        metadata: List[Dict[str, Any]],
        unexported: bool = False,
        index_digits: int = None
    ) -> None:
        """
        Save transcription metadata to JSON file.

        Args:
            metadata: List of segment metadata dictionaries
            unexported: If True, save as transcript_unexported.json (for transcribe-only mode)
            index_digits: Number of digits for index (calculated from segment count if None)
        """
        if unexported:
            metadata_path = self.output_dir / "transcript_unexported.json"
        else:
            metadata_path = self.output_dir / "transcript.json"

        # Calculate index_digits if not provided
        if index_digits is None:
            index_digits = calculate_index_digits(len(metadata))

        output_data = {
            "source_file": str(self.audio_path),
            "index_digits": index_digits,
            "segments": metadata,
        }

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

    def export_segment(self, segment: Dict[str, Any], index_digits: int = 3) -> str:
        """
        Export a single segment and return its filename.

        Args:
            segment: Segment dictionary with index, index_sub, start, end, text
            index_digits: Number of digits for index formatting

        Returns:
            Generated filename
        """
        file_extension = self.audio_path.suffix

        format_map = {
            '.m4a': 'ipod',
            '.mp4': 'mp4',
            '.aac': 'adts',
        }
        export_format = format_map.get(file_extension.lower(), file_extension.lstrip('.'))

        # Calculate start and end times in milliseconds
        start_ms = max(0, segment["start"] * 1000 - self.margin_before)
        end_ms = min(self.audio_duration, segment["end"] * 1000 + self.margin_after)

        # Extract audio segment
        audio_segment = self.audio[start_ms:end_ms]

        # Generate filename using index and index_sub
        filename = format_index_filename(
            index=segment["index"],
            index_sub=segment.get("index_sub"),
            text=segment["text"],
            extension=file_extension,
            index_digits=index_digits,
            max_text_length=self.max_filename_length,
        )
        output_path = self.output_dir / filename

        # Save audio segment
        audio_segment.export(
            str(output_path),
            format=export_format,
        )

        return filename

    def rename_file(self, old_filename: str, new_filename: str) -> bool:
        """
        Rename an audio file in the output directory.

        Args:
            old_filename: Current filename
            new_filename: New filename

        Returns:
            True if successful, False if old file doesn't exist
        """
        old_path = self.output_dir / old_filename
        new_path = self.output_dir / new_filename

        if old_path.exists():
            old_path.rename(new_path)
            return True
        return False

    def delete_file(self, filename: str) -> bool:
        """
        Delete an audio file from the output directory.

        Args:
            filename: Filename to delete

        Returns:
            True if successful, False if file doesn't exist
        """
        file_path = self.output_dir / filename
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def generate_filename(self, segment: Dict[str, Any], index_digits: int = 3) -> str:
        """
        Generate filename for a segment without exporting.

        Args:
            segment: Segment dictionary with index, index_sub, text
            index_digits: Number of digits for index formatting

        Returns:
            Generated filename
        """
        file_extension = self.audio_path.suffix
        return format_index_filename(
            index=segment["index"],
            index_sub=segment.get("index_sub"),
            text=segment["text"],
            extension=file_extension,
            index_digits=index_digits,
            max_text_length=self.max_filename_length,
        )

    def assign_indices(
        self,
        segments: List[Dict[str, Any]],
        existing_segments: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Assign index and index_sub to segments that don't have them.
        Segments are sorted by start time before assignment.

        Args:
            segments: List of segment dictionaries (may or may not have index)
            existing_segments: List of existing segments with confirmed indices

        Returns:
            List of segments with index and index_sub assigned
        """
        # Sort segments by start time
        sorted_segments = sorted(segments, key=lambda s: s["start"])

        # Build list of confirmed indices from existing segments
        confirmed = []
        if existing_segments:
            for seg in existing_segments:
                if seg.get("index") is not None and seg.get("filename"):
                    confirmed.append({
                        "index": seg["index"],
                        "index_sub": seg.get("index_sub", 0) or 0,
                        "start": seg["start"],
                    })
        confirmed.sort(key=lambda s: s["start"])

        # Process each segment
        result = []
        for seg in sorted_segments:
            if seg.get("index") is not None and seg.get("filename"):
                # Already has confirmed index
                result.append(seg.copy())
            else:
                # Need to determine index
                seg_copy = seg.copy()

                # Find before and after indices
                before = None
                after = None

                # Check confirmed indices
                for conf in confirmed:
                    if conf["start"] < seg["start"]:
                        before = (conf["index"], conf["index_sub"])
                    elif conf["start"] > seg["start"] and after is None:
                        after = (conf["index"], conf["index_sub"])
                        break

                # Check already processed segments in result
                for r in result:
                    if r.get("index") is not None:
                        if r["start"] < seg["start"]:
                            r_idx = (r["index"], r.get("index_sub", 0) or 0)
                            if before is None or r_idx > before:
                                before = r_idx
                        elif r["start"] > seg["start"]:
                            r_idx = (r["index"], r.get("index_sub", 0) or 0)
                            if after is None or r_idx < after:
                                after = r_idx

                # Determine index
                new_index, new_index_sub = determine_index(before, after)
                seg_copy["index"] = new_index
                seg_copy["index_sub"] = new_index_sub if new_index_sub != 0 else None

                result.append(seg_copy)

        return result
