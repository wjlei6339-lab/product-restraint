# 专业 HTML 报告渲染 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给本 skill 项目增加一个确定性渲染层,把评审报告(三部分 Markdown)转成专业、可读、可分享、印刷友好的自包含 HTML。

**Architecture:** 单文件 `render.py`(纯 Python3 标准库,零依赖)承载全部解析与样式,是 HTML 的唯一真源。skill 评审末尾调用它即时产出单份 HTML;`test.sh` 收尾调用它批量渲染最新 iteration + 汇总索引。语义化解析报告固定结构(评分卡六维 / 灯色 / 总体倾向 / Premortem / 验证动作 / 重启条件),而非通用 md→html。

**Tech Stack:** Python 3 标准库(`re`、`glob`、`html`、`argparse`、`datetime`、`os`、`sys`);测试用标准库 `unittest`;输出 HTML5 + 内联 CSS。

**工作分支:** `feat/professional-html-report`(已创建,设计文档已提交)。

**关联 spec:** `docs/superpowers/specs/2026-05-29-professional-html-report-design.md`

---

## 文件结构

| 文件 | 动作 | 职责 |
|---|---|---|
| `render.py` | 新增 | 渲染引擎:解析 + HTML 生成 + CLI。函数级分解见下。 |
| `test_render.py` | 新增 | `render.py` 解析逻辑的 unittest 单测。 |
| `test.sh` | 修改 | 全部 eval 跑完后调 `python3 render.py --latest`(失败不阻断)。 |
| `SKILL.md` | 修改 | 评审流程末尾加「生成 HTML 报告」步骤(含非交互回退)。 |
| `CLAUDE.md` | 修改 | 文件职责表加 `render.py`;注明 HTML 是渲染层、不改评审 prose。 |
| `.gitignore` | 修改 | 增加 `workspace/**/*.html`。 |
| `README.md` | 修改 | 加一节 HTML 报告用法。 |

**`render.py` 内部函数分解(单一职责):**

- 解析(纯函数,可单测):`split_sections` / `parse_tendency` / `parse_scorecard` / `parse_detail_blocks` / `derive_title` / `derive_subtitle` / `parse_report`
- Markdown→HTML:`md_inline` / `md_block` / `_strip_lead`
- 模板:`render_report_html` / `render_index_html`(共用 `HTML_DOC`、`STYLE`)
- 文件系统:`find_all_iterations` / `find_latest_iteration` / `find_report_mds` / `_eval_dirname_of` / `_date_of` / `render_file` / `render_iteration`
- CLI:`build_argparser` / `main`
- 常量:`LAMP_MAP` / `TENDENCY_CLASS` / `DIMENSIONS`

---

## Task 1: render.py 骨架 + 切块 + 总体倾向解析

**Files:**
- Create: `render.py`
- Test: `test_render.py`

- [ ] **Step 1: 写失败测试**

创建 `test_render.py`:

```python
import unittest
import render as R

SAMPLE = '''我先把你的想法用我的话说回去:你想做一个给独立健身教练的小程序。

---

## 一、可行性评价

**总体倾向:再想想**

| 维度 | 灯 | 一句话理由 |
|---|---|---|
| 真需求度 | 🟡 | 真在用 Excel 笨办法。 |
| 价值与差异 | 🔴 | 约课红海。 |
| 可行性 | 🟡 | 收款碰二清。 |
| 商业账 | 🔴 | 教练抗付费。 |
| 市场与时机 | 🔴 | 池子窄。 |
| 克制度 | 🟡 | 源于真痛点。 |

## 二、简要概述

痛点是真的,但难赚钱、难差异化。最致命:红海 + 抗付费人群。

## 三、详细说明

**价值与差异(🔴):** 约课收款已是红海。

**Premortem —— 假设它已经失败了,它是怎么死的:**
- 圈外教练宁可免费用 Excel。

**如果你一定要做,先花最小成本验证的那一件事:**
- 找 10 个圈外教练问退费怎么算。

**重启条件:** 拿到 10 个圈外教练的主动抱怨。
'''


class TestSplit(unittest.TestCase):
    def test_split_sections(self):
        sec = R.split_sections(SAMPLE)
        self.assertIn('说回去', sec['preamble'])
        self.assertIn('总体倾向', sec['one'])
        self.assertIn('最致命', sec['two'])
        self.assertIn('Premortem', sec['three'])

    def test_parse_tendency(self):
        sec = R.split_sections(SAMPLE)
        self.assertEqual(R.parse_tendency(sec['one']), '再想想')

    def test_parse_tendency_none(self):
        self.assertIsNone(R.parse_tendency('没有倾向字样'))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `python3 -m unittest test_render.TestSplit -v`
Expected: FAIL — `AttributeError: module 'render' has no attribute 'split_sections'`(或 import 错误)

- [ ] **Step 3: 写最小实现**

创建 `render.py`:

```python
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
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `python3 -m unittest test_render.TestSplit -v`
Expected: PASS(3 个测试)

