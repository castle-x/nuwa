#!/usr/bin/env bash
# 把 skills/ 下的每个 skill 软链接到目标目录，默认 ~/.claude/skills。
#   ./scripts/install.sh
#   ./scripts/install.sh ~/.claude/skills ~/.agents/skills
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
targets=("$@")
[ ${#targets[@]} -eq 0 ] && targets=("$HOME/.claude/skills")

for target in "${targets[@]}"; do
  mkdir -p "$target"
  for skill in "$repo"/skills/*/; do
    name="$(basename "$skill")"
    link="$target/$name"
    if [ -L "$link" ] && [ "$(readlink "$link")" = "${skill%/}" ]; then
      echo "已安装  $link"
    elif [ -e "$link" ] || [ -L "$link" ]; then
      echo "跳过    $link（已存在同名 skill，先手动处理）"
    else
      ln -s "${skill%/}" "$link"
      echo "新安装  $link"
    fi
  done
done
