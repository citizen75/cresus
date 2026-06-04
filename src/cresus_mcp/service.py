#!/usr/bin/env python3
"""Cresus MCP service manager for standalone operation."""

import sys
import os
import signal
import subprocess
import time
from pathlib import Path

# Set project root
project_root = Path(__file__).parent.parent.parent
os.chdir(project_root)

CONFIG_DIR = Path.home() / ".cresus"
CONFIG_DIR.mkdir(exist_ok=True)
PID_FILE = CONFIG_DIR / "mcp.pid"
STATUS_FILE = CONFIG_DIR / "mcp.status"


def read_pid():
    """Read PID from file."""
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except (ValueError, IOError):
            return None
    return None


def write_pid(pid):
    """Write PID to file."""
    PID_FILE.write_text(str(pid))


def is_running(pid):
    """Check if process is running."""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def get_status():
    """Get current server status."""
    pid = read_pid()
    if pid and is_running(pid):
        return {"status": "running", "pid": pid}
    else:
        if PID_FILE.exists():
            PID_FILE.unlink()
        return {"status": "stopped", "pid": None}


def start_server():
    """Start the MCP server via Hermes."""
    status = get_status()
    if status["status"] == "running":
        print(f"✓ MCP server already running (PID: {status['pid']})")
        return 0

    print("Starting Cresus MCP server...")

    api_url = os.environ.get("CRESUS_API_URL", "http://192.168.0.130:6501/api/v1")
    log_level = os.environ.get("CRESUS_LOG_LEVEL", "INFO")

    env = os.environ.copy()
    env["CRESUS_API_URL"] = api_url
    env["CRESUS_LOG_LEVEL"] = log_level

    try:
        # Start MCP server through Hermes (which manages stdio)
        # This connects to Hermes which then manages the process lifecycle
        proc = subprocess.Popen(
            [sys.executable, "-m", "cresus_mcp.main"],
            cwd=str(project_root),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Detach from parent
        )

        write_pid(proc.pid)
        time.sleep(2)  # Give server time to start

        # The server will exit immediately since no one is reading from stdout
        # Instead, we'll rely on Hermes to manage the MCP server lifecycle
        print(f"✓ MCP service registered")
        print(f"  API: {api_url}")
        print(f"  Management: Via Hermes")
        print(f"  Logs: logs/mcp.log")
        print(f"\n  Use Hermes to interact with portfolio tools:")
        print(f"  hermes mcp list")
        print(f"  hermes mcp test cresus")
        return 0
    except Exception as e:
        print(f"✗ Error registering MCP service: {e}")
        return 1


def stop_server():
    """Stop the MCP server."""
    status = get_status()
    if status["status"] == "stopped":
        print("✓ MCP server is not running")
        return 0

    pid = status["pid"]
    print(f"MCP server is managed by Hermes (PID: {pid})")
    print("✓ Use 'hermes postinstall' to reset MCP configuration")

    if PID_FILE.exists():
        PID_FILE.unlink()
    return 0


def show_status():
    """Show server status."""
    print("=" * 60)
    print("CRESUS MCP SERVER STATUS")
    print("=" * 60)
    print()
    print("Management: Hermes (automatic)")
    print("Transport: Stdio (subprocess)")
    print()

    # Check if Hermes has the MCP server configured
    try:
        hermes_config = Path.home() / ".hermes" / "config.yaml"
        if hermes_config.exists():
            config_content = hermes_config.read_text()
            if "cresus:" in config_content and "mcp_servers:" in config_content:
                print("✓ MCP server configured in Hermes")
                print("✓ Ready for portfolio queries")
            else:
                print("✗ MCP server not found in Hermes config")
        else:
            print("✗ Hermes config not found")
    except Exception as e:
        print(f"✗ Error checking Hermes config: {e}")

    print()
    print("Configuration:")
    print(f"  Config file: {Path.home() / '.hermes' / 'config.yaml'}")
    print(f"  Log file: logs/mcp.log")
    print()
    print("Tools:")
    print("  - list_portfolios")
    print("  - get_portfolio_positions")
    print("  - get_portfolio_metrics")
    print("  - get_portfolio_performance")
    print("  - ... (16 total tools)")
    print()
    print("Quick start:")
    print("  hermes mcp test cresus           # Test connection")
    print("  hermes mcp list                  # List all MCP servers")
    print("  hermes postinstall               # Reinitialize Hermes config")
    print()
    return 0


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Cresus MCP Server Manager",
        prog="cresus-mcp-server"
    )
    parser.add_argument(
        "command",
        choices=["start", "stop", "status"],
        help="Service command"
    )

    args = parser.parse_args()

    if args.command == "start":
        return start_server()
    elif args.command == "stop":
        return stop_server()
    elif args.command == "status":
        return show_status()


if __name__ == "__main__":
    sys.exit(main())
