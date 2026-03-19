"""
Phase 2: Whisperによる文字起こし（タイムスタンプ付き・多言語対応）
"""

import whisper
from pathlib import Path


def transcribe(video_path: str, language: str = None, model_size: str = "base") -> list[dict]:
    """
    動画/音声ファイルを文字起こしする。

    Args:
        video_path: 動画ファイルのパス
        language: 言語コード（例: "ja", "en"）。None で自動検出
        model_size: Whisperモデル ("tiny", "base", "small", "medium", "large")
                    ※ base は速度重視。精度が必要なら "small" 以上を推奨

    Returns:
        [{"start": 0.0, "end": 5.2, "text": "..."}, ...]
    """
    print(f"  Whisperモデル読み込み中 ({model_size})...")
    model = whisper.load_model(model_size)

    options = {"verbose": False}
    if language:
        options["language"] = language

    print(f"  文字起こし実行中（言語: {language or '自動検出'}）...")
    result = model.transcribe(str(Path(video_path).expanduser().resolve()), **options)

    detected_lang = result.get("language", "unknown")
    print(f"  検出言語: {detected_lang}")

    segments = [
        {
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip(),
            "language": detected_lang,
        }
        for seg in result["segments"]
        if seg["text"].strip()
    ]

    print(f"  セグメント数: {len(segments)}")
    return segments


def segments_to_text(segments: list[dict]) -> str:
    """セグメントリストを1つのテキストに結合"""
    return "\n".join(f"[{s['start']:.1f}s] {s['text']}" for s in segments)
