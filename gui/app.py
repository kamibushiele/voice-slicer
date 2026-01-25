"""
手動調整GUI - Flaskアプリケーション
"""

import json
import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
import sys

# 親ディレクトリをパスに追加（srcモジュールのインポート用）
sys.path.insert(0, str(Path(__file__).parent.parent))

from gui.audio_handler import AudioHandler

app = Flask(__name__)

# グローバル設定
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'}

# 起動時に読み込むデータ
_initial_data = None


def load_initial_data(dir_path: str) -> str | None:
    """
    起動時にディレクトリからJSONファイルを読み込む

    _unexported.jsonがあれば優先的に読み込む（未書き出しの変更あり）

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

    # transcript.jsonを探す（_unexported.jsonがあれば優先）
    unexported_path = directory / 'transcript_unexported.json'
    json_file = directory / 'transcript.json'

    has_unexported = unexported_path.exists()

    if has_unexported:
        load_path = unexported_path
    elif json_file.exists():
        load_path = json_file
    else:
        return f'transcript.jsonが見つかりません: {dir_path}'

    try:
        with open(load_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 必須フィールドの検証
        if 'source_file' not in data:
            return "JSON missing 'source_file' field"
        if 'segments' not in data:
            return "JSON missing 'segments' field"

        # 音声ファイルのパスを解決
        source_file = data['source_file']
        if not os.path.isabs(source_file):
            source_path = directory / source_file
            if not source_path.exists():
                source_path = directory.parent / source_file
            data['source_file_resolved'] = str(source_path.resolve())
        else:
            data['source_file_resolved'] = source_file

        # 音声ファイルの存在確認
        resolved_path = Path(data['source_file_resolved'])
        if not resolved_path.exists():
            return f'音声ファイルが見つかりません: {data["source_file"]}'

        # 音声情報を取得
        handler = AudioHandler(str(resolved_path))
        data['audio_info'] = handler.get_info()
        data['json_path'] = str(json_file.resolve())  # transcript.jsonのパスを保持
        data['dir_path'] = str(directory.resolve())  # ディレクトリパスを保持
        data['has_unexported'] = has_unexported  # 未書き出しフラグ

        _initial_data = data
        return None

    except json.JSONDecodeError as e:
        return f'JSONパースエラー: {str(e)}'
    except Exception as e:
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

    # ディレクトリから再読み込み（_unexported.jsonがあれば優先）
    dir_path = _initial_data.get('dir_path')
    if dir_path:
        error = load_initial_data(dir_path)
        if error:
            return jsonify({'error': error}), 500

    return jsonify(_initial_data)


@app.route('/api/save', methods=['POST'])
def save_json():
    """JSONファイルを保存する（_unexported.jsonとして保存）"""
    try:
        from src.utils import generate_segment_filename

        data = request.json

        if not data:
            return jsonify({'error': 'データがありません'}), 400

        json_path = data.get('json_path')
        if not json_path:
            return jsonify({'error': 'json_pathが指定されていません'}), 400

        # _unexported.jsonとして保存
        json_path = Path(json_path)
        unexported_path = json_path.parent / f"{json_path.stem}_unexported.json"

        # 音声ファイルの拡張子を取得
        source_file = data.get('source_file', '')
        extension = Path(source_file).suffix if source_file else '.mp3'

        # 保存用のデータを整形
        save_data = {
            'source_file': source_file,
            'segments': []
        }

        # セグメントを整形（ファイル名を自動再生成）
        for i, segment in enumerate(data.get('segments', [])):
            # ファイル名をテキストから自動生成
            index = segment.get('index', i + 1)
            text = segment.get('text', '')
            filename = generate_segment_filename(index, text, extension)

            cleaned_segment = {
                'index': index,
                'filename': filename,
                'start': segment.get('start', 0),
                'end': segment.get('end', 0),
                'text': text,
            }

            save_data['segments'].append(cleaned_segment)

        with open(unexported_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        return jsonify({
            'success': True,
            'message': f'保存しました: {unexported_path.name}',
            'unexported_path': str(unexported_path)
        })

    except Exception as e:
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


@app.route('/api/generate-filename', methods=['POST'])
def generate_filename():
    """テキストからファイル名を生成する"""
    try:
        from src.utils import generate_segment_filename
        
        data = request.json
        
        index = data.get('index', 1)
        text = data.get('text', '')
        extension = data.get('extension', '.mp3')
        max_length = data.get('max_length')
        
        filename = generate_segment_filename(index, text, extension, max_length)
        
        return jsonify({'filename': filename})
    
    except Exception as e:
        return jsonify({'error': f'ファイル名生成エラー: {str(e)}'}), 500


@app.route('/api/regenerate', methods=['POST'])
def regenerate_audio():
    """差分ベースで音声を書き出す（変更/削除/リネームに対応）"""
    try:
        from src.splitter import AudioSplitter

        data = request.json

        if not data:
            return jsonify({'error': 'データがありません'}), 400

        source_file = data.get('source_file_resolved')
        current_segments = data.get('segments', [])
        json_path = data.get('json_path')
        force_export = data.get('force', False)  # 強制書き出しフラグ

        if not source_file or not Path(source_file).exists():
            return jsonify({'error': '音声ファイルが見つかりません'}), 400

        # 出力ディレクトリ（transcript.jsonと同じ場所）
        json_path = Path(json_path)
        output_dir = json_path.parent

        # 前回書き出し済みのtranscript.jsonを読み込み
        exported_json_path = output_dir / 'transcript.json'
        previous_segments = {}
        if exported_json_path.exists() and not force_export:
            with open(exported_json_path, 'r', encoding='utf-8') as f:
                prev_data = json.load(f)
                for seg in prev_data.get('segments', []):
                    previous_segments[seg['index']] = seg

        # 現在のセグメントをindex→segのマップに変換
        current_by_index = {seg['index']: seg for seg in current_segments}

        # AudioSplitterを初期化
        splitter = AudioSplitter(
            audio_path=source_file,
            output_dir=str(output_dir),
            margin_before=0.1,
            margin_after=0.2
        )

        # 差分を計算
        deleted_files = []
        renamed_files = []
        exported_files = []

        # 1. 削除されたセグメント（前回にあって今回にない）
        for idx, prev_seg in previous_segments.items():
            if idx not in current_by_index:
                if splitter.delete_file(prev_seg['filename']):
                    deleted_files.append(prev_seg['filename'])

        # 2. 各セグメントの処理
        for seg in current_segments:
            idx = seg['index']
            new_filename = splitter.generate_filename(seg)

            if idx in previous_segments and not force_export:
                prev_seg = previous_segments[idx]
                old_filename = prev_seg['filename']

                # start/endが変更されたか確認
                time_changed = (
                    abs(seg['start'] - prev_seg['start']) > 0.001 or
                    abs(seg['end'] - prev_seg['end']) > 0.001
                )

                if time_changed:
                    # 時刻変更 → 古いファイル削除 + 再書き出し
                    if old_filename != new_filename:
                        splitter.delete_file(old_filename)
                    filename = splitter.export_segment(seg)
                    exported_files.append(filename)
                    seg['filename'] = filename
                elif old_filename != new_filename:
                    # テキストのみ変更 → リネーム
                    if splitter.rename_file(old_filename, new_filename):
                        renamed_files.append({'old': old_filename, 'new': new_filename})
                    seg['filename'] = new_filename
                else:
                    # 変更なし
                    seg['filename'] = old_filename
            else:
                # 新規セグメントまたは強制書き出し → 書き出し
                filename = splitter.export_segment(seg)
                exported_files.append(filename)
                seg['filename'] = filename

        # transcript.jsonを更新
        save_data = {
            'source_file': data.get('source_file', ''),
            'segments': [
                {
                    'index': seg['index'],
                    'filename': seg['filename'],
                    'start': seg['start'],
                    'end': seg['end'],
                    'text': seg['text'],
                }
                for seg in current_segments
            ]
        }

        with open(exported_json_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        # _unexported.jsonを削除
        unexported_path = output_dir / f"{json_path.stem}_unexported.json"
        if unexported_path.exists():
            unexported_path.unlink()

        # 結果メッセージを生成
        messages = []
        if exported_files:
            messages.append(f'書き出し: {len(exported_files)}件')
        if renamed_files:
            messages.append(f'リネーム: {len(renamed_files)}件')
        if deleted_files:
            messages.append(f'削除: {len(deleted_files)}件')

        if not messages:
            messages.append('変更なし')

        return jsonify({
            'success': True,
            'message': '、'.join(messages),
            'output_dir': str(output_dir),
            'exported': exported_files,
            'renamed': renamed_files,
            'deleted': deleted_files,
            'segments': save_data['segments']
        })

    except Exception as e:
        import traceback
        return jsonify({
            'error': f'書き出しエラー: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500


if __name__ == '__main__':
    print("手動調整GUI を起動します...")
    print("ブラウザで http://localhost:5000 を開いてください")
    app.run(debug=True, port=5000)
