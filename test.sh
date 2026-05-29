#!/usr/bin/env bash
# 回归测试:用 claude -p 把 evals/evals.json 里的每个用例跑一遍,结果存到 workspace/iteration-<时间戳>/
#
# 前提:已安装 claude CLI,且 ~/.claude/skills/product-restraint 软链接指向本项目(skill 全局可触发)。
# 用法:
#   ./test.sh            # 跑全部用例
#   ./test.sh 0 2        # 只跑 id 为 0 和 2 的用例

set -euo pipefail
cd "$(dirname "$0")"

if ! command -v claude >/dev/null 2>&1; then
  echo "找不到 claude CLI。请先安装 Claude Code,或改用 README 里的「方式二:直接在会话里聊」。" >&2
  exit 1
fi

EVALS="evals/evals.json"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUTDIR="workspace/iteration-$STAMP"
mkdir -p "$OUTDIR"

# 允许只跑指定 id
WANT="${*:-}"

# 用 python 解析 evals.json,逐行输出 "id<TAB>name<TAB>prompt"
python3 - "$EVALS" <<'PY' | while IFS=$'\t' read -r id name prompt; do
import json, sys
data = json.load(open(sys.argv[1]))
for e in data["evals"]:
    print(f'{e["id"]}\t{e.get("name","eval")}\t{e["prompt"]}')
PY
  if [ -n "$WANT" ] && ! grep -qw "$id" <<<"$WANT"; then
    continue
  fi
  dest="$OUTDIR/eval-$id-$name"
  mkdir -p "$dest"
  echo "▶ [eval $id] $name"
  echo "  prompt: $prompt"
  # 把想法作为用户消息丢给 claude;skill 会自动触发并产出三部分评审
  claude -p "$prompt" </dev/null > "$dest/output.md" 2>"$dest/stderr.log" \
    && echo "  ✓ -> $dest/output.md" \
    || echo "  ✗ 失败,看 $dest/stderr.log"
done

echo
echo "全部完成。结果在:$OUTDIR"

# 把本批报告渲染成专业 HTML + 汇总索引(渲染失败不阻断测试结论)
if command -v python3 >/dev/null 2>&1; then
  echo "渲染 HTML 报告..."
  python3 render.py --latest || echo "  ⚠ HTML 渲染跳过(见上方错误)"
fi

echo "对照三个判断目标自查:1) 该狠时够狠且不套话  2) 信息少→缺失即风险  3) 好想法不被无脑否定"
echo "HTML 报告:打开 $OUTDIR/index.html"
