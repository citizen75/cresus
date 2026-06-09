"""Alert management CLI commands."""

from rich.console import Console
from rich.table import Table
from rich import box
from typing import Optional

from tools.alerts import AlertManager, AlertEvaluator

console = Console()


class AlertCommands:
    """Handle alert CLI commands."""

    def __init__(self):
        """Initialize alert commands."""
        self.manager = AlertManager()
        self.evaluator = AlertEvaluator()

    def handle(self, args: str) -> None:
        """Route alert commands."""
        if not args:
            self.list()
            return

        parts = args.split(None, 1)
        command = parts[0]
        remaining = parts[1] if len(parts) > 1 else ""

        if command == "list":
            self.list(remaining)
        elif command == "create":
            self.create(remaining)
        elif command == "delete":
            self.delete(remaining)
        elif command == "show":
            self.show(remaining)
        elif command == "run":
            self.run(remaining)
        elif command == "enable":
            self.enable(remaining)
        elif command == "disable":
            self.disable(remaining)
        else:
            console.print(f"[red]Unknown alert command: {command}[/red]")
            self._print_usage()

    def list(self, args: str = "") -> None:
        """List all alerts."""
        alerts = self.manager.list_alerts()

        if not alerts:
            console.print("[yellow]No alerts defined[/yellow]")
            return

        table = Table(title="Configured Alerts", box=box.ROUNDED)
        table.add_column("Name", style="cyan")
        table.add_column("Source", style="blue")
        table.add_column("Formula", style="green")
        table.add_column("Enabled", style="yellow")
        table.add_column("Last Run", style="dim")

        for alert in alerts:
            last_run = alert.last_run[:10] if alert.last_run else "Never"
            source_display = f"{alert.source.value}"
            if alert.source_value:
                source_display += f" ({alert.source_value})"

            table.add_row(
                alert.name,
                source_display,
                alert.formula[:50] + "..." if len(alert.formula) > 50 else alert.formula,
                "✓" if alert.enabled else "✗",
                last_run,
            )

        console.print(table)

    def create(self, args: str) -> None:
        """Create new alert.

        Usage: alerts create --name <name> --source <source> --value <value> --formula <formula> [--description <desc>] [--notify <target>]
        """
        # Parse arguments (simple key=value parsing)
        kwargs = {}
        parts = args.split("--")
        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                kwargs[key.strip()] = value.strip().strip('"').strip("'")

        required_keys = {"name", "source", "formula"}
        if not required_keys.issubset(kwargs.keys()):
            console.print(f"[red]Missing required arguments: {required_keys - set(kwargs.keys())}[/red]")
            self._print_create_usage()
            return

        result = self.manager.create_alert(
            name=kwargs["name"],
            source=kwargs["source"],
            source_value=kwargs.get("value"),
            formula=kwargs["formula"],
            notify=kwargs.get("notify", "conversation"),
            description=kwargs.get("description"),
            tags=kwargs.get("tags", "").split(",") if kwargs.get("tags") else None,
        )

        if result["status"] == "success":
            console.print(f"[green]✓ {result['message']}[/green]")
        else:
            console.print(f"[red]✗ {result['message']}[/red]")

    def delete(self, args: str) -> None:
        """Delete alert."""
        alert_name = args.strip()
        if not alert_name:
            console.print("[red]Alert name required[/red]")
            return

        result = self.manager.delete_alert(alert_name)
        if result["status"] == "success":
            console.print(f"[green]✓ {result['message']}[/green]")
        else:
            console.print(f"[red]✗ {result['message']}[/red]")

    def show(self, args: str) -> None:
        """Show alert details."""
        alert_name = args.strip()
        if not alert_name:
            console.print("[red]Alert name required[/red]")
            return

        alert = self.manager.get_alert(alert_name)
        if not alert:
            console.print(f"[red]Alert '{alert_name}' not found[/red]")
            return

        console.print(f"\n[bold cyan]Alert: {alert.name}[/bold cyan]")
        console.print(f"[cyan]Source:[/cyan] {alert.source.value}", end="")
        if alert.source_value:
            console.print(f" ({alert.source_value})")
        else:
            console.print()
        console.print(f"[cyan]Formula:[/cyan] {alert.formula}")
        console.print(f"[cyan]Notify:[/cyan] {alert.notify.value}")
        console.print(f"[cyan]Enabled:[/cyan] {'Yes' if alert.enabled else 'No'}")
        console.print(f"[cyan]Created:[/cyan] {alert.created_at[:10]}")
        console.print(f"[cyan]Last run:[/cyan] {alert.last_run[:10] if alert.last_run else 'Never'}")
        if alert.description:
            console.print(f"[cyan]Description:[/cyan] {alert.description}")

    def run(self, args: str) -> None:
        """Run alert evaluation."""
        alert_name = args.strip()
        if not alert_name:
            console.print("[red]Alert name required[/red]")
            return

        alert = self.manager.get_alert(alert_name)
        if not alert:
            console.print(f"[red]Alert '{alert_name}' not found[/red]")
            return

        console.print(f"[cyan]Evaluating alert: {alert_name}[/cyan]")

        result = self.evaluator.evaluate_alert(alert)
        self.manager.update_last_run(alert_name)

        if result.error:
            console.print(f"[red]✗ Error: {result.error}[/red]")
            return

        if result.matched:
            console.print(f"[green]✓ Found {len(result.matches)} match(es)[/green]")
            self._print_matches(result.matches)
        else:
            console.print(f"[yellow]No matches found ({result.tickers_checked} tickers checked)[/yellow]")

    def enable(self, args: str) -> None:
        """Enable alert."""
        alert_name = args.strip()
        if not alert_name:
            console.print("[red]Alert name required[/red]")
            return

        result = self.manager.update_alert(alert_name, enabled=True)
        if result["status"] == "success":
            console.print(f"[green]✓ Alert enabled[/green]")
        else:
            console.print(f"[red]✗ {result['message']}[/red]")

    def disable(self, args: str) -> None:
        """Disable alert."""
        alert_name = args.strip()
        if not alert_name:
            console.print("[red]Alert name required[/red]")
            return

        result = self.manager.update_alert(alert_name, enabled=False)
        if result["status"] == "success":
            console.print(f"[green]✓ Alert disabled[/green]")
        else:
            console.print(f"[red]✗ {result['message']}[/red]")

    def _print_matches(self, matches: list) -> None:
        """Print matched rows in table format."""
        if not matches:
            return

        table = Table(title="Matches", box=box.ROUNDED)
        table.add_column("Date", style="cyan")
        table.add_column("Ticker", style="blue")
        table.add_column("Close", justify="right", style="green")

        for match in matches[:50]:  # Limit to 50 matches
            date_val = match.get('timestamp') or match.get('date', '?')
            ticker = match.get('ticker', '?')
            close = match.get('close', '?')

            table.add_row(str(date_val)[:10], ticker, f"{float(close):.2f}" if close and close != '?' else str(close))

        console.print(table)

    def _print_usage(self) -> None:
        """Print command usage."""
        console.print("""
[bold]Alert Management[/bold]

Usage:
  [cyan]alerts list[/cyan]                                    List all alerts
  [cyan]alerts create[/cyan] --name <name> --source <source> Create alert
                      --formula <formula> [--value <value>]
                      [--notify <target>] [--description <desc>]
  [cyan]alerts show[/cyan] <name>                             Show alert details
  [cyan]alerts run[/cyan] <name>                              Run alert evaluation
  [cyan]alerts enable[/cyan] <name>                           Enable alert
  [cyan]alerts disable[/cyan] <name>                          Disable alert
  [cyan]alerts delete[/cyan] <name>                           Delete alert

Sources:
  ticker         Single ticker
  tickers        Comma-separated tickers
  universe       Universe name
  portfolio      Portfolio name
  all_portfolios All open positions

Notify Targets:
  conversation   Send to alert conversation (default)
  email          Send email notification
  webhook        Send webhook notification
""")

    def _print_create_usage(self) -> None:
        """Print create command usage."""
        console.print("""
[bold]Create Alert Usage:[/bold]

[cyan]alerts create[/cyan] --name <name> \\
                --source <source> \\
                --formula <formula> \\
                [--value <value>] \\
                [--notify conversation|email|webhook] \\
                [--description <desc>]

Examples:
  [dim]# Alert on RSI < 50 for all portfolios[/dim]
  [cyan]alerts create[/cyan] --name rsi_low \\
                  --source all_portfolios \\
                  --formula "rsi_14[0]<50" \\
                  --notify conversation

  [dim]# Alert on universe etf_fr[/dim]
  [cyan]alerts create[/cyan] --name etf_oversold \\
                  --source universe \\
                  --value etf_fr \\
                  --formula "rsi_14[0]<30" \\
                  --description "RSI oversold in ETF universe"
""")
