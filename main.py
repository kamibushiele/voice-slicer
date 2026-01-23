"""Main entry point for audio transcription and splitting tool."""
from pathlib import Path
import sys

from src.cli import parse_args
from src.transcribe import Transcriber
from src.splitter import AudioSplitter
from src.json_loader import load_transcript_json, segments_to_whisper_format


def main():
    """Main processing pipeline."""
    print("=" * 60)
    print("Audio Transcription and Splitting Tool")
    print("=" * 60)

    # Parse command-line arguments
    try:
        args = parse_args()
    except SystemExit:
        return 1

    input_file = Path(args.input_file)

    try:
        # Auto-detect JSON mode from file extension
        is_json_file = input_file.suffix.lower() == '.json'

        # Mode 1: Split from existing JSON (auto-detected or explicit flag)
        if args.from_json or is_json_file:
            return process_from_json(input_file, args)

        # Mode 2: Transcribe only (no splitting)
        elif args.transcribe_only:
            return process_transcribe_only(input_file, args)

        # Mode 3: Normal mode (transcribe + split)
        else:
            return process_normal(input_file, args)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def process_normal(input_file: Path, args) -> int:
    """Normal mode: Transcribe and split audio."""
    # Generate default output directory from input filename (in same directory as input)
    if args.output_dir is None:
        output_dir = str(input_file.parent / f"{input_file.stem}_generated")
    else:
        output_dir = args.output_dir

    print(f"\nMode: Normal (transcribe + split)")
    print(f"Input file: {input_file}")
    print(f"Model: {args.model}")
    print(f"Output directory: {output_dir}")

    # Step 1: Transcribe audio
    print("\n" + "=" * 60)
    print("Step 1: Transcribing audio")
    print("=" * 60)

    transcriber = Transcriber(
        model_name=args.model,
        language=args.language,
        device=args.device
    )
    result = transcriber.transcribe(str(input_file))
    segments = transcriber.get_segments(result)

    print(f"[OK] Found {len(segments)} speech segments")

    if not segments:
        print("\nNo speech segments detected. Exiting.")
        return 0

    # Step 2: Split and save audio segments
    print("\n" + "=" * 60)
    print("Step 2: Splitting audio")
    print("=" * 60)

    splitter = AudioSplitter(
        audio_path=str(input_file),
        output_dir=output_dir,
        margin_before=args.margin_before,
        margin_after=args.margin_after,
        max_filename_length=args.max_filename_length,
    )

    metadata = splitter.split_and_save(segments)
    splitter.save_metadata(metadata)

    # Step 3: Generate cue sheet
    print("\n" + "=" * 60)
    print("Step 3: Generating cue sheet")
    print("=" * 60)

    cuesheet_files = splitter.save_cuesheet(metadata, args.cue_format)

    # Step 4: Summary
    print("\n" + "=" * 60)
    print("Processing Complete!")
    print("=" * 60)
    print(f"[OK] Total segments: {len(metadata)}")
    print(f"[OK] Output directory: {Path(output_dir).absolute()}")
    print(f"[OK] Metadata file: transcript.json")
    print(f"[OK] Cue sheet(s): {len(cuesheet_files)} file(s) generated")

    # Show sample outputs
    print("\nSample output files:")
    for item in metadata[:5]:
        print(f"  - {item['filename']}")
    if len(metadata) > 5:
        print(f"  ... and {len(metadata) - 5} more files")

    return 0


def process_transcribe_only(input_file: Path, args) -> int:
    """Transcribe-only mode: Only generate JSON, no audio splitting."""
    # Generate default output directory from input filename (in same directory as input)
    if args.output_dir is None:
        output_dir = str(input_file.parent / f"{input_file.stem}_generated")
    else:
        output_dir = args.output_dir

    print(f"\nMode: Transcribe only (no splitting)")
    print(f"Input file: {input_file}")
    print(f"Model: {args.model}")
    print(f"Output directory: {output_dir}")

    # Step 1: Transcribe audio
    print("\n" + "=" * 60)
    print("Step 1: Transcribing audio")
    print("=" * 60)

    transcriber = Transcriber(
        model_name=args.model,
        language=args.language,
        device=args.device
    )
    result = transcriber.transcribe(str(input_file))
    segments = transcriber.get_segments(result)

    print(f"[OK] Found {len(segments)} speech segments")

    if not segments:
        print("\nNo speech segments detected. Exiting.")
        return 0

    # Step 2: Generate metadata only (no splitting)
    print("\n" + "=" * 60)
    print("Step 2: Generating metadata")
    print("=" * 60)

    splitter = AudioSplitter(
        audio_path=str(input_file),
        output_dir=output_dir,
        margin_before=args.margin_before,
        margin_after=args.margin_after,
        max_filename_length=args.max_filename_length,
    )

    metadata = splitter.generate_metadata_only(segments)
    splitter.save_metadata(metadata)

    # Step 3: Summary
    print("\n" + "=" * 60)
    print("Transcription Complete!")
    print("=" * 60)
    print(f"[OK] Total segments: {len(metadata)}")
    print(f"[OK] Output directory: {Path(output_dir).absolute()}")
    print(f"[OK] Metadata file: transcript.json")
    print("\nNext step: Edit transcript.json if needed, then run:")
    print(f"  uv run python main.py {Path(output_dir) / 'transcript.json'}")

    return 0


def process_from_json(json_file: Path, args) -> int:
    """From-JSON mode: Split audio from existing JSON file."""
    # If output_dir is not specified, use JSON file's directory
    if args.output_dir is None:
        output_dir = str(json_file.parent)
    else:
        output_dir = args.output_dir

    print(f"\nMode: Split from JSON")
    print(f"JSON file: {json_file}")
    print(f"Output directory: {output_dir}")

    # Step 1: Load JSON
    print("\n" + "=" * 60)
    print("Step 1: Loading JSON")
    print("=" * 60)

    data = load_transcript_json(str(json_file))
    source_audio = Path(data["source_file"])

    print(f"[OK] Loaded {len(data['segments'])} segments")
    print(f"[OK] Source audio: {source_audio}")

    # Verify source audio exists
    if not source_audio.exists():
        print(f"\n[ERROR] Source audio file not found: {source_audio}")
        print("Please ensure the audio file exists at the path specified in transcript.json")
        return 1

    segments = segments_to_whisper_format(data["segments"])

    # Step 2: Split audio
    print("\n" + "=" * 60)
    print("Step 2: Splitting audio")
    print("=" * 60)

    splitter = AudioSplitter(
        audio_path=str(source_audio),
        output_dir=output_dir,
        margin_before=args.margin_before,
        margin_after=args.margin_after,
        max_filename_length=args.max_filename_length,
    )

    metadata = splitter.split_and_save(segments)
    splitter.save_metadata(metadata)

    # Step 3: Generate cue sheet
    print("\n" + "=" * 60)
    print("Step 3: Generating cue sheet")
    print("=" * 60)

    cuesheet_files = splitter.save_cuesheet(metadata, args.cue_format)

    # Step 4: Summary
    print("\n" + "=" * 60)
    print("Processing Complete!")
    print("=" * 60)
    print(f"[OK] Total segments: {len(metadata)}")
    print(f"[OK] Output directory: {Path(output_dir).absolute()}")
    print(f"[OK] Cue sheet(s): {len(cuesheet_files)} file(s) generated")

    # Show sample outputs
    print("\nSample output files:")
    for item in metadata[:5]:
        print(f"  - {item['filename']}")
    if len(metadata) > 5:
        print(f"  ... and {len(metadata) - 5} more files")

    return 0


if __name__ == "__main__":
    sys.exit(main())
