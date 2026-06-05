#!/usr/bin/env python3
"""Cresus Portfolio Manager Tool - Routes to run_tool.sh"""

import subprocess
import json
import sys
from pathlib import Path


def execute_cresus_command(action: str, portfolio: str = "PEA") -> dict:
    """Execute cresus portfolio command via run_tool.sh"""
    script_dir = Path(__file__).parent
    script = script_dir / "run_tool.sh"

    try:
        result = subprocess.run(
            ["bash", str(script), action, portfolio],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                # If JSON parsing fails, return the raw output as error
                return {
                    "status": "error",
                    "message": f"JSON parse error: {str(e)}",
                    "raw_output": result.stdout[:500]
                }
        else:
            return {
                "status": "error",
                "message": result.stderr or "Command failed"
            }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Command timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def main():
    """CLI entry point for Hermes"""
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "message": "Usage: tool.py <action> [portfolio]"
        }))
        sys.exit(1)

    action = sys.argv[1]
    portfolio = sys.argv[2] if len(sys.argv) > 2 else "PEA"

    result = execute_cresus_command(action, portfolio)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