- [ ] **Step 5: 提交**

```bash
git add render.py test_render.py
git commit -m "feat(render): 报告解析骨架(切块+总体倾向)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: 评分卡解析 + 灯色映射

**Files:**
- Modify: `render.py`
- Test: `test_render.py`

- [ ] **Step 1: 写失败测试**

在 `test_render.py` 末尾(`if __name__` 之前)追加:

```python
class TestScorecard(unittest.TestCase):
    def setUp(self):
        self.sec = R.split_sections(SAMPLE)
        self.rows = R.parse_scorecard(self.sec['one'])

    def test_six_rows(self):
        self.assertEqual(len(self.rows), 6)

    def test_first_row(self):
        self.assertEqual(self.rows[0],
                         {'dim': '真需求度', 'lamp': '🟡', 'reason': '真在用 Excel 笨办法。'})

    def test_lamp_emojis(self):
        self.assertEqual([r['lamp'] for r in self.rows],
                         ['🟡', '🔴', '🟡', '🔴', '🔴', '🟡'])

    def test_skips_header_and_divider(self):
        dims = [r['dim'] for r in self.rows]
        self.assertNotIn('维度', dims)
        self.assertNotIn('---', dims)

    def test_lamp_map(self):
        self.assertEqual(R.LAMP_MAP['🔴'][0], 'red')
        self.assertEqual(R.LAMP_MAP['🟢'], ('green', '绿'))
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `python3 -m unittest test_render.TestScorecard -v`
Expected: FAIL — `AttributeError: module 'render' has no attribute 'parse_scorecard'`

- [ ] **Step 3: 写最小实现**

在 `render.py` 的 `parse_tendency` 之后追加:

```python
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
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `python3 -m unittest test_render.TestScorecard -v`
Expected: PASS(5 个测试)

- [ ] **Step 5: 提交**

```bash
git add render.py test_render.py
git commit -m "feat(render): 评分卡解析与灯色映射

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: 详细说明块识别(Premortem / 验证动作 / 重启条件)

**Files:**
- Modify: `render.py`
- Test: `test_render.py`

- [ ] **Step 1: 写失败测试**

在 `test_render.py` 追加:

```python
class TestDetailBlocks(unittest.TestCase):
    def setUp(self):
        self.blocks = R.parse_detail_blocks(R.split_sections(SAMPLE)['three'])

    def test_body(self):
        self.assertIn('约课收款已是红海', self.blocks['body'])

    def test_premortem(self):
        self.assertIn('圈外教练宁可免费用 Excel', self.blocks['premortem'])

    def test_validation(self):
        self.assertIn('10 个圈外教练', self.blocks['validation'])

    def test_restart(self):
        self.assertIn('主动抱怨', self.blocks['restart'])

    def test_missing_restart_ok(self):
        three = R.split_sections(SAMPLE)['three'].split('**重启条件')[0]
        blocks = R.parse_detail_blocks(three)
        self.assertIsNone(blocks['restart'])
        self.assertIsNotNone(blocks['premortem'])

    def test_no_blocks_all_body(self):
        blocks = R.parse_detail_blocks('就是一段普通文字,没有特殊块。')
        self.assertIn('普通文字', blocks['body'])
        self.assertIsNone(blocks['premortem'])
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `python3 -m unittest test_render.TestDetailBlocks -v`
Expected: FAIL — `AttributeError: ... 'parse_detail_blocks'`

- [ ] **Step 3: 写最小实现**

在 `render.py` 的 `parse_scorecard` 之后追加:

```python
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
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `python3 -m unittest test_render.TestDetailBlocks -v`
Expected: PASS(6 个测试)

