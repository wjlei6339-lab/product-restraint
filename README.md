# product-restraint

一个用于产品想法预审的 Claude Code skill。它会在你动手做产品、功能、App、工具或创业想法前，先判断：**这件事值不值得做**。

核心立场：**默认怀疑，但不无脑否定。**

## 使用方式

在 Claude Code 里直接描述一个产品想法：

> 我想做一个 AI 工具，把播客自动剪成短视频，帮创作者发到小红书和抖音。

skill 会输出可行性评分卡、简要结论、详细理由和最小成本验证动作，并用红 / 黄 / 绿判断六个维度：

- 真需求度
- 价值与差异
- 可行性
- 商业账
- 市场与时机
- 克制度

## 本地链接

本仓库是 skill 的唯一真源。全局 skill 链接应指向这里：

```bash
~/.claude/skills/product-restraint -> ~/PycharmProjects/product-restraint
```

直接修改本仓库即可生效。只有一种例外：如果改了 `SKILL.md` frontmatter 里的 `description`，需要新开 Claude Code 会话才会重新加载触发条件。

## 文件说明

| 文件 | 用途 |
|---|---|
| `SKILL.md` | skill 主体：评审流程、口吻、评分卡、输出模板。 |
| `references/frameworks.md` | 评审框架资料：Mom Test、Premortem、单位经济等。 |
| `references/report-template.html` | HTML 报告模版：样式、版式、打印适配。 |
| `docs/design.md` | 设计说明，改核心方向前先看这里。 |

想让 skill 更严格、更温和、输出更短，通常优先改 `SKILL.md`。

## 验证方式

本项目没有自动化测试。改完后，新开 Claude Code 会话，丢几个产品想法手动检查：

- 套壳、伪需求类想法，是否敢明确说“不建议做”。
- 信息很少的一句话想法，是否把“没说清”当成风险。
- 有真实证据的好想法，是否没有被机械否定。
- 如果改了 HTML 报告模版，再检查移动端、打印版、灯色一致性，以及是否还有 `{{}}` 占位符。

## 维护提醒

- 不要复制第二份 skill 文件；本仓库就是唯一真源。
- 改评分维度时，同步更新 `SKILL.md` 的评分卡和输出模板。
