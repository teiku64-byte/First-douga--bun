"""
Phase 2: APIキー不要のHTML議事録生成
文字起こしテキスト＋キャプチャ画像をタイムライン順に並べたHTMLを生成する。
"""

import base64
import os
from datetime import datetime
from pathlib import Path
from capture_extractor import format_timestamp


def generate_minutes(
    segments: list[dict],
    captures: list[dict],
    mode: str = "demo_followup",
    translate_to_ja: bool = False,
    video_path: str = "",
) -> str:
    """
    APIキー不要でHTMLを生成する。
    文字起こし＋キャプチャをタイムライン順に並べてHTML化。
    """
    video_name = Path(video_path).name if video_path else "録画"
    now = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    detected_lang = segments[0].get("language", "") if segments else ""
    is_foreign = detected_lang not in ("ja", "japanese", "")

    mode_label = {
        "demo_followup": "デモフォローアップ",
        "webinar_study": "ウェビナー学習資料",
    }.get(mode, "議事録")

    lang_note = f"（元言語: {detected_lang}）" if is_foreign else ""

    # 冒頭3セグメントを概要として表示
    intro_text = " ".join(s["text"] for s in segments[:3]) if segments else ""

    # タイムラインカード（キャプチャ＋発言テキスト）
    timeline_html = ""
    for cap in captures:
        if not os.path.exists(cap["path"]):
            continue
        with open(cap["path"], "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        related = cap.get("related_text", "").strip()
        ts_str = cap.get("timestamp_str", format_timestamp(cap["timestamp"]))

        timeline_html += f"""
    <div class="cap-card">
      <div class="cap-meta">
        <span class="ts-badge">{ts_str}</span>
        <span class="cap-idx">シーン {cap['index']}</span>
      </div>
      <img src="data:image/jpeg;base64,{b64}" alt="scene_{cap['index']}" />
      <p class="cap-text">{related if related else '（この時間帯の発言なし）'}</p>
    </div>
"""

    # 全文テキスト（折りたたみ）
    full_text_rows = ""
    for seg in segments:
        ts = format_timestamp(seg["start"])
        text = seg["text"].replace("<", "&lt;").replace(">", "&gt;")
        full_text_rows += f'<tr><td class="ts-cell">{ts}</td><td>{text}</td></tr>\n'

    total_caps = len(captures)
    total_segs = len(segments)
    duration_str = format_timestamp(segments[-1]["end"]) if segments else "—"

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{mode_label} — {video_name}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif;
      background: #f1f5f9; color: #1e293b; padding: 32px 24px;
      max-width: 1100px; margin: 0 auto;
    }}

    /* ヘッダー */
    .header {{
      background: linear-gradient(135deg, #1e3a5f 0%, #0284c7 100%);
      border-radius: 16px; padding: 28px 32px; color: #fff; margin-bottom: 24px;
    }}
    .header h1 {{ font-size: 22px; font-weight: 700; }}
    .header .sub {{ font-size: 13px; opacity: 0.8; margin-top: 4px; }}
    .chips {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }}
    .chip {{
      background: rgba(255,255,255,0.18); border-radius: 6px;
      padding: 3px 10px; font-size: 12px; font-weight: 600;
    }}

    /* セクション共通 */
    .section {{
      background: #fff; border-radius: 14px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.07); margin-bottom: 20px; overflow: hidden;
    }}
    .section-header {{
      display: flex; align-items: center; gap: 12px;
      padding: 16px 20px; border-bottom: 1px solid #f1f5f9;
    }}
    .section-icon {{
      width: 36px; height: 36px; border-radius: 8px;
      display: flex; align-items: center; justify-content: center; font-size: 18px;
    }}
    .section-header h2 {{ font-size: 16px; font-weight: 700; }}
    .section-body {{ padding: 20px; }}

    /* 概要 */
    .intro-text {{
      font-size: 14px; line-height: 1.8; color: #334155;
      border-left: 3px solid #0284c7; padding-left: 14px;
    }}

    /* タイムライン */
    .timeline {{ display: flex; flex-direction: column; gap: 24px; }}
    .cap-card {{
      border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden;
    }}
    .cap-meta {{
      display: flex; align-items: center; gap: 10px;
      padding: 10px 14px; background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
    }}
    .ts-badge {{
      background: #0284c7; color: #fff; border-radius: 6px;
      padding: 2px 9px; font-size: 12px; font-weight: 700;
      font-family: monospace; letter-spacing: 0.5px;
    }}
    .cap-idx {{ font-size: 12px; color: #64748b; font-weight: 600; }}
    .cap-card img {{ width: 100%; display: block; }}
    .cap-text {{
      padding: 12px 14px; font-size: 13px; color: #475569;
      line-height: 1.7; background: #fff;
    }}

    /* 全文テキスト */
    details summary {{
      cursor: pointer; font-weight: 600; font-size: 14px;
      color: #0284c7; padding: 4px 0;
    }}
    .transcript-table {{
      width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 12px;
    }}
    .transcript-table tr:nth-child(even) {{ background: #f8fafc; }}
    .transcript-table td {{ padding: 6px 10px; vertical-align: top; }}
    .ts-cell {{
      white-space: nowrap; color: #0284c7; font-family: monospace;
      font-size: 12px; font-weight: 600; width: 60px;
    }}

    .footer {{
      text-align: center; color: #94a3b8; font-size: 12px; margin-top: 24px;
    }}
  </style>
</head>
<body>

  <div class="header">
    <h1>🎬 {mode_label}{lang_note}</h1>
    <div class="sub">{video_name}</div>
    <div class="chips">
      <span class="chip">📸 {total_caps}枚のキャプチャ</span>
      <span class="chip">🗒 {total_segs}セグメント</span>
      <span class="chip">⏱ {duration_str}</span>
      <span class="chip">🕐 {now}</span>
    </div>
  </div>

  <!-- 概要 -->
  <div class="section">
    <div class="section-header">
      <div class="section-icon" style="background:#e0f2fe;color:#0284c7;">📋</div>
      <div><h2>概要</h2></div>
    </div>
    <div class="section-body">
      <p class="intro-text">{intro_text}</p>
    </div>
  </div>

  <!-- 画面タイムライン -->
  <div class="section">
    <div class="section-header">
      <div class="section-icon" style="background:#fef3c7;color:#d97706;">🖥</div>
      <div><h2>画面タイムライン</h2></div>
    </div>
    <div class="section-body">
      <div class="timeline">
        {timeline_html}
      </div>
    </div>
  </div>

  <!-- 全文テキスト -->
  <div class="section">
    <div class="section-header">
      <div class="section-icon" style="background:#f0fdf4;color:#16a34a;">📝</div>
      <div><h2>全文テキスト</h2></div>
    </div>
    <div class="section-body">
      <details>
        <summary>クリックして全文を表示</summary>
        <table class="transcript-table">
          {full_text_rows}
        </table>
      </details>
    </div>
  </div>

  <div class="footer">video-minutes — APIキー不要モードで生成</div>

</body>
</html>
"""
