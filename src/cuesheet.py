"""Cue sheet generation for various formats."""
import csv
from pathlib import Path
from typing import List, Dict, Any
from .utils import format_timestamp


def format_srt_timestamp(seconds: float) -> str:
    """
    Format seconds to SRT timestamp format (HH:MM:SS,mmm).

    Args:
        seconds: Time in seconds

    Returns:
        SRT formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_vtt_timestamp(seconds: float) -> str:
    """
    Format seconds to WebVTT timestamp format (HH:MM:SS.mmm).

    Args:
        seconds: Time in seconds

    Returns:
        VTT formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def generate_csv(metadata: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Generate CSV format cue sheet.

    Args:
        metadata: List of segment metadata dictionaries
        output_path: Output file path
    """
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Index', 'Start', 'End', 'Duration', 'Text', 'Filename'])

        for item in metadata:
            duration = item['end'] - item['start']
            writer.writerow([
                item['index'],
                format_timestamp(item['start']),
                format_timestamp(item['end']),
                f"{duration:.3f}",
                item['text'],
                item['filename']
            ])


def generate_tsv(metadata: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Generate TSV format cue sheet.

    Args:
        metadata: List of segment metadata dictionaries
        output_path: Output file path
    """
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(['Index', 'Start', 'End', 'Duration', 'Text', 'Filename'])

        for item in metadata:
            duration = item['end'] - item['start']
            writer.writerow([
                item['index'],
                format_timestamp(item['start']),
                format_timestamp(item['end']),
                f"{duration:.3f}",
                item['text'],
                item['filename']
            ])


def generate_srt(metadata: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Generate SRT (SubRip) format cue sheet for video editing software.

    Args:
        metadata: List of segment metadata dictionaries
        output_path: Output file path
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in metadata:
            # Sequence number
            f.write(f"{item['index']}\n")

            # Timecode
            start_time = format_srt_timestamp(item['start'])
            end_time = format_srt_timestamp(item['end'])
            f.write(f"{start_time} --> {end_time}\n")

            # Text
            f.write(f"{item['text']}\n")

            # Blank line separator
            f.write("\n")


def generate_vtt(metadata: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Generate WebVTT format cue sheet for web video players.

    Args:
        metadata: List of segment metadata dictionaries
        output_path: Output file path
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        # VTT header
        f.write("WEBVTT\n\n")

        for item in metadata:
            # Timecode
            start_time = format_vtt_timestamp(item['start'])
            end_time = format_vtt_timestamp(item['end'])
            f.write(f"{start_time} --> {end_time}\n")

            # Text
            f.write(f"{item['text']}\n")

            # Blank line separator
            f.write("\n")


def generate_cuesheet(
    metadata: List[Dict[str, Any]],
    output_dir: Path,
    formats: List[str]
) -> List[Path]:
    """
    Generate cue sheets in specified formats.

    Args:
        metadata: List of segment metadata dictionaries
        output_dir: Output directory
        formats: List of format names ('csv', 'tsv', 'srt', 'vtt')

    Returns:
        List of generated file paths
    """
    generated_files = []

    format_generators = {
        'csv': (generate_csv, 'cuesheet.csv'),
        'tsv': (generate_tsv, 'cuesheet.tsv'),
        'srt': (generate_srt, 'cuesheet.srt'),
        'vtt': (generate_vtt, 'cuesheet.vtt'),
    }

    for fmt in formats:
        if fmt in format_generators:
            generator_func, filename = format_generators[fmt]
            output_path = output_dir / filename
            generator_func(metadata, output_path)
            generated_files.append(output_path)

    return generated_files
