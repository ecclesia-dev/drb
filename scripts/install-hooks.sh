#!/bin/sh
# install-hooks.sh — installs pre-push safety hook for ecclesia-dev repos
# Maintained by: Albert (ecclesia-dev DevOps)

set -e

HOOK_DIR="$(git rev-parse --show-toplevel)/.git/hooks"
HOOK_FILE="$HOOK_DIR/pre-push"

mkdir -p "$HOOK_DIR"

cat > "$HOOK_FILE" << 'HOOKEOF'
#!/bin/sh
# Pre-push safety hook — blocks pushes of workspace files
# Installed in all ecclesia-dev project repos

FORBIDDEN="MEMORY.md USER.md SOUL.md IDENTITY.md AGENTS.md HEARTBEAT.md ORG.MD PIPELINE.md SPRINTS.md STATUS.md PROJECT_INDEX.md MISSION.md MISTAKES.md memory/ .secrets/ knowledge/"

# Check that git root is NOT the workspace root
GIT_ROOT=$(git rev-parse --show-toplevel)
WORKSPACE="${OPENCLAW_WORKSPACE:-}"

if [ -n "$WORKSPACE" ] && [ "$GIT_ROOT" = "$WORKSPACE" ]; then
  echo "❌ PUSH BLOCKED: git root is the workspace root. This would leak personal files."
  echo "   Run git operations from inside the project directory only."
  exit 1
fi

# Check if any forbidden workspace files are tracked
for f in $FORBIDDEN; do
  if git ls-files --error-unmatch "$f" 2>/dev/null; then
    echo "❌ PUSH BLOCKED: workspace file '$f' is tracked in this repo."
    echo "   Remove it with: git rm --cached $f"
    exit 1
  fi
done

echo "✅ Pre-push check passed."
exit 0
HOOKEOF

chmod +x "$HOOK_FILE"

echo "✅ Pre-push hook installed at $HOOK_FILE"
