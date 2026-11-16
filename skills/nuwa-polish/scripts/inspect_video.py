"""视频抽帧检查：全片总览图，以及指定区域的连续帧条带。需要 ffmpeg 和 ffprobe。

  python3 inspect_video.py 视频.mp4 -o 检查帧/
  python3 inspect_video.py 视频.mp4 -o 检查帧/ --crop 250,140,200,200 --start 2.5 --end 4.5
"""
import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames:format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    s = d["streams"][0]
    num, den = map(int, s["r_frame_rate"].split("/"))
    return {"width": s["width"], "height": s["height"], "fps": num / den,
            "frames": int(s.get("nb_read_frames", 0)), "duration": float(d["format"]["duration"])}


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


def main():
    ap = argparse.ArgumentParser(description="视频抽帧检查")
    ap.add_argument("video")
    ap.add_argument("-o", "--out", default="检查帧")
    ap.add_argument("--every", type=float, default=0.5, help="总览图每隔几秒取一帧，默认 0.5")
    ap.add_argument("--cols", type=int, default=8, help="每行几格，默认 8")
    ap.add_argument("--width", type=int, default=240, help="总览图每格宽度，默认 240")
    ap.add_argument("--crop", help="裁剪区域 x,y,宽,高（原视频像素），输出连续帧条带")
    ap.add_argument("--start", type=float, default=0.0, help="条带起始秒")
    ap.add_argument("--end", type=float, help="条带结束秒，默认到结尾")
    ap.add_argument("--step", type=int, default=3, help="条带每隔几帧取一帧，默认 3")
    args = ap.parse_args()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        sys.exit("需要先安装 ffmpeg（含 ffprobe）")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    info = probe(args.video)
    lines = [f"{k}: {v}" for k, v in info.items()]
    (out / "info.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

    n = max(1, int(info["duration"] / args.every))
    rows = math.ceil(n / args.cols)
    ffmpeg("-i", args.video, "-vf",
           f"fps=1/{args.every},scale={args.width}:-2,tile={args.cols}x{rows}", "-frames:v", 1,
           out / "sheet.png")
    print(f"总览图：{out / 'sheet.png'}（每 {args.every} 秒一帧，共 {n} 帧）")

    if args.crop:
        x, y, w, h = map(int, args.crop.split(","))
        end = args.end if args.end is not None else info["duration"]
        f0, f1 = int(args.start * info["fps"]), int(end * info["fps"])
        count = max(1, (f1 - f0 + args.step - 1) // args.step)
        cols = min(count, args.cols)
        ffmpeg("-i", args.video, "-vf",
               f"select='between(n\\,{f0}\\,{f1 - 1})*not(mod(n-{f0}\\,{args.step}))',"
               f"crop={w}:{h}:{x}:{y},tile={cols}x{math.ceil(count / cols)}",
               "-frames:v", 1, "-fps_mode", "passthrough", out / "crop.png")
        print(f"局部条带：{out / 'crop.png'}（第 {f0}～{f1} 帧，每 {args.step} 帧一张，共 {count} 张）")


if __name__ == "__main__":
    main()
