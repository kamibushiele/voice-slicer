"""Split audio into segments based on transcript.json and edit_segments.json."""
from pathlib import Path
import sys
import json

from src.cli import parse_split_args
from src.splitter import AudioSplitter
from src.json_loader import (
    load_transcript_json,
    load_edit_segments,
    merge_segments,
)
from src.utils import calculate_index_digits


def load_and_merge_segments(output_dir: Path) -> tuple[dict, dict, dict]:
    """
    Load transcript.json and edit_segments.json, then merge segments.

    Args:
        output_dir: Output directory path

    Returns:
        (merged_segments, transcript_data, edit_segments_data)
    """
    transcript_path = output_dir / "transcript.json"
    edit_segments_path = output_dir / "edit_segments.json"

    # Load transcript.json (required)
    if not transcript_path.exists():
        # Check for old format and migrate
        unexported_path = output_dir / "transcript_unexported.json"
        if unexported_path.exists():
            # Load and migrate old format
            transcript_data = load_transcript_json(str(unexported_path))
            # Save as new format
            with open(transcript_path, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, ensure_ascii=False, indent=2)
            # Rename old file
            unexported_path.rename(output_dir / "transcript_unexported.json.bak")
            print("Migrated old format to new format")
        else:
            raise FileNotFoundError(f"transcript.json not found in: {output_dir}")
    else:
        transcript_data = load_transcript_json(str(transcript_path))

    # Load edit_segments.json if exists
    edit_segments_data = {"version": 2, "segments": {}}
    if edit_segments_path.exists():
        edit_segments_data = load_edit_segments(str(edit_segments_path))

    # Merge segments
    merged = merge_segments(
        transcript_data.get("segments", {}),
        edit_segments_data.get("segments", {})
    )

    return merged, transcript_data, edit_segments_data


def main():
    """Main splitting pipeline."""
    print("=" * 60)
    print("Audio Splitting Tool")
    print("=" * 60)

    # Parse arguments
    try:
        args = parse_split_args()
    except SystemExit:
        return 1

    output_dir = Path(args.output_dir)
    force_export = args.force

    print(f"\nOutput directory: {output_dir}")
    if force_export:
        print("Mode: Force export (all segments)")
    else:
        print("Mode: Diff export (changed segments only)")

    try:
        # Step 1: Load and merge JSON files
        print("\n" + "-" * 40)
        print("Loading transcript JSON...")
        print("-" * 40)

        merged_segments, transcript_data, edit_segments_data = load_and_merge_segments(output_dir)

        source_audio = Path(transcript_data["source_file"])
        output_format = transcript_data.get("output_format", {})

        print(f"Source audio: {source_audio}")
        print(f"Total segments (merged): {len(merged_segments)}")

        # Verify source audio exists
        if not source_audio.exists():
            print(f"\n[ERROR] Source audio file not found: {source_audio}")
            print("Please ensure the audio file exists at the path specified in transcript.json")
            return 1

        # Get settings from output_format
        index_digits = output_format.get("index_digits")
        if index_digits is None:
            index_digits = calculate_index_digits(len(merged_segments))

        index_sub_digits = output_format.get("index_sub_digits", 3)
        margin_before = output_format.get("margin", {}).get("before", 0.1)
        margin_after = output_format.get("margin", {}).get("after", 0.2)

        # Step 2: Split audio with diff
        print("\n" + "-" * 40)
        if force_export:
            print("Exporting all segments...")
        else:
            print("Calculating diff and exporting...")
        print("-" * 40)

        splitter = AudioSplitter(
            audio_path=str(source_audio),
            output_dir=str(output_dir),
            margin_before=margin_before,
            margin_after=margin_after,
            max_filename_length=args.max_filename_length,
        )

        result = splitter.export_diff(
            merged_segments=merged_segments,
            previous_segments=transcript_data.get("segments", {}),
            edit_segments=edit_segments_data.get("segments", {}),
            index_digits=index_digits,
            index_sub_digits=index_sub_digits,
            force=force_export
        )

        # Step 3: Save transcript.json and remove edit_segments.json
        print("\n" + "-" * 40)
        print("Saving transcript.json...")
        print("-" * 40)

        # Update output_format with calculated index_digits
        output_format["index_digits"] = index_digits
        output_format["index_sub_digits"] = index_sub_digits

        splitter.save_metadata(
            segments=result["segments"],
            output_format=output_format
        )



        # Summary
        print("\n" + "=" * 60)
        print("Splitting Complete!")
        print("=" * 60)
        print(f"Total segments: {len(result['segments'])}")

        if result["exported"]:
            print(f"Exported: {len(result['exported'])} files")
        if result["renamed"]:
            print(f"Renamed: {len(result['renamed'])} files")
        if result["deleted"]:
            print(f"Deleted: {len(result['deleted'])} files")
        if result["skipped"] > 0:
            print(f"Skipped (no changes): {result['skipped']} files")

        if not result["exported"] and not result["renamed"] and not result["deleted"]:
            print("No changes detected.")

        print(f"\nOutput directory: {output_dir.absolute()}")

        # Show sample outputs
        if result["exported"]:
            print("\nExported files:")
            for filename in result["exported"][:5]:
                print(f"  - {filename}")
            if len(result["exported"]) > 5:
                print(f"  ... and {len(result['exported']) - 5} more files")

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
