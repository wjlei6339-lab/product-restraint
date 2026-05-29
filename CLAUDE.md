# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 这是什么

这是一个 **Claude Code skill 项目**,不是应用程序代码库。核心交付物是 skill 本身(自然语言 prose);`render.py` 是围绕 skill 输出的确定性报告渲染层,不是第二个产品。skill 名为 `product-restraint`(产品克制):一个**默认怀疑**的产品想法评审器,用六维评分卡(红/黄/绿)+ Premortem + 最小验证动作,帮用户在动手前判断一个产品/功能/创业想法值不值得做。

因此:**"写代码"在这里主要 = 编辑 `SKILL.md` 的 prose**。改 prose 就是改产品行为;改 `render.py` 只改变报告呈现,不能改变评审判断。

## 唯一真源 + 软链接生效机制

本仓库是 skill 的唯一真源。`~/.claude/skills/product-restraint` 是指向本仓库的**软链接**,所以:

- 改 `SKILL.md` / `references/frameworks.md` 正文 → **保存即生效**,下次任意 Claude Code 会话触发 skill 时读到的就是最新版。
- 改 frontmatter 的 `description`(决定触发准确率)→ 需**新开会话**才会重新加载(会话启动时才扫描 skill 元数据)。

不要把 skill 文件拷贝到别处去同步——那会制造第二份真源。脱钩只删软链接(`rm ~/.claude/skills/product-restraint`),不动仓库。

## 测试

```bash
./test.sh          # 跑 evals/evals.json 里全部用例,结果存到 workspace/iteration-<时间戳>/
./test.sh 0 2      # 只跑 id 为 0 和 2 的用例
python3 -m unittest -v test_render.py  # 跑 HTML 渲染层单元测试
python3 render.py --latest             # 渲染最新一批 eval 输出为 HTML + index
```

`test.sh` 用 `claude -p` 把每个 eval 的 prompt 当用户消息丢进去,skill 自动触发并产出三部分评审,输出存到 `workspace/iteration-<stamp>/eval-<id>-<name>/output.md`。跑完**人工对照三个判断目标**(没有自动断言打分):

1. **该狠时够狠且不套话** —— 套壳/伪需求要敢给「别做」,红灯理由要具体到这个想法。
2. **信息少时按"缺失即风险"** —— 一句话想法要把说不清的维度判红,并点明信息不足本身就是危险信号。
3. **好想法不被无脑否定** —— 有真实证据(有人在用笨办法解决)的想法,真需求度要敢给绿灯。

> ⚠️ 用 `skill-creator` 跑带对照的正式评测时:因为 skill 已通过软链接全局注册,subagent 会自动加载它,**baseline 裸跑那一列会被"污染"**。要做干净 A/B,需把 skill 临时拷到 `~/.claude/skills/` 之外的路径当 baseline。日常迭代看 with-skill 那一列即可。

## 文件职责(big picture)

| 文件 | 职责 |
|---|---|
| `SKILL.md` | skill 的"灵魂"。frontmatter(name/description = 触发条件)+ 正文:性格五原则、评审流程(含第 0 步提问闸门)、六维评分卡、三部分输出模板、AI 产品专项、反套话自检。**改行为主要改这里。** |
| `references/frameworks.md` | 框架弹药库(Mom Test / Cagan 四风险 / Premortem / 单位经济 / TAM-SAM-SOM / 护城河)。**渐进式披露**:SKILL.md 里是浓缩版,只有需要展开"为什么这么判"时才按需读这份。 |
| `evals/evals.json` | 3 个测试用例(弱套壳 / 模糊一句话 / 有证据的像样想法),含 `expected_output`。改了 skill 行为应同步审视这里的用例是否还覆盖关键场景。 |
| `docs/design.md` | 设计决策记录(形态/默认立场/范围/结论形式),改动核心设计前先读它,理解原始权衡。 |
| `render.py` | 报告渲染层。把固定三段 Markdown 报告解析为自包含 HTML、批次索引和打印友好页面。它只能呈现报告,不能改写评审逻辑。用法:`python3 render.py --latest`(最新一批+索引)/ `python3 render.py <file.md> -o out.html --title "想法"`(单份)。 |
| `test_render.py` | `render.py` 的单元测试,覆盖解析、灯色、索引、HTML 基本结构。 |
| `workspace/iteration-1/` | 已入库的基准样例,用于对照历史行为。 |
| `workspace/iteration-<时间戳>/` | 本地测试运行产物,默认不入库。`stderr.log`、HTML 报告、缓存文件都应保持为本地产物。 |

## 编辑 skill 时必须守住的不变量

这些是 skill 之所以"有用而非捧场"的核心约束,改 `SKILL.md` 时不要破坏:

1. **默认怀疑,举证责任在用户** —— 每个维度默认从红灯起步,只有用户描述里有扎实证据才往黄/绿调。说不清 = 红灯,不是中性。
2. **缺失即风险,先逼问再判更红** —— 评审前先走「提问闸门」就六维关键空白当面发问(最多 6 问,选择题,走 `AskUserQuestion`);能答上来答案变评分证据,当面问到仍答不上 / 选"说不清"则该维判更红。非交互环境(如 `claude -p`)无法发问时,回退一次性评审、说不清的维度直接判红。举证责任始终在用户。
3. **拒绝套话否定(最重要)** —— 每个红灯必须给**具体到这个想法**的理由。判据:把理由里的产品名换成任何别的产品,如果还成立,它就是套话,必须重写。这条是 skill 价值的命门,任何修改都不能稀释它。
4. **三部分输出模板,顺序固定** —— ①可行性评价(评分卡 + 总体倾向:别做/再想想/可以试)②简要概述(3-5 句,点出最致命 1-2 点)③详细说明(逐维度展开 + Premortem + 最小验证动作)。
5. **给放行路径但门槛高** —— 结论"别做"也要给"什么条件下值得重启";结论"可以试"也要给"最该先用最小成本验证的那一件事"(优先《The Mom Test》式观察过去行为,而非问"会不会用")。
6. **HTML 是渲染层,不是新行为** —— `render.py` 只把已生成的报告换种呈现,不得反向改变评审逻辑、维度、模板措辞。SKILL.md 里「评审之后落地 HTML」那步必须"失败 / 非交互即静默跳过",绝不影响三部分评审输出本身,也不污染 `claude -p` 评测产物(批量渲染由 `test.sh` 收尾统一做)。

六个维度:真需求度、价值与差异、可行性、商业账、市场与时机、克制度。增减维度须同步改 SKILL.md 评分卡表、输出模板表头,以及 evals 预期。

## 语言

项目全程中文,新增内容(SKILL.md / 文档 / 注释)保持中文。
