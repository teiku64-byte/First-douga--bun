"""
Phase 1: キャプチャ一覧のHTMLプレビュー生成
"""

import base64
import os
from pathlib import Path
from datetime import datetime


def build_preview_html(captures: list[dict], video_path: str) -> str:
    video_name = Path(video_path).name
    now = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    total = len(captures)

    cards_html = ""
    for cap in captures:
        if not os.path.exists(cap["path"]):
            continue
        with open(cap["path"], "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        cards_html += f"""
        <div class="capture-card">
          <div class="capture-meta">
            <span class="ts-badge">{cap['timestamp_str']}</span>
            <span class="cap-label">シーン {cap['index']}</span>
            <span class="cap-size">{cap['size_kb']} KB</span>
          </div>
          <img src="data:image/jpeg;base64,{b64}" alt="frame_{cap['index']:04d}" />
        </div>
"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>キャプチャプレビュー — {video_name}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif;
      background: #f1f5f9; color: #1e293b; padding: 32px 24px;
    }}
    .header {{
      background: linear-gradient(135deg, #1e3a5f 0%, #0284c7 100%);
      border-radius: 16px; padding: 28px 32px; color: #fff; margin-bottom: 28px;
    }}
    .header h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 6px; }}
    .meta {{ font-size: 13px; opacity: 0.8; display: flex; gap: 20px; flex-wrap: wrap; margin-top: 10px; }}
    .meta-chip {{
      background: rgba(255,255,255,0.15); border-radius: 6px;
      padding: 3px 10px; font-size: 12px; font-weight: 600;
    }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px; }}
    .capture-card {{
      background: #fff; border-radius: 12px; overflow: hidden;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08); transition: box-shadow 0.2s;
    }}
    .capture-card:hover {{ box-shadow: 0 4px 16px rgba(0,0,0,0.14); }}
    .capture-meta {{
      display: flex; align-items: center; gap: 8px;
      padding: 10px 14px; border-bottom: 1px solid #f1f5f9;
    }}
    .ts-badge {{
      background: #0284c7; color: #fff; border-radius: 6px;
      padding: 2px 9px; font-size: 12px; font-weight: 700;
      font-family: monospace; letter-spacing: 0.5px;
    }}
    .cap-label {{ font-weight: 600; font-size: 13px; color: #334155; }}
    .cap-size {{ margin-left: auto; font-size: 11px; color: #94a3b8; }}
    .capture-card img {{ width: 100%; display: block; }}
    .footer {{ text-align: center; color: #94a3b8; font-size: 12px; margin-top: 32px; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>🎬 キャプチャプレビュー</h1>
    <p style="font-size:14px;opacity:0.9;margin-top:4px;">{video_name}</p>
    <div class="meta">
      <span class="meta-chip">📸 {total}枚のキャプチャ</span>
      <span class="meta-chip">🕐 生成: {now}</span>
    </div>
  </div>
  <div class="grid">{cards_html}</div>
  <div class="footer">video-minutes / Phase 1 — capture_extractor.py で自動生成</div>
</body>
</html>
"""


def save_preview(captures: list[dict], video_path: str, output_dir: str) -> str:
    html = build_preview_html(captures, video_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(output_dir, f"preview_{timestamp}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
