#!/bin/bash
# Portfolio Manager Tool Runner
# Executes cresus portfolio commands and returns JSON

set -e

action=$1
portfolio=${2:-PEA}

# Find cresus command - try venv first, then PATH
if [ -f ~/.cresus/venv/bin/cresus ]; then
  CRESUS_CMD="~/.cresus/venv/bin/cresus"
elif [ -f "$HOME/.cresus/venv/bin/cresus" ]; then
  CRESUS_CMD="$HOME/.cresus/venv/bin/cresus"
else
  CRESUS_CMD="cresus"
fi

# Expand tilde in path
CRESUS_CMD=$(eval echo "$CRESUS_CMD")

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
