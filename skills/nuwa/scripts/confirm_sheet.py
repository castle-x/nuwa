#!/usr/bin/env python3
"""渲染生成确认单：把一次生图任务的全部参数、提示词、参考图固化成自包含 HTML。

用法：
    python3 confirm_sheet.py --示例 > 任务.json            # 打印任务模板
    python3 confirm_sheet.py 任务.json                     # 渲染确认单，输出到 ./确认单/
    python3 confirm_sheet.py 任务.json --out 目录 --open   # 指定输出目录并打开

参考图路径相对于当前工作目录（一般是项目根目录）。

任务 JSON 字段见 --示例 输出。参考图会被压缩内嵌，不依赖任何外部文件。
确认后的回执由页面下载，落在系统「下载」目录，文件名 回执-<jobId>.json。
"""
import argparse
import base64
import datetime
import hashlib
import html
import io
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path.cwd()
SKILL_TEMPLATE = pathlib.Path(__file__).resolve().parents[1] / "assets" / "generation-confirm-sheet.html"
MAX_EDGE = 640
JPEG_QUALITY = 82

EXAMPLE = {
    "角色": "角色名",
    "批次": "YYYY-MM-DD 批次名",
    "通道": "Gemini 直连（API 预付）",
    "模型": "gemini-nano-banana-2.1",
    "画幅": "3:2",
    "分辨率": "2K",
    "张数": 4,
    "预计花费": "约 ¥6（按 4 张 2K 估）",
    "输出目录": "模特/<模特名>/生成记录/YYYY-MM-DD-任务名/",
    "提示词": "完整提示词原文，含负面约束。不要写摘要。",
    "提示词中文": "原文不是中文时填中文对照；原文就是中文时留空。",
    "参考图": [
        {"路径": "模特/<模特名>/素材/外部参考/示例.jpg", "职责": "身份：骨相与五官", "来源": "用户提供的原始参考"},
        {"路径": "模特/<模特名>/素材/定稿/示例-基准脸.png", "职责": "身份：正面基准脸", "来源": "GPT Image 生成，用户已确认；本次为第 1 次回喂"}
    ],
    "自检": {
        "每张图来源已标注": True,
        "成图回喂已说明": True,
        "比例来源唯一": True,
        "顺序与职责已写清": True,
    },
}

CHECK_LABELS = {
    "每张图来源已标注": "每张输入图都标明了来源：用户原始参考，还是哪一次生成的成图",
    "成图回喂已说明": "如果有我们生成的图再次输入（比如基准脸），已在来源里写明，且没有在同一张成图上反复修改",
    "比例来源唯一": "头身比例只有一个来源；无头图没有和别的全身图同时决定比例",
    "顺序与职责已写清": "输入顺序与每张图的职责已写进记录",
}


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(1)


def embed_image(path):
    try:
        from PIL import Image
    except ImportError:
        fail("需要 Pillow 才能内嵌参考图。请先安装 Pillow。")
    source = pathlib.Path(path)
    if not source.is_file():
        fail("参考图不存在：" + str(path))
    with Image.open(source) as image:
        image.load()
        width, height = image.size
        scale = min(1.0, MAX_EDGE / max(width, height))
        if scale < 1.0:
            image = image.resize((max(1, round(width * scale)), max(1, round(height * scale))), Image.LANCZOS)
        if image.mode not in ("RGB", "L"):
            background = Image.new("RGB", image.size, (247, 247, 245))
            if image.mode in ("RGBA", "LA", "P"):
                image = image.convert("RGBA")
                background.paste(image, mask=image.split()[-1])
            else:
                background.paste(image.convert("RGB"))
            image = background
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return "data:image/jpeg;base64," + encoded, (width, height)


def render_params(job, prompt_hash):
    rows = [
        ("通道", job.get("通道", "")),
        ("模型", job.get("模型", "")),
        ("画幅", job.get("画幅", "")),
        ("分辨率", job.get("分辨率", "")),
        ("生成张数", str(job.get("张数", ""))),
        ("预计花费", job.get("预计花费", "")),
        ("批次", job.get("批次", "")),
        ("输出目录", job.get("输出目录", "")),
    ]
    if job.get("备注"):
        rows.append(("备注", job["备注"]))
    cells = []
    for key, value in rows:
        text = html.escape(str(value)) if str(value).strip() else "—"
        wide = ' wide' if key in ("输出目录", "备注") else ''
        cells.append('<div class="kv{}"><dt>{}</dt><dd>{}</dd></div>'.format(wide, html.escape(key), text))
    return "".join(cells)


def render_refs(job):
    cards = []
    for index, item in enumerate(job.get("参考图", []), 1):
        relative = str(item.get("路径", ""))
        absolute = pathlib.Path(relative) if pathlib.Path(relative).is_absolute() else ROOT / relative
        data_uri, size = embed_image(absolute)
        name = absolute.name
        cards.append(
            '<div class="ref">'
            '<img src="{uri}" alt="{alt}">'
            '<div class="meta">'
            '<div class="role">{idx}. {role}</div>'
            '<div class="name">{name}<br>{w}×{h}</div>'
            '<div class="name">来源：{source}</div>'
            "</div></div>".format(
                uri=data_uri,
                alt=html.escape(name),
                idx=index,
                role=html.escape(str(item.get("职责", "未标注"))),
                name=html.escape(name),
                w=size[0],
                h=size[1],
                source=html.escape(str(item.get("来源", "未标注"))),
            )
        )
    if not cards:
        cards.append('<div class="ref"><div class="meta">本次不使用参考图（纯文生图）。</div></div>')
    return "".join(cards)


