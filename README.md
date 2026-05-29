# product-restraint：产品克制 Skill

`product-restraint` 是一个 Claude Code skill，用来在你动手做产品、功能、App、工具或创业想法前，先判断它**值不值得做**。

它不会默认帮你把想法做出来，而是用产品、用户、商业、市场几个角度，把想法过一遍，输出：

- 可行性评分卡
- 简要概述
- 详细说明
- 最小成本验证动作

核心立场：**默认怀疑，但不无脑否定。**

本项目有两层：

- **评审层**：`SKILL.md` 是唯一真源，决定 skill 如何判断一个想法。
- **渲染层**：`render.py` 把评审输出的固定三段 Markdown 渲染成专业 HTML，方便归档、转发和打印；它不改变评审逻辑。

## 什么时候用

当你想评估一个产品想法时，直接在 Claude Code 里描述它即可，例如：

> 我想做一个 AI 工具，把播客自动剪成短视频，帮创作者发到小红书和抖音。

skill 会自动触发，并从六个维度给出红 / 黄 / 绿判断：

- 真需求度
- 价值与差异
- 可行性
- 商业账
- 市场与时机
- 克制度

## 怎么使用

本仓库是 skill 的唯一真源。当前全局 skill 链接应指向本项目：

```bash
~/.claude/skills/product-restraint -> ~/PycharmProjects/product-restraint
```

因此，直接编辑本仓库文件即可生效。

注意：

- 修改 `SKILL.md` 正文：保存后，下次触发就会使用新版内容。
- 修改 `SKILL.md` frontmatter 里的 `description`：需要新开 Claude Code 会话才会重新加载触发条件。

## 怎么修改

最常改这几个文件：

| 文件 | 用途 |
|---|---|
| `SKILL.md` | skill 主体。改性格、评审流程、评分卡、输出模板。 |
| `references/frameworks.md` | 框架资料。补充 Mom Test、Premortem、单位经济、护城河等判断依据。 |
| `evals/evals.json` | 测试用例。新增或调整典型产品想法，观察输出是否跑偏。 |
| `docs/design.md` | 设计说明。改核心方向前先看这里。 |
| `render.py` | 报告渲染层。把 `output.md` 转成 HTML 报告和索引。 |
| `test_render.py` | `render.py` 的单元测试。 |

如果想让 skill 更严格、更温和、输出更短、增加评审维度，优先改 `SKILL.md`。

## 怎么测试

运行全部评测：

```bash
./test.sh
```

只运行指定 eval：

```bash
./test.sh 0 2
```

测试结果会写入：

```bash
workspace/iteration-<时间戳>/
```

看结果时重点检查三件事：

1. 套壳、伪需求类想法，是否敢给“别做”，且理由具体。
2. 信息很少的一句话想法，是否把“没说清”当成风险。
3. 有真实证据的好想法，是否没有被机械否定。

验证 HTML 渲染层：

```bash
python3 -m unittest -v test_render.py
python3 render.py --latest
```

`render.py --latest` 会把最新一批 `workspace/iteration-*` 里的 `output.md` 渲染为同目录的 `report.html`（与 `output.md` 同级），并生成该批次的 `index.html`。

如果用 `skill-creator` 做带 baseline 的正式对照评测，要注意：因为本 skill 通过软链接全局注册，subagent 可能自动加载它，导致 baseline 被污染。要做干净 A/B，需要临时把 skill 放到 `~/.claude/skills/` 之外。

## 项目结构

```text
product-restraint/
├── SKILL.md
├── references/frameworks.md
├── evals/evals.json
├── docs/design.md
├── render.py
├── test_render.py
├── workspace/
├── test.sh
└── README.md
```

## 维护原则

- 不要复制出第二份 skill 文件，本仓库就是唯一真源。
- 改评分维度时，同步更新 `SKILL.md` 的评分卡、输出模板和 `evals/evals.json`。
- `workspace/iteration-1/` 是已入库的基准样例；新跑出来的 timestamp iteration、HTML 报告、`stderr.log` 和 `__pycache__/` 默认属于本地产物，不要把它们混进日常提交。
- 如果确实需要把某次 eval 输出作为 PR 证据，明确说明原因后再单独加入，不要顺手提交整批运行产物。
