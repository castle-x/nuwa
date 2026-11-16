"""一次性安装：建独立 Python 环境，装 PyTorch 和依赖，下载模型。

可重复运行，已完成的步骤会跳过。默认装到 ~/.image-upscale，可用环境变量 IMAGE_UPSCALE_HOME 改位置。

  python3 setup.py                 # 自动识别 NVIDIA / Apple / CPU
  python3 setup.py --cuda cu128    # 老显卡（GTX 10 系等）用 CUDA 12.8 版 PyTorch
"""
import argparse
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config  # noqa: E402

PACKAGES = ["spandrel>=0.4.2", "pillow", "numpy"]


def run(cmd):
    print("$", " ".join(map(str, cmd)), flush=True)
    subprocess.run(list(map(str, cmd)), check=True)


def make_venv(uv):
    if config.venv_python().exists():
        return
    config.HOME.mkdir(parents=True, exist_ok=True)
    if uv:
        run([uv, "venv", "--python", "3.12", config.VENV])
    elif sys.version_info >= (3, 10):
        run([sys.executable, "-m", "venv", config.VENV])
    else:
        sys.exit("需要 Python 3.10 以上，或者先装 uv（https://docs.astral.sh/uv/），它会自动下载 Python")


def pip_install(uv, args):
    if uv:
        run([uv, "pip", "install", "--python", config.venv_python(), *args])
    else:
        run([config.venv_python(), "-m", "pip", "install", *args])


def has_package(name):
    return subprocess.run([str(config.venv_python()), "-c", f"import {name}"],
                          capture_output=True).returncode == 0


def install_torch(uv, cuda):
    if has_package("torch"):
        return
    if shutil.which("nvidia-smi"):
        pip_install(uv, ["torch", "--index-url", f"https://download.pytorch.org/whl/{cuda}"])
    elif platform.system() == "Darwin":
        pip_install(uv, ["torch"])
    else:  # 没有 NVIDIA 的 Windows/Linux：CPU 版，体积小很多
        pip_install(uv, ["torch", "--index-url", "https://download.pytorch.org/whl/cpu"])


def download(url, dst):
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    part = dst.with_suffix(dst.suffix + ".part")
    print(f"下载 {dst.name}", flush=True)
    total = None
    for _ in range(8):  # 连接中途断开时，从断点续传
        got = part.stat().st_size if part.exists() else 0
        if total is not None and got >= total:
            break
        req = urllib.request.Request(url, headers={"Range": f"bytes={got}-"} if got else {})
        try:
            with urllib.request.urlopen(req, timeout=60) as r, open(part, "ab" if got else "wb") as f:
                if r.status != 206:  # 服务器不支持续传，从头下载
                    f.truncate(0)
                    got = 0
                length = int(r.headers.get("Content-Length", 0))
                total = got + length if length else total
                while chunk := r.read(1 << 20):
                    f.write(chunk)
                    got += len(chunk)
                    if total:
                        print(f"\r  {got / 2**20:.0f}/{total / 2**20:.0f} MB", end="", flush=True)
        except OSError as e:
            print(f"\n  连接中断（{e}），重试", flush=True)
    print()
    if total is None or part.stat().st_size != total:
        sys.exit(f"{dst.name} 下载不完整，请检查网络后重新运行 setup.py（会续传）")
    part.rename(dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cuda", default="cu130", help="NVIDIA 显卡用的 PyTorch CUDA 版本，默认 cu130")
    ap.add_argument("--models", nargs="+", default=list(config.MODEL_FILES), help="要下载的模型别名")
    args = ap.parse_args()

    uv = shutil.which("uv")
    make_venv(uv)
    install_torch(uv, args.cuda)
    if not has_package("spandrel"):
        pip_install(uv, PACKAGES)
    for name in args.models:
        fname, url = config.MODEL_FILES[name]
        download(url, config.MODELS / fname)

    run([config.venv_python(), "-c",
         "import sys; sys.path.insert(0, %r); import sr_core; print('设备:', sr_core.device_name(), ' 默认 tile:', sr_core.auto_tile())"
         % str(Path(__file__).parent)])
    print(f"安装完成：{config.HOME}")


if __name__ == "__main__":
    main()
