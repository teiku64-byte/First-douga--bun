"""
Phase 1: FFmpegによるシーンチェンジ検出 + キャプチャ抽出
"""

import subprocess
import re
import os
import shutil
from pathlib import Path
from PIL import Image


FFMPEG = str(Path.home() / "bin" / "ffmpeg")


def check_ffmpeg():
    result = subprocess.run([FFMPEG, "-version"], capture_output=True)
    return result.returncode == 0


def extract_scene_change_timestamps(video_path: str, threshold: float = 0.35) -> list[float]:
    """
    シーンチェンジを検出してタイムスタンプ（秒）のリストを返す
    """
    cmd = [
        FFMPEG, "-i", video_path,
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stderr

    timestamps = []
    for line in output.splitlines():
        if "pts_time:" in line:
            match = re.search(r"pts_time:([\d.]+)", line)
            if match:
                timestamps.append(float(match.group(1)))

    return sorted(timestamps)


def get_video_duration(video_path: str) -> float:
    """動画の長さ（秒）を取得"""
    cmd = [
        FFMPEG, "-i", video_path,
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", result.stderr)
    if match:
        h, m, s = int(match.group(1)), int(match.group(2)), float(match.group(3))
        return h * 3600 + m * 60 + s
    return 0.0


def merge_with_interval_cap(scene_timestamps: list[float], duration: float, max_interval: float = 120.0, max_captures: int = 30) -> list[float]:
    """
    シーンチェンジ timestamps に「最大N秒間隔でキャプチャが空白にならない」保証を追加。
    先頭（5秒）と末尾付近も必ず含める。
    """
    timestamps = [5.0] if duration > 10 else [0.0]

    for ts in scene_timestamps:
        if ts < 5.0:
            continue
        if timestamps and (ts - timestamps[-1]) < 3.0:
            continue
        timestamps.append(ts)

    # 最大間隔を超えている区間に補完
    filled = []
    for i, ts in enumerate(timestamps):
        filled.append(ts)
        if i + 1 < len(timestamps):
            gap = timestamps[i + 1] - ts
            if gap > max_interval:
                steps = int(gap // max_interval)
                for j in range(1, steps + 1):
                    filled.append(ts + max_interval * j)

    # 末尾付近
    if duration > 30 and (not filled or duration - filled[-1] > 30):
        filled.append(max(duration - 10, 0))

    filled = sorted(set(filled))

    # 上限でフィルタ（均等間引き）
    if len(filled) > max_captures:
        step = len(filled) / max_captures
        filled = [filled[int(i * step)] for i in range(max_captures)]

    return filled


def extract_frame(video_path: str, timestamp: float, output_path: str, max_width: int = 1280) -> bool:
    """指定タイムスタンプのフレームを抽出してJPEGで保存（200KB以下にリサイズ）"""
    tmp_path = output_path + ".tmp.jpg"
    cmd = [
        FFMPEG, "-ss", str(timestamp), "-i", video_path,
        "-frames:v", "1", "-q:v", "3", tmp_path, "-y"
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0 or not os.path.exists(tmp_path):
        return False

    try:
        img = Image.open(tmp_path)
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)

        quality = 82
        img.save(output_path, "JPEG", quality=quality, optimize=True)

        while os.path.getsize(output_path) > 200 * 1024 and quality > 40:
            quality -= 10
            img.save(output_path, "JPEG", quality=quality, optimize=True)

        os.remove(tmp_path)
        return True
    except Exception:
        if os.path.exists(tmp_path):
            shutil.move(tmp_path, output_path)
        return True


def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def extract_captures(video_path: str, output_dir: str, threshold: float = 0.35, max_captures: int = 30) -> list[dict]:
    """
    メイン関数: シーンチェンジ検出 → フレーム抽出 → キャプチャ情報リストを返す
    """
    video_path = str(Path(video_path).expanduser().resolve())
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")

    output_dir = str(Path(output_dir).expanduser().resolve())
    os.makedirs(output_dir, exist_ok=True)

    print(f"[1/3] 動画情報を取得中...")
    duration = get_video_duration(video_path)
    print(f"      動画の長さ: {format_timestamp(duration)} ({duration:.1f}秒)")

    print(f"[2/3] シーンチェンジを検出中 (threshold={threshold})...")
    scene_ts = extract_scene_change_timestamps(video_path, threshold)
    print(f"      シーンチェンジ検出数: {len(scene_ts)}箇所")

    timestamps = merge_with_interval_cap(scene_ts, duration, max_captures=max_captures)
    print(f"      抽出対象フレーム数: {len(timestamps)}枚")

    print(f"[3/3] フレームを抽出中...")
    captures = []
    for i, ts in enumerate(timestamps):
        out_path = os.path.join(output_dir, f"frame_{i+1:04d}.jpg")
        ok = extract_frame(video_path, ts, out_path)
        if ok and os.path.exists(out_path):
            size_kb = os.path.getsize(out_path) // 1024
            captures.append({
                "index": i + 1,
                "timestamp": ts,
                "timestamp_str": format_timestamp(ts),
                "path": out_path,
                "size_kb": size_kb,
            })
            print(f"      [{i+1:2d}/{len(timestamps)}] {format_timestamp(ts)} → frame_{i+1:04d}.jpg ({size_kb}KB)")
        else:
            print(f"      [{i+1:2d}/{len(timestamps)}] {format_timestamp(ts)} → 抽出失敗")

    print(f"\n完了: {len(captures)}枚のキャプチャを {output_dir} に保存しました")
    return captures
