#!/usr/bin/env python3
"""生成白模 / 视频结果总览页（对比原片用）。

页面规范见 ../references/video-overview-page.md。版式来自 2026-11-17 用户认可的
「白模总览.html」，改版式前先改规范文档。

用法：
  python3 video_overview.py 任务.json            # 生成 HTML，输出到 JSON 里的 out
  python3 video_overview.py --示例               # 打印任务 JSON 模板
"""
import html
import json
import os
import sys
import urllib.parse

EXAMPLE = {
    "title": "白模总览",
    "out": "/绝对路径/参考资料/视频/白模总览.html",
    "sections": [
        {
            "name": "Milo 线 · 白长袖短发参考源",
            "cards": [
                {
                    "title": "抬臂交叉手势舞 · Milo 脸型版",
                    "date": "11/17",
                    "meta": ["8 秒", "Wan 3.0", "480P", "最新"],
                    "segments": [
                        {"label": "白模", "path": "/绝对路径/成片.mp4"},
                        {"label": "对照原片", "path": "/绝对路径/对照-左原片右白模.mp4"},
                        {"label": "2秒起-6秒", "path": "/绝对路径/白模-2秒起-6秒.mp4"},
                    ],
                }
            ],
        }
    ],
}

CSS = """
:root{--bg:#f4f2ee;--surface:#ffffff;--ink:#1c1b19;--muted:#6b675f;--line:rgba(0,0,0,.08);--accent:#d9623b;--stage:#e7e4de;--seg:rgba(0,0,0,.05)}
@media (prefers-color-scheme:dark){:root{--bg:#121211;--surface:#1c1b1a;--ink:#eeebe5;--muted:#9c978d;--line:rgba(255,255,255,.07);--accent:#f07d55;--stage:#0b0b0a;--seg:rgba(255,255,255,.06)}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,"PingFang SC",system-ui,sans-serif}
header{position:sticky;top:0;z-index:2;display:flex;align-items:center;gap:16px;padding:12px 24px;background:color-mix(in srgb,var(--bg) 70%,transparent);backdrop-filter:blur(24px) saturate(1.4);border-bottom:1px solid var(--line)}
header h1{font-size:15px;margin:0;font-weight:600;white-space:nowrap}
.pill{display:flex;gap:2px;padding:3px;border-radius:999px;background:var(--seg)}
.pill button,.segs button{border:0;background:none;color:var(--muted);font:inherit;font-size:13px;padding:4px 12px;border-radius:999px;cursor:pointer;white-space:nowrap}
.pill button.on,.segs button.on{background:var(--surface);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.08)}
.sp{flex:1}.hint{color:var(--muted);font-size:12px;white-space:nowrap}
main{padding:20px 24px 60px}
section h2{font-size:13px;font-weight:600;color:var(--muted);margin:20px 0 12px;display:flex;align-items:center;gap:8px}
section h2 .dot{width:8px;height:8px;border-radius:50%;background:var(--accent)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:16px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.stage{position:relative;background:var(--stage);aspect-ratio:9/16;display:flex;align-items:center;justify-content:center}
.stage video{width:100%;height:100%;object-fit:contain;display:block}
.date{position:absolute;top:8px;left:8px;font-size:11px;padding:2px 8px;border-radius:999px;background:rgba(0,0,0,.35);color:#fff;backdrop-filter:blur(8px)}
.body{padding:10px 12px 12px;display:flex;flex-direction:column;gap:6px}
.body h3{margin:0;font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.meta{margin:0;color:var(--muted);font-size:12px}
.segs{display:flex;flex-wrap:wrap;gap:2px;padding:3px;border-radius:999px;background:var(--seg);align-self:flex-start}
.segs button{font-size:12px;padding:2px 10px}
.path{all:unset;cursor:pointer;color:var(--muted);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
.path:hover{color:var(--accent)}
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);padding:6px 14px;border-radius:999px;background:color-mix(in srgb,var(--surface) 55%,transparent);backdrop-filter:blur(30px) saturate(1.5);border:1px solid var(--line);opacity:0;transition:opacity .15s;font-size:13px}
.toast.on{opacity:1}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
"""

