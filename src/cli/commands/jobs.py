"""Job management commands (cresus jobs ...)."""

from pathlib import Path
from typing import Optional, List
from datetime import datetime
import json

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from core.job import JobStatus
from tools.jobs import JobManager

console = Console()


class JobsCommands:
	"""Job management command handlers."""

	def __init__(self):
		"""Initialize jobs commands."""
		self.manager = JobManager()

	def handle(self, args: str):
		"""Handle jobs commands.

		Usage:
			jobs list [status]
			jobs create <job_name> [--config FILE]
			jobs info <job_name>
			jobs start <job_name>
			jobs complete <job_name> [--results JSON]
			jobs fail <job_name> <error_message>
			jobs delete <job_name>
			jobs config <job_name> [show|save|load]
			jobs results <job_name> [key]
			jobs logs <job_name> [log_name]
			jobs cleanup [--keep N] [--status STATUS]
			jobs summary
		"""
		args_str = str(args).strip() if args else ""

		if not args_str:
			self._print_help()
			return

		parts = args_str.split(maxsplit=1)
		cmd = parts[0]
		args_rest = parts[1] if len(parts) > 1 else ""

		if cmd == "list":
			self._handle_list(args_rest)
		elif cmd == "create":
			self._handle_create(args_rest)
		elif cmd == "info":
			self._handle_info(args_rest)
		elif cmd == "start":
			self._handle_start(args_rest)
		elif cmd == "complete":
			self._handle_complete(args_rest)
		elif cmd == "fail":
			self._handle_fail(args_rest)
		elif cmd == "delete":
			self._handle_delete(args_rest)
		elif cmd == "config":
			self._handle_config(args_rest)
		elif cmd == "results":
			self._handle_results(args_rest)
		elif cmd == "logs":
			self._handle_logs(args_rest)
		elif cmd == "cleanup":
			self._handle_cleanup(args_rest)
		elif cmd == "summary":
			self._handle_summary()
		else:
			console.print(f"[red]✗[/red] Unknown command: {cmd}")
			self._print_help()

	def _print_help(self):
		"""Print help for jobs commands."""
		table = Table(title="Job Management Commands", box=box.ROUNDED)
		table.add_column("Command", style="cyan")
		table.add_column("Description")

		table.add_row("jobs list [status]", "List all jobs (optionally filter by status)")
		table.add_row("jobs summary", "Show summary of all jobs by status")
		table.add_row("jobs create <name>", "Create a new job")
		table.add_row("jobs info <name>", "Show job details and metadata")
		table.add_row("jobs start <name>", "Mark job as running")
		table.add_row("jobs complete <name>", "Mark job as completed successfully")
		table.add_row("jobs fail <name> <error>", "Mark job as failed with error")
		table.add_row("jobs delete <name>", "Delete a job and all its data")
		table.add_row("jobs config <name> [show|save|load]", "Manage job configuration")
		table.add_row("jobs results <name> [key]", "Show job results")
		table.add_row("jobs logs <name> [log_name]", "Show job logs")
		table.add_row("jobs cleanup [--keep N]", "Clean up old jobs")

		console.print(table)

	def _handle_list(self, args: str):
		"""List jobs, optionally filtered by status."""
		parts = args.split() if args.strip() else []
		status_filter = None

		if parts:
			try:
				status_filter = JobStatus(parts[0].lower())
			except ValueError:
				console.print(f"[red]✗[/red] Invalid status: {parts[0]}")
				console.print(f"  Valid statuses: {', '.join([s.value for s in JobStatus])}")
				return

		jobs = self.manager.list_jobs(status_filter)

		if not jobs:
			console.print("[yellow]⧗[/yellow] No jobs found")
			if status_filter:
				console.print(f"  Filter: {status_filter.value}")
			return

		table = Table(title=f"Jobs ({len(jobs)})", box=box.ROUNDED)
		table.add_column("Name", style="cyan")
		table.add_column("Status", style="green")
		table.add_column("Created")
		table.add_column("Duration")

		for job_name in jobs:
			job = self.manager.get_job(job_name)
			if job:
				duration = ""
				if job.get_duration_seconds():
					duration = f"{job.get_duration_seconds():.1f}s"

				created = job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else "N/A"
				status_color = self._status_color(job.status)

				table.add_row(
					job_name,
					f"[{status_color}]{job.status.value}[/{status_color}]",
					created,
					duration
				)

		console.print(table)

	def _handle_summary(self):
		"""Show summary of jobs by status."""
		summary = self.manager.get_jobs_summary()

		table = Table(title="Job Summary", box=box.ROUNDED)
		table.add_column("Status", style="cyan")
		table.add_column("Count", justify="right")

		for status in ["pending", "running", "success", "error", "cancelled"]:
			count = summary.get(status, 0)
			if count > 0:
				color = self._status_color(JobStatus(status))
				table.add_row(
					f"[{color}]{status}[/{color}]",
					str(count)
				)

		total = summary.get("total", 0)
		table.add_row(f"[bold]Total[/bold]", str(total))

		console.print(table)

	def _handle_create(self, args: str):
		"""Create a new job."""
		if not args.strip():
			console.print("[red]✗[/red] Usage: jobs create <job_name> [--config FILE]")
			return

		parts = args.split()
		job_name = parts[0]
		config = None

		# Parse config file if provided
		if "--config" in parts:
			config_idx = parts.index("--config")
			if config_idx + 1 < len(parts):
				config_file = parts[config_idx + 1]
				try:
					with open(config_file) as f:
						config = json.load(f)
				except Exception as e:
					console.print(f"[red]✗[/red] Failed to load config: {e}")
					return

		try:
			job = self.manager.create_job(job_name, config)
			console.print(f"[green]✓[/green] Job created: {job_name}")
			console.print(f"  Directory: {job.job_dir}")
			if config:
				console.print(f"  Configuration: {len(config)} keys")
		except ValueError as e:
			console.print(f"[red]✗[/red] {e}")
		except Exception as e:
			console.print(f"[red]✗[/red] Error creating job: {e}")

	def _handle_info(self, args: str):
		"""Show job information."""
		job_name = args.strip()
		if not job_name:
			console.print("[red]✗[/red] Usage: jobs info <job_name>")
			return

		job = self.manager.get_job(job_name)
		if not job:
			console.print(f"[red]✗[/red] Job not found: {job_name}")
			return

		# Create info panel
		info_text = f"""
[bold]Name:[/bold] {job.name}
[bold]Status:[/bold] {self._format_status(job.status)}
[bold]Created:[/bold] {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}
[bold]Started:[/bold] {job.started_at.strftime('%Y-%m-%d %H:%M:%S') if job.started_at else 'N/A'}
[bold]Ended:[/bold] {job.ended_at.strftime('%Y-%m-%d %H:%M:%S') if job.ended_at else 'N/A'}
[bold]Duration:[/bold] {f'{job.get_duration_seconds():.2f}s' if job.get_duration_seconds() else 'N/A'}
[bold]Agents Executed:[/bold] {len(job.agents_executed)}
[bold]Results Keys:[/bold] {len(job.results)}
[bold]Error:[/bold] {job.error_message or 'None'}
		"""

		console.print(Panel(info_text.strip(), title=f"Job: {job_name}", style="cyan"))

		# Show agents executed
		if job.agents_executed:
			console.print("\n[bold]Agents:[/bold]")
			for agent in job.agents_executed:
				console.print(f"  • {agent}")

		# Show results
		if job.results:
			console.print("\n[bold]Results:[/bold]")
			for key, value in job.results.items():
				value_str = str(value)
				if len(value_str) > 50:
					value_str = value_str[:47] + "..."
				console.print(f"  • {key}: {value_str}")

	def _handle_start(self, args: str):
		"""Start a job (mark as running)."""
		job_name = args.strip()
		if not job_name:
			console.print("[red]✗[/red] Usage: jobs start <job_name>")
			return

		job = self.manager.get_job(job_name)
		if not job:
			console.print(f"[red]✗[/red] Job not found: {job_name}")
			return

		job.start()
		job.save_metadata()
		console.print(f"[green]✓[/green] Job started: {job_name}")

	def _handle_complete(self, args: str):
		"""Complete a job (mark as success)."""
		if not args.strip():
			console.print("[red]✗[/red] Usage: jobs complete <job_name> [--results JSON]")
			return

		parts = args.split(maxsplit=1)
		job_name = parts[0]

		job = self.manager.get_job(job_name)
		if not job:
			console.print(f"[red]✗[/red] Job not found: {job_name}")
			return

		# Parse results if provided
		results = None
		if len(parts) > 1 and "--results" in parts[1]:
			try:
				results_json = parts[1].split("--results")[1].strip()
				results = json.loads(results_json)
			except Exception as e:
				console.print(f"[red]✗[/red] Invalid JSON results: {e}")
				return

		job.complete(results)
		job.save_metadata()
		console.print(f"[green]✓[/green] Job completed: {job_name}")

	def _handle_fail(self, args: str):
		"""Mark a job as failed."""
		if not args.strip():
			console.print("[red]✗[/red] Usage: jobs fail <job_name> <error_message>")
			return

		parts = args.split(maxsplit=1)
		job_name = parts[0]
		error_message = parts[1] if len(parts) > 1 else "Unknown error"

		job = self.manager.get_job(job_name)
		if not job:
			console.print(f"[red]✗[/red] Job not found: {job_name}")
			return

		job.fail(error_message)
		job.save_metadata()
		console.print(f"[green]✓[/green] Job marked as failed: {job_name}")
		console.print(f"  Error: {error_message}")

	def _handle_delete(self, args: str):
		"""Delete a job."""
		job_name = args.strip()
		if not job_name:
			console.print("[red]✗[/red] Usage: jobs delete <job_name>")
			return

		if self.manager.delete_job(job_name):
			console.print(f"[green]✓[/green] Job deleted: {job_name}")
		else:
			console.print(f"[red]✗[/red] Job not found: {job_name}")

	def _handle_config(self, args: str):
		"""Manage job configuration."""
		if not args.strip():
			console.print("[red]✗[/red] Usage: jobs config <job_name> [show|save <file>|load <file>]")
			return

		parts = args.split(maxsplit=2)
		job_name = parts[0]
		action = parts[1] if len(parts) > 1 else "show"
		target = parts[2] if len(parts) > 2 else None

		config = self.manager.load_config(job_name)
		if config is None:
			console.print(f"[red]✗[/red] Configuration not found for job: {job_name}")
			return

		if action == "show":
			console.print(Panel(json.dumps(config, indent=2), title=f"Config: {job_name}"))
		elif action == "save" and target:
			try:
				with open(target, "w") as f:
					json.dump(config, f, indent=2)
				console.print(f"[green]✓[/green] Configuration saved to: {target}")
			except Exception as e:
				console.print(f"[red]✗[/red] Error saving config: {e}")
		elif action == "load" and target:
			try:
				with open(target) as f:
					new_config = json.load(f)
				self.manager.save_config(job_name, new_config)
				console.print(f"[green]✓[/green] Configuration loaded from: {target}")
			except Exception as e:
				console.print(f"[red]✗[/red] Error loading config: {e}")
		else:
			console.print("[red]✗[/red] Invalid config action")

	def _handle_results(self, args: str):
		"""Show job results."""
		if not args.strip():
			console.print("[red]✗[/red] Usage: jobs results <job_name> [key]")
			return

		parts = args.split(maxsplit=1)
		job_name = parts[0]
		key_filter = parts[1] if len(parts) > 1 else None

		job = self.manager.get_job(job_name)
		if not job:
			console.print(f"[red]✗[/red] Job not found: {job_name}")
			return

		if not job.results:
			console.print(f"[yellow]⧗[/yellow] No results for job: {job_name}")
			return

		if key_filter:
			if key_filter in job.results:
				value = job.results[key_filter]
				console.print(Panel(json.dumps(value, indent=2, default=str), title=f"Result: {key_filter}"))
			else:
				console.print(f"[red]✗[/red] Result key not found: {key_filter}")
		else:
			table = Table(title=f"Results: {job_name}", box=box.ROUNDED)
			table.add_column("Key", style="cyan")
			table.add_column("Value")

			for key, value in job.results.items():
				value_str = json.dumps(value, default=str)
				if len(value_str) > 50:
					value_str = value_str[:47] + "..."
				table.add_row(key, value_str)

			console.print(table)

	def _handle_logs(self, args: str):
		"""Show job logs."""
		if not args.strip():
			console.print("[red]✗[/red] Usage: jobs logs <job_name> [log_name]")
			return

		parts = args.split(maxsplit=1)
		job_name = parts[0]
		log_name = parts[1] if len(parts) > 1 else "job"

		log_file = self.manager.get_job_log_file(job_name, log_name)

		if not log_file.exists():
			console.print(f"[red]✗[/red] Log file not found: {log_file}")
			return

		try:
			with open(log_file) as f:
				content = f.read()

			console.print(Panel(content, title=f"Logs: {job_name}/{log_name}.log"))
		except Exception as e:
			console.print(f"[red]✗[/red] Error reading log: {e}")

	def _handle_cleanup(self, args: str):
		"""Clean up old jobs."""
		keep_count = 10
		status_filter = None

		if args.strip():
			parts = args.split()
			if "--keep" in parts:
				idx = parts.index("--keep")
				if idx + 1 < len(parts):
					try:
						keep_count = int(parts[idx + 1])
					except ValueError:
						console.print(f"[red]✗[/red] Invalid keep count: {parts[idx + 1]}")
						return

			if "--status" in parts:
				idx = parts.index("--status")
				if idx + 1 < len(parts):
					try:
						status_filter = JobStatus(parts[idx + 1].lower())
					except ValueError:
						console.print(f"[red]✗[/red] Invalid status: {parts[idx + 1]}")
						return

		deleted = self.manager.cleanup_old_jobs(keep_count, status_filter)

		if deleted > 0:
			console.print(f"[green]✓[/green] Cleaned up {deleted} old job(s)")
			if status_filter:
				console.print(f"  Filter: {status_filter.value}")
			console.print(f"  Kept: {keep_count} most recent")
		else:
			console.print(f"[yellow]⧗[/yellow] No jobs to clean up")

	def _status_color(self, status: JobStatus) -> str:
		"""Get color for status."""
		colors = {
			JobStatus.PENDING: "yellow",
			JobStatus.RUNNING: "blue",
			JobStatus.SUCCESS: "green",
			JobStatus.ERROR: "red",
			JobStatus.CANCELLED: "yellow",
		}
		return colors.get(status, "white")

	def _format_status(self, status: JobStatus) -> str:
		"""Format status with color."""
		color = self._status_color(status)
		return f"[{color}]{status.value}[/{color}]"
