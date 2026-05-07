"""Scheduler commands (cron job management)."""

from datetime import datetime
from pathlib import Path
import yaml
from apscheduler.triggers.cron import CronTrigger
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


class SchedulerCommands:
	"""Scheduler command handlers."""

	def handle(self, args: str):
		"""Handle scheduler commands."""
		args_str = str(args).strip() if args else ""

		if not args_str or args_str == "list":
			self._print_cron_jobs()
		else:
			console.print(f"[red]✗[/red] Unknown command: {args_str}")
			console.print("Try: cron list")

	def _print_cron_jobs(self):
		"""Display all cron jobs and their next run times."""
		try:
			cron_config_path = Path("config/cron.yml")
			if not cron_config_path.exists():
				console.print("[yellow]⚠[/yellow] Cron config file not found")
				return

			with open(cron_config_path) as f:
				config = yaml.safe_load(f) or {}

			jobs = config.get("jobs", [])
			if not jobs:
				console.print("[yellow]⚠[/yellow] No cron jobs configured")
				return

			table = Table(title="Cron Jobs", box=box.ROUNDED)
			table.add_column("Name", style="cyan")
			table.add_column("Status", style="green")
			table.add_column("Schedule", style="magenta")
			table.add_column("Target", style="blue")
			table.add_column("Next Run", style="yellow")

			for job in jobs:
				name = job.get("name", "unnamed")
				enabled = job.get("enabled", False)
				schedule = job.get("schedule", "")
				target = job.get("target", "")
				job_type = job.get("type", "flow")

				status = "[green]✓ Enabled[/green]" if enabled else "[dim]✗ Disabled[/dim]"
				target_display = f"{job_type}: {target}"

				# Calculate next run time
				next_run = "[dim]N/A[/dim]"
				if enabled and schedule:
					try:
						trigger = CronTrigger.from_crontab(schedule)
						next_datetime = trigger.get_next_fire_time(None, datetime.now())
						if next_datetime:
							next_run = next_datetime.strftime("%Y-%m-%d %H:%M:%S")
					except Exception as e:
						next_run = f"[red]Error: {e}[/red]"

				table.add_row(name, status, schedule, target_display, next_run)

			console.print(table)

		except Exception as e:
			console.print(f"[red]✗[/red] Error loading cron jobs: {e}")
