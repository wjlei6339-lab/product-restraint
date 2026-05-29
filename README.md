# product-restraint —— 产品克制 Skill

一个**默认怀疑**的产品想法评审 Claude Code skill。用产品、用户、商业、市场四个视角的成熟框架,对一个产品/功能/创业想法过一遍,输出「可行性评分卡 + 简要概述 + 详细说明」三部分,帮你在动手前判断**值不值得做**——而不是帮你把不成熟的想法快速做出来。

> 背景:AI 让"能做出来"变得太便宜,大量不成熟的想法被冲动上马,烧 token、烧时间、烧钱却没价值。这个 skill 的角色是那个在你兴头上替你泼冷水的冷静产品顾问。

## 项目结构

```
product-restraint/
├── SKILL.md              # 技能主体:性格、评审流程、六维评分卡、输出模板、AI 专项、反套话自检
├── references/
│   └── frameworks.md     # 框架弹药库:Mom Test / Cagan 四风险 / Premortem / 单位经济 / TAM-SAM-SOM / 护城河
├── evals/
│   └── evals.json        # 测试用例(3 个:弱套壳 / 模糊一句话 / 有证据的像样想法)
├── docs/
│   └── design.md         # 设计文档(决策记录:形态/立场/范围/结论形式)
├── workspace/            # 测试运行结果,按 iteration-N 组织
│   └── iteration-1/
│       └── eval-*/{with_skill,without_skill}/outputs/output.md
├── test.sh               # 一键回归测试(用 claude -p 跑全部 eval 用例)
└── README.md
```

## 修改即生效的机制(软链接)

这个项目是 skill 的**唯一真源**。`~/.claude/skills/product-restraint` 是一个指向本项目的**软链接**:

```
~/.claude/skills/product-restraint  ->  ~/PycharmProjects/product-restraint
```

所以你在 PyCharm 里直接编辑 `SKILL.md` / `references/frameworks.md`,**保存即生效**,下次在任意 Claude Code 会话里触发 skill 时读到的就是最新版,不用手动拷贝同步。

> 注:Claude Code 在会话启动时扫描 skill。改完 `description`(触发条件)需要新开会话才会重新加载;改 `SKILL.md` 正文则当场生效。

如果某天想脱钩,只删软链接、不动项目即可:

```bash
rm ~/.claude/skills/product-restraint        # 删的是链接,不是项目
```

## 怎么修改

主要改两个文件:

- **`SKILL.md`** —— 改性格、评审流程、六个维度、输出模板。这是 skill 的"灵魂"。
  - 想让它更狠 / 更温和 → 改"你的性格"那五条原则的措辞
  - 想加减评审维度 → 改"评分卡:六个维度"那张表 + 输出模板里的表头
  - 觉得输出太长 / 太短 → 改"输出模板"
  - 改了 `frontmatter` 的 `description` → 影响触发准确率,改完新开会话生效
- **`references/frameworks.md`** —— 改"为什么这么判"的框架底料,深入展开时才会被读到。

改完务必跑一遍 `test.sh` 看有没有跑偏(见下)。

## 怎么测试

### 方式一:一键回归(推荐)

```bash
cd ~/PycharmProjects/product-restraint
./test.sh
```

它会用 `claude -p` 把 `evals/evals.json` 里的每个用例都跑一遍,输出存到 `workspace/iteration-<时间戳>/`。跑完自己对照三个判断目标看:

1. **该狠时够狠** —— 套壳/伪需求要敢给「别做」,红灯理由要具体、不是套话
2. **信息少时按"缺失即风险"** —— 一句话想法要把说不清的维度判红,并点明信息不足本身就是危险信号
3. **好想法不被无脑否定** —— 有真实证据(有人在用笨办法解决)的想法,真需求度要敢给绿灯

### 方式二:直接在 Claude Code 里聊

新开一个 Claude Code 会话,直接说一个产品想法,比如:

> 我想做个 AI 工具,把播客自动剪成短视频。

skill 会自动触发(因为 description 覆盖了"我想做…"这类表达)。这是最贴近真实使用的测法。

### 方式三:在本项目内迭代评测(skill-creator 全流程)

如果想要带对照、带评分卡的正式评测,在 Claude Code 里用 `skill-creator` 技能,指向本项目跑 with-skill / baseline 对比。

> ⚠️ 注意:因为 skill 已通过软链接全局注册,subagent 会自动加载它,**baseline 对照会被"污染"**(裸跑那一列其实也用了 skill)。要做干净对照,需把 skill 临时拷到一个不在 `~/.claude/skills/` 下的路径再当 baseline。日常迭代看 with-skill 那一列的质量即可。

## 当前状态

初版(iteration-1)在三个测试场景上表现良好:套壳→别做、模糊→缺失即风险、有证据→不无脑否定且锁定关键验证动作。详见 `workspace/iteration-1/`。
