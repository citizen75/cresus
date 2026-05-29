"""Scheduler commands (cron job management)."""

from datetime import datetime
from pathlib import Path
from typing import Optional
import json
from apscheduler.triggers.cron import CronTrigger
from rich.console import Console
from rich.table import Table
from rich import box

from tools.cron import CronManager

console = Console()


class SchedulerCommands:
	"""Scheduler command handlers."""

	def __init__(self):
		"""Initialize scheduler commands."""
		self.manager = CronManager()

	def _parse_args(self, args_str: str):
		"""Parse arguments respecting quoted strings.

		Returns:
			List of arguments where quoted strings are kept together
		"""
		parts = []
		current = ""
		in_quotes = False
		quote_char = None

		for char in args_str:
			if char in ('"', "'") and not in_quotes:
				in_quotes = True
				quote_char = char
			elif char == quote_char and in_quotes:
				in_quotes = False
				quote_char = None
			elif char == ' ' and not in_quotes:
				if current:
					parts.append(current)
					current = ""
			else:
				current += char

		if current:
			parts.append(current)

		return parts

	def handle(self, args: str):
		"""Handle scheduler commands."""
		args_str = str(args).strip() if args else ""

		if not args_str or args_str == "list":
			self._list_jobs()
		elif args_str.startswith("create"):
			self._handle_create(args_str)
		elif args_str.startswith("delete"):
			self._handle_delete(args_str)
		elif args_str.startswith("enable"):
			self._handle_enable(args_str)
		elif args_str.startswith("disable"):
			self._handle_disable(args_str)
		elif args_str.startswith("info"):
			self._handle_info(args_str)
		elif args_str.startswith("edit"):
			self._handle_edit(args_str)
		else:
			console.print(f"[red]✗[/red] Unknown command: {args_str}")
			self._print_help()

	def _print_help(self):
		"""Print help for cron commands."""
		table = Table(title="Cron Job Management", box=box.ROUNDED)
		table.add_column("Command", style="cyan")
		table.add_column("Description")
		table.add_row("cron list", "List all cron jobs")
		table.add_row("cron info <name>", "Show job details")
		table.add_row(
			"cron create <name> <schedule> <target> [--type flow|agent] [--desc DESC] [--params JSON] [--enable]",
			"Create new cron job"
		)
		table.add_row("cron edit <name> <schedule> <target>", "Edit existing job")
		table.add_row("cron enable <name>", "Enable a job")
		table.add_row("cron disable <name>", "Disable a job")
		table.add_row("cron delete <name>", "Delete a job")
		console.print(table)

	def _list_jobs(self):
		"""Display all cron jobs and their next run times."""
		jobs = self.manager.list_jobs()

		if not jobs:
			console.print("[yellow]⚠[/yellow] No cron jobs configured")
			return

		table = Table(title="Cron Jobs", box=box.ROUNDED)
		table.add_column("Name", style="cyan")
		table.add_column("Status", style="green")
		table.add_column("Schedule", style="magenta")
		table.add_column("Target", style="blue")
		table.add_column("Type", style="yellow")
		table.add_column("Next Run", style="white")

		for job in jobs:
			status = "[green]✓ Enabled[/green]" if job.enabled else "[dim]✗ Disabled[/dim]"
			target_display = job.target

			# Calculate next run time
			next_run = "[dim]N/A[/dim]"
			if job.enabled and job.schedule:
				try:
					trigger = CronTrigger.from_crontab(job.schedule)
					next_datetime = trigger.get_next_fire_time(None, datetime.now())
					if next_datetime:
						next_run = next_datetime.strftime("%Y-%m-%d %H:%M:%S")
				except Exception as e:
					next_run = f"[red]Error[/red]"

			table.add_row(job.name, status, job.schedule, target_display, job.type, next_run)

		console.print(table)

	def _handle_info(self, args_str: str):
		"""Handle cron info command."""
		parts = self._parse_args(args_str)
		if len(parts) < 2:
			console.print("[red]✗[/red] Usage: cron info <name>")
			return

		job_name = parts[1]
		job = self.manager.get_job(job_name)

		if not job:
			console.print(f"[red]✗[/red] Job '{job_name}' not found")
			return

		table = Table(title=f"Cron Job: {job_name}", box=box.ROUNDED)
		table.add_column("Property", style="cyan")
		table.add_column("Value", style="green")

		table.add_row("Name", job.name)
		table.add_row("Description", job.description or "-")
		table.add_row("Status", "Enabled" if job.enabled else "Disabled")
		table.add_row("Schedule", job.schedule)
		table.add_row("Type", job.type)
		table.add_row("Target", job.target)
		table.add_row("Parameters", json.dumps(job.params) if job.params else "{}")

		# Next run time
		next_run = "N/A"
		if job.enabled and job.schedule:
			try:
				trigger = CronTrigger.from_crontab(job.schedule)
				next_datetime = trigger.get_next_fire_time(None, datetime.now())
				if next_datetime:
					next_run = next_datetime.strftime("%Y-%m-%d %H:%M:%S")
			except Exception:
				next_run = "Invalid schedule"

		table.add_row("Next Run", next_run)

		console.print(table)

	def _handle_create(self, args_str: str):
		"""Handle cron create command."""
		# Format: cron create <name> <schedule> <target> [--type flow|agent] [--desc DESC] [--params JSON] [--enable]
		# Note: schedule must have underscores instead of spaces: "0_10_*_*_*" → "0 10 * * *"
		parts = self._parse_args(args_str)

		if len(parts) < 4:
			console.print("[red]✗[/red] Usage: cron create <name> <schedule> <target> [--type flow|agent] [--desc DESC] [--params JSON] [--enable]")
			console.print("[yellow]Note: Use underscores in schedule: cron create my_job 0_10_*_*_* target --enable[/yellow]")
			return

		name = parts[1]
		schedule = parts[2].replace('_', ' ')  # Convert underscores back to spaces
		target = parts[3]

		job_type = "flow"
		description = ""
		params = {}
		enabled = False

		# Parse optional arguments
		i = 4
		while i < len(parts):
			if parts[i] == "--type" and i + 1 < len(parts):
				job_type = parts[i + 1]
				i += 2
			elif parts[i] == "--desc" and i + 1 < len(parts):
				description = parts[i + 1]
				i += 2
			elif parts[i] == "--params" and i + 1 < len(parts):
				try:
					params = json.loads(parts[i + 1])
					i += 2
				except json.JSONDecodeError:
					console.print("[red]✗[/red] Invalid JSON in --params")
					return
			elif parts[i] == "--enable":
				enabled = True
				i += 1
			else:
				i += 1

		success, message = self.manager.create_job(
			name=name,
			schedule=schedule,
			target=target,
			job_type=job_type,
			description=description,
			params=params,
			enabled=enabled,
		)

		if success:
			console.print(f"[green]✓ {message}[/green]")
		else:
			console.print(f"[red]✗ {message}[/red]")

	def _handle_delete(self, args_str: str):
		"""Handle cron delete command."""
		parts = self._parse_args(args_str)

		if len(parts) < 2:
			console.print("[red]✗[/red] Usage: cron delete <name>")
			return

		job_name = parts[1]

		# Confirm deletion
		response = console.input(f"Delete cron job '{job_name}'? (yes/no): ").lower()
		if response != "yes":
			console.print("[yellow]Cancelled[/yellow]")
			return

		success, message = self.manager.delete_job(job_name)

		if success:
			console.print(f"[green]✓ {message}[/green]")
		else:
			console.print(f"[red]✗ {message}[/red]")

	def _handle_enable(self, args_str: str):
		"""Handle cron enable command."""
		parts = self._parse_args(args_str)

		if len(parts) < 2:
			console.print("[red]✗[/red] Usage: cron enable <name>")
			return

		job_name = parts[1]
		success, message = self.manager.enable_job(job_name)

		if success:
			console.print(f"[green]✓ {message}[/green]")
		else:
			console.print(f"[red]✗ {message}[/red]")

	def _handle_disable(self, args_str: str):
		"""Handle cron disable command."""
		parts = self._parse_args(args_str)

		if len(parts) < 2:
			console.print("[red]✗[/red] Usage: cron disable <name>")
			return

		job_name = parts[1]
		success, message = self.manager.disable_job(job_name)

		if success:
			console.print(f"[green]✓ {message}[/green]")
		else:
			console.print(f"[red]✗ {message}[/red]")

	def _handle_edit(self, args_str: str):
		"""Handle cron edit command."""
		# Format: cron edit <name> <schedule> <target> [--type flow|agent] [--desc DESC] [--params JSON]
		# Note: schedule must have underscores instead of spaces: "0_10_*_*_*" → "0 10 * * *"
		parts = self._parse_args(args_str)

		if len(parts) < 4:
			console.print("[red]✗[/red] Usage: cron edit <name> <schedule> <target> [--type flow|agent] [--desc DESC] [--params JSON]")
			console.print("[yellow]Note: Use underscores in schedule: cron edit my_job 0_10_*_*_* target[/yellow]")
			return

		name = parts[1]
		schedule = parts[2].replace('_', ' ')  # Convert underscores back to spaces
		target = parts[3]

		job_type = None
		description = None
		params = None

		# Parse optional arguments
		i = 4
		while i < len(parts):
			if parts[i] == "--type" and i + 1 < len(parts):
				job_type = parts[i + 1]
				i += 2
			elif parts[i] == "--desc" and i + 1 < len(parts):
				description = parts[i + 1]
				i += 2
			elif parts[i] == "--params" and i + 1 < len(parts):
				try:
					params = json.loads(parts[i + 1])
					i += 2
				except json.JSONDecodeError:
					console.print("[red]✗[/red] Invalid JSON in --params")
					return
			else:
				i += 1

		success, message = self.manager.update_job(
			name=name,
			schedule=schedule,
			target=target,
			job_type=job_type,
			description=description,
			params=params,
		)

		if success:
			console.print(f"[green]✓ {message}[/green]")
		else:
			console.print(f"[red]✗ {message}[/red]")
