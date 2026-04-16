#!/usr/bin/env sh

# Render 部署辅助脚本
# 执行前请确认你已经登录 GitHub，并且可访问 Render。

set -eu

# 当前仓库根目录
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

# 检查工作区是否干净
if [ -n "$(git status --short)" ]; then
  echo "请先提交或清理工作区中的更改。"
  git status --short
  exit 1
fi

# 推送当前分支到远程
CURRENT_BRANCH=$(git branch --show-current)
if [ -z "$CURRENT_BRANCH" ]; then
  echo "无法检测当前分支，请检查 git 配置。"
  exit 1
fi

echo "推送当前分支 $CURRENT_BRANCH 到 origin..."
git push origin "$CURRENT_BRANCH"

echo "推送完成。请在 Render 控制台继续创建 Web Service。"

echo "正在打开 Render 控制台..."
if command -v open >/dev/null 2>&1; then
  open https://render.com
else
  echo "请手动访问 https://render.com"
fi

echo "部署脚本执行结束。"
