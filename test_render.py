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

    def test_reason_with_pipe_not_truncated(self):
        # 理由列本身含 `|` 时,cells[2:] 应被完整拼回,不被静默截断
        text = ('| 维度 | 灯 | 理由 |\n|---|---|---|\n'
                '| 商业账 | 🔴 | 效率低 | 成本高 |')
        rows = R.parse_scorecard(text)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['reason'], '效率低 | 成本高')


class TestMdBlockRobustness(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(R.md_block(''), '')

    def test_none(self):
        self.assertEqual(R.md_block(None), '')


if __name__ == '__main__':
    unittest.main()
