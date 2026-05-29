#!/usr/bin/env python3
"""把「产品克制」评审报告(三部分 Markdown)渲染成专业 HTML。纯标准库,零依赖。"""
import re
import os
import sys
import glob
import html as html_lib
from datetime import datetime

DIMENSIONS = ['真需求度', '价值与差异', '可行性', '商业账', '市场与时机', '克制度']

# emoji -> (css 类名, 文字标签)
LAMP_MAP = {'🔴': ('red', '红'), '🟡': ('amber', '黄'), '🟢': ('green', '绿')}

# 总体倾向 -> css 类名
TENDENCY_CLASS = {'别做': 'red', '再想想': 'amber', '可以试': 'green'}


def split_sections(md):
    """按 ## 二级标题把报告切成 preamble / one / two / three 四块。"""
    parts = re.split(r'(?m)^##\s+', md)
    sec = {'preamble': parts[0].strip(), 'one': '', 'two': '', 'three': ''}
    for p in parts[1:]:
        header, _, body = p.partition('\n')
        body = body.strip()
        if '可行性评价' in header:
            sec['one'] = body
        elif '简要概述' in header:
            sec['two'] = body
        elif '详细说明' in header:
            sec['three'] = body
    return sec


def parse_tendency(text):
    """从「总体倾向:X」抓出 别做 / 再想想 / 可以试。"""
    m = re.search(r'总体倾向[::]\s*\*{0,2}\s*(别做|再想想|可以试)', text)
    return m.group(1) if m else None


def parse_scorecard(text):
    """解析评分卡表格,返回 [{'dim','lamp','reason'}, ...]。只收含灯 emoji 的数据行。"""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < 3:
            continue
        dim, lamp, reason = cells[0], cells[1], cells[2]
        if dim == '维度' or set(dim) <= set('-: '):  # 跳过表头与分隔行
            continue
        emoji = next((e for e in LAMP_MAP if e in lamp), None)
        if not emoji:
            continue
        rows.append({'dim': dim, 'lamp': emoji, 'reason': reason})
    return rows


def parse_detail_blocks(text):
    """从「三、详细说明」里切出 body 与三个固定块。缺块返回 None,不报错。"""
    anchors = [
        ('premortem', re.compile(r'\*\*\s*Premortem')),
        ('validation', re.compile(r'\*\*[^\n]*?最小成本验证')),
        ('restart', re.compile(r'\*\*\s*重启条件')),
    ]
    positions = []
    for key, pat in anchors:
        m = pat.search(text)
        if m:
            positions.append((m.start(), key))
    positions.sort()
    blocks = {'body': text.strip(), 'premortem': None, 'validation': None, 'restart': None}
    if not positions:
        return blocks
    blocks['body'] = text[:positions[0][0]].strip()
    for i, (start, key) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        blocks[key] = text[start:end].strip()
    return blocks


def md_inline(text):
    """行内 Markdown:先 HTML 转义,再处理 **粗体** 与 `代码`。"""
    text = html_lib.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return text


_LI = r'^\s*[-*]\s+'
_OLI = r'^\s*\d+\.\s+'


def md_block(md):
    """块级 Markdown:段落 / 无序列表 / 有序列表 / 分隔线。"""
    lines = md.split('\n')
    out, i, n = [], 0, len(md.split('\n'))
    while i < n:
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if re.match(r'^---+$', line.strip()):
            out.append('<hr/>')
            i += 1
            continue
        if re.match(_LI, line):
            items = []
            while i < n and re.match(_LI, lines[i]):
                items.append('<li>' + md_inline(re.sub(_LI, '', lines[i].rstrip())) + '</li>')
                i += 1
            out.append('<ul>' + ''.join(items) + '</ul>')
            continue
        if re.match(_OLI, line):
            items = []
            while i < n and re.match(_OLI, lines[i]):
                items.append('<li>' + md_inline(re.sub(_OLI, '', lines[i].rstrip())) + '</li>')
                i += 1
            out.append('<ol>' + ''.join(items) + '</ol>')
            continue
        para = [line]
        i += 1
        while i < n and lines[i].strip() and not re.match(_LI + r'|' + _OLI + r'|^---+$', lines[i]):
            para.append(lines[i].rstrip())
            i += 1
        out.append('<p>' + md_inline(' '.join(para)) + '</p>')
    return '\n'.join(out)


