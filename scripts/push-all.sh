#!/usr/bin/env bash
set -euo pipefail

REMOTE="origin"
BACKEND_REMOTE="ox-backend"
WEBAPP_REMOTE="ox-webapp"

BACKEND_REMOTE_URL="https://gitlab.openxcell.dev/a-team/ces-automation/backend"
WEBAPP_REMOTE_URL="https://gitlab.openxcell.dev/a-team/ces-automation/webapp"

BACKEND_PREFIX="ces-ddr-platform/ces-backend"
WEBAPP_PREFIX="ces-ddr-platform/ces-frontend"

BRANCH="${1:-main}"

PREV=$(git rev-parse "$REMOTE/$BRANCH" 2>/dev/null || echo "")

ensure_remote() {
    local name="$1"
    local url="$2"
    if ! git remote get-url "$name" >/dev/null 2>&1; then
        echo ">>> Adding $name remote"
        git remote add "$name" "$url"
    fi
}

ensure_remote "$BACKEND_REMOTE" "$BACKEND_REMOTE_URL"
ensure_remote "$WEBAPP_REMOTE" "$WEBAPP_REMOTE_URL"

echo ">>> Pushing to $REMOTE/$BRANCH"
git push "$REMOTE" "$BRANCH"

if [ -n "$PREV" ]; then
    BACKEND_CHANGES=$(git diff --name-only "$PREV" HEAD -- "$BACKEND_PREFIX/" | head -1)
    WEBAPP_CHANGES=$(git diff --name-only "$PREV" HEAD -- "$WEBAPP_PREFIX/" | head -1)
else
    BACKEND_CHANGES="yes"
    WEBAPP_CHANGES="yes"
fi

if [ -n "$BACKEND_CHANGES" ]; then
    echo ">>> Backend changes detected — splitting and force pushing to $BACKEND_REMOTE/development"
    SPLIT=$(git subtree split --prefix="$BACKEND_PREFIX" HEAD)
    git push "$BACKEND_REMOTE" "$SPLIT:refs/heads/development" --force
else
    echo ">>> No backend changes — skipping $BACKEND_REMOTE"
fi

if [ -n "$WEBAPP_CHANGES" ]; then
    echo ">>> Webapp changes detected — splitting and force pushing to $WEBAPP_REMOTE/development"
    SPLIT=$(git subtree split --prefix="$WEBAPP_PREFIX" HEAD)
    git push "$WEBAPP_REMOTE" "$SPLIT:refs/heads/development" --force
else
    echo ">>> No webapp changes — skipping $WEBAPP_REMOTE"
fi

echo ">>> Done"
