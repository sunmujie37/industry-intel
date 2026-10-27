#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""行业情报日报网页生成器
读取 industry-intel/archive/*.md → 生成 web/index.html
archive 格式见 config/topics.md（## 板块 / - **标题**｜摘要｜来源｜URL）
"""
import re, html, glob, os, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(BASE, 'archive')
OUT = os.path.join(BASE, 'web', 'index.html')

SECTION_COLORS = {
    '半导体': '#1F5C8B',
    '光通信': '#B03A2E',
    '物理AI': '#2F6B3A',
    'AI算力与资本': '#9A6B1F',
    '值得追问的线索': '#6B4FA0',
}

def parse_file(path):
    date = os.path.splitext(os.path.basename(path))[0]
    sections, cur, items = [], None, []
    def flush():
        if cur is not None:
            sections.append((cur, items))
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            m = re.match(r'^##\s+(.+)$', line)
            if m:
                flush(); cur = m.group(1).strip(); items = []; continue
            m = re.match(r'^-\s+\*\*(.+?)\*\*｜(.+?)｜(.+?)｜(\S+)$', line)
            if m and cur is not None:
                items.append({'title': m.group(1), 'summary': m.group(2),
                              'source': m.group(3), 'url': m.group(4)})
        flush()
    return date, sections

def esc(s):
    return html.escape(s, quote=True)

def render():
    files = sorted(glob.glob(os.path.join(ARCHIVE, '*.md')), reverse=True)
    dates = [os.path.splitext(os.path.basename(f))[0] for f in files]
    days = len(files)
    total_items = 0
    body = []
    for f in files:
        date, sections = parse_file(f)
        is_first = (f == files[0])
        body.append(f'<article class="day{" today" if is_first else ""}">')
        d = datetime.date.fromisoformat(date)
        wd = '一二三四五六日'[d.weekday()]
        body.append(f'<h2 class="day-title">{
            d.strftime("%Y年%m月%d日")} <span>星期{wd}</span>{
            " <em>今日</em>" if is_first else ""}</h2>')
        for name, items in sections:
            color = SECTION_COLORS.get(name, '#444')
            body.append(f'<section><h3 style="border-color:{color}">'
                        f'<span class="dot" style="background:{color}"></span>'
                        f'{esc(name)}</h3><ul>')
            for it in items:
                total_items += 1
                body.append(
                    '<li>'
                    f'<a class="t" href="{esc(it["url"])}" target="_blank">{esc(it["title"])}</a>'
                    f'<p class="s">{esc(it["summary"])}</p>'
                    f'<p class="m">{esc(it["source"])} · <a href="{esc(it["url"])}" target="_blank">原文</a></p>'
                    '</li>')
            body.append('</ul></section>')
        body.append('</article>')

    nav = ''.join(f'<option value="{d}">{d}</option>' for d in dates)
    page = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>行业情报日报 · 半导体 / 光通信 / 物理AI</title>
<style>
:root {{ --ink:#1a1a1a; --sub:#666; --line:#e6e2da; --accent:#B03A2E; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:"Noto Serif SC","Songti SC","SimSun",serif; background:#f7f5f0; color:var(--ink); line-height:1.75; }}
.wrap {{ max-width:780px; margin:0 auto; padding:32px 20px 80px; }}
.masthead {{ border-bottom:3px double var(--ink); padding-bottom:18px; margin-bottom:8px; }}
.masthead h1 {{ font-size:26px; letter-spacing:2px; }}
.masthead h1 small {{ font-size:13px; letter-spacing:1px; color:var(--sub); font-weight:normal; margin-left:10px; }}
.masthead p {{ color:var(--sub); font-size:13px; margin-top:6px; }}
.stats {{ display:flex; gap:24px; font-size:13px; color:var(--sub); padding:10px 0 20px; }}
.stats b {{ color:var(--accent); font-size:16px; margin-right:4px; }}
.jump {{ margin:0 0 24px; }}
.jump select {{ font-family:inherit; padding:6px 10px; border:1px solid var(--line); background:#fff; font-size:13px; }}
article.day {{ background:#fff; border:1px solid var(--line); padding:28px 30px; margin-bottom:28px; }}
article.day.today {{ box-shadow:0 2px 14px rgba(0,0,0,.05); }}
h2.day-title {{ font-size:20px; margin-bottom:18px; padding-bottom:10px; border-bottom:1px solid var(--line); }}
h2.day-title span {{ font-size:13px; color:var(--sub); font-weight:normal; margin-left:8px; }}
h2.day-title em {{ font-style:normal; font-size:12px; color:#fff; background:var(--accent); padding:1px 8px; border-radius:2px; margin-left:10px; vertical-align:2px; }}
section {{ margin-bottom:20px; }}
h3 {{ font-size:16px; padding-left:10px; border-left:4px solid; margin-bottom:10px; }}
h3 .dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:8px; vertical-align:1px; }}
ul {{ list-style:none; }}
li {{ padding:10px 0 10px 2px; border-bottom:1px dashed var(--line); }}
li:last-child {{ border-bottom:none; }}
a.t {{ font-size:15.5px; font-weight:bold; color:var(--ink); text-decoration:none; }}
a.t:hover {{ color:var(--accent); text-decoration:underline; }}
p.s {{ font-size:14px; color:#333; margin-top:4px; }}
p.m {{ font-size:12.5px; color:var(--sub); margin-top:4px; }}
p.m a {{ color:var(--sub); }}
footer {{ color:var(--sub); font-size:12px; text-align:center; padding-top:16px; border-top:1px solid var(--line); }}
</style>
</head>
<body>
<div class="wrap">
  <header class="masthead">
    <h1>行业情报日报<small>半导体 · 光通信 · 物理AI</small></h1>
    <p>每日定时采集公开信息，预筛归并入库。仅公开来源，由 Kimi Claw 生成。</p>
  </header>
  <div class="stats"><span><b>{days}</b>期</span><span><b>{total_items}</b>条入库</span><span>更新于每日 08:17（工作日）</span></div>
  <div class="jump"><select onchange="if(this.value)location.hash=this.value"><option value="">跳转到日期…</option>{nav}</select></div>
  {''.join(body)}
  <footer>合规声明：本信息库仅收录公开来源信息，不含任何未公开或内部材料。生成：Kimi Claw for sum</footer>
</div>
</body>
</html>'''
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'generated {OUT} ({days} days, {total_items} items)')

if __name__ == '__main__':
    render()
