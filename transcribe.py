"""Transcribe audio file using Whisper."""
from pathlib import Path
import sys

from src.cli import parse_transcribe_args
from src.transcribe import Transcriber
from src.splitter import AudioSplitter
from src.utils import calculate_index_digits


def main():
    """Main transcription pipeline."""
    print("=" * 60)
    print("Audio Transcription Tool")
    print("=" * 60)

    # Parse arguments
    try:
        args = parse_transcribe_args()
    except SystemExit:
        return 1

    input_file = Path(args.input_file)

    # Generate default output directory
    if args.output_dir is None:
        output_dir = str(input_file.parent / f"{input_file.stem}_generated")
    else:
        output_dir = args.output_dir

    output_path = Path(output_dir)

    print(f"\nInput file: {input_file}")
    print(f"Model: {args.model}")
    print(f"Output directory: {output_dir}")

    # Check if transcript.json already exists
    transcript_path = output_path / "transcript.json"
    if transcript_path.exists():
        print(f"\n[ERROR] transcript.json already exists in: {output_dir}", file=sys.stderr)
        print("Please remove it or use a different output directory.", file=sys.stderr)
        return 1

    try:
        # Step 1: Initialize transcriber
        print("\n" + "-" * 40)
        print("Loading Whisper model...")
        print("-" * 40)

        transcriber = Transcriber(
            model_name=args.model,
            language=args.language,
            device=args.device
        )

        # Display device info
        if transcriber.gpu_name:
            print(f"Using GPU: {transcriber.gpu_name}")
        else:
            print("Using CPU")
        print(f"Model: {transcriber.model_name} on {transcriber.device}")

        # Step 2: Transcribe
        print("\n" + "-" * 40)
        print(f"Transcribing: {input_file.name}")
        print("-" * 40)

        result = transcriber.transcribe(str(input_file))
        segments = transcriber.get_segments(result)

        print(f"Found {len(segments)} speech segments")

        if not segments:
            print("\nNo speech segments detected. Exiting.")
            return 0

        # Step 3: Generate metadata in new format
        print("\n" + "-" * 40)
        print("Generating metadata...")
        print("-" * 40)

        # Calculate index_digits if not provided
        index_digits = args.index_digits
        if index_digits is None:
            index_digits = calculate_index_digits(len(segments))

        # Build output_format
        output_format = {
            "index_digits": index_digits,
            "index_sub_digits": args.index_sub_digits,
            "filename_template": args.filename_template,
            "margin": {
                "before": args.margin_before,
                "after": args.margin_after
            }
        }

        splitter = AudioSplitter(
            audio_path=str(input_file),
            output_dir=output_dir,
            margin_before=args.margin_before,
            margin_after=args.margin_after,
        )

        # Convert segments to dict format with IDs (for edit_segments.json)
        edit_segments = {}
        for i, seg in enumerate(segments, start=1):
            edit_segments[str(i)] = {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
            }

        # Save transcript.json with empty segments (new format)
        splitter.save_metadata(segments={}, output_format=output_format)

        # Save edit_segments.json with all segments
        splitter.save_edit_segments(edit_segments)

        # Summary
        print("\n" + "=" * 60)
        print("Transcription Complete!")
        print("=" * 60)
        print(f"Total segments: {len(segments)}")
        print(f"Output directory: {Path(output_dir).absolute()}")
        print(f"Files created:")
        print(f"  - transcript.json (settings only)")
        print(f"  - edit_segments.json (all segments)")
        print("\nNext step:")
        print(f"  uv run python edit.py {output_dir}")

        return 0

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
