#!/usr/bin/env python
"""
Edit transcript.json with GUI and export audio segments.

Usage:
    python edit.py <output_directory>
"""

import sys
import webbrowser
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.cli import parse_edit_args
from src.utils import find_available_port


def find_transcript_json(directory: Path) -> Path | None:
    """
    Find transcript.json in directory.
    Prefer _unexported.json if it exists.
    """
    unexported = directory / 'transcript_unexported.json'
    if unexported.exists():
        return unexported

    transcript = directory / 'transcript.json'
    if transcript.exists():
        return transcript

    return None


def main():
    print("=" * 60)
    print("Audio Segment Editor (GUI)")
    print("=" * 60)

    # Parse arguments
    try:
        args = parse_edit_args()
    except SystemExit:
        return 1

    dir_path = Path(args.output_dir).resolve()

    # Find transcript.json
    json_path = find_transcript_json(dir_path)
    if json_path is None:
        print(f"Error: transcript.json not found in: {dir_path}")
        return 1

    # Import Flask app
    from gui.app import app, load_initial_data

    # Load initial data
    error = load_initial_data(str(dir_path))
    if error:
        print(f"Error: {error}")
        return 1

    # ポート決定
    if args.port is not None:
        port = args.port
    else:
        try:
            port = find_available_port()
        except RuntimeError as e:
            print(f"Error: {e}")
            return 1

    url = f'http://localhost:{port}'

    print(f"\nDirectory: {dir_path}")
    print(f"JSON file: {json_path.name}")
    print(f"URL: {url}")
    print("\nPress Ctrl+C to stop the server")

    # Open browser automatically
    if not args.no_browser:
        webbrowser.open(url)

    # Start Flask server
    app.run(debug=False, port=port, host='127.0.0.1')

    return 0


if __name__ == '__main__':
    sys.exit(main())
