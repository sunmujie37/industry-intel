#!/usr/bin/env bash
# 行业情报日报 · 每日自动部署到 GitHub Pages（gh-pages 分支）
# 用法：bash tools/deploy_gh.sh   （在 industry-intel 目录下运行）
set -e
cd "$(dirname "$0")/.."

git add -A
# 有变更才提交
if git diff --cached --quiet; then
  echo "no changes, skip commit"
else
  git commit -q -m "daily: $(date +%F) 情报更新"
fi

git push -q origin main

git subtree split --prefix web main -b tmp-gh >/dev/null 2>&1
git push -q -f origin tmp-gh:gh-pages
git branch -q -D tmp-gh

echo "deployed: https://sunmujie37.github.io/industry-intel/"