- [ ] **Step 5: 提交**

```bash
git add render.py test_render.py
git commit -m "feat(render): 详细说明块识别(premortem/验证/重启)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: 行内/块 Markdown 转 HTML(含转义)

**Files:**
- Modify: `render.py`
- Test: `test_render.py`

- [ ] **Step 1: 写失败测试**

在 `test_render.py` 追加:

```python
class TestMarkdown(unittest.TestCase):
    def test_inline_bold_and_escape(self):
        self.assertEqual(R.md_inline('**粗** <x> `c`'),
                         '<strong>粗</strong> &lt;x&gt; <code>c</code>')

    def test_inline_escape_amp(self):
        self.assertEqual(R.md_inline('A & B'), 'A &amp; B')

    def test_block_paragraph(self):
        self.assertEqual(R.md_block('一句话。'), '<p>一句话。</p>')

    def test_block_unordered_list(self):
        self.assertEqual(R.md_block('- a\n- b'),
                         '<ul><li>a</li><li>b</li></ul>')

    def test_block_ordered_list(self):
        self.assertEqual(R.md_block('1. 甲\n2. 乙'),
                         '<ol><li>甲</li><li>乙</li></ol>')

    def test_block_hr(self):
        self.assertEqual(R.md_block('---'), '<hr/>')

    def test_strip_lead_inline_title(self):
        # 「**重启条件:** 拿到…」去掉粗体标题后保留正文
        self.assertEqual(R._strip_lead('**重启条件:** 拿到证据。'), '拿到证据。')

    def test_strip_lead_titleonly_then_list(self):
        out = R._strip_lead('**Premortem —— 它怎么死:**\n- 没人用。')
        self.assertEqual(out, '- 没人用。')
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `python3 -m unittest test_render.TestMarkdown -v`
Expected: FAIL — `AttributeError: ... 'md_inline'`

- [ ] **Step 3: 写最小实现**

在 `render.py` 的 `parse_detail_blocks` 之后追加:

```python
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
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `python3 -m unittest test_render.TestMarkdown -v`
Expected: PASS(8 个测试)

- [ ] **Step 5: 提交**

```bash
git add render.py test_render.py
git commit -m "feat(render): 行内/块 Markdown 转 HTML(含转义)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: 标题/副标题推断 + 报告组装

**Files:**
- Modify: `render.py`
- Test: `test_render.py`

- [ ] **Step 1: 写失败测试**

在 `test_render.py` 追加:

```python
class TestAssemble(unittest.TestCase):
    def test_title_explicit_wins(self):
        self.assertEqual(R.derive_title('我的想法', eval_dirname='eval-2-foo'), '我的想法')

    def test_title_from_dirname(self):
        self.assertEqual(R.derive_title(None, eval_dirname='eval-2-evidenced-decent-idea'),
                         'evidenced decent idea')

    def test_title_fallback(self):
        self.assertEqual(R.derive_title(None), '未命名想法')

    def test_subtitle_from_preamble(self):
        sub = R.derive_subtitle('你想做一个给独立健身教练的小程序。后面还有。')
        self.assertEqual(sub, '你想做一个给独立健身教练的小程序')

    def test_subtitle_empty(self):
        self.assertIsNone(R.derive_subtitle('---'))

    def test_parse_report(self):
        rep = R.parse_report(SAMPLE, title='健身教练小程序', date='2026-05-29')
        self.assertEqual(rep['title'], '健身教练小程序')
        self.assertEqual(rep['tendency'], '再想想')
        self.assertEqual(len(rep['scorecard']), 6)
        self.assertIn('最致命', rep['summary'])
        self.assertIsNotNone(rep['premortem'])
        self.assertEqual(rep['date'], '2026-05-29')
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `python3 -m unittest test_render.TestAssemble -v`
Expected: FAIL — `AttributeError: ... 'derive_title'`

- [ ] **Step 3: 写最小实现**

在 `render.py` 的 `_strip_lead` 之后追加:

```python
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
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `python3 -m unittest test_render.TestAssemble -v`
Expected: PASS(6 个测试)