def render_checks(job):
    checks = job.get("自检", {})
    items = []
    for key, label in CHECK_LABELS.items():
        value = checks.get(key)
        if value is True:
            mark, css, text = "✓", "ok", "已核对"
        elif value is False:
            mark, css, text = "✗", "warn", "不通过，不得生成"
        else:
            mark, css, text = "?", "warn", "未标注"
        items.append(
            '<li><span class="mark {css}">{mark}</span><span>{}：<strong>{}</strong></span></li>'.format(
                html.escape(label), text, css=css, mark=mark
            )
        )
    return "".join(items)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("job", nargs="?", help="任务 JSON 路径")
    parser.add_argument("--示例", dest="example", action="store_true", help="打印任务 JSON 模板")
    parser.add_argument("--out", default="确认单", help="输出目录，默认 ./确认单；建议指向这次任务的生成记录目录")
    parser.add_argument("--open", dest="open_result", action="store_true", help="渲染后用默认浏览器打开")
    args = parser.parse_args()

    if args.example:
        print(json.dumps(EXAMPLE, ensure_ascii=False, indent=2))
        return 0

    if not args.job:
        parser.print_help()
        return 1
    job = json.loads(pathlib.Path(args.job).read_text(encoding="utf-8"))
    if not job.get("提示词", "").strip():
        fail("任务缺少「提示词」。确认单必须带提示词原文。")
    prompt_zh = str(job.get("提示词中文", "")).strip()
    if not prompt_zh:
        print("提醒：任务没有提供「提示词中文」。原文不是中文时，确认单应当带中文对照。", file=sys.stderr)
    failing = [k for k, v in job.get("自检", {}).items() if v is False]
    if failing:
        fail("自检不通过：" + "；".join(failing) + "。先解决，再出确认单。")
    if not SKILL_TEMPLATE.is_file():
        fail("找不到确认单骨架：" + str(SKILL_TEMPLATE))

    stamp = datetime.datetime.now()
    slug = "".join(ch for ch in str(job.get("角色", "角色")) if ch.isalnum() or ch in "-_") or "角色"
    job_id = stamp.strftime("%Y%m%d-%H%M%S") + "-" + slug
    prompt = job["提示词"].strip()
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]

    template = SKILL_TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "{{TITLE}}": html.escape(str(job.get("角色", "未命名角色")) + " · 生成确认"),
        "{{SUBTITLE}}": html.escape(str(job.get("批次", ""))),
        "{{JOB_ID}}": html.escape(job_id),
        "{{CREATED}}": stamp.strftime("%Y-%m-%d %H:%M:%S"),
        "{{PARAM_ROWS}}": render_params(job, prompt_hash),
        "{{PROMPT}}": html.escape(prompt),
        "{{PROMPT_ZH}}": html.escape(prompt_zh) if prompt_zh else "（本单未提供中文译文）",
        "{{PROMPT_META}}": html.escape("{} 字符 · {}".format(len(prompt), prompt_hash)),
        "{{REF_COUNT}}": str(len(job.get("参考图", []))),
        "{{REF_CARDS}}": render_refs(job),
        "{{CHECK_ROWS}}": render_checks(job),
        "{{JOB_ID_JSON}}": json.dumps(job_id, ensure_ascii=False),
        "{{TITLE_JSON}}": json.dumps(str(job.get("角色", "未命名角色")), ensure_ascii=False),
        "{{MODEL_JSON}}": json.dumps(str(job.get("模型", "")), ensure_ascii=False),
        "{{COUNT_JSON}}": json.dumps(str(job.get("张数", "")), ensure_ascii=False),
        "{{OUT_JSON}}": json.dumps(str(job.get("输出目录", "")), ensure_ascii=False),
        "{{PROMPT_HASH_JSON}}": json.dumps(prompt_hash, ensure_ascii=False),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    leftover = [k for k in replacements if k in template]
    if leftover:
        fail("模板占位符未替换完整：" + "、".join(leftover))

    OUT_DIR = pathlib.Path(args.out)
    if not OUT_DIR.is_absolute():
        OUT_DIR = ROOT / OUT_DIR
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / ("生成确认单-{}-{}.html".format(stamp.strftime("%Y%m%d-%H%M%S"), slug))
    target.write_text(template, encoding="utf-8")

    size_kb = target.stat().st_size / 1024
    print("确认单已生成：" + str(target))
    print("JOB " + job_id + " · 参考图 {} 张 · {:.0f} KB".format(len(job.get("参考图", [])), size_kb))
    print("提示词指纹 " + prompt_hash)
    print("确认后回执会下载为 回执-" + job_id + ".json，出图前会核对 jobId 与提示词指纹。")

    if args.open_result:
        opener = "open" if sys.platform == "darwin" else ("start" if sys.platform == "win32" else "xdg-open")
        subprocess.run([opener, str(target)], check=False, shell=sys.platform == "win32")
    return 0


if __name__ == "__main__":
    sys.exit(main())
