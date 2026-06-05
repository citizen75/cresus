#!/bin/bash
# Portfolio Manager Tool Runner
# Executes cresus portfolio commands and returns JSON

set -e

action=$1
portfolio=${2:-PEA}

# Ensure HOME is set (Hermes may not set it)
if [ -z "$HOME" ]; then
  export HOME=$(getent passwd $(whoami) | cut -d: -f6)
fi

# Find cresus command - check multiple paths
# 1. Try ~/.cresus/venv/bin (production standard)
if [ -f "$HOME/.cresus/venv/bin/cresus" ]; then
  CRESUS_CMD="$HOME/.cresus/venv/bin/cresus"
# 2. Try ~/.local/bin (symlink location)
elif [ -f "$HOME/.local/bin/cresus" ]; then
  CRESUS_CMD="$HOME/.local/bin/cresus"
# 3. Try /var/apps/cresus/venv/bin (alternative production location)
elif [ -f "/var/apps/cresus/venv/bin/cresus" ]; then
  CRESUS_CMD="/var/apps/cresus/venv/bin/cresus"
# 4. Fall back to PATH search
else
  CRESUS_CMD="cresus"
fi

case "$action" in
  list)
    "$CRESUS_CMD" portfolio list --mcp
    ;;
  positions)
    "$CRESUS_CMD" portfolio positions "$portfolio" --mcp
    ;;
  metrics)
    "$CRESUS_CMD" portfolio metrics "$portfolio" --mcp
    ;;
  performance)
    "$CRESUS_CMD" portfolio performance "$portfolio" --mcp
    ;;
  allocation)
    "$CRESUS_CMD" portfolio allocation "$portfolio" --mcp
    ;;
  value)
    "$CRESUS_CMD" portfolio value "$portfolio" --mcp
    ;;
  *)
    echo "{\"error\": \"Unknown action: $action\"}" >&2
    exit 1
    ;;
esac
