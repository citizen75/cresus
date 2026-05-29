"""Refactored Cresus CLI application - Phase 2/3."""

import os
import cmd2
from pathlib import Path
from typing import Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from src.cli.base import BaseCommand, CommandResult
from src.cli.utils import Formatter
from src.cli.commands.screener import ScreenerCommand

console = Console()


class CresusCLI(cmd2.Cmd):
	"""Refactored Cresus portfolio management CLI.

	Minimal routing, all command logic in subclasses.
	"""

	intro = ""

	def __init__(self, interactive: bool = True):
		"""Initialize CLI.

		Args:
			interactive: Whether to run in interactive mode
		"""
		super().__init__()
		self.interactive = interactive
		self.project_root = self._find_project_root()
		os.environ["CRESUS_PROJECT_ROOT"] = str(self.project_root)

		# Initialize commands
		self.commands: Dict[str, BaseCommand] = {
			"screener": ScreenerCommand(),
			# Additional commands to be refactored:
			# "strategy": StrategyCommand(),
			# "data": DataCommand(),
			# "portfolio": PortfolioCommand(),
			# "flow": FlowCommand(),
		}

		self._setup_history()
		self._setup_prompt()

		if self.interactive:
			self._print_intro()

	def _find_project_root(self) -> Path:
		"""Find project root directory."""
		if "CRESUS_PROJECT_ROOT" in os.environ:
			env_root = Path(os.environ["CRESUS_PROJECT_ROOT"]).resolve()
			if (env_root / "config" / "cresus.yml").exists():
				return env_root

		# Check current directory and parents
		current = Path.cwd()
		for parent in [current] + list(current.parents):
			if (parent / "config" / "cresus.yml").exists():
				return parent

		# Default to project directory
		return Path(__file__).parent.parent.parent

	def _setup_history(self):
		"""Setup command history."""
		history_file = Path.home() / ".cresus" / "history"
		self.history_file = str(history_file)

	def _setup_prompt(self):
		"""Setup CLI prompt."""
		self.prompt = "cresus> "

	def _print_intro(self):
		"""Print welcome banner."""
		banner = Panel(
			Text("Cresus CLI v2.0.0\nRefactored Portfolio Management", justify="center", style="bold cyan"),
			style="cyan",
			box=box.DOUBLE
		)
		console.print(banner)
		console.print(f"\n[dim]Project Root:[/dim] {self.project_root}")
		console.print("[dim]Type 'help' for commands, 'quit' to exit[/dim]\n")

	def default(self, args: str):
		"""Route command to appropriate handler.

		Args:
			args: Full command line with command name and arguments
		"""
		if not args or not args.strip():
			return

		# Parse command
		parts = args.split(None, 1)
		cmd_name = parts[0]
		cmd_args = parts[1] if len(parts) > 1 else ""

		# Route to command handler
		if cmd_name not in self.commands:
			Formatter.error(f"Unknown command: {cmd_name}")
			return

		try:
			cmd = self.commands[cmd_name]
			result = cmd.handle(cmd_args)

			# Result already printed by command, but we can handle here if needed
			if not result.success and not cmd_args:
				# Show help if no args
				pass

		except Exception as e:
			Formatter.error(f"Unexpected error: {e}")

	def do_help(self, args: str):
		"""Show help for commands.

		Usage:
			help              Show all commands
			help <command>    Show help for specific command
		"""
		if args:
			cmd_name = args.split()[0]
			if cmd_name in self.commands:
				cmd = self.commands[cmd_name]
				help_text = cmd.__class__.__doc__ or f"Help for {cmd_name}"
				Formatter.panel(help_text, title=f"Command: {cmd_name}")
			else:
				Formatter.error(f"Unknown command: {cmd_name}")
			return

		# Show all commands
		console.print("\n[bold cyan]Available Commands:[/bold cyan]\n")
		for cmd_name, cmd in sorted(self.commands.items()):
			# Get first line of docstring
			doc = (cmd.__class__.__doc__ or "").split("\n")[0]
			console.print(f"  [cyan]{cmd_name:<15}[/cyan] {doc}")
		console.print()

	def do_history(self, args: str):
		"""Show command history."""
		if hasattr(self, 'history_file') and Path(self.history_file).exists():
			with open(self.history_file, 'r') as f:
				lines = f.readlines()
			Formatter.list_items(lines[-20:], title="Recent Commands (Last 20)", numbered=True)
		else:
			Formatter.info("No command history")

	def do_status(self, _):
		"""Show system status."""
		data = {
			"Project Root": str(self.project_root),
			"Interactive": str(self.interactive),
			"Available Commands": str(len(self.commands)),
		}
		table = Formatter.key_value_table(data, title="System Status")
		console.print(table)

	def do_info(self, _):
		"""Show system information."""
		Formatter.panel(
			"Cresus CLI v2.0.0 (Refactored)\n\n"
			"Features:\n"
			"• Simplified command routing\n"
			"• Consistent command structure\n"
			"• Improved error handling\n"
			"• Better code organization\n",
			title="System Information",
			style="blue"
		)

	def do_quit(self, _):
		"""Exit CLI."""
		console.print("[cyan]Goodbye![/cyan]")
		return True

	do_exit = do_quit  # Alias


def main():
	"""CLI entry point."""
	import sys

	# Non-interactive mode: single command
	if len(sys.argv) > 1:
		app = CresusCLI(interactive=False)
		command = " ".join(sys.argv[1:])
		app.onecmd(command)
		return 0

	# Interactive mode
	app = CresusCLI(interactive=True)
	return app.cmdloop()


if __name__ == "__main__":
	import sys
	sys.exit(main())
