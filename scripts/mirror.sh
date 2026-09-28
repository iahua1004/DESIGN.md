#!/usr/bin/env bash
# Mirror every DESIGN.md from VoltAgent/awesome-design-md into your own public
# GitHub + Gitee repositories, so the skill has a fast domestic fetch source.
#
# Prerequisites (done once, by you — this script never asks for a password):
#   1. Create an EMPTY public repo on GitHub and on Gitee (no README, no license).
#   2. Add your public key to both sites:  cat ~/.ssh/id_ed25519.pub | pbcopy
#        GitHub: Settings -> SSH and GPG keys -> New SSH key
#        Gitee : 设置 -> SSH 公钥
#
# Usage:
#   ./mirror.sh <github-ssh-url> <gitee-ssh-url> [workdir]
#   GITHUB_REPO=git@github.com:u/r.git GITEE_REPO=git@gitee.com:u/r.git ./mirror.sh
#
# Example:
#   ./mirror.sh git@github.com:iahua1004/awesome-design-md-mirror.git \
#               git@gitee.com:iahua1004/awesome-design-md-mirror.git

set -euo pipefail

PYTHON="/Users/liyanji/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DM="$PYTHON $SCRIPT_DIR/design_md.py"

GITHUB_REPO="${1:-${GITHUB_REPO:-}}"
GITEE_REPO="${2:-${GITEE_REPO:-}}"
WORKDIR="${3:-${WORKDIR:-$HOME/.cache/design-md-mirror}}"

if [[ -z "$GITHUB_REPO" || -z "$GITEE_REPO" ]]; then
  echo "usage: $0 <github-ssh-url> <gitee-ssh-url> [workdir]" >&2
  echo "   or: GITHUB_REPO=... GITEE_REPO=... $0" >&2
  exit 1
fi

echo "== workdir: $WORKDIR"
mkdir -p "$WORKDIR/design-md"
cd "$WORKDIR"

if [[ ! -d .git ]]; then
  git init -q -b main
fi

echo "== listing brands"
mapfile -t DIRS < <($DM list --format names)
echo "   ${#DIRS[@]} brands"

ok=0; fail=0
for d in "${DIRS[@]}"; do
  out="design-md/$d/DESIGN.md"
  mkdir -p "design-md/$d"
  if $DM fetch "$d" --out "$out" >/dev/null 2>&1 && [[ -s "$out" ]]; then
    ok=$((ok+1))
  else
    echo "   ! failed: $d"
    fail=$((fail+1))
    rm -f "$out"
  fi
done
echo "== fetched $ok, failed $fail"

cat > README.md <<'EOF'
# awesome-design-md mirror

A read-only mirror of the `DESIGN.md` files published by
[**VoltAgent/awesome-design-md**](https://github.com/VoltAgent/awesome-design-md).

**Attribution / 归属声明**

- 数据来源 / Source: https://github.com/VoltAgent/awesome-design-md
- 原仓库协议 / Upstream license: **MIT** — Copyright (c) the awesome-design-md authors.
  See https://github.com/VoltAgent/awesome-design-md/blob/main/LICENSE
- 本仓库仅为镜像与备份，用于加速本地访问（尤其是国内网络）。
  This repository is a mirror for fetch acceleration only.
- 所有设计令牌与文档内容著作权归原作者及各品牌方所有；本仓库不主张任何权利。
  All design tokens and documents remain the property of their respective authors
  and brands. No ownership is claimed here.
- `DESIGN.md` 为 Google Stitch 提出的设计系统文档格式：纯 markdown，供 AI agent 读取以
  生成视觉一致的 UI。

Layout: `design-md/<brand>/DESIGN.md` —目录结构与上游一致。
Regenerate with `scripts/mirror.sh` from the `design-md` skill.
EOF

git add -A
if git diff --cached --quiet; then
  echo "== no changes to commit"
else
  git -c user.name="${GIT_USER_NAME:-$(git config user.name || echo mirror)}" \
      -c user.email="${GIT_USER_EMAIL:-$(git config user.email || echo mirror@local)}" \
      commit -q -m "chore: sync $(date +%F) — ${#DIRS[@]} brands from VoltAgent/awesome-design-md (MIT)"
  echo "== committed"
fi

for remote in "$GITHUB_REPO" "$GITEE_REPO"; do
  host=$(echo "$remote" | sed -E 's#^[a-z]+@([^:/]+).*#\1#')
  echo "== pushing to $host"
  git remote remove mirror 2>/dev/null || true
  git remote add mirror "$remote"
  if git push -u mirror main 2>&1 | sed 's/^/   /'; then
    echo "   ok: $host"
  else
    echo "   ! push failed for $host — check that the repo exists, is empty, and your SSH key is added"
  fi
done
git remote remove mirror 2>/dev/null || true

cat <<EOF

== done. Now enable the mirrors in the skill:

  references/mirrors.json
    gitee         -> https://gitee.com/<owner>/<repo>/raw/main/design-md/{dir}/DESIGN.md   "enabled": true
    github-mirror-> https://raw.githubusercontent.com/<owner>/<repo>/main/design-md/{dir}/DESIGN.md  "enabled": true

Verify with:  $DM fetch linear
EOF