def _strip_lead(content):
    """去掉块首的 **标题** 行(已由 <h3> 呈现),保留其余内容。"""
    lines = content.split('\n')
    if lines and lines[0].lstrip().startswith('**'):
        m = re.match(r'\s*\*\*(.+?)\*\*[::]?\s*(.*)', lines[0])
        if m:
            rest = m.group(2)
            lines = ([rest] if rest.strip() else []) + lines[1:]
    return '\n'.join(lines).strip()


def derive_title(explicit, eval_dirname=None, md_path=None):
    """标题优先级:显式参数 > eval 目录名 > 文件名 > 兜底。"""
    if explicit:
        return explicit
    if eval_dirname:
        return re.sub(r'^eval-\d+-', '', eval_dirname).replace('-', ' ')
    if md_path:
        return os.path.splitext(os.path.basename(md_path))[0]
    return '未命名想法'


def derive_subtitle(preamble):
    """取序言复述的第一句作副标题(去 --- 行、限长)。"""
    if not preamble:
        return None
    text = re.sub(r'(?m)^---+$', '', preamble).strip()
    if not text:
        return None
    first = re.split(r'[。\n]', text, 1)[0].strip()
    if not first:
        return None
    return first[:48] + '…' if len(first) > 48 else first


def parse_report(md, title=None, eval_dirname=None, md_path=None, date=''):
    """把一份报告 Markdown 解析成结构化 dict。"""
    sec = split_sections(md)
    detail = parse_detail_blocks(sec['three'])
    return {
        'title': derive_title(title, eval_dirname=eval_dirname, md_path=md_path),
        'subtitle': derive_subtitle(sec['preamble']),
        'date': date,
        'tendency': parse_tendency(sec['one']),
        'preamble': sec['preamble'],
        'scorecard': parse_scorecard(sec['one']),
        'summary': sec['two'],
        'detail_body': detail['body'],
        'premortem': detail['premortem'],
        'validation': detail['validation'],
        'restart': detail['restart'],
    }


