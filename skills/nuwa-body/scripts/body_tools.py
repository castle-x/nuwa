"""身材锁定图工具：局部抠头出无头版，计算头身比、腰线和腿长比例。

  python3 body_tools.py dehead 锁定图.png --head 242,36,385,232 -o 锁定图-无头.png
  python3 body_tools.py ratio --top 120 --chin 245 --waist 520 --crotch 600 --feet 1100

去头一律用 dehead（用户 2026-11-17 定的规范）：只在露脸的格子里用椭圆遮罩盖住头部，
按行用头部左右两侧的背景插值补齐，脖子从下巴以下保留，画布尺寸和其余格子不动。
crop（整行横裁）只为旧记录保留，不再用于锁定图。
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


def dehead(args):
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError:
        sys.exit("需要 Pillow：python3 -m pip install pillow")
    im = Image.open(args.image).convert("RGB")
    W, H = im.size
    bg = im.copy()
    px, bp = im.load(), bg.load()
    mask = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask)
    for spec in args.head:
        try:
            l, t, r, chin = (int(v) for v in spec.split(","))
        except ValueError:
            sys.exit(f"--head 要写成 左,头顶,右,下巴 四个像素值，收到 {spec}")
        if not (0 <= l < r <= W and 0 <= t < chin <= H):
            sys.exit(f"--head {spec} 超出图片范围（{W}×{H}）或顺序不对")
        box = (l - args.pad, max(0, t - args.pad - 6), r + args.pad, chin + 6)
        draw.ellipse(box, fill=255)
        # 头顶到画面上边一并清掉，避免残留发丝
        draw.rectangle((box[0] + 20, 0, box[2] - 20, (box[1] + box[3]) // 2), fill=255)
        xl, xr = max(0, box[0] - 12), min(W - 1, box[2] + 12)
        for y in range(0, min(H, box[3] + 12)):
            def avg(x0):
                pts = [px[min(W - 1, max(0, x0 + k)), y] for k in range(-4, 5)]
                return [sum(c[i] for c in pts) / len(pts) for i in range(3)]
            left, right = avg(xl), avg(xr)
            for x in range(xl, xr + 1):
                f = (x - xl) / max(1, xr - xl)
                bp[x, y] = tuple(int(left[i] * (1 - f) + right[i] * f) for i in range(3))
    soft = mask.filter(ImageFilter.GaussianBlur(args.feather))
    out = Path(args.out) if args.out else Path(args.image).with_name(Path(args.image).stem + "-无头.png")
    Image.composite(bg, im, soft).save(out)
    print(f"已抠头 {out}，{W}×{H}（尺寸不变），处理 {len(args.head)} 个头部")


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
    h = sub.add_parser("dehead", help="局部抠头：椭圆遮罩盖住头部、背景按行补齐，画布不变（默认用这个）")
    h.add_argument("image")
    h.add_argument("--head", action="append", required=True, help="左,头顶,右,下巴 的像素坐标，左右含耳朵；多个露脸格子就写多次")
    h.add_argument("--pad", type=int, default=10, help="遮罩向外扩的像素，默认 10")
    h.add_argument("--feather", type=float, default=4, help="遮罩边缘羽化半径，默认 4")
    h.add_argument("-o", "--out")
    h.set_defaults(func=dehead)
    c = sub.add_parser("crop", help="（旧）从脖子处整行裁掉头部，锁定图不再用")
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
