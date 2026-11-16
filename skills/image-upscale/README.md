# image-upscale

让 AI 助手在本机把图片放大到 2K/4K/8K。只放大、不重绘，人物的脸不会变。

## 安装 skill

- **Claude Code**：把 `image-upscale` 文件夹放到 `~/.claude/skills/`，重开会话。
- **Claude 桌面版 / Claude.ai**：在「设置 → 功能 → Skills」里上传 `image-upscale.skill`。注意 Claude.ai 网页版在云端沙盒里跑，用不了你的显卡，建议用 Claude Code 或桌面版的 Code。
- **Codex / Cursor**：放到 `~/.codex/skills/` 或 `~/.cursor/skills/`。

第一次使用时，助手会运行 `scripts/setup.py`，自动装好 PyTorch 和模型（装到 `~/.image-upscale`，约 0.5～3GB，取决于显卡）。

## 怎么用

直接说：「把这张图转成 4K」「这个文件夹里的图都放大到 8K，电脑别太卡」「放大这张人像，脸不能变，做个前后对比页」。

## 不用助手，自己跑

```bash
python3 scripts/setup.py
python3 scripts/upscale.py 图片或文件夹 -o 输出目录 --target 3840 --check --compare
```

`python3 scripts/upscale.py -h` 查看全部参数。常用的：

| 参数 | 作用 |
|---|---|
| `-m dat2 / hat / plksr` | 模型：通用默认 / 干净原图最保真 / 最快 |
| `--target 3840` | 输出长边像素 |
| `--blend 0.2` | 和普通插值混合的比例，压掉假纹理 |
| `--eco` | 低占用模式，峰值约 2GB 内存或显存 |
| `--check` | 输出一致性分数和差异热图 |
| `--compare` | 生成拖动对比网页 |

## 支持的设备

Apple 芯片 Mac、带 NVIDIA 显卡的 Windows/Linux。没有显卡也能跑，但很慢。
