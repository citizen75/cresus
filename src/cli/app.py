"""Cresus CLI application."""

import cmd2
from pathlib import Path
from cli.commands.service import ServiceManager
from cli.commands.data import DataManager


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
        self.data_manager = DataManager(self.project_root)
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

    def do_data(self, args):
        """Manage historical and fundamental data: fetch|list|clear|stats [options]"""
        args_str = str(args).strip() if args else ""

        if not args_str:
            print("Data management commands:")
            print("  data fetch history <ticker> [start_date]    Fetch historical data")
            print("  data fetch fundamental <ticker>             Fetch fundamental data")
            print("  data fetch universe <name> [start_date]     Fetch all tickers in universe")
            print("  data list [history|fundamentals|all]        List cached data")
            print("  data clear [type] [ticker]                  Clear cache")
            print("    Types: history, fundamentals, all (default: all)")
            print("  data stats                                  Show cache statistics")
            print("  data universes                              List available universes")
            return

        parts = args_str.split()
        cmd = parts[0] if parts else None

        if cmd == "fetch":
            if len(parts) < 3:
                print("Usage: data fetch <history|fundamental|universe> <ticker|name> [start_date]")
                return
            data_type = parts[1]
            target = parts[2]
            start_date = parts[3] if len(parts) > 3 else None

            if data_type == "history":
                result = self.data_manager.fetch_history(target, start_date)
                self._print_result(result)
            elif data_type == "fundamental":
                result = self.data_manager.fetch_fundamental(target)
                self._print_result(result)
            elif data_type == "universe":
                result = self.data_manager.fetch_universe(target, start_date)
                self._print_universe_result(result)
            else:
                print(f"Unknown data type: {data_type}")

        elif cmd == "list":
            data_type = parts[1] if len(parts) > 1 else "all"
            result = self.data_manager.list_cached(data_type)
            self._print_list_result(result)

        elif cmd == "clear":
            data_type = parts[1] if len(parts) > 1 else "all"
            ticker = parts[2] if len(parts) > 2 else None
            result = self.data_manager.clear_cache(data_type, ticker)
            self._print_result(result)

        elif cmd == "stats":
            result = self.data_manager.cache_stats()
            self._print_stats_result(result)

        elif cmd == "universes":
            self._print_universes()

        else:
            print(f"Unknown command: {cmd}")
            print("Try: data fetch|list|clear|stats|universes")

    def _print_result(self, result):
        """Print command result."""
        status = result.get("status", "unknown")
        icon = "✓" if status == "success" else "✗"
        print(f"  {icon} {result.get('message', 'Command executed')}")
        if status == "error":
            return
        for key, value in result.items():
            if key not in ("status", "message", "ticker"):
                if isinstance(value, (dict, list)):
                    print(f"    {key}: {value}")
                else:
                    print(f"    {key}: {value}")

    def _print_list_result(self, result):
        """Print list result."""
        if result.get("status") == "error":
            print(f"  ✗ {result.get('message')}")
            return

        print(f"\n  History ({result.get('total_history', 0)} files):")
        if result.get("history"):
            for item in result["history"]:
                print(f"    {item['ticker']:8} {item['size_kb']:8.1f} KB")
        else:
            print("    (empty)")

        print(f"\n  Fundamentals ({result.get('total_fundamentals', 0)} files):")
        if result.get("fundamentals"):
            for item in result["fundamentals"]:
                print(f"    {item['ticker']:8} {item['size_kb']:8.1f} KB")
        else:
            print("    (empty)")
        print()

    def _print_stats_result(self, result):
        """Print stats result."""
        if result.get("status") == "error":
            print(f"  ✗ {result.get('message')}")
            return

        print("\n  Cache Statistics:")
        hist = result.get("history", {})
        print(f"    History:      {hist.get('count', 0)} files, {hist.get('size_mb', 0)} MB")
        print(f"    Path:         {hist.get('path', 'N/A')}")

        fund = result.get("fundamentals", {})
        print(f"\n    Fundamentals: {fund.get('count', 0)} files, {fund.get('size_mb', 0)} MB")
        print(f"    Path:         {fund.get('path', 'N/A')}")

        print(f"\n    Total Size:   {result.get('total_size_mb', 0)} MB")
        print()

    def _print_universe_result(self, result):
        """Print universe fetch result."""
        status = result.get("status", "unknown")
        icon = "✓" if status == "success" else "✗"

        print(f"\n  {icon} {result.get('message', 'Command executed')}")

        if status == "error":
            if result.get("available"):
                print(f"\n    Available universes: {', '.join(result.get('available', []))}")
            return

        print(f"\n    Universe:  {result.get('universe')}")
        print(f"    Total:     {result.get('total')} tickers")
        print(f"    Fetched:   {result.get('fetched')}")
        print(f"    Failed:    {result.get('failed')}")

        # Show summary stats
        details = result.get("details", [])
        successful = [d for d in details if d.get("status") == "success"]
        if successful:
            rows_fetched = sum(d.get("rows", 0) for d in successful)
            print(f"    Rows:      {rows_fetched} total historical prices")
        print()

    def _print_universes(self):
        """Print available universes."""
        from portfolio.universe import Universe

        universes = Universe.list_universes()

        if not universes:
            print("  No universes found")
            return

        print(f"\n  Available Universes ({len(universes)}):")
        for universe_name in universes:
            info = Universe.get_universe_info(universe_name)
            if info:
                print(f"    {universe_name:15} {info.get('count', 0):4} tickers, {info.get('file_size_kb', 0):.1f} KB")
        print()
