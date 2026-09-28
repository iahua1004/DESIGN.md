#!/usr/bin/env bash
# Push this repository to GitHub and Gitee.
#
# Usage A — SSH (recommended, no password ever leaves your machine):
#   1. cat ~/.ssh/id_ed25519.pub | pbcopy
#   2. GitHub: Settings -> SSH and GPG keys -> New SSH key   (paste)
#      Gitee : 设置 -> SSH 公钥                                (paste)
#   3. ./scripts/push.sh
#
# Usage B — HTTPS with a token (if you cannot add an SSH key):
#   GITHUB_TOKEN=xxx GITEE_TOKEN=xxx ./scripts/push.sh
#   Revoke the tokens afterwards.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

GITHUB_SSH="${GITHUB_SSH:-git@github.com:iahua1004/DESIGN.md.git}"
GITEE_SSH="${GITEE_SSH:-git@gitee.com:Muzi1004/design.md.git}"

push_one() {
  local name="$1" url="$2"
  echo "== pushing to $name ($url)"
  git remote remove _push 2>/dev/null || true
  git remote add _push "$url"
  if git push -u _push main; then
    echo "   ok"
  else
    echo "   ! failed — see the guidance in README / below"
  fi
  git remote remove _push 2>/dev/null || true
}

if [[ -n "${GITHUB_TOKEN:-}" || -n "${GITEE_TOKEN:-}" ]]; then
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    push_one github "https://iahua1004:${GITHUB_TOKEN}@github.com/iahua1004/DESIGN.md.git"
  fi
  if [[ -n "${GITEE_TOKEN:-}" ]]; then
    push_one gitee "https://Muzi1004:${GITEE_TOKEN}@gitee.com/Muzi1004/design.md.git"
  fi
else
  push_one github "$GITHUB_SSH"
  push_one gitee "$GITEE_SSH"
fi

cat <<'EOF'

== If GitHub said "Permission denied (publickey)":
   cat ~/.ssh/id_ed25519.pub | pbcopy
   then add it at https://github.com/settings/ssh/new  and  https://gitee.com/profile/sshkeys
   and re-run this script.

== After a successful push, enable the mirrors in references/mirrors.json
   (set "enabled": true for gitee) so the skill fetches from your own repo first.
EOF
