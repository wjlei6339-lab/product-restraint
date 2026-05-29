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


if __name__ == '__main__':
    unittest.main()
