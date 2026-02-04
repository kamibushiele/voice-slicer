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


def export_diff_v2(
    splitter: AudioSplitter,
    merged_segments: dict,
    previous_segments: dict,
    edit_segments: dict,
    index_digits: int,
    index_sub_digits: int,
    force: bool = False
) -> dict:
    """
    差分ベースで書き出しを行う（新スキーマ対応）。

    Args:
        splitter: AudioSplitterインスタンス
        merged_segments: マージ済みセグメント（ID -> segment）
        previous_segments: 前回書き出し済みセグメント（transcript.json）
        edit_segments: 編集差分セグメント（edit_segments.json）
        index_digits: indexの桁数
        index_sub_digits: index_subの桁数
        force: 強制書き出しフラグ

    Returns:
        結果辞書 (exported, renamed, deleted, skipped, segments)
    """
    deleted_files = []
    renamed_files = []
    exported_files = []
    skipped_count = 0

    # 1. 削除処理: edit_segmentsで"deleted: true"のセグメント
    for seg_id, changes in edit_segments.items():
        if changes.get("deleted"):
            if seg_id in previous_segments:
                prev_seg = previous_segments[seg_id]
                # ファイル名を再計算
                if prev_seg.get("index") is not None:
                    filename = splitter.generate_filename(
                        prev_seg,
                        index_digits=index_digits,
                        index_sub_digits=index_sub_digits
                    )
                    if splitter.delete_file(filename):
                        deleted_files.append(filename)

    # 2. マージ済みセグメントにindexを割り当て
    segments_with_index = splitter.assign_indices(
        merged_segments,
        existing_segments=previous_segments if not force else None,
        index_sub_digits=index_sub_digits
    )

    # 3. 各セグメントの処理
    result_segments = {}
    for seg_id, seg in segments_with_index.items():
        new_filename = splitter.generate_filename(
            seg,
            index_digits=index_digits,
            index_sub_digits=index_sub_digits
        )

        # 前回のセグメントを取得
        prev_seg = previous_segments.get(seg_id) if not force else None

        # 変更内容を取得
        changes = edit_segments.get(seg_id, {})

        if prev_seg and not force:
            # 既存セグメントの処理

            # 時間変更があるか確認
            time_changed = (
                "start" in changes or "end" in changes or
                abs(seg["start"] - prev_seg["start"]) > 0.001 or
                abs(seg["end"] - prev_seg["end"]) > 0.001
            )

            # 古いファイル名を計算
            old_filename = splitter.generate_filename(
                prev_seg,
                index_digits=index_digits,
                index_sub_digits=index_sub_digits
            )

            if time_changed:
                # 時間変更 → 古いファイル削除 + 再書き出し
                if old_filename != new_filename:
                    splitter.delete_file(old_filename)
                filename = splitter.export_segment(
                    seg,
                    index_digits=index_digits,
                    index_sub_digits=index_sub_digits
                )
                exported_files.append(filename)
            elif "text" in changes or old_filename != new_filename:
                # テキストのみ変更 → リネーム
                if splitter.rename_file(old_filename, new_filename):
                    renamed_files.append({"old": old_filename, "new": new_filename})
                elif not Path(splitter.output_dir / old_filename).exists():
                    # 古いファイルがない場合は新規書き出し
                    filename = splitter.export_segment(
                        seg,
                        index_digits=index_digits,
                        index_sub_digits=index_sub_digits
                    )
                    exported_files.append(filename)
            else:
                # 変更なし → スキップ
                skipped_count += 1
        else:
            # 新規セグメントまたは強制書き出し → 書き出し
            filename = splitter.export_segment(
                seg,
                index_digits=index_digits,
                index_sub_digits=index_sub_digits
            )
            exported_files.append(filename)

        # 結果セグメントを保存
        result_segments[seg_id] = {
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"],
            "index": seg["index"],
            "index_sub": seg.get("index_sub"),
        }

    return {
        "exported": exported_files,
        "renamed": renamed_files,
        "deleted": deleted_files,
        "skipped": skipped_count,
        "segments": result_segments
    }


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

        result = export_diff_v2(
            splitter=splitter,
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

        # Remove edit_segments.json
        splitter.delete_edit_segments()
        print("Removed: edit_segments.json")

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
