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

# Enforce ClickUp-style ticket ID in feature branches
# Example: feature/ABC-123-add-something
if echo "$BRANCH_NAME" | grep -Eq '^(feature|fix|chore|hotfix|bugfix)/[A-Za-z]+-[0-9]+(-[a-z0-9-]*)?$'; then
  echo "✅ Valid feature branch with ClickUp ID: $BRANCH_NAME"
  exit 0
fi

echo "❌ Invalid branch name: $BRANCH_NAME"
echo "Branch name must match one of the following:"
echo "  - main, master, dev, develop, staging, hotfix, release"
echo "  - feature/<TICKET-ID>-slug (e.g., feature/ABC-123-add-scan-endpoint)"
echo "  - fix/<TICKET-ID>-slug"
echo "  - chore/<TICKET-ID>-slug"
exit 1