- [ ] **Step 5: 提交**

```bash
git add render.py test_render.py
git commit -m "feat(render): 标题推断与报告组装

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: 单报告 HTML 模板 + 简洁商务 CSS

**Files:**
- Modify: `render.py`
- Test: `test_render.py`

- [ ] **Step 1: 写失败测试**

在 `test_render.py` 追加:

```python
class TestRenderHtml(unittest.TestCase):
    def setUp(self):
        self.rep = R.parse_report(SAMPLE, title='健身教练小程序', date='2026-05-29')
        self.html = R.render_report_html(self.rep)

    def test_is_html_doc(self):
        self.assertTrue(self.html.lstrip().lower().startswith('<!doctype html>'))

    def test_has_title_and_date(self):
        self.assertIn('健身教练小程序', self.html)
        self.assertIn('2026-05-29', self.html)

    def test_has_tendency_badge(self):
        self.assertIn('badge amber', self.html)
        self.assertIn('再想想', self.html)

    def test_has_all_six_dims(self):
        for dim in R.DIMENSIONS:
            self.assertIn(dim, self.html)

    def test_has_blocks(self):
        self.assertIn('box premortem', self.html)
        self.assertIn('box validation', self.html)
        self.assertIn('box restart', self.html)

    def test_has_style_and_print(self):
        self.assertIn('<style>', self.html)
        self.assertIn('print-color-adjust', self.html)
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `python3 -m unittest test_render.TestRenderHtml -v`
Expected: FAIL — `AttributeError: ... 'render_report_html'`

- [ ] **Step 3: 写最小实现**

在 `render.py` 的 `parse_report` 之后追加(常量 + 渲染函数):

```python
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
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `python3 -m unittest test_render.TestRenderHtml -v`
Expected: PASS(6 个测试)

- [ ] **Step 5: 提交**

```bash
git add render.py test_render.py
git commit -m "feat(render): 单报告 HTML 模板与简洁商务 CSS

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: 索引 + workspace 扫描 + CLI 入口

**Files:**
- Modify: `render.py`
- Test: `test_render.py`

- [ ] **Step 1: 写失败测试**

在 `test_render.py` 追加(顶部需 `import tempfile, os, time`,加到文件首行的 import 区):

