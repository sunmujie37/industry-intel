#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""行业情报日报 · 网页生成器 v2
从 archive/*.md 生成单页报纸版 index.html + feed.xml

条目格式（archive/*.md）：
  ## 半导体
  - **标题**｜摘要含关键数字｜来源+日期｜URL｜标签a,标签b   （标签段可选）
  ## 今日要点     （可选，TL;DR 区）
  - 一句话要点
"""
import re
import html
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / 'archive'
OUT = ROOT / 'web'
TZ = timezone(timedelta(hours=8))

SECTIONS = ['全球政经', '半导体', '光通信', '物理AI', 'AI算力与资本', '值得追问的线索']
SECTION_COLORS = {
    '全球政经': '#234E70',
    '半导体': '#8C1F18',
    '光通信': '#1F4E79',
    '物理AI': '#1E5E3E',
    'AI算力与资本': '#9A6B1F',
    '值得追问的线索': '#6B4FA0',
}
BOARDS = [
    ('板块一 · 全球政经速递', ['全球政经']),
    ('板块二 · 行业动态情报', ['半导体', '光通信', '物理AI', 'AI算力与资本']),
]

ITEM_RE = re.compile(r'^- \*\*(.+?)\*\*｜(.*?)｜(.*?)｜(\S+)(?:｜(.*))?$')
DAY_TITLE_RE = re.compile(r'^# (.+)$')

def parse_day(md_path):
    date = md_path.stem
    title = date
    sections = {}
    highlights = []
    cur = None
    for line in md_path.read_text(encoding='utf-8').splitlines():
        m = DAY_TITLE_RE.match(line)
        if m:
            title = m.group(1).strip()
            continue
        if line.startswith('## '):
            cur = line[3:].strip()
            if cur != '今日要点':
                sections.setdefault(cur, [])
            continue
        if cur == '今日要点':
            if line.startswith('- '):
                highlights.append(line[2:].strip())
            continue
        if cur is None or cur not in SECTIONS:
            continue
        m = ITEM_RE.match(line)
        if m:
            t, summary, source, url, tags = m.groups()
            sections[cur].append({
                'title': t.strip(),
                'summary': summary.strip(),
                'source': source.strip(),
                'url': url.strip(),
                'tags': [x.strip() for x in (tags or '').split(',') if x.strip()],
            })
        elif line.startswith('- ') and cur == '值得追问的线索':
            sections[cur].append({'clue': line[2:].strip()})
    return {'date': date, 'title': title, 'sections': sections, 'highlights': highlights}

def esc(s):
    return html.escape(s, quote=True)

def main():
    OUT.mkdir(exist_ok=True)
    days = sorted(ARCHIVE.glob('*.md'), reverse=True)
    parsed = [parse_day(p) for p in days]
    today_str = datetime.now(TZ).strftime('%Y-%m-%d')
    generated = datetime.now(TZ).strftime('%Y-%m-%d %H:%M')

    # ---------- 聚合标签 ----------
    all_tags = {}
    for d in parsed:
        for sec, items in d['sections'].items():
            for it in items:
                if not isinstance(it, dict) or 'tags' not in it:
                    continue
                for tg in it['tags']:
                    all_tags[tg] = all_tags.get(tg, 0) + 1
    top_tags = sorted(all_tags.items(), key=lambda kv: (-kv[1], kv[0]))[:30]

    # ---------- 构建 HTML ----------
    toc = []
    body = []
    rss_items = []
    total_items = 0

    for d in parsed:
        is_today = d['date'] == today_str
        badge = ' <span class="today-badge">今日</span>' if is_today else ''
        toc.append(
            f'<option value="d-{d["date"]}">{d["date"]}{"（今日）" if is_today else ""}</option>'
        )
        body.append(f'<article class="day" id="d-{d["date"]}" data-date="{d["date"]}">')
        body.append(f'<header class="day-header"><span class="day-date">{esc(d["date"])}</span>'
                    f'<span class="day-title">{esc(d["title"].split(" ", 1)[-1] if d["title"].startswith(d["date"]) else d["title"])}</span>{badge}</header>')

        if d['highlights'] and is_today:
            body.append('<section class="highlights"><h3>📌 今日要点</h3><ul>')
            for h in d['highlights']:
                body.append(f'<li>{esc(h)}</li>')
            body.append('</ul></section>')

        for board_name, board_secs in BOARDS:
            board_parts = [(s, d['sections'].get(s)) for s in board_secs]
            board_parts = [(s, its) for s, its in board_parts if its]
            if not board_parts:
                continue
            body.append(f'<div class="board-banner">{esc(board_name)}</div>')
            for sec, items in board_parts:
                color = SECTION_COLORS.get(sec, '#333')
                body.append(f'<section class="block" data-sec="{esc(sec)}">')
                body.append(f'<h3 style="color:{color};border-color:{color}">{esc(sec)}'
                            f'<span class="sec-count">{len(items)}</span></h3>')
                body.append('<ul class="items">')
                for i, it in enumerate(items):
                    total_items += 1
                    anchor = f'd-{d["date"]}-{sec}-{i}'
                    tag_html = ''.join(
                        f'<button class="tag" data-tag="{esc(t)}">{esc(t)}</button>' for t in it['tags']
                    )
                    tag_attr = ','.join(it['tags'])
                    search_blob = esc(' '.join([it['title'], it['summary'], it['source'], tag_attr]))
                    body.append(
                        f'<li class="item" id="{anchor}" data-sec="{esc(sec)}" data-tags="{esc(tag_attr)}" '
                        f'data-search="{search_blob}">'
                        f'<div class="item-head"><a class="item-title" href="{esc(it["url"])}" target="_blank" rel="noopener">{esc(it["title"])}</a>'
                        f'<a class="anchor" href="#{anchor}" title="复制本条链接">#</a></div>'
                        f'<p class="summary">{esc(it["summary"])}</p>'
                        f'<div class="meta"><span class="src">{esc(it["source"])}</span>'
                        f'<a class="orig" href="{esc(it["url"])}" target="_blank" rel="noopener">阅读原文 ↗</a>'
                        f'{f"<span class=\"tags\">{tag_html}</span>" if tag_html else ""}</div>'
                        f'</li>'
                    )
                    if is_today or len(rss_items) < 40:
                        rss_items.append((d, it))
                body.append('</ul></section>')
        # 值得追问的线索：纯文本列表，无链接
        clues = [c['clue'] for c in d['sections'].get('值得追问的线索', []) if 'clue' in c]
        if clues:
            body.append('<section class="block clues" data-sec="值得追问的线索">'
                        '<h3 style="color:#6B4FA0;border-color:#6B4FA0">值得追问的线索'
                        f'<span class="sec-count">{len(clues)}</span></h3><ul class="clue-list">')
            for c in clues:
                body.append(f'<li>{esc(c)}</li>')
            body.append('</ul></section>')
        body.append('</article>')

    tags_cloud = ''.join(
        f'<button class="tag cloud-tag" data-tag="{esc(t)}">{esc(t)} <em>{c}</em></button>'
        for t, c in top_tags
    )

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="个人行业情报日报：全球政经速递 + 行业动态情报（半导体/光通信/物理AI/AI算力与资本），每日公开信息精选。">
<meta property="og:title" content="行业情报日报 · 全球政经/行业动态情报">
<meta property="og:description" content="板块一：全球政经速递（财新/官媒/BBC/WaPo等公开渠道）；板块二：行业动态情报（券商投研摘要/企业公告）。每日更新。">
<title>行业情报日报 · 全球政经 / 行业动态情报</title>
<link rel="alternate" type="application/rss+xml" title="行业情报日报" href="feed.xml">
<style>
:root {{
  --bg: #F5F1E8; --paper: #FCFAF4; --ink: #26221B; --muted: #7A7264;
  --line: #E4DECF; --accent: #8C1F18; --head: #1F1B14;
  --chip-bg: #EFE9DA; --chip-on: #8C1F18; --shadow: rgba(38,34,27,.08);
}}
html[data-theme="dark"] {{
  --bg: #16130E; --paper: #1E1A13; --ink: #E8E2D4; --muted: #9A917E;
  --line: #35301F; --accent: #C4625A; --head: #F0EAD9;
  --chip-bg: #2B2618; --chip-on: #D4706A; --shadow: rgba(0,0,0,.4);
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  background: var(--bg); color: var(--ink);
  font-family: "Songti SC", "Noto Serif CJK SC", "SimSun", Georgia, serif;
  line-height: 1.75; -webkit-font-smoothing: antialiased;
}}
.page {{ max-width: 860px; margin: 0 auto; padding: 32px 20px 80px; }}
header.masthead {{
  border-bottom: 3px double var(--accent); padding-bottom: 14px; margin-bottom: 8px;
}}
.masthead .kicker {{
  font-size: 12px; letter-spacing: 3px; color: var(--muted);
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
}}
.masthead h1 {{ font-size: 30px; color: var(--head); letter-spacing: 1px; line-height: 1.3; }}
.masthead .sub {{ font-size: 13px; color: var(--muted); margin-top: 4px;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif; }}
.masthead .sub b {{ color: var(--accent); font-weight: 600; }}

.toolbar {{
  position: sticky; top: 0; z-index: 50; background: var(--paper);
  border: 1px solid var(--line); border-radius: 10px; box-shadow: 0 4px 16px var(--shadow);
  padding: 10px 12px; margin: 16px 0 20px;
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
}}
.search-wrap {{ flex: 1 1 180px; position: relative; }}
.search-wrap input {{
  width: 100%; padding: 8px 12px 8px 32px; border: 1px solid var(--line); border-radius: 8px;
  background: var(--bg); color: var(--ink); font-size: 14px; outline: none;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
}}
.search-wrap input:focus {{ border-color: var(--accent); }}
.search-wrap::before {{
  content: "🔍"; position: absolute; left: 9px; top: 50%; transform: translateY(-50%);
  font-size: 13px; opacity: .7;
}}
.chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.chip {{
  padding: 6px 12px; border-radius: 999px; border: 1px solid var(--line);
  background: var(--chip-bg); color: var(--ink); font-size: 12.5px; cursor: pointer;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif; transition: all .15s;
}}
.chip.on {{ background: var(--chip-on); color: #FCFAF4; border-color: var(--chip-on); }}
#themeBtn {{
  margin-left: auto; border: 1px solid var(--line); background: var(--chip-bg);
  border-radius: 8px; padding: 6px 10px; cursor: pointer; font-size: 14px;
}}
.active-filter {{
  display: none; margin: 0 0 14px; padding: 8px 12px; border: 1px dashed var(--accent);
  border-radius: 8px; font-size: 13px; color: var(--accent);
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
}}
.active-filter.show {{ display: block; }}
.active-filter button {{
  margin-left: 10px; background: none; border: none; color: var(--muted);
  cursor: pointer; font-size: 12px; text-decoration: underline;
}}
.tags-cloud {{ margin: 0 0 20px; padding: 12px 14px; background: var(--paper);
  border: 1px solid var(--line); border-radius: 10px; }}
.tags-cloud h4 {{ font-size: 12px; color: var(--muted); letter-spacing: 2px; margin-bottom: 8px;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-weight: 500; }}
.tag {{
  display: inline-block; margin: 2px 4px 2px 0; padding: 2px 10px; border-radius: 999px;
  border: 1px solid var(--line); background: var(--chip-bg); color: var(--muted);
  font-size: 12px; cursor: pointer;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
}}
.tag:hover {{ border-color: var(--accent); color: var(--accent); }}
.tag em {{ font-style: normal; opacity: .65; font-size: 11px; }}
.tag.on {{ background: var(--chip-on); color: #FCFAF4; border-color: var(--chip-on); }}

.board-banner {{
  font-size: 17px; font-weight: 800; color: var(--head); letter-spacing: 5px;
  border-top: 3px double var(--accent); border-bottom: 1px solid var(--line);
  padding: 9px 0 7px; margin: 22px 0 14px; text-align: center;
}}
.clue-list li {{ font-size: 13.5px; color: var(--ink); opacity: .88; margin: 0 0 7px 20px; list-style: '→  '; }}

article.day {{
  background: var(--paper); border: 1px solid var(--line); border-radius: 12px;
  padding: 24px 26px; margin-bottom: 28px; box-shadow: 0 2px 10px var(--shadow);
}}
.day-header {{
  border-bottom: 1px solid var(--line); padding-bottom: 10px; margin-bottom: 14px;
  display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
}}
.day-date {{ font-size: 20px; font-weight: 700; color: var(--head); letter-spacing: 1px; }}
.day-title {{ font-size: 14px; color: var(--muted); }}
.today-badge {{
  background: var(--accent); color: #FCFAF4; font-size: 11px; padding: 2px 10px;
  border-radius: 4px; letter-spacing: 2px;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
}}
.highlights {{
  background: var(--chip-bg); border-left: 4px solid var(--accent);
  padding: 12px 16px; border-radius: 0 8px 8px 0; margin-bottom: 18px;
}}
.highlights h3 {{ font-size: 14px; color: var(--accent); margin-bottom: 6px;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif; }}
.highlights li {{ font-size: 14.5px; margin-left: 18px; margin-bottom: 4px; }}
.block {{ margin-bottom: 18px; }}
.block h3 {{
  font-size: 17px; border-bottom: 2px solid; padding-bottom: 4px; margin-bottom: 10px;
  display: flex; align-items: center; gap: 8px;
}}
.sec-count {{
  font-size: 11px; background: var(--chip-bg); color: var(--muted);
  border-radius: 999px; padding: 1px 9px; font-weight: 400;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
}}
ul.items {{ list-style: none; }}
li.item {{ padding: 12px 0; border-bottom: 1px dashed var(--line); }}
li.item:last-child {{ border-bottom: none; }}
li.item.hidden {{ display: none; }}
.item-head {{ display: flex; align-items: baseline; gap: 8px; }}
a.item-title {{ font-size: 15.5px; font-weight: 700; color: var(--ink); text-decoration: none; }}
a.item-title:hover {{ color: var(--accent); text-decoration: underline; }}
a.anchor {{ color: var(--muted); text-decoration: none; font-size: 12px; opacity: 0; transition: opacity .15s; }}
li.item:hover a.anchor {{ opacity: 1; }}
.summary {{ font-size: 14px; color: var(--ink); opacity: .92; margin: 6px 0; }}
.meta {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 12.5px;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif; }}
.src {{ color: var(--muted); }}
a.orig {{ color: var(--accent); text-decoration: none; }}
a.orig:hover {{ text-decoration: underline; }}
footer {{ text-align: center; font-size: 12px; color: var(--muted); margin-top: 24px;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif; }}
.result-empty {{ display:none; text-align:center; color:var(--muted); padding: 30px 0; }}
.result-empty.show {{ display:block; }}
.day.dimmed {{ display: none; }}
@media (max-width: 600px) {{
  .page {{ padding: 20px 12px 60px; }}
  .masthead h1 {{ font-size: 23px; }}
  article.day {{ padding: 16px 14px; }}
  .toolbar {{ position: static; }}
}}
</style>
</head>
<body>
<div class="page">
  <header class="masthead">
    <div class="kicker">行业情报日报 · 公开信息跟踪</div>
    <h1>全球政经 <span style="color:var(--accent)">·</span> 行业动态情报</h1>
    <div class="sub">工作日更新 · 仅基于公开来源 · <b>共 {len(parsed)} 期 · {total_items} 条</b></div>
  </header>

  <div class="toolbar">
    <div class="search-wrap"><input id="q" type="search" placeholder="搜索标题 / 摘要 / 标签…"></div>
    <div class="chips" id="secChips">
      <button class="chip on" data-sec="all">全部</button>
      <button class="chip" data-sec="全球政经">政经</button>
      <button class="chip" data-sec="半导体">半导体</button>
      <button class="chip" data-sec="光通信">光通信</button>
      <button class="chip" data-sec="物理AI">物理AI</button>
      <button class="chip" data-sec="AI算力与资本">AI算力与资本</button>
      <button class="chip" data-sec="值得追问的线索">线索</button>
    </div>
    <button id="themeBtn" title="切换深色模式">🌙</button>
  </div>

  <div class="active-filter" id="activeFilter"></div>

  <div class="tags-cloud">
    <h4>🏷 高频标签（点击筛选相关跟踪）</h4>
    {tags_cloud}
  </div>

  <nav style="margin-bottom:16px">
    <select id="jump" style="padding:8px 12px;border:1px solid var(--line);border-radius:8px;background:var(--paper);color:var(--ink);font-size:14px;width:100%;font-family:'PingFang SC','Microsoft YaHei',sans-serif">
      <option value="">📅 跳转到指定日期…</option>
      {''.join(toc)}
    </select>
  </nav>

  <div class="result-empty" id="empty">没有匹配的内容，换个关键词或清除筛选试试。</div>

  {''.join(body)}

  <footer>
    行业情报日报 · 由 Kimi Claw 自动采集生成 · 仅基于公开信息，不构成投资建议<br>
    生成时间 {generated}（Asia/Shanghai） · <a href="feed.xml" style="color:var(--accent)">RSS订阅</a>
  </footer>
</div>

<script>
const state = {{ q: '', sec: 'all', tag: null }};
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));

function applyFilters() {{
  let visible = 0;
  $$('li.item').forEach(el => {{
    const okSec = state.sec === 'all' || el.dataset.sec === state.sec;
    const okTag = !state.tag || (el.dataset.tags || '').split(',').includes(state.tag);
    const okQ = !state.q || el.dataset.search.toLowerCase().includes(state.q);
    const show = okSec && okTag && okQ;
    el.classList.toggle('hidden', !show);
    if (show) visible++;
  }});
  $$('article.day').forEach(day => {{
    const any = Array.from(day.querySelectorAll('li.item')).some(el => !el.classList.contains('hidden'));
    day.classList.toggle('dimmed', !any);
  }});
  $('#empty').classList.toggle('show', visible === 0);

  const parts = [];
  if (state.sec !== 'all') parts.push('板块：' + state.sec);
  if (state.tag) parts.push('标签：' + state.tag);
  const af = $('#activeFilter');
  if (parts.length) {{
    af.innerHTML = '筛选中 — ' + parts.join(' · ') + '<button id="clearFilter">清除全部</button>';
    af.classList.add('show');
    $('#clearFilter').onclick = () => {{
      state.sec = 'all'; state.tag = null; state.q = '';
      $('#q').value = '';
      $$('#secChips .chip').forEach(c => c.classList.toggle('on', c.dataset.sec === 'all'));
      $$('.tag.on').forEach(t => t.classList.remove('on'));
      applyFilters();
    }};
  }} else {{
    af.classList.remove('show');
  }}
}}

$('#q').addEventListener('input', e => {{ state.q = e.target.value.trim().toLowerCase(); applyFilters(); }});

$$('#secChips .chip').forEach(chip => {{
  chip.onclick = () => {{
    state.sec = chip.dataset.sec;
    $$('#secChips .chip').forEach(c => c.classList.toggle('on', c === chip));
    applyFilters();
  }};
}});

$$('.tag').forEach(t => {{
  t.onclick = () => {{
    const tag = t.dataset.tag;
    if (state.tag === tag) {{
      state.tag = null;
      $$('.tag.on').forEach(x => x.classList.remove('on'));
    }} else {{
      state.tag = tag;
      $$('.tag.on').forEach(x => x.classList.remove('on'));
      $$(`.tag[data-tag="${{CSS.escape(tag)}}"]`).forEach(x => x.classList.add('on'));
    }}
    applyFilters();
    document.querySelector('.toolbar').scrollIntoView({{ behavior: 'smooth' }});
  }};
}});

$('#jump').addEventListener('change', e => {{
  if (!e.target.value) return;
  const el = document.getElementById(e.target.value);
  if (el) el.scrollIntoView({{ behavior: 'smooth' }});
  e.target.value = '';
}});

// 深色模式
const html = document.documentElement;
const savedTheme = localStorage.getItem('theme');
if (savedTheme) html.dataset.theme = savedTheme;
else if (window.matchMedia('(prefers-color-scheme: dark)').matches) html.dataset.theme = 'dark';
const syncThemeBtn = () => $('#themeBtn').textContent = html.dataset.theme === 'dark' ? '☀️' : '🌙';
syncThemeBtn();
$('#themeBtn').onclick = () => {{
  html.dataset.theme = html.dataset.theme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('theme', html.dataset.theme);
  syncThemeBtn();
}};

// 锚点链接复制
$$('a.anchor').forEach(a => {{
  a.onclick = ev => {{
    ev.preventDefault();
    const url = location.origin + location.pathname + a.getAttribute('href');
    navigator.clipboard?.writeText(url);
    a.textContent = '✓';
    setTimeout(() => a.textContent = '#', 1200);
  }};
}});
</script>
</body>
</html>
"""
    (OUT / 'index.html').write_text(html_doc, encoding='utf-8')

    # ---------- feed.xml ----------
    base_url = 'https://sunmujie37.github.io/industry-intel'
    rss = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0"><channel>',
           '<title>行业情报日报 · 半导体/光通信/物理AI/AI算力与资本</title>',
           f'<link>{base_url}/</link>',
           '<description>每日行业情报追踪，仅基于公开信息。</description>',
           f'<lastBuildDate>{datetime.now(TZ).strftime("%a, %d %b %Y %H:%M:%S +0800")}</lastBuildDate>']
    for d, it in rss_items[:40]:
        rss.append('<item>')
        rss.append(f'<title>[{esc(d["date"])}] {esc(it["title"])}</title>')
        rss.append(f'<link>{esc(it["url"])}</link>')
        rss.append(f'<guid>{esc(it["url"])}</guid>')
        rss.append(f'<description>{esc(it["summary"])}（{esc(it["source"])}）</description>')
        rss.append(f'<pubDate>{datetime.strptime(d["date"], "%Y-%m-%d").strftime("%a, %d %b %Y 09:00:00 +0800")}</pubDate>')
        rss.append('</item>')
    rss.append('</channel></rss>')
    (OUT / 'feed.xml').write_text('\n'.join(rss), encoding='utf-8')

    print(f"generated {OUT/'index.html'} ({len(parsed)} days, {total_items} items), feed.xml ok")


if __name__ == '__main__':
    main()
