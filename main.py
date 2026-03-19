"""
video-minutes / Phase 1+2 エントリーポイント

使い方:
  # Phase 1のみ（キャプチャ抽出 + プレビュー）
  python3 main.py --input video.mp4 --phase 1

  # Phase 1+2（文字起こし + 議事録生成）
  python3 main.py --input video.mp4

  # 英語動画 → 日本語議事録
  python3 main.py --input webinar.mp4 --lang en --translate

  # オプション全指定例
  python3 main.py --input demo.mp4 --mode demo_followup --lang en --translate --max-caps 20 --threshold 0.3
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from capture_extractor import check_ffmpeg, extract_captures
from html_preview import save_preview
from transcriber import transcribe
from matcher import match_captures_to_segments
from minutes_generator import generate_minutes


def main():
    parser = argparse.ArgumentParser(
        description="録画動画から文字起こし＋キャプチャを自動抽出して議事録HTMLを生成します"
    )
    parser.add_argument("--input", "-i", required=True,
                        help="入力動画ファイルのパス（mp4, mov, webm）")
    parser.add_argument("--phase", type=int, default=2, choices=[1, 2],
                        help="実行フェーズ: 1=キャプチャ抽出のみ, 2=文字起こし+議事録生成（デフォルト: 2）")
    parser.add_argument("--mode", default="demo_followup",
                        choices=["demo_followup", "webinar_study"],
                        help="議事録スタイル（デフォルト: demo_followup）")
    parser.add_argument("--lang", default=None,
                        help="文字起こし言語コード（例: ja, en）省略時は自動検出")
    parser.add_argument("--translate", action="store_true",
                        help="外国語音声を日本語議事録に翻訳する")
    parser.add_argument("--whisper-model", default="base",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisperモデルサイズ（デフォルト: base）")
    parser.add_argument("--threshold", "-t", type=float, default=0.35,
                        help="シーンチェンジ検出感度 0.2〜0.5（デフォルト: 0.35）")
    parser.add_argument("--max-caps", "-m", type=int, default=30,
                        help="最大キャプチャ枚数（デフォルト: 30）")
    parser.add_argument("--output-dir", "-o", default=None,
                        help="出力ディレクトリ（省略時: output/）")
    args = parser.parse_args()

    # --- 事前チェック ---
    if not check_ffmpeg():
        print("エラー: ffmpegが見つかりません。~/bin/ffmpeg を確認してください。")
        sys.exit(1)

    video_path = str(Path(args.input).expanduser().resolve())
    if not os.path.exists(video_path):
        print(f"エラー: ファイルが見つかりません: {video_path}")
        sys.exit(1)

    script_dir = Path(__file__).parent
    output_root = Path(args.output_dir).expanduser().resolve() if args.output_dir else script_dir / "output"
    captures_dir = str(output_root / "captures")

    print("=" * 60)
    print("  video-minutes / Phase", args.phase)
    print("=" * 60)
    print(f"  入力    : {Path(video_path).name}")
    print(f"  モード  : {args.mode}")
    print(f"  言語    : {args.lang or '自動検出'}")
    print(f"  翻訳    : {'有効（→日本語）' if args.translate else '無効'}")
    print(f"  感度    : {args.threshold}  最大枚数: {args.max_caps}")
    print("=" * 60)
    print()

    # === Phase 1: キャプチャ抽出 ===
    print("▶ Phase 1: キャプチャ抽出")
    captures = extract_captures(
        video_path=video_path,
        output_dir=captures_dir,
        threshold=args.threshold,
        max_captures=args.max_caps,
    )

    if not captures:
        print("\n⚠️  キャプチャが抽出できませんでした。--threshold を下げて再試行してください。")
        sys.exit(1)

    # Phase 1のみの場合はプレビューを表示して終了
    if args.phase == 1:
        print("\nHTMLプレビューを生成中...")
        preview_path = save_preview(captures, video_path, str(output_root))
        subprocess.run(["open", preview_path])
        print(f"\n✅ Phase 1 完了！ → {preview_path}")
        return

    # === Phase 2: 文字起こし ===
    print("\n▶ Phase 2-A: 文字起こし（Whisper）")
    segments = transcribe(
        video_path=video_path,
        language=args.lang,
        model_size=args.whisper_model,
    )

    if not segments:
        print("⚠️  文字起こし結果が空でした。動画に音声が含まれているか確認してください。")
        sys.exit(1)

    # キャプチャ ↔ 発言マッチング
    print("\n▶ Phase 2-B: キャプチャ ↔ 発言テキストのマッチング")
    matched_captures = match_captures_to_segments(captures, segments)
    print(f"  {len(matched_captures)}枚のキャプチャに発言テキストを紐づけました")

    # 自動翻訳の判定（--translateフラグ or 日本語以外が検出された場合）
    detected_lang = segments[0].get("language", "ja")
    should_translate = args.translate or (detected_lang not in ("ja", "japanese"))
    if should_translate and not args.translate:
        print(f"  ℹ️  {detected_lang}語を検出。自動的に日本語議事録に翻訳します。")

    # === Phase 2: 議事録生成 ===
    print("\n▶ Phase 2-C: 議事録生成（Claude API）")
    html = generate_minutes(
        segments=segments,
        captures=matched_captures,
        mode=args.mode,
        translate_to_ja=should_translate,
        video_path=video_path,
    )

    # HTML保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_html = str(output_root / f"議事録_{timestamp}.html")
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html)

    subprocess.run(["open", output_html])

    print(f"\n✅ 完了！")
    print(f"   キャプチャ : {len(captures)}枚 → {captures_dir}")
    print(f"   議事録HTML : {output_html}")


if __name__ == "__main__":
    main()
