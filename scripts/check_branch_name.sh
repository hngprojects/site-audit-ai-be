#!/usr/bin/env bash

BRANCH_NAME=$(git symbolic-ref --short HEAD || echo "")

if [ -z "$BRANCH_NAME" ]; then
  echo "⚠️  Unable to determine branch name."
  exit 0
fi

echo "Current branch: $BRANCH_NAME"

# Allowed base branches
if echo "$BRANCH_NAME" | grep -Eq '^(main|master|dev(elop)?|staging|hotfix|release)/?$'; then
  echo "✅ Allowed base branch: $BRANCH_NAME"
  exit 0
fi

# Enforce simple feature branch naming, e.g. feature/what-i-am-working-on
if echo "$BRANCH_NAME" | grep -Eq '^(feature|fix|chore|hotfix|bugfix|refactor)/[a-z0-9-]+$'; then
  echo "✅ Valid feature branch name: $BRANCH_NAME"
  exit 0
fi

echo "❌ Invalid branch name: $BRANCH_NAME"
echo "Branch name must match one of the following:"
echo "  - main, master, dev, develop, staging, hotfix, release"
echo "  - <type>/<slug>, e.g.:"
echo "      feature/setup-fastapi-backend"
echo "      fix/health-endpoint-timeout"
echo "      chore/update-readme"
echo "      refactor/split-db-layer"
exit 1
