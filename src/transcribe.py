"""Audio transcription using OpenAI Whisper."""
import whisper
import torch
from typing import Dict, List, Any
from pathlib import Path

from .utils import split_sentences_by_punctuation, split_sentences_with_positions


class Transcriber:
    """Handles audio transcription using Whisper."""

    def __init__(self, model_name: str = "base", language: str = None, device: str = None):
        """
        Initialize transcriber with Whisper model.

        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
            language: Language code for transcription (None for auto-detect)
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
        """
        # Auto-detect device if not specified
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = device

        # Display device info
        if device == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            print(f"Using GPU: {gpu_name}")
        else:
            print("Using CPU (GPU not available or not selected)")

        print(f"Loading Whisper model: {model_name} on {device}...")
        self.model = whisper.load_model(model_name, device=device)
        self.language = language

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file with timestamps.

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary containing transcription results with segments
        """
        print(f"Transcribing: {Path(audio_path).name}")

        # Transcribe with word-level timestamps
        result = self.model.transcribe(
            audio_path,
            language=self.language,
            word_timestamps=True,
            verbose=False
        )

        return result

    def get_segments(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract segment information from transcription result.
        Split sentences by Japanese punctuation marks (。！？).

        Args:
            result: Whisper transcription result

        Returns:
            List of segment dictionaries with start, end, and text (split by punctuation)
        """
        segments = []
        match_stats = {"matched": 0, "fallback": 0}

        for segment in result.get("segments", []):
            text = segment["text"].strip()

            # Split by punctuation (。！？)
            sentences = split_sentences_by_punctuation(text)

            if not sentences:
                # If no punctuation was found, use the whole segment
                sentences = [text]

            # Calculate timestamp for each sentence using word-level timestamps
            words = segment.get("words", [])

            if len(sentences) == 1:
                # Single sentence: use original segment timestamps
                segments.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": sentences[0],
                })
                match_stats["matched"] += 1
            else:
                # Multiple sentences: calculate timestamps based on word positions
                sentence_positions = split_sentences_with_positions(text)
                word_idx = 0

                for sentence_text, _, _ in sentence_positions:
                    # Track which words belong to this sentence
                    sentence_start_time = None
                    sentence_end_time = None

                    # Iterate through words and match them with sentence text
                    sentence_char_idx = 0
                    matched_any = False

                    while word_idx < len(words) and sentence_char_idx < len(sentence_text):
                        word_info = words[word_idx]
                        word = word_info.get("word", "").strip()

                        if not word:
                            word_idx += 1
                            continue

                        # Check if word matches at current position in sentence
                        remaining_sentence = sentence_text[sentence_char_idx:].lstrip()
                        if remaining_sentence.startswith(word):
                            word_start = word_info.get("start", segment["start"])
                            word_end = word_info.get("end", segment["end"])

                            if sentence_start_time is None:
                                sentence_start_time = word_start
                            sentence_end_time = word_end

                            sentence_char_idx += len(remaining_sentence) - len(remaining_sentence.lstrip()) + len(word)
                            word_idx += 1
                            matched_any = True
                        else:
                            # Word doesn't match, might be punctuation or mismatch
                            break

                    # Add sentence segment
                    if matched_any and sentence_start_time is not None:
                        segments.append({
                            "start": sentence_start_time,
                            "end": sentence_end_time,
                            "text": sentence_text,
                        })
                        match_stats["matched"] += 1
                    else:
                        # Fallback: use segment timestamps
                        segments.append({
                            "start": segment["start"],
                            "end": segment["end"],
                            "text": sentence_text,
                        })
                        match_stats["fallback"] += 1

        # Print matching statistics for debugging
        total = match_stats["matched"] + match_stats["fallback"]
        if total > 0:
            match_rate = (match_stats["matched"] / total) * 100
            print(f"[DEBUG] Sentence splitting: {match_stats['matched']}/{total} matched ({match_rate:.1f}%)")

        return segments
