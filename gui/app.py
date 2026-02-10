"""
手動調整GUI - Flaskアプリケーション（新スキーマ対応・フロントエンド互換）
"""

import json
import os
import uuid
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
import sys

# 親ディレクトリをパスに追加（srcモジュールのインポート用）
sys.path.insert(0, str(Path(__file__).parent.parent))

from gui.audio_handler import AudioHandler
from src.json_loader import (
    load_transcript_json,
    load_edit_segments,
    merge_segments,
    get_next_segment_id,
)
from src.utils import format_index_string

app = Flask(__name__)

# グローバル設定
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'}

# 起動時に読み込むデータ
_initial_data = None
# セッションID（サーバー起動ごとに生成）
_session_id = str(uuid.uuid4())


def segments_dict_to_list(segments_dict: dict, output_format: dict = None) -> list:
    """オブジェクト形式のセグメントを配列形式に変換（フロントエンド互換）"""
    # output_formatからindex桁数を取得
    index_digits = 3
    index_sub_digits = 3
    if output_format:
        index_digits = output_format.get('index_digits', 3)
        index_sub_digits = output_format.get('index_sub_digits', 3)

    result = []
    for seg_id, seg in segments_dict.items():
        seg_copy = seg.copy()
        seg_copy['_seg_id'] = seg_id  # 内部IDを保持
        # indexがある場合はフォーマット済み文字列を追加
        if seg.get('index') is not None:
            seg_copy['index_formatted'] = format_index_string(
                seg['index'],
                seg.get('index_sub'),
                index_digits,
                index_sub_digits
            )
        result.append(seg_copy)
    # 開始時刻順にソート
    result.sort(key=lambda x: x['start'])
    return result


def segments_list_to_dict(segments_list: list, transcript_segments: dict) -> tuple:
    """
    配列形式のセグメントをオブジェクト形式に変換し、edit_segmentsを生成。

    Returns:
        (current_segments_dict, edit_segments_dict)
    """
    current_segments = {}
    edit_segments = {}

    # 除外するキー（内部用・表示専用フィールド）
    exclude_keys = {'index_formatted'}

    # まず既存のセグメント（_seg_idあり）を処理
    existing_seg_ids = set()
    for seg in segments_list:
        seg_id = seg.get('_seg_id')
        if seg_id is not None:
            existing_seg_ids.add(seg_id)
            seg_copy = {k: v for k, v in seg.items() if not k.startswith('_') and k not in exclude_keys}
            current_segments[seg_id] = seg_copy

    # 次に新規セグメント（_seg_idなし）を処理
    # 既存IDと重複しないように採番
    for seg in segments_list:
        seg_id = seg.get('_seg_id')
        if seg_id is None:
            # 新規セグメント - 既存IDと重複しないようにIDを採番
            all_existing_ids = existing_seg_ids | set(current_segments.keys()) | set(transcript_segments.keys())
            seg_id = get_next_segment_id({k: {} for k in all_existing_ids})

            seg_copy = {k: v for k, v in seg.items() if not k.startswith('_') and k not in exclude_keys}
            current_segments[seg_id] = seg_copy

    # edit_segmentsを生成（変更差分のみ）
    all_seg_ids = set(current_segments.keys()) | set(transcript_segments.keys())

    for seg_id in all_seg_ids:
        if seg_id in current_segments and seg_id not in transcript_segments:
            # 新規追加
            seg = current_segments[seg_id]
            edit_segments[seg_id] = {
                'start': seg['start'],
                'end': seg['end'],
                'text': seg['text'],
            }
        elif seg_id not in current_segments and seg_id in transcript_segments:
            # 削除（edit_segmentsには含めない）
            pass
        elif seg_id in current_segments and seg_id in transcript_segments:
            # 変更チェック
            curr = current_segments[seg_id]
            prev = transcript_segments[seg_id]
            changes = {}

            if abs(curr.get('start', 0) - prev.get('start', 0)) > 0.001:
                changes['start'] = curr['start']
            if abs(curr.get('end', 0) - prev.get('end', 0)) > 0.001:
                changes['end'] = curr['end']
            if curr.get('text', '') != prev.get('text', ''):
                changes['text'] = curr['text']

            if changes:
                edit_segments[seg_id] = changes

    return current_segments, edit_segments


