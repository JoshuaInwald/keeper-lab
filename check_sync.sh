#!/usr/bin/env bash
# Confirms the local working tree and GitHub agree. Run before ending any
# session that touched tracked files (docs, klab/, scripts/, tests/, out/).
set -euo pipefail
cd "$(dirname "$0")"

git fetch origin -q

dirty=$(git status --porcelain)
local_head=$(git rev-parse HEAD)
remote_head=$(git rev-parse origin/main)

ok=true

if [ -n "$dirty" ]; then
  echo "UNCOMMITTED CHANGES:"
  echo "$dirty"
  ok=false
fi

if [ "$local_head" != "$remote_head" ]; then
  echo "LOCAL AND GITHUB DIVERGE:"
  echo "  local  main: $local_head"
  echo "  origin main: $remote_head"
  echo "  (git log --oneline main..origin/main for what's on GitHub but not here)"
  echo "  (git log --oneline origin/main..main for what's here but not pushed)"
  ok=false
fi

if [ "$ok" = true ]; then
  echo "OK — working tree clean, local main == origin/main ($local_head)"
else
  exit 1
fi