```python
class TestIndexAndFs(unittest.TestCase):
    def test_render_index_html(self):
        entries = [{'title': '想法甲', 'tendency': '别做',
                    'scorecard': R.parse_report(SAMPLE)['scorecard'], 'href': 'eval-0/report.html'}]
        html = R.render_index_html(entries, 'iteration-x')
        self.assertIn('想法甲', html)
        self.assertIn('eval-0/report.html', html)
        self.assertIn('badge red', html)
        self.assertIn('iteration-x', html)

    def test_eval_dirname_of(self):
        self.assertEqual(R._eval_dirname_of('workspace/iteration-9/eval-2-foo/output.md'),
                         'eval-2-foo')
        self.assertIsNone(R._eval_dirname_of('a/b/output.md'))

    def test_find_latest_iteration(self):
        import tempfile, os, time
        with tempfile.TemporaryDirectory() as d:
            old = os.path.join(d, 'iteration-1')
            new = os.path.join(d, 'iteration-2')
            os.makedirs(old)
            os.makedirs(new)
            os.utime(old, (1000, 1000))
            os.utime(new, (2000, 2000))
            self.assertEqual(R.find_latest_iteration(d), new)

    def test_find_latest_none(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(R.find_latest_iteration(d))
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `python3 -m unittest test_render.TestIndexAndFs -v`
Expected: FAIL — `AttributeError: ... 'render_index_html'`

- [ ] **Step 3: 写最小实现**

在 `render.py` 的 `render_report_html` 之后追加:

```python
def render_index_html(entries, iter_name):
    items = []
    for e in entries:
        mini = ''.join(
            f'<span class="lamp-dot lamp-{LAMP_MAP.get(s["lamp"], ("gray", ""))[0]}" title="{html_lib.escape(s["dim"])}"></span>'
            for s in e['scorecard'])
        tcls = TENDENCY_CLASS.get(e['tendency'], 'gray')
        items.append(
            f'<li><a href="{html_lib.escape(e["href"])}">'
            f'<span class="idx-title">{html_lib.escape(e["title"])}</span>'
            f'<span class="badge {tcls}">{html_lib.escape(e["tendency"] or "—")}</span>'
            f'<span class="mini">{mini}</span></a></li>')
    body = (f'<div class="cover"><h1>产品克制 · 评审汇总</h1>'
            f'<div class="idea-title">{html_lib.escape(iter_name)}</div></div>'
            f'<ul class="index-list">{"".join(items)}</ul>')
    return HTML_DOC.format(title='评审汇总 · ' + html_lib.escape(iter_name), style=STYLE, body=body)


def _date_of(path):
    try:
        return datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d')
    except OSError:
        return ''


def _eval_dirname_of(md_path):
    for part in os.path.normpath(md_path).split(os.sep):
        if re.match(r'eval-\d+', part):
            return part
    return None


def find_all_iterations(workspace='workspace'):
    dirs = [d for d in glob.glob(os.path.join(workspace, 'iteration-*')) if os.path.isdir(d)]
    return sorted(dirs, key=os.path.getmtime)


def find_latest_iteration(workspace='workspace'):
    dirs = find_all_iterations(workspace)
    return dirs[-1] if dirs else None


def find_report_mds(iter_dir):
    return sorted(glob.glob(os.path.join(iter_dir, '**', 'output.md'), recursive=True))


def render_file(md_path, out=None, title=None):
    with open(md_path, encoding='utf-8') as f:
        md = f.read()
    report = parse_report(md, title=title, eval_dirname=_eval_dirname_of(md_path),
                          md_path=md_path, date=_date_of(md_path))
    if out is None:
        out = os.path.splitext(md_path)[0] + '.html'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(render_report_html(report))
    print(f'  ✓ {out}')
    return out


def render_iteration(iter_dir):
    mds = find_report_mds(iter_dir)
    if not mds:
        print(f'  ⚠ {iter_dir} 无 output.md,跳过', file=sys.stderr)
        return
    entries = []
    for md in mds:
        try:
            out = os.path.join(os.path.dirname(md), 'report.html')
            render_file(md, out=out)
            with open(md, encoding='utf-8') as f:
                rep = parse_report(f.read(), eval_dirname=_eval_dirname_of(md),
                                   md_path=md, date=_date_of(md))
            entries.append({'title': rep['title'], 'tendency': rep['tendency'],
                            'scorecard': rep['scorecard'],
                            'href': os.path.relpath(out, iter_dir)})
        except Exception as e:  # 单份坏掉不拖垮整批
            print(f'  ⚠ 渲染失败 {md}: {e}', file=sys.stderr)
    idx = os.path.join(iter_dir, 'index.html')
    with open(idx, 'w', encoding='utf-8') as f:
        f.write(render_index_html(entries, os.path.basename(iter_dir)))
    print(f'  ✓ {idx}(共 {len(entries)} 份)')


