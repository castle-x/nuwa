"""身材锁定图工具：局部抠头出无头版，计算头身比、腰线和腿长比例。

  python3 body_tools.py dehead 锁定图.png --head 291,26,441,230 --mosaic 925,45,1075,240 -o 锁定图-无头.png
  python3 body_tools.py ratio --top 120 --chin 245 --waist 520 --crotch 600 --feet 1100

去头一律用 dehead（用户 2026-11-17 定的规范）：正面格用椭圆遮罩盖住头部，按行用头部左右两侧的背景
插值补齐（--head）；侧面格不抠头，只给脸打码（--mosaic），保住头的大小和轮廓，头身比不崩。
打码一律柔和揉开，不用硬方块（用户 2026-11-17 定）；胸前透出的凸点用 --dot 同样柔和打码。
脖子从下巴以下保留，画布尺寸和其余格子不动。背面格不处理。
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


def soft_patch(img, box, ellipse, block):
    """在 box 区域内，把 ellipse（相对 box 的坐标）里的内容揉开：粗像素化、平滑放大、模糊，边缘羽化。"""
    from PIL import Image, ImageDraw, ImageFilter
    reg = img.crop(box)
    blk = max(4, block)
    small = reg.resize((max(1, reg.width // blk), max(1, reg.height // blk)), Image.BILINEAR)
    smooth = small.resize(reg.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(blk / 2))
    mask = Image.new("L", reg.size, 0)
    ImageDraw.Draw(mask).ellipse(ellipse, fill=255)
    ew = ellipse[2] - ellipse[0]
    mask = mask.filter(ImageFilter.GaussianBlur(max(1, ew / 8)))
    reg.paste(smooth, (0, 0), mask)
    out = img.copy()
    out.paste(reg, box[:2])
    return out


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
    for spec in args.head or []:
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
    result = Image.composite(bg, im, soft)
    # 侧脸打码：只把五官区域揉掉，头的轮廓和大小保留，头身比不变。
    # 默认柔和打码（用户 2026-11-17 定）：粗像素化后双线性放大再高斯模糊，椭圆遮罩羽化边缘，
    # 看上去像失焦揉开，不留硬方块；硬方块会让下游模型学到马赛克纹理。--hard 才用旧的方块马赛克。
    for spec in args.mosaic or []:
        try:
            l, t, r, b = (int(v) for v in spec.split(","))
        except ValueError:
            sys.exit(f"--mosaic 要写成 左,上,右,下 四个像素值，收到 {spec}")
        if args.hard:
            region = result.crop((l, t, r, b))
            small = region.resize((max(1, (r - l) // args.block), max(1, (b - t) // args.block)), Image.BILINEAR)
            result.paste(small.resize(region.size, Image.NEAREST), (l, t))
            continue
        m = max(r - l, b - t) // 4
        box = (max(0, l - m), max(0, t - m), min(W, r + m), min(H, b + m))
        result = soft_patch(result, box, (l - box[0], t - box[1], r - box[0], b - box[1]), args.block)
    # 敏感点打码（胸前透出的凸点等）：同样的柔和方式，圆形
    for spec in args.dot or []:
        try:
            x, y, rad = (int(v) for v in spec.split(","))
        except ValueError:
            sys.exit(f"--dot 要写成 x,y,半径 三个像素值，收到 {spec}")
        box = (max(0, x - 2 * rad), max(0, y - 2 * rad), min(W, x + 2 * rad), min(H, y + 2 * rad))
        e = (x - rad - box[0], y - rad - box[1], x + rad - box[0], y + rad - box[1])
        result = soft_patch(result, box, e, max(4, rad // 2))
    out = Path(args.out) if args.out else Path(args.image).with_name(Path(args.image).stem + "-无头.png")
    result.save(out)
    print(f"已处理 {out}，{W}×{H}（尺寸不变），抠头 {len(args.head or [])} 个，打码 {len(args.mosaic or [])} 处，敏感点 {len(args.dot or [])} 处")


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
    h.add_argument("--head", action="append", help="正面格要抠掉的头：左,头顶,右,下巴 的像素坐标，左右含耳朵；可写多次")
    h.add_argument("--mosaic", action="append", help="侧面格要打码的脸：左,上,右,下 的像素坐标，盖住额头到下巴、鼻尖到耳前，头发和发髻留着；可写多次")
    h.add_argument("--dot", action="append", help="敏感点柔和打码（例如胸前透出的凸点）：x,y,半径；全身格半径约 11～14，特写格约 24；可写多次")
    h.add_argument("--block", type=int, default=14, help="打码的像素化粒度，默认 14 像素；柔和模式下越大越糊")
    h.add_argument("--hard", action="store_true", help="侧脸改用旧的硬方块马赛克（不推荐）")
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
    if args.cmd == "dehead" and not (args.head or args.mosaic or args.dot):
        ap.error("dehead 至少要给一个 --head、--mosaic 或 --dot")
    args.func(args)


if __name__ == "__main__":
    main()
