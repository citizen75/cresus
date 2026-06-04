#!/bin/bash
# Portfolio Manager Tool Runner
# Executes cresus portfolio commands and returns JSON

set -e

action=$1
portfolio=${2:-PEA}

case "$action" in
  list)
    cresus portfolio list --mcp
    ;;
  positions)
    cresus portfolio positions "$portfolio" --mcp
    ;;
  metrics)
    cresus portfolio metrics "$portfolio" --mcp
    ;;
  performance)
    cresus portfolio performance "$portfolio" --mcp
    ;;
  allocation)
    cresus portfolio allocation "$portfolio" --mcp
    ;;
  value)
    cresus portfolio value "$portfolio" --mcp
    ;;
  *)
    echo "{\"error\": \"Unknown action: $action\"}" >&2
    exit 1
    ;;
esac