def load_initial_data(dir_path: str) -> str | None:
    """
    起動時にディレクトリからJSONファイルを読み込む（新スキーマ対応）

    Args:
        dir_path: transcript.jsonが含まれるディレクトリのパス

    Returns:
        エラーメッセージ（成功時はNone）
    """
    global _initial_data

    directory = Path(dir_path)

    if not directory.exists():
        return f'ディレクトリが見つかりません: {dir_path}'

    if not directory.is_dir():
        return f'ディレクトリを指定してください: {dir_path}'

    # ファイルパスを確認
    transcript_path = directory / 'transcript.json'
    edit_segments_path = directory / 'edit_segments.json'
    unexported_path = directory / 'transcript_unexported.json'

    try:
        # transcript.jsonを読み込み（旧フォーマットは自動マイグレーション）
        if transcript_path.exists():
            transcript_data = load_transcript_json(str(transcript_path))
        elif unexported_path.exists():
            # 旧フォーマット: transcript_unexported.jsonのみ存在
            transcript_data = load_transcript_json(str(unexported_path))
            # edit_segments.jsonとして変換
            edit_segments_data = {
                "version": 2,
                "segments": transcript_data.get("segments", {})
            }
            # transcript.jsonは空のセグメントで作成
            transcript_data["segments"] = {}
            with open(transcript_path, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, ensure_ascii=False, indent=2)
            with open(edit_segments_path, 'w', encoding='utf-8') as f:
                json.dump(edit_segments_data, f, ensure_ascii=False, indent=2)
        else:
            return f'transcript.jsonが見つかりません: {dir_path}'

        # edit_segments.jsonを読み込み（存在する場合）
        edit_segments_data = {"version": 2, "segments": {}}
        has_edit_segments = False
        if edit_segments_path.exists():
            edit_segments_data = load_edit_segments(str(edit_segments_path))
            has_edit_segments = True

        # セグメントをマージ
        merged_segments = merge_segments(
            transcript_data.get("segments", {}),
            edit_segments_data.get("segments", {})
        )

        # 音声ファイルのパスを解決
        source_file = transcript_data['source_file']
        if not os.path.isabs(source_file):
            source_path = directory / source_file
            if not source_path.exists():
                source_path = directory.parent / source_file
            resolved_path = str(source_path.resolve())
        else:
            resolved_path = source_file

        # 音声ファイルの存在確認
        if not Path(resolved_path).exists():
            return f'音声ファイルが見つかりません: {source_file}'

        # 音声情報を取得
        handler = AudioHandler(resolved_path)

        # output_formatを取得
        output_format = transcript_data.get('output_format', {
            'index_digits': 3,
            'index_sub_digits': 3,
            'filename_template': '{index}_{basename}',
            'margin': {'before': 0.1, 'after': 0.2}
        })

        # データを構築（配列形式でフロントエンドに渡す）
        data = {
            'version': 2,
            'source_file': transcript_data['source_file'],
            'source_file_resolved': resolved_path,
            'output_format': output_format,
            # フロントエンド互換: 配列形式
            'segments': segments_dict_to_list(merged_segments, output_format),
            # 内部用: オブジェクト形式
            '_transcript_segments': transcript_data.get('segments', {}),
            '_edit_segments': edit_segments_data.get('segments', {}),
            'audio_info': handler.get_info(),
            'json_path': str(transcript_path.resolve()),
            'dir_path': str(directory.resolve()),
            'has_unexported': has_edit_segments,
            # index_digits を旧フォーマット互換で提供
            'index_digits': transcript_data.get('output_format', {}).get('index_digits', 3),
        }

        _initial_data = data
        return None

    except json.JSONDecodeError as e:
        return f'JSONパースエラー: {str(e)}'
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f'読み込みエラー: {str(e)}'