def build_argparser():
    import argparse
    p = argparse.ArgumentParser(description='把「产品克制」评审报告渲染成专业 HTML')
    p.add_argument('file', nargs='?', help='单个报告 md 路径')
    p.add_argument('-o', '--output', help='输出 html 路径(单文件模式)')
    p.add_argument('--title', help='想法标题(覆盖自动推断)')
    p.add_argument('--latest', action='store_true', help='渲染最新 iteration + 索引')
    p.add_argument('--all', action='store_true', help='渲染所有 iteration + 各自索引')
    p.add_argument('--workspace', default='workspace', help='workspace 目录(默认 ./workspace)')
    return p


def main(argv=None):
    args = build_argparser().parse_args(argv)
    if args.latest:
        it = find_latest_iteration(args.workspace)
        if not it:
            print('未找到 iteration 目录', file=sys.stderr)
            return 1
        render_iteration(it)
        return 0
    if args.all:
        its = find_all_iterations(args.workspace)
        if not its:
            print('未找到 iteration 目录', file=sys.stderr)
            return 1
        for it in its:
            render_iteration(it)
        return 0
    if args.file:
        render_file(args.file, out=args.output, title=args.title)
        return 0
    build_argparser().print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `python3 -m unittest test_render -v`
Expected: PASS(全部测试,约 34 个)

- [ ] **Step 5: 提交**

```bash
git add render.py test_render.py
git commit -m "feat(render): 索引/workspace 扫描/CLI 入口

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: 用现有 workspace 报告做端到端肉眼验证

**Files:**
- 只读现有 `workspace/iteration-20260529-183529/`,生成 HTML(产物,不入库)

- [ ] **Step 1: 跑批量渲染**

Run: `python3 render.py --latest`
Expected: 打印若干 `✓ workspace/iteration-20260529-183529/eval-*/output.html` + `✓ .../index.html(共 3 份)`,退出码 0

- [ ] **Step 2: 浏览器肉眼检查(对照 spec 第 11 节)**

打开 `workspace/iteration-20260529-183529/eval-2-evidenced-decent-idea/report.html`,确认:
- 封面有标题、日期、「再想想」黄徽章;
- 评分卡六维齐全,灯色圆点与原报告一致(🟡🔴 对应黄/红点);
- 「Premortem · 事前验尸」红框、「最小验证动作」绿框、「重启条件」灰框样式正确;
- 中文与 `**粗体**`、有序/无序列表正常,无 `&lt;` 等转义破损;
- Cmd+P 打印预览:分页正常、颜色保留(灯色/徽章不褪成灰白)。
打开同目录 `../index.html`,确认 3 份报告都列出、徽章与迷你灯条正确、链接可点。

- [ ] **Step 3: 单文件模式 + 标题验证**

Run: `python3 render.py workspace/iteration-20260529-183529/eval-1-vague-one-liner/output.md --title "模糊一句话想法" -o /tmp/pr-test.html`
Expected: 生成 `/tmp/pr-test.html`,打开后封面标题为「模糊一句话想法」。

- [ ] **Step 4: 缺块健壮性(若上面三份里没有缺重启条件的,手造一个)**

Run: `printf '## 一、可行性评价\n\n**总体倾向:别做**\n\n| 维度 | 灯 | 理由 |\n|---|---|---|\n| 真需求度 | 🔴 | x |\n\n## 二、简要概述\n\ns\n\n## 三、详细说明\n\nbody only\n' > /tmp/min.md && python3 render.py /tmp/min.md -o /tmp/min.html && echo OK`
Expected: 打印 `✓ /tmp/min.html` 和 `OK`,无异常栈(缺 Premortem/验证/重启时对应框自然省略)。

- [ ] **Step 5: 无需提交**

(本任务只验证,不产生入库文件;若验证中发现 bug,回到对应 Task 修复并补测试。)

---

## Task 9: 接入 test.sh(批量渲染收尾)

**Files:**
- Modify: `test.sh`

- [ ] **Step 1: 修改 test.sh**

把 `test.sh` 结尾这段:

```bash
echo
echo "全部完成。结果在:$OUTDIR"
echo "对照三个判断目标自查:1) 该狠时够狠且不套话  2) 信息少→缺失即风险  3) 好想法不被无脑否定"
```

改为(在「全部完成」之后、自查提示之前插入渲染):

```bash
echo
echo "全部完成。结果在:$OUTDIR"

