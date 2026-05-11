#!/usr/bin/env bash
set -euo pipefail

BACKEND_REMOTE="ox-backend"
WEBAPP_REMOTE="ox-webapp"

BACKEND_PREFIX="ces-ddr-platform/ces-backend"
WEBAPP_PREFIX="ces-ddr-platform/ces-frontend"

BRANCH="${1:-development}"

ensure_remote() {
    local name="$1"
    if ! git remote get-url "$name" >/dev/null 2>&1; then
        echo ">>> Remote $name not found. Run ./scripts/push-all.sh first to set up remotes."
        exit 1
    fi
}

ensure_remote "$BACKEND_REMOTE"
ensure_remote "$WEBAPP_REMOTE"

echo ">>> Pulling backend changes from $BACKEND_REMOTE/$BRANCH"
git subtree pull --prefix="$BACKEND_PREFIX" "$BACKEND_REMOTE" "$BRANCH"

echo ">>> Pulling webapp changes from $WEBAPP_REMOTE/$BRANCH"
git subtree pull --prefix="$WEBAPP_PREFIX" "$WEBAPP_REMOTE" "$BRANCH"

echo ">>> Done"
