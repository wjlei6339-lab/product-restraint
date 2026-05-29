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