# 把本批报告渲染成专业 HTML + 汇总索引(渲染失败不阻断测试结论)
if command -v python3 >/dev/null 2>&1; then
  echo "渲染 HTML 报告..."
  python3 render.py --latest || echo "  ⚠ HTML 渲染跳过(见上方错误)"
fi

echo "对照三个判断目标自查:1) 该狠时够狠且不套话  2) 信息少→缺失即风险  3) 好想法不被无脑否定"
echo "HTML 报告:打开 $OUTDIR/index.html"
```

> 注意:`test.sh` 顶部有 `set -euo pipefail`,所以用 `|| echo ...` 兜底确保渲染失败不会让脚本以非 0 退出而吞掉结论。

- [ ] **Step 2: 验证 test.sh 仍能跑通(只跑一个用例省时)**

Run: `./test.sh 1`
Expected: 跑完 eval 1 后看到「渲染 HTML 报告...」与 `✓ .../index.html`,脚本正常结束。

> 若环境无 `claude` CLI 导致 eval 无法跑,可跳过此步,改为单独验证渲染段:手动 `python3 render.py --latest` 已在 Task 8 验证过。

- [ ] **Step 3: 提交**

```bash
git add test.sh
git commit -m "feat(test): test.sh 跑完批量渲染 HTML 报告与索引

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: 接入 SKILL.md(评审末尾生成 HTML)

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: 在评审流程「第 1–4 步」后新增一步**

在 `SKILL.md` 的「### 第 1–4 步:评审」小节里,第 4 步「按三部分输出」之后、该小节结尾「如果信息实在太少…」那段之前,插入:

```markdown
5. **(附加交付)把报告落成专业 HTML。** 在三部分输出之后,如果当前是**可与用户来回的真实交互会话**(同提问闸门的交互判断):把这份报告的 Markdown 原文存成一个临时 `.md`,调用 skill 目录下的 `render.py` 渲染成自包含 HTML,落到当前工作目录,文件名形如 `产品克制-评审-<想法标题>-<日期>.html`,再用一句话告知文件路径(便于转发、归档、打印)。命令形如:

       python3 <skill目录>/render.py <报告.md> -o "产品克制-评审-<想法标题>-<日期>.html" --title "<想法一句话>"

   这一步是**附加交付,不是评审的一部分**:若处于非交互批处理(如 `claude -p`)、无法写文件或 `render.py` 出错,**静默跳过**,绝不影响、不改写上面已输出的三部分评审。HTML 只是同一份报告的另一种呈现,内容与判断必须与正文完全一致。
```

> 措辞约束:不得改动既有五原则、评分卡、三部分模板;明确"附加交付、失败即跳过"。`<skill目录>` 在运行时即 SKILL.md 所在目录(软链接指向本仓库),Claude 可用相对该目录的 `render.py` 调用。

- [ ] **Step 2: 一致性自查(无自动测试)**

通读修改后的「评审流程」小节,确认:
- 新步骤编号顺承(第 1–4 步 → 新增第 5 步),不与既有「第 0 步:提问闸门」冲突;
- 没有把 HTML 生成写成评审必经环节(必须是"附加、可跳过");
- 与 spec 第 9 节措辞语义一致。

- [ ] **Step 3: 提交**

