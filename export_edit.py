"""Generate edit_segments.json for manual editing."""
from pathlib import Path
import sys

from src.cli import parse_export_edit_args
from src.splitter import AudioSplitter
from src.json_loader import load_transcript_json


def main():
    """Main export_edit pipeline."""
    print("=" * 60)
    print("Export edit_segments.json for Manual Editing")
    print("=" * 60)

    # Parse arguments
    try:
        args = parse_export_edit_args()
    except SystemExit:
        return 1

    output_dir = Path(args.output_dir)

    print(f"\nOutput directory: {output_dir}")

    try:
        # Load transcript.json
        print("\n" + "-" * 40)
        print("Loading transcript.json...")
        print("-" * 40)

        transcript_path = output_dir / "transcript.json"
        transcript_data = load_transcript_json(str(transcript_path))

        segments = transcript_data.get("segments", {})
        source_file = transcript_data.get("source_file", "")

        print(f"Source audio: {source_file}")
        print(f"Total segments: {len(segments)}")

        if not segments:
            print("\n[WARNING] No segments found in transcript.json")
            print("Nothing to export.")
            return 0

        # Generate edit_segments.json
        print("\n" + "-" * 40)
        print("Generating edit_segments.json...")
        print("-" * 40)

        splitter = AudioSplitter(
            audio_path=source_file,
            output_dir=str(output_dir),
        )

        edit_path = splitter.generate_full_edit_segments(segments)

        # Summary
        print("\n" + "=" * 60)
        print("Export Complete!")
        print("=" * 60)
        print(f"Generated: {edit_path}")
        print(f"Segments: {len(segments)}")
        print("\nYou can now edit the file manually.")
        print("Run 'uv run split.py' to apply changes after editing.")

        return 0

    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
