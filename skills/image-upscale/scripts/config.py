"""安装位置、模型清单和别名。只用标准库，安装脚本和推理脚本共用。"""
import os
import sys
from pathlib import Path

# Python 环境和模型都装在这里，不放进 skill 目录（skill 目录可能只读或被多人共享）
HOME = Path(os.environ.get("IMAGE_UPSCALE_HOME", Path.home() / ".image-upscale"))
VENV = HOME / "venv"
MODELS = HOME / "models"

# 别名 → (文件名, 下载地址)
MODEL_FILES = {
    "dat2": ("4xBHI_dat2_real.safetensors",
             "https://github.com/Phhofm/models/releases/download/4xBHI_dat2_real/4xBHI_dat2_real.safetensors"),
    "hat": ("HAT_SRx4_ImageNet-pretrain.pth",
            "https://huggingface.co/Acly/hat/resolve/main/HAT_SRx4_ImageNet-pretrain.pth"),
    "plksr": ("4xNomosWebPhoto_RealPLKSR.pth",
              "https://github.com/Phhofm/models/releases/download/4xNomosWebPhoto_RealPLKSR/4xNomosWebPhoto_RealPLKSR.pth"),
}

DESCRIPTIONS = {
    "dat2": "DAT2-real，压缩重的网图、截图用；会抹淡雀斑和毛孔",
    "hat": "HAT，最保真，保住皮肤纹理（默认，blend 0）",
    "plksr": "RealPLKSR，最快，适合批量预览",
}


def venv_python():
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def in_venv():
    return Path(sys.prefix).resolve() == VENV.resolve()


def model_path(name):
    """别名或文件路径 → 模型文件路径。"""
    if name in MODEL_FILES:
        return MODELS / MODEL_FILES[name][0]
    return Path(name)
