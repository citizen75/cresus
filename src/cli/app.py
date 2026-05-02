"""Cresus CLI application."""

import cmd2
from pathlib import Path
from cli.commands.service import ServiceManager


class CresusCLI(cmd2.Cmd):
    """Cresus portfolio management CLI."""

    intro = """
╔══════════════════════════════════════╗
║          Cresus CLI v1.0.0           ║
║   Portfolio Management Service CLI   ║
╚══════════════════════════════════════╝
Type 'help' for commands or 'quit' to exit.
"""
    prompt = "\033[36mcresus>\033[0m "

    def __init__(self):
        super().__init__()
        self.project_root = self._find_project_root()
        self.service_manager = ServiceManager(self.project_root)
        self._setup_history()

    def _find_project_root(self) -> Path:
        """Find project root by looking for config/cresus.yml."""
        cwd = Path.cwd().resolve()
        for p in [cwd, cwd.parent, cwd.parent.parent]:
            if (p / "config" / "cresus.yml").exists():
                return p
        return cwd

    def _setup_history(self):
        """Set up persistent command history."""
        history_dir = Path.home() / ".cresus"
        history_dir.mkdir(exist_ok=True)
        self.persistent_history_file = str(history_dir / "history")

    def do_service(self, args):
        """Manage services: start|stop|status|logs [service] [-d]"""
        # Convert Statement to string
        args_str = str(args).strip() if args else ""

        if not args_str:
            print("Service management commands:")
            print("  service start <api|mcp|front|all> [-d]    Start service(s)")
            print("  service stop <api|mcp|front|all>          Stop service(s)")
            print("  service status [service]                  Show status")
            print("  service logs <service> [lines]            Show logs")
            return

        parts = args_str.split()
        cmd = parts[0] if parts else None
        service = parts[1] if len(parts) > 1 else None
        daemon = "-d" in parts

        if cmd == "start":
            if not service:
                print("Usage: service start <api|mcp|front|all> [-d]")
                return
            if service == "all":
                for svc in ["api", "mcp", "front"]:
                    result = self.service_manager.start(svc, daemon)
                    print(f"  {svc}: {result}")
            else:
                result = self.service_manager.start(service, daemon)
                print(result)

        elif cmd == "stop":
            if not service:
                print("Usage: service stop <api|mcp|front|all>")
                return
            if service == "all":
                for svc in ["api", "mcp", "front"]:
                    result = self.service_manager.stop(svc)
                    print(f"  {svc}: {result}")
            else:
                result = self.service_manager.stop(service)
                print(result)

        elif cmd == "status":
            status = self.service_manager.status(service)
            for svc, info in status.items():
                print(f"  {svc}: {info}")

        elif cmd == "logs":
            if not service:
                print("Usage: service logs <service> [lines]")
                return
            lines = int(parts[2]) if len(parts) > 2 else 20
            logs = self.service_manager.logs(service, lines)
            print(logs)

        else:
            print(f"Unknown command: {cmd}")
            print("Try: service start|stop|status|logs")


    def do_status(self, _):
        """Show overall system status."""
        status = self.service_manager.status()
        print("\n╔════════════════════════════════════╗")
        print("║      Cresus System Status          ║")
        print("╚════════════════════════════════════╝\n")
        for svc, info in status.items():
            icon = "✓" if info.get("status") == "running" else "✗"
            print(f"  {icon} {svc:8} {info}")
        print()

    def do_info(self, _):
        """Show project info."""
        print(f"\nProject Root: {self.project_root}\n")
