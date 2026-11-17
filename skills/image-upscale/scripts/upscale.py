"""保真超分命令行。用任意 python3 运行，会自动切换到安装好的环境。

  python3 upscale.py 图片或目录 -o 输出目录 --target 3840 --check --compare
  python3 upscale.py 图片 -m dat2 --target 7680   # 换 DAT2（默认混合 0.2）
"""
import argparse
import os
from html import escape
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config  # noqa: E402

if not config.in_venv():
    if not config.venv_python().exists():
        sys.exit(f"还没安装。先运行：python3 {Path(__file__).with_name('setup.py')}")
    sys.exit(subprocess.call([str(config.venv_python()), *sys.argv]))

from PIL import Image  # noqa: E402

import sr_core  # noqa: E402

EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
TEMPLATE = Path(__file__).parent.parent / "assets" / "compare.html"


def collect(inputs):
    for p in map(Path, inputs):
        if p.is_dir():
            yield from sorted(f for f in p.iterdir() if f.suffix.lower() in EXTS)
        else:
            yield p


def lower_priority():
    if hasattr(os, "nice"):
        os.nice(10)
    elif sys.platform == "win32":
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.SetPriorityClass(k32.GetCurrentProcess(), 0x4000)  # BELOW_NORMAL_PRIORITY_CLASS


def write_compare(dst_dir, src, sr, title, method):
    """生成前后对比页：拖动中线对比，支持缩放和平移。"""
    dst_dir.mkdir(parents=True, exist_ok=True)
    src.convert("RGB").save(dst_dir / "before.webp", quality=95)
    sr.save(dst_dir / "after.webp", quality=92)
    html = TEMPLATE.read_text(encoding="utf-8")
    for k, v in {"TITLE": escape(title), "METHOD": escape(method), "BW": src.width, "BH": src.height,
                 "AW": sr.width, "AH": sr.height}.items():
        html = html.replace("{{" + k + "}}", str(v))
    (dst_dir / "index.html").write_text(html, encoding="utf-8")
    return dst_dir / "index.html"


def main():
    ap = argparse.ArgumentParser(description="非生成式超分：放大但不重绘，脸和细节保持一致")
    ap.add_argument("inputs", nargs="+", help="图片文件或目录")
    ap.add_argument("-m", "--model", default="hat",
                    help="模型别名 " + "；".join(f"{k}={v}" for k, v in config.DESCRIPTIONS.items())
                    + "。也可以给 .pth / .safetensors 路径")
    ap.add_argument("-o", "--out", default="upscaled", help="输出目录")
    ap.add_argument("--target", type=int, help="输出长边像素，如 3840(4K) / 7680(8K)；默认按模型倍率放大 4 倍")
    ap.add_argument("--blend", type=float, default=None,
                    help="与 Lanczos 混合比例 0~1，压掉模型造出的假纹理。默认 HAT 为 0，其他模型为 0.2")
    ap.add_argument("--tile", type=int, help="分块边长，越小越省显存/内存；默认按设备自动选")
    ap.add_argument("--throttle", type=float, default=0.0, help="每块算完休息“耗时×该值”，1.0 约让 GPU 空闲一半")
    ap.add_argument("--threads", type=int, help="限制 CPU 线程数")
    ap.add_argument("--eco", action="store_true",
                    help="低占用：tile 128、throttle 0.5、2 线程、低进程优先级；峰值约 2GB，画质几乎不变，只是更慢")
    ap.add_argument("--fp16", action="store_true", help="半精度，更快；HAT/DAT 不支持，会自动忽略")
    ap.add_argument("--check", action="store_true", help="输出回投影一致性 PSNR 和差异热图")
    ap.add_argument("--compare", action="store_true", help="为每张图生成拖动对比网页")
    args = ap.parse_args()
    if args.blend is None:
        args.blend = 0.0 if str(args.model).lower() == "hat" else 0.2

    import torch
    tile = args.tile or sr_core.auto_tile()
    if args.eco:
        tile, args.throttle = min(tile, 128), max(args.throttle, 0.5)
        args.threads = args.threads or 2
        lower_priority()
    if args.threads:
        torch.set_num_threads(args.threads)

    path = config.model_path(args.model)
    if not path.exists():
        sys.exit(f"找不到模型 {path}。别名模型请先运行 setup.py 下载")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    model = sr_core.load_model(path, fp16=args.fp16)
    print(f"模型 {model.architecture.name} x{model.scale} @ {sr_core.device_name()}  tile {tile}", flush=True)

    for f in collect(args.inputs):
        img = Image.open(f).convert("RGB")
        with sr_core.Timer() as t:
            sr = sr_core.upscale_to(model, img, args.target, args.blend, tile=tile, throttle=args.throttle)
        dst = out_dir / f"{f.stem}_{args.model if args.model in config.MODEL_FILES else path.stem}_{sr.width}.png"
        sr.save(dst)
        line = f"{f.name}: {img.width}x{img.height} -> {sr.width}x{sr.height}  {t.elapsed:.1f}s"
        if sr_core.PEAK["gb"]:
            line += f"  显存峰值 {sr_core.PEAK['gb']:.2f}GB"
        line += f"  -> {dst}"
        if args.check:
            score, heat = sr_core.backproject(sr, img)
            heat.save(out_dir / f"{dst.stem}_diff.png")
            line += f"\n  回投影 PSNR {score:.2f}dB，差异热图 {dst.stem}_diff.png"
        if args.compare:
            method = f"{model.architecture.name} {model.scale}x" + (f"，混合 {args.blend:.0%} Lanczos" if args.blend else "")
            page = write_compare(out_dir / f"{dst.stem}_compare", img, sr, f"{f.stem} 超分对比", method)
            line += f"\n  对比页 {page}"
        print(line, flush=True)


if __name__ == "__main__":
    main()
