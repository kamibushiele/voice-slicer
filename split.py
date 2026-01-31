"""Split audio into segments based on transcript_unexported.json."""
from pathlib import Path
import sys
import json

from src.cli import parse_split_args
from src.splitter import AudioSplitter
from src.json_loader import load_transcript_json
from src.utils import calculate_index_digits


def find_transcript_json(directory: Path) -> tuple[Path | None, bool]:
    """
    Find transcript JSON file in directory.
    Prefer _unexported.json if it exists.

    Returns:
        (path, has_unexported): JSON file path and whether it's unexported
    """
    unexported = directory / 'transcript_unexported.json'
    if unexported.exists():
        return unexported, True

    transcript = directory / 'transcript.json'
    if transcript.exists():
        return transcript, False

    return None, False


def export_diff(
    splitter: AudioSplitter,
    current_segments: list,
    previous_segments: list,
    index_digits: int,
    force: bool = False
) -> dict:
    """
    差分ベースで書き出しを行う。

    Args:
        splitter: AudioSplitterインスタンス
        current_segments: 現在のセグメント
        previous_segments: 前回書き出し済みセグメント
        index_digits: indexの桁数
        force: 強制書き出しフラグ

    Returns:
        結果辞書 (exported, renamed, deleted, segments)
    """
    # 前回のセグメントをファイル名でマッピング
    previous_by_filename = {}
    if not force:
        for seg in previous_segments:
            if seg.get('filename'):
                previous_by_filename[seg['filename']] = seg

    # 未確定セグメントにindexを割り当て
    segments_with_index = splitter.assign_indices(
        current_segments,
        existing_segments=previous_segments if not force else None
    )

    # 差分を計算
    deleted_files = []
    renamed_files = []
    exported_files = []

    # 現在のセグメントのファイル名を収集
    current_filenames = set()
    for seg in segments_with_index:
        if seg.get('filename'):
            current_filenames.add(seg['filename'])

    # 1. 削除されたセグメント（前回にあって今回にないファイル名）
    if not force:
        for prev_seg in previous_segments:
            prev_filename = prev_seg.get('filename')
            if prev_filename and prev_filename not in current_filenames:
                # このセグメントに対応する新しいセグメントがあるか確認
                found_update = False
                for seg in segments_with_index:
                    if (abs(seg['start'] - prev_seg['start']) < 0.001 and
                        abs(seg['end'] - prev_seg['end']) < 0.001):
                        found_update = True
                        break
                if not found_update:
                    if splitter.delete_file(prev_filename):
                        deleted_files.append(prev_filename)

    # 2. 各セグメントの処理
    for seg in segments_with_index:
        new_filename = splitter.generate_filename(seg, index_digits=index_digits)

        # 既存のファイル名を持つセグメントを検索
        old_seg = None
        if not force:
            if seg.get('filename') and seg['filename'] in previous_by_filename:
                old_seg = previous_by_filename[seg['filename']]
            else:
                # ファイル名がない場合、同じstart/endを持つセグメントを検索
                for prev_seg in previous_segments:
                    if (abs(seg['start'] - prev_seg['start']) < 0.001 and
                        abs(seg['end'] - prev_seg['end']) < 0.001):
                        old_seg = prev_seg
                        break

        if old_seg and not force:
            old_filename = old_seg.get('filename')

            # start/endが変更されたか確認
            time_changed = (
                abs(seg['start'] - old_seg['start']) > 0.001 or
                abs(seg['end'] - old_seg['end']) > 0.001
            )

            if time_changed:
                # 時刻変更 → 古いファイル削除 + 再書き出し
                if old_filename and old_filename != new_filename:
                    splitter.delete_file(old_filename)
                filename = splitter.export_segment(seg, index_digits=index_digits)
                exported_files.append(filename)
                seg['filename'] = filename
            elif old_filename != new_filename:
                # テキストのみ変更またはindex変更 → リネーム
                if old_filename and splitter.rename_file(old_filename, new_filename):
                    renamed_files.append({'old': old_filename, 'new': new_filename})
                    seg['filename'] = new_filename
                elif not old_filename:
                    # 古いファイルがない場合は新規書き出し
                    filename = splitter.export_segment(seg, index_digits=index_digits)
                    exported_files.append(filename)
                    seg['filename'] = filename
                else:
                    seg['filename'] = new_filename
            else:
                # 変更なし
                seg['filename'] = old_filename
        else:
            # 新規セグメントまたは強制書き出し → 書き出し
            filename = splitter.export_segment(seg, index_digits=index_digits)
            exported_files.append(filename)
            seg['filename'] = filename

    return {
        'exported': exported_files,
        'renamed': renamed_files,
        'deleted': deleted_files,
        'segments': segments_with_index
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
        # Step 1: Find and load JSON
        print("\n" + "-" * 40)
        print("Loading transcript JSON...")
        print("-" * 40)

        json_path, has_unexported = find_transcript_json(output_dir)
        if json_path is None:
            print(f"\n[ERROR] No transcript JSON found in: {output_dir}")
            return 1

        print(f"Loading: {json_path.name}")
        data = load_transcript_json(str(json_path))
        source_audio = Path(data["source_file"])

        print(f"Source audio: {source_audio}")
        print(f"Segments: {len(data['segments'])}")

        # Verify source audio exists
        if not source_audio.exists():
            print(f"\n[ERROR] Source audio file not found: {source_audio}")
            print("Please ensure the audio file exists at the path specified in transcript JSON")
            return 1

        current_segments = data['segments']

        # Load previous transcript.json for diff calculation
        previous_segments = []
        exported_json_path = output_dir / 'transcript.json'
        if exported_json_path.exists() and not force_export:
            print(f"Loading previous: transcript.json")
            with open(exported_json_path, 'r', encoding='utf-8') as f:
                prev_data = json.load(f)
                previous_segments = prev_data.get('segments', [])
            print(f"Previous segments: {len(previous_segments)}")

        # Get or calculate index_digits
        index_digits = data.get('index_digits')
        if index_digits is None:
            index_digits = calculate_index_digits(len(current_segments))

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
            margin_before=args.margin_before,
            margin_after=args.margin_after,
            max_filename_length=args.max_filename_length,
        )

        result = export_diff(
            splitter=splitter,
            current_segments=current_segments,
            previous_segments=previous_segments,
            index_digits=index_digits,
            force=force_export
        )

        # Step 3: Save transcript.json and remove _unexported
        print("\n" + "-" * 40)
        print("Saving transcript.json...")
        print("-" * 40)

        save_data = {
            'source_file': data.get('source_file', ''),
            'index_digits': index_digits,
            'segments': [
                {
                    'index': seg['index'],
                    'index_sub': seg.get('index_sub'),
                    'filename': seg['filename'],
                    'start': seg['start'],
                    'end': seg['end'],
                    'text': seg['text'],
                }
                for seg in result['segments']
            ]
        }

        with open(exported_json_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        # Remove _unexported.json
        unexported_path = output_dir / 'transcript_unexported.json'
        if unexported_path.exists():
            unexported_path.unlink()
            print("Removed: transcript_unexported.json")

        # Summary
        print("\n" + "=" * 60)
        print("Splitting Complete!")
        print("=" * 60)
        print(f"Total segments: {len(result['segments'])}")

        if result['exported']:
            print(f"Exported: {len(result['exported'])} files")
        if result['renamed']:
            print(f"Renamed: {len(result['renamed'])} files")
        if result['deleted']:
            print(f"Deleted: {len(result['deleted'])} files")

        if not result['exported'] and not result['renamed'] and not result['deleted']:
            print("No changes detected.")

        print(f"\nOutput directory: {output_dir.absolute()}")

        # Show sample outputs
        if result['exported']:
            print("\nExported files:")
            for filename in result['exported'][:5]:
                print(f"  - {filename}")
            if len(result['exported']) > 5:
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
