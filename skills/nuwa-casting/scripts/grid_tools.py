"""面部锁定图工具：把 2×2 四视图切成四张单独的 1:1 图。

  python3 grid_tools.py split 面部锁定图.png
  python3 grid_tools.py split 面部锁定图.png --keep 0.85 -o 输出目录
"""
import argparse
import sys
from pathlib import Path

VIEWS = ["正面", "45度", "侧面", "背面"]  # 左上、右上、左下、右下


def split(args):
    try:
        from PIL import Image
    except ImportError:
        sys.exit("需要 Pillow：python3 -m pip install pillow")
    img = Image.open(args.image).convert("RGB")
    w, h = img.width // 2, img.height // 2
    if abs(img.width - img.height) > max(img.width, img.height) * 0.02:
        print(f"提醒：图片是 {img.width}×{img.height}，不是方图，切出的四格也不会是 1:1")
    if not 0.3 <= args.keep <= 1:
        sys.exit("--keep 要在 0.3 到 1 之间")
    out = Path(args.out) if args.out else Path(args.image).parent
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(args.image).stem
    for i, name in enumerate(VIEWS):
        x, y = (i % 2) * w, (i // 2) * h
        side = min(w, round(h * args.keep))  # 只保留上部时，左右等量收窄，切出来仍是方图
        x += (w - side) // 2
        cell = img.crop((x, y, x + side, y + side))
        dst = out / f"{stem}-{name}.png"
        cell.save(dst)
        print(f"{dst}  {cell.width}×{cell.height}")


def main():
    ap = argparse.ArgumentParser(description="面部锁定图工具")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split", help="按四等分切成四张单视角图")
    s.add_argument("image")
    s.add_argument("--keep", type=float, default=1.0, help="每格保留上面多少比例，用来裁掉底部的衣服，左右等量收窄保持方图，默认 1")
    s.add_argument("-o", "--out", help="输出目录，默认和原图同目录")
    s.set_defaults(func=split)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
