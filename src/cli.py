"""Command-line interface argument parser."""
import argparse
import sys
from pathlib import Path


def parse_args():
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    # Extract input file from sys.argv before argparse processes it
    # This handles file paths with spaces and special characters correctly
    input_file_from_argv = None
    if len(sys.argv) > 1:
        # First positional argument should be the input file
        # It could be wrapped in quotes which we need to handle
        potential_input = sys.argv[1]
        if potential_input and not potential_input.startswith('--'):
            # Remove surrounding quotes if present
            if (potential_input.startswith('"') and potential_input.endswith('"')):
                input_file_from_argv = potential_input[1:-1]
            else:
                input_file_from_argv = potential_input

    parser = argparse.ArgumentParser(
        description="Transcribe and split audio files into separate clips based on speech segments."
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
        "--max-filename-length",
        type=int,
        default=None,
        help="Maximum length of generated filenames (default: None, respects OS limit). Useful for shortening long filenames."
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

    parser.add_argument(
        "--transcribe-only",
        action="store_true",
        help="Only transcribe audio and generate JSON (no audio splitting)"
    )

    parser.add_argument(
        "--from-json",
        action="store_true",
        help="Split audio from existing JSON file (skips transcription)"
    )

    parser.add_argument(
        "--device",
        type=str,
        default=None,
        choices=["cuda", "cpu"],
        help="Device to use for transcription: cuda (GPU) or cpu. Auto-detect if not specified."
    )

    args = parser.parse_args()

    # Use input file extracted from sys.argv if available, otherwise use argparse result
    if input_file_from_argv:
        args.input_file = input_file_from_argv
    else:
        # Clean up input file path: remove surrounding quotes if present
        input_file = args.input_file.strip()
        if (input_file.startswith('"') and input_file.endswith('"')):
            input_file = input_file[1:-1]
        args.input_file = input_file

    # Validate input file exists
    if not Path(args.input_file).exists():
        parser.error(f"Input file not found: {args.input_file}")

    # Validate mode conflicts
    if args.transcribe_only and args.from_json:
        parser.error("Cannot use --transcribe-only and --from-json together")

    return args