HTML_DOC = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{style}</style></head>
<body>{body}</body></html>'''

STYLE = '''
:root{--red:#c0392b;--amber:#b7791f;--green:#1e8449;--gray:#6b7280;--line:#e6e6e6;--ink:#1f2430;--soft:#fafafa}
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei","Helvetica Neue",Arial,sans-serif;
max-width:820px;margin:0 auto;padding:48px 28px;color:var(--ink);line-height:1.75;background:#fff;font-size:15.5px}
h1{font-size:13px;letter-spacing:.18em;color:var(--gray);font-weight:600;margin:0 0 14px}
.cover{border-bottom:2px solid var(--ink);padding-bottom:20px;margin-bottom:24px}
.idea-title{font-size:27px;font-weight:700;line-height:1.3;margin:2px 0 6px}
.subtitle{color:var(--gray);font-size:14px}
.meta{display:flex;align-items:center;gap:14px;margin-top:14px;flex-wrap:wrap}
.meta .date{color:var(--gray);font-size:13px}
.badge{display:inline-block;padding:5px 14px;border-radius:999px;color:#fff;font-weight:600;font-size:13px}
.badge.red{background:var(--red)}.badge.amber{background:var(--amber)}.badge.green{background:var(--green)}.badge.gray{background:var(--gray)}
nav.toc{display:flex;gap:18px;flex-wrap:wrap;font-size:13.5px;margin-bottom:28px;padding-bottom:14px;border-bottom:1px solid var(--line)}
nav.toc a{color:var(--gray);text-decoration:none}nav.toc a:hover{color:var(--ink);text-decoration:underline}
h2{font-size:19px;margin:34px 0 14px;padding-left:11px;border-left:4px solid var(--ink)}
table.scorecard{width:100%;border-collapse:collapse;font-size:14.5px}
.scorecard th{text-align:left;color:var(--gray);font-weight:600;font-size:12.5px;border-bottom:2px solid var(--line);padding:8px 10px}
.scorecard td{border-bottom:1px solid var(--line);padding:11px 10px;vertical-align:top}
.scorecard .dim{white-space:nowrap;font-weight:600;border-left:4px solid transparent}
.row-red .dim{border-left-color:var(--red)}.row-amber .dim{border-left-color:var(--amber)}.row-green .dim{border-left-color:var(--green)}
.scorecard .lamp{white-space:nowrap;color:var(--gray)}
.lamp-dot{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px;vertical-align:middle}
.lamp-red{background:var(--red)}.lamp-amber{background:var(--amber)}.lamp-green{background:var(--green)}.lamp-gray{background:var(--gray)}
blockquote.summary{margin:0;background:var(--soft);border-left:4px solid var(--gray);padding:14px 18px;border-radius:0 6px 6px 0;font-size:15.5px}
.box{padding:14px 18px;border-radius:0 6px 6px 0;margin:18px 0}
.box h3{margin:0 0 8px;font-size:15px}
.box.premortem{background:#fdf3f2;border-left:4px solid var(--red)}
.box.validation{background:#f1faf4;border-left:4px solid var(--green)}
.box.restart{background:var(--soft);border-left:4px solid var(--gray)}
p{margin:10px 0}ul,ol{margin:10px 0;padding-left:22px}li{margin:5px 0}
code{background:#f0f0f0;padding:1px 5px;border-radius:4px;font-size:.9em}
hr{border:none;border-top:1px solid var(--line);margin:20px 0}
.index-list{list-style:none;padding:0}
.index-list li{border-bottom:1px solid var(--line)}
.index-list a{display:flex;align-items:center;gap:12px;padding:13px 4px;text-decoration:none;color:var(--ink)}
.index-list a:hover{background:var(--soft)}
.idx-title{flex:1;font-weight:600}
.mini{display:flex;gap:4px}
@media print{body{max-width:none;padding:0;font-size:12pt;-webkit-print-color-adjust:exact;print-color-adjust:exact}
nav.toc{display:none}section{break-inside:avoid}
.badge,.lamp-dot,.box,blockquote.summary{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
'''


def _scorecard_html(scorecard):
    rows = []
    for s in scorecard:
        cls, label = LAMP_MAP.get(s['lamp'], ('gray', '?'))
        rows.append(
            f'<tr class="row-{cls}"><td class="dim">{html_lib.escape(s["dim"])}</td>'
            f'<td class="lamp"><span class="lamp-dot lamp-{cls}"></span>{label}</td>'
            f'<td class="reason">{md_inline(s["reason"])}</td></tr>')
    return ('<table class="scorecard"><thead><tr><th>维度</th><th>灯</th><th>理由</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


def _box_html(kind, label, content):
    if not content:
        return ''
    return f'<section class="box {kind}"><h3>{label}</h3>{md_block(_strip_lead(content))}</section>'


def render_report_html(report):
    tcls = TENDENCY_CLASS.get(report['tendency'], 'gray')
    subtitle = (f'<div class="subtitle">{html_lib.escape(report["subtitle"])}</div>'
                if report.get('subtitle') else '')
    detail = md_block(report['detail_body'])
    detail += _box_html('premortem', 'Premortem · 事前验尸', report['premortem'])
    detail += _box_html('validation', '最小验证动作', report['validation'])
    detail += _box_html('restart', '重启条件', report['restart'])
    body = f'''<article>
<div class="cover">
<h1>产品克制 · 可行性评审报告</h1>
<div class="idea-title">{html_lib.escape(report['title'])}</div>
{subtitle}
<div class="meta"><span class="date">{html_lib.escape(report.get('date', ''))}</span>
<span class="badge {tcls}">总体倾向:{html_lib.escape(report['tendency'] or '—')}</span></div>
</div>
<nav class="toc"><a href="#s1">一、可行性评价</a><a href="#s2">二、简要概述</a><a href="#s3">三、详细说明</a></nav>
<section id="s1"><h2>一、可行性评价</h2>{_scorecard_html(report['scorecard'])}</section>
<section id="s2"><h2>二、简要概述</h2><blockquote class="summary">{md_block(report['summary'])}</blockquote></section>
<section id="s3"><h2>三、详细说明</h2>{detail}</section>
</article>'''
    return HTML_DOC.format(title=html_lib.escape(report['title']) + ' · 评审报告', style=STYLE, body=body)