@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')


@app.route('/api/data', methods=['GET'])
def get_data():
    """初期データを取得（毎回ファイルを再読み込み）"""
    if _initial_data is None:
        return jsonify({'error': 'データが読み込まれていません'}), 500

    # ディレクトリから再読み込み
    dir_path = _initial_data.get('dir_path')
    if dir_path:
        error = load_initial_data(dir_path)
        if error:
            return jsonify({'error': error}), 500

    # フロントエンド用にクリーンアップしたデータを返す
    response_data = {k: v for k, v in _initial_data.items() if not k.startswith('_')}
    response_data['session_id'] = _session_id
    return jsonify(response_data)


@app.route('/api/save', methods=['POST'])
def save_json():
    """edit_segments.jsonを保存する（全セグメント情報）"""
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'データがありません'}), 400

        # セッションID検証
        client_session_id = data.get('session_id')
        if client_session_id != _session_id:
            return jsonify({
                'error': 'セッションが無効です。ページを再読み込みしてください。',
                'error_code': 'SESSION_MISMATCH'
            }), 409

        segments_list = data.get('segments', [])

        dir_path = data.get('dir_path') or (_initial_data and _initial_data.get('dir_path'))
        if not dir_path:
            # json_pathからdir_pathを取得
            json_path = data.get('json_path')
            if json_path:
                dir_path = str(Path(json_path).parent)

        if not dir_path:
            return jsonify({'error': 'dir_pathが指定されていません'}), 400

        edit_segments_path = Path(dir_path) / 'edit_segments.json'

        # transcript_segmentsを取得
        transcript_segments = {}
        if _initial_data:
            transcript_segments = _initial_data.get('_transcript_segments', {})

        # 配列形式のセグメントをオブジェクト形式に変換
        segments_list = data.get('segments', [])
        current_segments, edit_segments = segments_list_to_dict(segments_list, transcript_segments)

        # 全セグメント情報を作成（削除されたセグメントは含まない）
        full_segments = {}
        for seg_id, seg in current_segments.items():
            full_segments[seg_id] = {
                'start': seg['start'],
                'end': seg['end'],
                'text': seg['text'],
            }

        # edit_segments.jsonを保存（全セグメント情報）
        save_data = {
            'version': 2,
            'segments': full_segments
        }

        with open(edit_segments_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        return jsonify({
            'success': True,
            'message': f'保存しました: edit_segments.json',
            'unexported_path': str(edit_segments_path),
            'segments_count': len(full_segments)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'保存エラー: {str(e)}'}), 500


@app.route('/api/waveform', methods=['GET'])
def get_waveform():
    """波形データを取得する"""
    audio_path = request.args.get('path')

    if not audio_path:
        return jsonify({'error': 'パスが指定されていません'}), 400

    audio_file = Path(audio_path)

    if not audio_file.exists():
        return jsonify({'error': f'ファイルが見つかりません: {audio_path}'}), 404

    try:
        handler = AudioHandler(str(audio_file))
        waveform_data = handler.get_waveform_data()
        return jsonify(waveform_data)

    except Exception as e:
        return jsonify({'error': f'波形データ取得エラー: {str(e)}'}), 500


@app.route('/api/audio/<path:audio_path>')
def serve_audio(audio_path):
    """音声ファイルを提供する"""
    try:
        # パスの正規化とセキュリティチェック
        audio_file = Path(audio_path).resolve()

        if not audio_file.exists():
            return jsonify({'error': 'ファイルが見つかりません'}), 404

        if audio_file.suffix.lower() not in ALLOWED_AUDIO_EXTENSIONS:
            return jsonify({'error': '許可されていないファイル形式です'}), 400

        return send_file(str(audio_file))

    except Exception as e:
        return jsonify({'error': f'音声ファイル提供エラー: {str(e)}'}), 500


@app.route('/api/regenerate', methods=['POST'])
def regenerate_audio():
    """差分ベースで音声を書き出す（新スキーマ対応・フロントエンド互換）"""
    try:
        from src.splitter import AudioSplitter
        from src.utils import calculate_index_digits

        data = request.json

        if not data:
            return jsonify({'error': 'データがありません'}), 400

        # セッションID検証
        client_session_id = data.get('session_id')
        if client_session_id != _session_id:
            return jsonify({
                'error': 'セッションが無効です。ページを再読み込みしてください。',
                'error_code': 'SESSION_MISMATCH'
            }), 409

        source_file = data.get('source_file_resolved')
        segments_list = data.get('segments', [])
        dir_path = data.get('dir_path') or (_initial_data and _initial_data.get('dir_path'))
        output_format = data.get('output_format') or (_initial_data and _initial_data.get('output_format', {}))
        force_export = data.get('force', False)

        if not dir_path:
            json_path = data.get('json_path')
            if json_path:
                dir_path = str(Path(json_path).parent)

        if not source_file or not Path(source_file).exists():
            return jsonify({'error': '音声ファイルが見つかりません'}), 400

        output_dir = Path(dir_path)

        # transcript_segmentsを取得
        transcript_segments = {}
        if _initial_data:
            transcript_segments = _initial_data.get('_transcript_segments', {})

        # 配列形式のセグメントをオブジェクト形式に変換
        current_segments, edit_segments = segments_list_to_dict(segments_list, transcript_segments)

        # 設定を取得
        if output_format is None:
            output_format = {}
        index_digits = output_format.get('index_digits') or data.get('index_digits')
        if index_digits is None:
            index_digits = calculate_index_digits(len(current_segments))

        index_sub_digits = output_format.get('index_sub_digits', 3)
        margin_before = output_format.get('margin', {}).get('before', 0.1)
        margin_after = output_format.get('margin', {}).get('after', 0.2)

        # AudioSplitterを初期化
        splitter = AudioSplitter(
            audio_path=source_file,
            output_dir=str(output_dir),
            margin_before=margin_before,
            margin_after=margin_after
        )

        # 差分書き出し（Core層）
        result = splitter.export_diff(
            merged_segments=current_segments,
            previous_segments=transcript_segments,
            edit_segments=edit_segments,
            index_digits=index_digits,
            index_sub_digits=index_sub_digits,
            force=force_export
        )

        exported_files = result['exported']
        renamed_files = result['renamed']
        deleted_files = result['deleted']
        skipped_count = result['skipped']
        result_segments = result['segments']

        # transcript.jsonを更新
        output_format['index_digits'] = index_digits
        output_format['index_sub_digits'] = index_sub_digits

        splitter.save_metadata(
            segments=result_segments,
            output_format=output_format
        )

        # _initial_dataを更新（次回の差分計算のため）
        if _initial_data:
            _initial_data['_transcript_segments'] = result_segments
            _initial_data['_edit_segments'] = {}

        # 結果メッセージを生成
        messages = []
        if exported_files:
            messages.append(f'書き出し: {len(exported_files)}件')
        if renamed_files:
            messages.append(f'リネーム: {len(renamed_files)}件')
        if deleted_files:
            messages.append(f'削除: {len(deleted_files)}件')
        if skipped_count > 0:
            messages.append(f'スキップ: {skipped_count}件')

        if not messages:
            messages.append('変更なし')

        # フロントエンド互換: 配列形式で返す
        result_segments_list = segments_dict_to_list(result_segments, output_format)

        return jsonify({
            'success': True,
            'message': '、'.join(messages),
            'output_dir': str(output_dir),
            'exported': exported_files,
            'renamed': renamed_files,
            'deleted': deleted_files,
            'skipped': skipped_count,
            'segments': result_segments_list
        })

    except Exception as e:
        import traceback
        return jsonify({
            'error': f'書き出しエラー: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500
