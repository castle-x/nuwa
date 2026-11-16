# 原理与选型依据

## 为什么不用 AI 重绘放大

超分方法按"敢不敢编内容"排成一条线：

| 类型 | 代表 | 会不会改脸 |
|---|---|---|
| 插值 | Lanczos、双三次 | 不改，但糊 |
| 回归式 | SwinIR、HAT、DAT | 基本不改，偏柔 |
| GAN | Real-ESRGAN | 会改睫毛、眼线、皮肤纹理 |
| 扩散 | SeedVR2、SUPIR、Topaz Redefine、Magnific | 会改，小脸尤其明显 |
| 大模型重绘 | Nano Banana 等 | 整张重画 |

越往下观感越"锐"，越容易改五官。这是理论上的取舍：在同样的模型能力下，结果看起来越逼真，和原图的偏差就越大（Blau & Michaeli 2018，感知-失真权衡）。本 skill 只用前两类，再和插值按比例混合压掉假纹理。

**回投影检查**：把放大结果缩回原尺寸，和原图比较 PSNR。保真模型缩回去几乎和原图一样；模型改过的地方在差异热图里会亮起来。

## 分块推理

整图一次送进模型，显存随图片面积增长。脚本把图切成带重叠的小块逐块推理，重叠区用渐变权重融合，没有接缝；结果按行写入 8 位缓冲，浮点缓冲只保留一行块的高度。显存峰值由分块边长决定，和整图尺寸无关。

DAT2 处理 1532×1027 → 4K 的数据（Apple M5 Pro，整个进程的峰值内存）：

| 设置 | 峰值 | 用时 | 和默认结果的差异 |
|---|---|---|---|
| tile 384 | 8.1GB | 60s | - |
| tile 256 | 4.7GB | 65s | 49.7dB |
| tile 192 | 3.4GB | 88s | 47.6dB |
| tile 128 | 2.0GB | 101s | 45.4dB |
| `--eco` | 2.0GB | 122s | 45.4dB（脸部约 48.5dB） |

差异 45dB 以上肉眼看不出。约 1GB 是 PyTorch 和模型权重的固定开销，2GB 基本是下限。

## 模型对比数据

保真度（4 张标准测试图放大 4 倍，Y 通道 PSNR，越高越接近真实高清图）：

| 模型 | 干净输入 | JPEG 压缩输入 |
|---|---|---|
| HAT | 32.99 | 28.79 |
| SwinIR | 32.68 | - |
| DAT2-real | 30.10 | 28.86（最好） |

一张 AIGC 三视图人像（1532×1027 → 4K）的回投影 PSNR 和用时（M5 Pro）：

| 模型 | 回投影 PSNR | 用时 |
|---|---|---|
| HAT | 63.3dB | 97s |
| DAT2 + blend 0.2 | 45.6dB | 约 100s |
| DAT2 | 41.9dB | 102s |
| RealPLKSR | 39.7dB | 9s |
| Real-ESRGAN | 36.6dB，会改粗睫毛和眼线 | - |

HAT 最保真但偏柔；DAT2 + blend 0.2 观感更清楚，脸不变，所以作为默认。

速度（960×540 → 4K，M5 Pro）：RealPLKSR 5.5s，SwinIR 20s，DAT2 38s，HAT 43s。

## 云端方案参考价（价格会变，以官网为准）

| 服务 | 价格 | 类型 |
|---|---|---|
| fal SeedVR2 | $0.001/MP | 扩散，会改脸 |
| Recraft Crisp | $0.004/张 | |
| Topaz Precision | 24MP 以内 $0.08 | |
| Clarity Upscaler | $0.03/MP | 扩散 |
| Magnific | 1080p→4K 约 €0.20 | 扩散 |
| Nano Banana Pro 4K | $0.24 | 重绘 |
| Topaz Gigapixel 本地版 | $149/年 | |

要求脸不变时，本地回归式模型免费且最稳；要"补细节、更好看"并接受改脸，云端扩散方案更便宜省事。

## 模型来源

- DAT2-real：Phhofm/models（`4xBHI_dat2_real`）
- HAT：XPixelGroup/HAT，权重镜像自 Hugging Face `Acly/hat`
- RealPLKSR：Phhofm/models（`4xNomosWebPhoto_RealPLKSR`）

推理框架：PyTorch + spandrel。