JS = """
const vids=()=>[...document.querySelectorAll('video')];
let mode='play';
const play=()=>vids().forEach(v=>v.play().catch(()=>{}));
play();
document.querySelector('.pill').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
 document.querySelectorAll('.pill button').forEach(x=>x.classList.toggle('on',x===b&&b.dataset.act!=='sync'));
 if(b.dataset.act==='play'){mode='play';play()}if(b.dataset.act==='pause'){mode='pause';vids().forEach(v=>v.pause())}
 if(b.dataset.act==='sync'){mode='play';vids().forEach(v=>{v.currentTime=0});play();document.querySelector('[data-act=play]').classList.add('on')}});
document.querySelectorAll('.card').forEach(c=>{const v=c.querySelector('video');
 c.addEventListener('mouseenter',()=>{vids().forEach(x=>{if(x!==v)x.pause()});v.play().catch(()=>{})});
 c.addEventListener('mouseleave',()=>{if(mode==='play')play();else v.pause()});
 c.querySelectorAll('.segs button').forEach(b=>b.addEventListener('click',()=>{c.querySelectorAll('.segs button').forEach(x=>x.classList.toggle('on',x===b));v.src=b.dataset.src;v.play().catch(()=>{})}));
 c.querySelector('.path').addEventListener('click',e=>{navigator.clipboard.writeText(e.currentTarget.dataset.path);const t=document.getElementById('t');t.classList.add('on');setTimeout(()=>t.classList.remove('on'),1200)});});
"""

esc = lambda s: html.escape(str(s), quote=True)


def rel_src(path, out_dir):
    rel = os.path.relpath(path, out_dir)
    return urllib.parse.quote(rel.replace(os.sep, "/"))


def card_html(card, out_dir, missing):
    segs = card["segments"]
    for s in segs:
        if not os.path.isfile(s["path"]):
            missing.append(s["path"])
    main = segs[0]
    seg_btns = "".join(
        f'<button class="seg{" on" if i == 0 else ""}" data-src="{esc(rel_src(s["path"], out_dir))}">{esc(s["label"])}</button>'
        for i, s in enumerate(segs)
    )
    date = f'<span class="date">{esc(card["date"])}</span>' if card.get("date") else ""
    meta = " · ".join(card.get("meta", []))
    return (
        f'<article class="card"><div class="stage"><video src="{esc(rel_src(main["path"], out_dir))}" '
        f'muted loop playsinline preload="metadata"></video>{date}</div>\n'
        f'<div class="body"><h3>{esc(card["title"])}</h3><p class="meta">{esc(meta)}</p>'
        f'<div class="segs">{seg_btns}</div>\n'
        f'<button class="path" data-path="{esc(main["path"])}" title="复制文件路径">'
        f'{esc(os.path.basename(main["path"]))}</button></div></article>'
    )


def render(task):
    out = os.path.abspath(task["out"])
    out_dir = os.path.dirname(out)
    missing = []
    sections = []
    for i, sec in enumerate(task["sections"]):
        cards = "\n".join(card_html(c, out_dir, missing) for c in sec["cards"])
        dot = '<span class="dot"></span>' if i == 0 else ""
        sections.append(
            f'<section><h2>{dot}{esc(sec["name"])} · {len(sec["cards"])} 条</h2>'
            f'<div class="grid">{cards}</div></section>'
        )
    title = esc(task.get("title", "白模总览"))
    page = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f"<title>{title}</title>\n<style>{CSS}</style></head><body>\n"
        f'<header><h1>{title}</h1><div class="pill" role="group" aria-label="播放">'
        '<button class="on" data-act="play">全部播放</button><button data-act="pause">全部暂停</button>'
        '<button data-act="sync">从头同步</button></div><span class="sp"></span>'
        '<span class="hint">悬停卡片单独播放 · 点文件名复制路径</span></header>\n'
        f'<main>\n{chr(10).join(sections)}\n</main><div class="toast" id="t">已复制路径</div>\n'
        f"<script>{JS}</script></body></html>\n"
    )
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    return out, missing


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    if sys.argv[1] == "--示例":
        print(json.dumps(EXAMPLE, ensure_ascii=False, indent=2))
        return
    with open(sys.argv[1], encoding="utf-8") as f:
        task = json.load(f)
    out, missing = render(task)
    print(out)
    for p in missing:
        print(f"缺文件：{p}", file=sys.stderr)


if __name__ == "__main__":
    main()
