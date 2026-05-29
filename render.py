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
