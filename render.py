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
