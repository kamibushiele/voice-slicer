"""Audio file splitting based on transcription segments."""
from pathlib import Path
from typing import List, Dict, Any
from pydub import AudioSegment
from tqdm import tqdm
import json

from .utils import sanitize_filename
from .cuesheet import generate_cuesheet


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
        print(f"Loading audio file: {self.audio_path.name}")
        self.audio = AudioSegment.from_file(str(self.audio_path))
        self.audio_duration = len(self.audio)  # in milliseconds

    def split_and_save(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Split audio into segments and save as separate files.

        Args:
            segments: List of segment dictionaries with start, end, text

        Returns:
            List of output file metadata
        """
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

        print(f"\nSplitting audio into {len(segments)} segments...")

        for i, segment in enumerate(tqdm(segments, desc="Processing segments")):
            # Calculate start and end times in milliseconds
            start_ms = max(0, segment["start"] * 1000 - self.margin_before)
            end_ms = min(self.audio_duration, segment["end"] * 1000 + self.margin_after)

            # Extract audio segment
            audio_segment = self.audio[start_ms:end_ms]

            # Generate filename
            file_number = f"{i+1:03d}"
            text_part = sanitize_filename(segment["text"], self.max_filename_length)
            filename = f"{file_number}_{text_part}{file_extension}"
            output_path = self.output_dir / filename

            # Save audio segment
            audio_segment.export(
                str(output_path),
                format=export_format,
            )

            # Store metadata
            metadata = {
                "index": i + 1,
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

        Args:
            segments: List of segment dictionaries with start, end, text

        Returns:
            List of output file metadata
        """
        output_metadata = []
        file_extension = self.audio_path.suffix

        print(f"\nGenerating metadata for {len(segments)} segments...")

        for i, segment in enumerate(segments):
            # Generate filename
            file_number = f"{i+1:03d}"
            text_part = sanitize_filename(segment["text"], self.max_filename_length)
            filename = f"{file_number}_{text_part}{file_extension}"

            # Store metadata
            metadata = {
                "index": i + 1,
                "filename": filename,
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
            }
            output_metadata.append(metadata)

        return output_metadata

    def save_metadata(self, metadata: List[Dict[str, Any]]) -> None:
        """
        Save transcription metadata to JSON file.

        Args:
            metadata: List of segment metadata dictionaries
        """
        metadata_path = self.output_dir / "transcript.json"

        output_data = {
            "source_file": str(self.audio_path),
            "total_segments": len(metadata),
            "segments": metadata,
        }

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"\nMetadata saved to: {metadata_path}")

    def save_cuesheet(self, metadata: List[Dict[str, Any]], formats: str) -> List[Path]:
        """
        Save cue sheet(s) in specified format(s).

        Args:
            metadata: List of segment metadata dictionaries
            formats: Format string (csv, tsv, srt, vtt, or all)

        Returns:
            List of generated cue sheet file paths
        """
        # Parse format string
        if formats.lower() == 'all':
            format_list = ['csv', 'tsv', 'srt', 'vtt']
        else:
            format_list = [fmt.strip().lower() for fmt in formats.split(',')]

        # Generate cue sheets
        generated_files = generate_cuesheet(metadata, self.output_dir, format_list)

        # Print summary
        print(f"\nCue sheet(s) saved:")
        for file_path in generated_files:
            print(f"  - {file_path.name}")

        return generated_files
