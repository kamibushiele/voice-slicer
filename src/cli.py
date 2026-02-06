"""Command-line interface argument parsers."""
import argparse
import sys
from pathlib import Path


def _extract_positional_arg():
    """Extract first positional argument handling quotes."""
    if len(sys.argv) > 1:
        potential_input = sys.argv[1]
        if potential_input and not potential_input.startswith('--'):
            if potential_input.startswith('"') and potential_input.endswith('"'):
                return potential_input[1:-1]
            return potential_input
    return None


def _clean_path(path: str) -> str:
    """Remove surrounding quotes from path."""
    path = path.strip()
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    return path


def parse_transcribe_args():
    """
    Parse arguments for transcribe.py.

    Returns:
        Parsed arguments namespace with: input_file, model, language, output_dir, device,
        index_digits, index_sub_digits, filename_template, margin_before, margin_after
    """
    input_from_argv = _extract_positional_arg()

    parser = argparse.ArgumentParser(
        description="Transcribe audio file using Whisper and generate transcript.json."
    )

    parser.add_argument(
        "input_file",
        type=str,
        help="Path to input audio file"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)"
    )

    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language code (e.g., 'ja' for Japanese, 'en' for English). Auto-detect if not specified."
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory path (default: {input_filename}_generated/)"
    )

    parser.add_argument(
        "--device",
        type=str,
        default=None,
        choices=["cuda", "cpu"],
        help="Device to use for transcription: cuda (GPU) or cpu. Auto-detect if not specified."
    )

    parser.add_argument(
        "--index-digits",
        type=int,
        default=None,
        help="Number of digits for index (default: auto-calculated from segment count)"
    )

    parser.add_argument(
        "--index-sub-digits",
        type=int,
        default=3,
        help="Number of digits for sub-index (default: 3)"
    )

    parser.add_argument(
        "--filename-template",
        type=str,
        default="{index}_{basename}",
        help="Filename template (default: {index}_{basename})"
    )

    parser.add_argument(
        "--margin-before",
        type=float,
        default=0.1,
        help="Margin in seconds before segment start (default: 0.1)"
    )

    parser.add_argument(
        "--margin-after",
        type=float,
        default=0.2,
        help="Margin in seconds after segment end (default: 0.2)"
    )

    args = parser.parse_args()

    # Use input file extracted from sys.argv if available
    if input_from_argv:
        args.input_file = input_from_argv
    else:
        args.input_file = _clean_path(args.input_file)

    # Validate input file exists
    if not Path(args.input_file).exists():
        parser.error(f"Input file not found: {args.input_file}")

    return args


def parse_split_args():
    """
    Parse arguments for split.py.

    Returns:
        Parsed arguments namespace with: output_dir, max_filename_length, force
    """
    input_from_argv = _extract_positional_arg()

    parser = argparse.ArgumentParser(
        description="Split audio into segments based on transcript.json and edit_segments.json."
    )

    parser.add_argument(
        "output_dir",
        type=str,
        help="Output directory containing transcript.json"
    )

    parser.add_argument(
        "--max-filename-length",
        type=int,
        default=None,
        help="Maximum length of generated filenames (default: None, respects OS limit)"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force export all segments (ignore diff)"
    )

    args = parser.parse_args()

    # Use output_dir extracted from sys.argv if available
    if input_from_argv:
        args.output_dir = input_from_argv
    else:
        args.output_dir = _clean_path(args.output_dir)

    # Validate output directory exists
    output_path = Path(args.output_dir)
    if not output_path.exists():
        parser.error(f"Output directory not found: {args.output_dir}")

    # Validate transcript.json exists (required for new format)
    transcript_path = output_path / "transcript.json"
    if not transcript_path.exists():
        # Check for old format files for migration
        unexported_path = output_path / "transcript_unexported.json"
        if unexported_path.exists():
            pass  # Will be migrated during loading
        else:
            parser.error(f"transcript.json not found in: {args.output_dir}")

    return args


def parse_edit_args():
    """
    Parse arguments for edit.py (GUI).

    Returns:
        Parsed arguments namespace with: output_dir, port, no_browser
    """
    input_from_argv = _extract_positional_arg()

    parser = argparse.ArgumentParser(
        description="Edit transcript.json with GUI and export audio segments."
    )

    parser.add_argument(
        "output_dir",
        type=str,
        help="Output directory containing transcript.json"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port for the web server (default: 5000)"
    )

    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically"
    )

    args = parser.parse_args()

    # Use output_dir extracted from sys.argv if available
    if input_from_argv:
        args.output_dir = input_from_argv
    else:
        args.output_dir = _clean_path(args.output_dir)

    # Validate output directory exists
    output_path = Path(args.output_dir)
    if not output_path.exists():
        parser.error(f"Output directory not found: {args.output_dir}")

    # Validate transcript.json exists
    transcript_path = output_path / "transcript.json"
    unexported_path = output_path / "transcript_unexported.json"
    if not transcript_path.exists() and not unexported_path.exists():
        parser.error(f"transcript.json not found in: {args.output_dir}")

    return args


def parse_export_edit_args():
    """
    Parse arguments for export_edit.py.

    Returns:
        Parsed arguments namespace with: output_dir
    """
    input_from_argv = _extract_positional_arg()

    parser = argparse.ArgumentParser(
        description="Generate edit_segments.json with all segment data for manual editing."
    )

    parser.add_argument(
        "output_dir",
        type=str,
        help="Output directory containing transcript.json"
    )

    args = parser.parse_args()

    # Use output_dir extracted from sys.argv if available
    if input_from_argv:
        args.output_dir = input_from_argv
    else:
        args.output_dir = _clean_path(args.output_dir)

    # Validate output directory exists
    output_path = Path(args.output_dir)
    if not output_path.exists():
        parser.error(f"Output directory not found: {args.output_dir}")

    # Validate transcript.json exists
    transcript_path = output_path / "transcript.json"
    if not transcript_path.exists():
        parser.error(f"transcript.json not found in: {args.output_dir}")

    return args
