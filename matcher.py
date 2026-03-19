"""
Phase 2: キャプチャ ↔ 文字起こしセグメントのマッチング
"""


def match_captures_to_segments(
    captures: list[dict],
    segments: list[dict],
    context_window: float = 10.0,
) -> list[dict]:
    """
    各キャプチャのタイムスタンプ前後 context_window 秒の発言テキストを紐づける。

    Args:
        captures: [{"timestamp": 10.5, "path": "...", ...}]
        segments: [{"start": 9.0, "end": 14.0, "text": "..."}]
        context_window: キャプチャの前後何秒の発言を取得するか

    Returns:
        captures に "related_text" を追加したリスト
    """
    result = []
    for cap in captures:
        ts = cap["timestamp"]
        related = []
        for seg in segments:
            # キャプチャ時刻の前後 context_window 秒に重なるセグメントを収集
            if seg["start"] <= ts + context_window and seg["end"] >= ts - context_window:
                related.append(seg["text"])
        cap = dict(cap)
        cap["related_text"] = " ".join(related).strip()
        result.append(cap)
    return result
