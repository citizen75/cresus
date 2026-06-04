#!/bin/bash
# Executable tool wrapper for Hermes portfolio_manager skill
# Enables Hermes to invoke portfolio commands

set -e

ACTION="${1:-list}"
PORTFOLIO="${2:-PEA}"

# Map action to cresus-mcp command
case "$ACTION" in
  list)
    cresus-mcp portfolio list
    ;;
  positions)
    cresus-mcp portfolio positions "$PORTFOLIO"
    ;;
  metrics)
    cresus-mcp portfolio metrics "$PORTFOLIO"
    ;;
  performance)
    cresus-mcp portfolio performance "$PORTFOLIO"
    ;;
  allocation)
    cresus-mcp portfolio allocation "$PORTFOLIO"
    ;;
  value)
    cresus-mcp portfolio value "$PORTFOLIO"
    ;;
  *)
    echo "Unknown action: $ACTION"
    echo "Available actions: list, positions, metrics, performance, allocation, value"
    exit 1
    ;;
esac
