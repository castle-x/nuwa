"""非生成式超分核心：spandrel 加载模型 + 分块推理 + 回投影一致性检查。支持 CUDA、Apple MPS 和 CPU。"""
import math
import os
import time
import warnings

import numpy as np
import torch
from PIL import Image
from spandrel import ImageModelDescriptor, ModelLoader

warnings.filterwarnings("ignore", message="torch.meshgrid")  # HAT/DAT 内部触发，无害

if torch.cuda.is_available():
    DEVICE = torch.device("cuda")
elif torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
else:
    DEVICE = torch.device("cpu")


def device_name():
    if DEVICE.type == "cuda":
        return f"cuda ({torch.cuda.get_device_name(0)})"
    return DEVICE.type


def _system_memory_gb():
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
    except (AttributeError, ValueError, OSError):
        return 16.0


def auto_tile():
    """按可用显存挑分块边长。DAT2 实测进程峰值：384≈8.1GB，256≈4.7GB，192≈3.4GB，128≈2.0GB。"""
    if DEVICE.type == "cuda":
        gb = torch.cuda.get_device_properties(0).total_memory / 2**30
        return 384 if gb >= 12 else 256 if gb >= 8 else 192
    gb = _system_memory_gb()  # MPS 与 CPU 都吃内存
    return 384 if gb >= 32 else 256 if gb >= 16 else 192


def load_model(path, fp16=False):
    model = ModelLoader().load_from_file(str(path))
    if not isinstance(model, ImageModelDescriptor):
        raise ValueError(f"{path} 不是图像超分模型")
    model.to(DEVICE).eval()
    if fp16 and model.supports_half and DEVICE.type != "cpu":
        model.half()
    return model


def pil_to_tensor(img):
    arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)


def _starts(length, tile, step):
    if length <= tile:
        return [0]
    return list(range(0, length - tile, step)) + [length - tile]


def _feather(h, w, ramp):
    """边缘线性渐变的权重窗，用于重叠区平滑拼接。"""
    def axis(n):
        r = min(ramp, n // 2)
        v = torch.ones(n)
        if r > 0:
            edge = torch.linspace(1.0 / (r + 1), 1.0, r)
            v[:r], v[n - r:] = edge, edge.flip(0)
        return v
    return axis(h)[:, None] * axis(w)[None, :]


PEAK = {"gb": 0.0}  # 推理过程中观测到的显存峰值（CPU 上不统计）


def _sync():
    if DEVICE.type == "cuda":
        torch.cuda.synchronize()
        PEAK["gb"] = max(PEAK["gb"], torch.cuda.max_memory_reserved() / 2**30)
    elif DEVICE.type == "mps":
        torch.mps.synchronize()
        PEAK["gb"] = max(PEAK["gb"], torch.mps.driver_allocated_memory() / 2**30)


def _empty_cache():
    if DEVICE.type == "cuda":
        torch.cuda.empty_cache()
    elif DEVICE.type == "mps":
        torch.mps.empty_cache()


@torch.inference_mode()
def upscale(model, img, tile=384, overlap=32, throttle=0.0):
    """对 PIL 图做一次模型放大，返回 PIL。

    按块推理、按行落盘：每算完一行块，就把之后不会再被覆盖的输出行转成 8 位写进结果，
    浮点累加缓冲只保留一行块的高度，不随整图尺寸增长。显存峰值主要由 tile 决定。
    throttle：每块算完后休息“该块耗时 × throttle”，1.0 即 GPU 约一半时间空闲。"""
    x = pil_to_tensor(img)
    _, _, h, w = x.shape
    s = model.scale
    dtype = next(model.model.parameters()).dtype
    out = np.empty((h * s, w * s, 3), np.uint8)
    step = tile - overlap
    ys, xs = _starts(h, tile, step), _starts(w, tile, step)
    acc = np.zeros((0, w * s, 3), np.float32)
    weight = np.zeros((0, w * s, 1), np.float32)
    acc_top = 0  # acc 第 0 行对应的输出行号
    for i, y0 in enumerate(ys):
        bottom = (y0 + min(tile, h - y0)) * s
        grow = bottom - acc_top - acc.shape[0]
        if grow > 0:
            acc = np.concatenate([acc, np.zeros((grow, w * s, 3), np.float32)])
            weight = np.concatenate([weight, np.zeros((grow, w * s, 1), np.float32)])
        for x0 in xs:
            t0 = time.perf_counter()
            patch = x[:, :, y0:y0 + tile, x0:x0 + tile].to(DEVICE, dtype)
            o = model(patch).float().cpu()[0].permute(1, 2, 0).numpy()
            _sync()
            ph, pw = o.shape[:2]
            win = _feather(ph, pw, overlap * s // 2).numpy()[..., None]
            r = y0 * s - acc_top
            acc[r:r + ph, x0 * s:x0 * s + pw] += o * win
            weight[r:r + ph, x0 * s:x0 * s + pw] += win
            if throttle > 0:
                time.sleep((time.perf_counter() - t0) * throttle)
        done = (ys[i + 1] * s if i + 1 < len(ys) else bottom) - acc_top
        out[acc_top:acc_top + done] = (np.clip(acc[:done] / weight[:done], 0, 1) * 255.0).round()
        acc, weight, acc_top = acc[done:], weight[done:], acc_top + done
    _empty_cache()
    return Image.fromarray(out)


def upscale_to(model, img, target_long=None, blend=0.0, **kw):
    """放大到目标长边：不够就多跑几遍模型，超出则用 Lanczos 缩回（超采样）。
    第二遍起若剩余倍率不足 2 倍，改用 Lanczos 补齐，避免放到远超目标再缩回。
    blend>0 时与 Lanczos 直接放大的结果按比例混合，压掉模型造出的假纹理。"""
    img = img.convert("RGB")
    out = img
    target_long = target_long or max(img.size) * model.scale
    passes = 0
    while max(out.size) < target_long:
        if passes and target_long / max(out.size) < 2:
            break
        out = upscale(model, out, **kw)
        passes += 1
    ratio = target_long / max(out.size)
    size = (round(out.width * ratio), round(out.height * ratio))
    if size != out.size:
        out = out.resize(size, Image.LANCZOS)
    if blend > 0:
        out = Image.blend(out, img.resize(out.size, Image.LANCZOS), blend)
    return out


def psnr(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    mse = np.mean((a - b) ** 2)
    return float("inf") if mse == 0 else 10 * math.log10(255.0 ** 2 / mse)


def backproject(sr, lr, amplify=8):
    """回投影一致性：把超分结果缩回原尺寸与输入比较。
    返回 (PSNR, 差异热图)。保真模型 PSNR 高、热图暗；被重绘的区域会亮起来。"""
    lr = lr.convert("RGB")
    down = sr.resize(lr.size, Image.BICUBIC)
    diff = np.abs(np.asarray(down, np.float32) - np.asarray(lr, np.float32))
    heat = np.clip(diff.mean(axis=2) * amplify, 0, 255).astype(np.uint8)
    return psnr(down, lr), Image.fromarray(heat)


class Timer:
    def __enter__(self):
        _sync()
        self.t = time.perf_counter()
        return self

    def __exit__(self, *a):
        _sync()
        self.elapsed = time.perf_counter() - self.t
