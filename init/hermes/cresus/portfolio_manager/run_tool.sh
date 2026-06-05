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

# Find cresus command - try venv first, then PATH
VENV_CRESUS="$HOME/.cresus/venv/bin/cresus"
if [ -f "$VENV_CRESUS" ]; then
  CRESUS_CMD="$VENV_CRESUS"
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