```bash
git add SKILL.md
git commit -m "feat(skill): 评审末尾附加生成专业 HTML 报告(非交互回退)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: 同步 CLAUDE.md / .gitignore / README.md

**Files:**
- Modify: `CLAUDE.md`、`.gitignore`、`README.md`

- [ ] **Step 1: .gitignore 增加产物忽略**

读现有 `.gitignore`,在末尾追加:

```
# HTML 渲染产物(由 render.py 生成,不入库)
workspace/**/*.html
```

- [ ] **Step 2: CLAUDE.md 文件职责表加一行**

在 `CLAUDE.md` 的「## 文件职责(big picture)」表格里,`workspace/iteration-N/` 行之后追加一行:

```markdown
| `render.py` | **渲染层**。把评审报告(三部分 Markdown)转成专业、自包含、印刷友好的 HTML。纯标准库零依赖,是 HTML 样式的唯一真源;skill 评审末尾与 `test.sh` 都调用它。**HTML 不改变评审 prose 行为**——只是同一份报告的另一种呈现。用法:`python3 render.py --latest`(最新一批+索引)/ `render.py <file.md> -o out.html --title "…"`(单份)。 |
```

并在「## 编辑 skill 时必须守住的不变量」末尾追加一条:

```markdown
6. **HTML 是渲染层,不是新行为。** `render.py` 只把已生成的报告换种呈现,不得反向改变评审逻辑、维度、模板措辞。skill 内生成 HTML 的步骤必须"失败/非交互即静默跳过",绝不影响三部分评审输出本身,也不污染 `claude -p` 评测产物(批量渲染由 `test.sh` 收尾统一做)。
```

- [ ] **Step 3: README.md 增加一节**

在 `README.md` 的「## 怎么测试」一节之后,插入新节:

```markdown
## HTML 报告

评审报告除了终端 Markdown,还能渲染成专业、自包含、可离线转发、印刷友好的 HTML(简洁商务风,带评分卡灯色可视化、Premortem/验证动作高亮、可打印)。

由 `render.py` 生成(纯 Python3 标准库,**零依赖**):

```bash
python3 render.py --latest               # 渲染最新一批 + 汇总索引 index.html
python3 render.py <报告.md> -o out.html  # 渲染单份,--title 可指定想法标题
python3 render.py --all                  # 渲染全部历史 iteration
```

`./test.sh` 跑完会自动渲染最新一批,打开 `workspace/iteration-<时间戳>/index.html` 即可浏览。
交互式会话里评审完,skill 也会把报告自动落成一份 HTML 到当前目录(非交互环境跳过)。

生成的 `*.html` 属产物,已在 `.gitignore` 忽略,不入库。
```

- [ ] **Step 4: 运行全部单测做最终回归**

Run: `python3 -m unittest test_render -v`
Expected: PASS(全部)

- [ ] **Step 5: 提交**

```bash
git add CLAUDE.md .gitignore README.md
git commit -m "docs: 同步 CLAUDE/README/gitignore 至 HTML 渲染功能

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## 完成标准(Definition of Done)

- `python3 -m unittest test_render -v` 全绿。
- `python3 render.py --latest` 对现有 workspace 报告生成 HTML + index,肉眼检查通过 spec 第 11 节清单。
- 单文件模式、缺块健壮性、打印保色均验证通过。
- `test.sh`、`SKILL.md`、`CLAUDE.md`、`.gitignore`、`README.md` 均按上文接入,且未稀释既有不变量。
- 所有提交在 `feat/professional-html-report` 分支;生成的 `*.html` 未被 git 跟踪。

## Self-Review 记录

- **Spec 覆盖**:用途(自包含单文件+索引→Task 6/7)、形态(skill 末尾调用→Task 10)、范围(最新一批+索引→Task 7 `--latest`)、视觉(简洁商务→Task 6 STYLE)、即时落点/自动生成/gitignore(Task 10/11)——逐项有对应任务。
- **占位符**:无 TBD/TODO;每个代码步骤含完整可运行代码。
- **类型/命名一致**:`parse_report` 产出的 dict 键(title/subtitle/date/tendency/scorecard/summary/detail_body/premortem/validation/restart)在 Task 5 定义,Task 6/7 的 `render_report_html`/`render_iteration` 全程沿用;`LAMP_MAP`/`TENDENCY_CLASS`/`DIMENSIONS` 在 Task 1 定义,后续引用一致;函数名(`split_sections`/`parse_scorecard`/`render_file`/`render_iteration` 等)前后统一。
```