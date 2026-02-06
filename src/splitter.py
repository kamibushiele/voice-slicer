"""Audio file splitting based on transcription segments."""
from pathlib import Path
from typing import List, Dict, Any
from pydub import AudioSegment
from tqdm import tqdm
import json

from .utils import (
    format_index_filename,
    determine_index,
    calculate_index_digits,
)


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
        self.audio = AudioSegment.from_file(str(self.audio_path))
        self.audio_duration = len(self.audio)  # in milliseconds  # in milliseconds

    def split_and_save(
        self,
        segments: List[Dict[str, Any]],
        index_digits: int = None
    ) -> List[Dict[str, Any]]:
        """
        Split audio into segments and save as separate files.
        Assigns sequential indices (1, 2, 3, ...) to all segments.

        Args:
            segments: List of segment dictionaries with start, end, text
            index_digits: Number of digits for index (calculated from segment count if None)

        Returns:
            List of output file metadata
        """
        # Calculate index_digits if not provided
        if index_digits is None:
            index_digits = calculate_index_digits(len(segments))

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

        for i, segment in enumerate(tqdm(segments, desc="Processing segments")):
            # Calculate start and end times in milliseconds
            start_ms = max(0, segment["start"] * 1000 - self.margin_before)
            end_ms = min(self.audio_duration, segment["end"] * 1000 + self.margin_after)

            # Extract audio segment
            audio_segment = self.audio[start_ms:end_ms]

            # Generate filename with sequential index
            index = i + 1
            filename = format_index_filename(
                index=index,
                index_sub=None,
                text=segment["text"],
                extension=file_extension,
                index_digits=index_digits,
                max_text_length=self.max_filename_length,
            )
            output_path = self.output_dir / filename

            # Save audio segment
            audio_segment.export(
                str(output_path),
                format=export_format,
            )

            # Store metadata
            metadata = {
                "index": index,
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
        index, index_sub, filename are not set (will be determined at export time).

        Args:
            segments: List of segment dictionaries with start, end, text

        Returns:
            List of output file metadata (without index/filename)
        """
        output_metadata = []

        for segment in segments:
            # Store metadata without index/filename (determined at export time)
            metadata = {
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
            }
            output_metadata.append(metadata)

        return output_metadata

    def save_metadata(
        self,
        segments: Dict[str, Dict[str, Any]],
        output_format: Dict[str, Any] = None,
    ) -> None:
        """
        Save transcription metadata to transcript.json in new format (version 2).

        Args:
            segments: Dictionary of segment metadata (ID as key)
            output_format: Output format settings (optional, uses defaults if not provided)
        """
        metadata_path = self.output_dir / "transcript.json"

        # Calculate default index_digits if not in output_format
        if output_format is None:
            output_format = {}

        if "index_digits" not in output_format:
            output_format["index_digits"] = calculate_index_digits(len(segments))

        # Set defaults for output_format
        output_format.setdefault("index_sub_digits", 3)
        output_format.setdefault("filename_template", "{index}_{basename}")
        output_format.setdefault("margin", {"before": 0.1, "after": 0.2})

        output_data = {
            "version": 2,
            "source_file": str(self.audio_path),
            "output_format": output_format,
            "segments": segments,
        }

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

    def save_edit_segments(
        self,
        segments: Dict[str, Dict[str, Any]],
    ) -> None:
        """
        Save edit_segments.json (pending changes).

        Args:
            segments: Dictionary of segment changes (ID as key)
        """
        edit_path = self.output_dir / "edit_segments.json"

        output_data = {
            "version": 2,
            "segments": segments,
        }

        with open(edit_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

    def delete_edit_segments(self) -> bool:
        """
        Delete edit_segments.json file.

        Returns:
            True if file was deleted, False if it didn't exist
        """
        edit_path = self.output_dir / "edit_segments.json"
        if edit_path.exists():
            edit_path.unlink()
            return True
        return False

    def generate_full_edit_segments(
        self,
        segments: Dict[str, Dict[str, Any]],
    ) -> Path:
        """
        Generate edit_segments.json with all segment data for manual editing.

        If edit_segments.json already exists, merges existing edits on top of
        the transcript segments (transcript as base, edit_segments as overlay).

        Args:
            segments: Dictionary of all segments from transcript.json (ID as key)

        Returns:
            Path to generated edit_segments.json
        """
        edit_path = self.output_dir / "edit_segments.json"

        # Start with transcript segments as base (only essential fields)
        full_segments = {}
        for seg_id, seg in segments.items():
            full_segments[seg_id] = {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
            }

        # If edit_segments.json exists, merge existing edits on top
        if edit_path.exists():
            with open(edit_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            existing_segments = existing_data.get("segments", {})

            for seg_id, changes in existing_segments.items():
                if seg_id in full_segments:
                    # Overlay changes on existing segment
                    full_segments[seg_id].update(changes)
                else:
                    # New segment from edit_segments
                    full_segments[seg_id] = changes.copy()

        output_data = {
            "version": 2,
            "segments": full_segments,
        }

        with open(edit_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        return edit_path

    def export_diff(
        self,
        merged_segments: Dict[str, Dict[str, Any]],
        previous_segments: Dict[str, Dict[str, Any]],
        edit_segments: Dict[str, Dict[str, Any]],
        index_digits: int,
        index_sub_digits: int,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        差分ベースで書き出しを行う。

        Args:
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

        # 1. 削除処理: previous_segmentsにあってmerged_segmentsにないセグメント
        for seg_id, prev_seg in previous_segments.items():
            if seg_id not in merged_segments:
                # ファイル名を再計算
                if prev_seg.get("index") is not None:
                    filename = self.generate_filename(
                        prev_seg,
                        index_digits=index_digits,
                        index_sub_digits=index_sub_digits
                    )
                    if self.delete_file(filename):
                        deleted_files.append(filename)

        # 2. マージ済みセグメントにindexを割り当て
        segments_with_index = self.assign_indices(
            merged_segments,
            existing_segments=previous_segments if not force else None,
            index_sub_digits=index_sub_digits
        )

        # 3. 各セグメントの処理
        result_segments = {}
        for seg_id, seg in segments_with_index.items():
            new_filename = self.generate_filename(
                seg,
                index_digits=index_digits,
                index_sub_digits=index_sub_digits
            )

            # 前回のセグメントを取得
            prev_seg = previous_segments.get(seg_id) if not force else None

            if prev_seg and not force:
                # 既存セグメントの処理

                # 時間変更があるか確認（値の比較）
                time_changed = (
                    abs(seg["start"] - prev_seg["start"]) > 0.001 or
                    abs(seg["end"] - prev_seg["end"]) > 0.001
                )

                # 古いファイル名を計算
                old_filename = self.generate_filename(
                    prev_seg,
                    index_digits=index_digits,
                    index_sub_digits=index_sub_digits
                )

                if time_changed:
                    # 時間変更 → 古いファイル削除 + 再書き出し
                    if old_filename != new_filename:
                        self.delete_file(old_filename)
                    filename = self.export_segment(
                        seg,
                        index_digits=index_digits,
                        index_sub_digits=index_sub_digits
                    )
                    exported_files.append(filename)
                elif seg["text"] != prev_seg["text"] or old_filename != new_filename:
                    # テキストのみ変更 → リネーム
                    if self.rename_file(old_filename, new_filename):
                        renamed_files.append({"old": old_filename, "new": new_filename})
                    elif not (self.output_dir / old_filename).exists():
                        # 古いファイルがない場合は新規書き出し
                        filename = self.export_segment(
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
                filename = self.export_segment(
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

    def export_segment(
        self,
        segment: Dict[str, Any],
        index_digits: int = 3,
        index_sub_digits: int = 3
    ) -> str:
        """
        Export a single segment and return its filename.

        Args:
            segment: Segment dictionary with index, index_sub, start, end, text
            index_digits: Number of digits for index formatting
            index_sub_digits: Number of digits for index_sub formatting

        Returns:
            Generated filename
        """
        file_extension = self.audio_path.suffix

        format_map = {
            '.m4a': 'ipod',
            '.mp4': 'mp4',
            '.aac': 'adts',
        }
        export_format = format_map.get(file_extension.lower(), file_extension.lstrip('.'))

        # Calculate start and end times in milliseconds
        start_ms = max(0, segment["start"] * 1000 - self.margin_before)
        end_ms = min(self.audio_duration, segment["end"] * 1000 + self.margin_after)

        # Extract audio segment
        audio_segment = self.audio[start_ms:end_ms]

        # Generate filename using index and index_sub
        filename = format_index_filename(
            index=segment["index"],
            index_sub=segment.get("index_sub"),
            text=segment["text"],
            extension=file_extension,
            index_digits=index_digits,
            index_sub_digits=index_sub_digits,
            max_text_length=self.max_filename_length,
        )
        output_path = self.output_dir / filename

        # Save audio segment
        audio_segment.export(
            str(output_path),
            format=export_format,
        )

        return filename

    def rename_file(self, old_filename: str, new_filename: str) -> bool:
        """
        Rename an audio file in the output directory.

        Args:
            old_filename: Current filename
            new_filename: New filename

        Returns:
            True if successful, False if old file doesn't exist
        """
        old_path = self.output_dir / old_filename
        new_path = self.output_dir / new_filename

        if old_path.exists():
            old_path.rename(new_path)
            return True
        return False

    def delete_file(self, filename: str) -> bool:
        """
        Delete an audio file from the output directory.

        Args:
            filename: Filename to delete

        Returns:
            True if successful, False if file doesn't exist
        """
        file_path = self.output_dir / filename
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def generate_filename(
        self,
        segment: Dict[str, Any],
        index_digits: int = 3,
        index_sub_digits: int = 3,
        filename_template: str = "{index}_{basename}"
    ) -> str:
        """
        Generate filename for a segment without exporting.

        Args:
            segment: Segment dictionary with index, index_sub, text
            index_digits: Number of digits for index formatting
            index_sub_digits: Number of digits for index_sub formatting
            filename_template: Filename template string

        Returns:
            Generated filename
        """
        file_extension = self.audio_path.suffix
        return format_index_filename(
            index=segment["index"],
            index_sub=segment.get("index_sub"),
            text=segment["text"],
            extension=file_extension,
            index_digits=index_digits,
            index_sub_digits=index_sub_digits,
            max_text_length=self.max_filename_length,
        )

    def assign_indices(
        self,
        segments: Dict[str, Dict[str, Any]],
        existing_segments: Dict[str, Dict[str, Any]] = None,
        index_sub_digits: int = 3
    ) -> Dict[str, Dict[str, Any]]:
        """
        Assign index and index_sub to segments that don't have them.
        Segments are sorted by start time before assignment.

        Args:
            segments: Dictionary of segment (may or may not have index)
            existing_segments: Dictionary of existing segments with confirmed indices
            index_sub_digits: Number of digits for index_sub

        Returns:
            Dictionary of segments with index and index_sub assigned
        """
        # Convert to list and sort by start time
        sorted_items = sorted(segments.items(), key=lambda x: x[1]["start"])

        # Build list of confirmed indices from existing segments
        confirmed = []
        if existing_segments:
            for seg_id, seg in existing_segments.items():
                if seg.get("index") is not None:
                    confirmed.append({
                        "index": seg["index"],
                        "index_sub": seg.get("index_sub", 0) or 0,
                        "start": seg["start"],
                    })
        confirmed.sort(key=lambda s: s["start"])

        # Process each segment
        result = {}
        for seg_id, seg in sorted_items:
            if seg.get("index") is not None:
                # Already has confirmed index
                result[seg_id] = seg.copy()
            else:
                # Need to determine index
                seg_copy = seg.copy()

                # Find before and after indices
                before = None
                after = None

                # Check confirmed indices
                for conf in confirmed:
                    if conf["start"] < seg["start"]:
                        before = (conf["index"], conf["index_sub"])
                    elif conf["start"] > seg["start"] and after is None:
                        after = (conf["index"], conf["index_sub"])
                        break

                # Check already processed segments in result
                for r_id, r in result.items():
                    if r.get("index") is not None:
                        if r["start"] < seg["start"]:
                            r_idx = (r["index"], r.get("index_sub", 0) or 0)
                            if before is None or r_idx > before:
                                before = r_idx
                        elif r["start"] > seg["start"]:
                            r_idx = (r["index"], r.get("index_sub", 0) or 0)
                            if after is None or r_idx < after:
                                after = r_idx

                # Determine index
                new_index, new_index_sub = determine_index(
                    before, after, index_sub_digits=index_sub_digits
                )
                seg_copy["index"] = new_index
                seg_copy["index_sub"] = new_index_sub if new_index_sub != 0 else None

                result[seg_id] = seg_copy

        return result
