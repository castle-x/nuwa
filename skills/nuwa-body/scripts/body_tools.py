"""身材锁定图工具：裁出无头版，计算头身比、腰线和腿长比例。

  python3 body_tools.py crop 锁定图.png --y 155 -o 锁定图-无头.png
  python3 body_tools.py ratio --top 120 --chin 245 --waist 520 --crotch 600 --feet 1100
"""
import argparse
import sys
from pathlib import Path


def crop(args):
    try:
        from PIL import Image
    except ImportError:
        sys.exit("需要 Pillow：python3 -m pip install pillow")
    img = Image.open(args.image)
    if not 0 < args.y < img.height:
        sys.exit(f"--y 要在 1 到 {img.height - 1} 之间（图片高 {img.height}）")
    out = Path(args.out) if args.out else Path(args.image).with_name(Path(args.image).stem + "-无头.png")
    img.crop((0, args.y, img.width, img.height)).save(out)
    print(f"已裁出 {out}，{img.width}×{img.height - args.y}，裁掉上方 {args.y} 像素")


def ratio(args):
    height = args.feet - args.top
    head = args.chin - args.top
    if height <= 0 or head <= 0:
        sys.exit("像素高度要满足：头顶 < 下巴 < 脚底")
    print(f"头身比  1:{height / head:.1f}（全身 {height} 像素，头 {head} 像素）")
    if args.waist is not None:
        print(f"腰线    离地约身高的 {(args.feet - args.waist) / height:.0%}（腰部最细处到脚底）")
    if args.crotch is not None:
        print(f"腿长    占身高的 {(args.feet - args.crotch) / height:.0%}（裆部到脚底）")


def main():
    ap = argparse.ArgumentParser(description="身材锁定图工具")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("crop", help="从脖子处整行裁掉头部")
    c.add_argument("image")
    c.add_argument("--y", type=int, required=True, help="裁切线的像素高度，以上全部裁掉")
    c.add_argument("-o", "--out")
    c.set_defaults(func=crop)
    r = sub.add_parser("ratio", help="按关键点像素高度计算比例")
    for name, need in [("top", True), ("chin", True), ("feet", True), ("waist", False), ("crotch", False)]:
        r.add_argument(f"--{name}", type=int, required=need)
    r.set_defaults(func=ratio)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
