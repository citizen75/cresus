"""Output formatting utilities for consistent CLI styling."""

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .constants import (
	BOX_STYLE_DEFAULT,
	BOX_STYLE_TITLE,
	COLUMN_STYLE_KEY,
	COLUMN_STYLE_VALUE,
	PREFIX_ERROR,
	PREFIX_SUCCESS,
	PREFIX_WARNING,
	STYLE_ERROR,
	STYLE_SUCCESS,
	STYLE_WARNING,
)

console = Console()


class Formatter:
	"""Unified formatting utilities for CLI output."""

	@staticmethod
	def table(
		data: List[Dict[str, Any]],
		title: str = "",
		columns: Optional[Dict[str, str]] = None,
		key_style: str = COLUMN_STYLE_KEY,
		value_style: str = COLUMN_STYLE_VALUE,
	) -> Table:
		"""Create a formatted table from data.

		Args:
			data: List of dictionaries to display
			title: Table title
			columns: Dict mapping data keys to display names
			key_style: Style for key column
			value_style: Style for value columns

		Returns:
			Configured Rich Table
		"""
		table = Table(title=title, box=BOX_STYLE_TITLE)

		if not data:
			return table

		# Use provided columns or infer from first row
		cols = columns or data[0].keys()

		# Add columns
		for i, (key, display_name) in enumerate(cols.items() if isinstance(cols, dict) else [(c, c) for c in cols]):
			style = key_style if i == 0 else value_style
			table.add_column(display_name, style=style)

		# Add rows
		for row in data:
			values = [str(row.get(key, "-")) for key in (cols.keys() if isinstance(cols, dict) else cols)]
			table.add_row(*values)

		return table

	@staticmethod
	def key_value_table(
		data: Dict[str, Any],
		title: str = "",
	) -> Table:
		"""Create a key-value table.

		Args:
			data: Dictionary to display
			title: Table title

		Returns:
			Configured Rich Table
		"""
		table = Table(title=title, box=BOX_STYLE_TITLE)
		table.add_column("Property", style=COLUMN_STYLE_KEY)
		table.add_column("Value", style=COLUMN_STYLE_VALUE)

		for key, value in data.items():
			table.add_row(key, str(value))

		return table

	@staticmethod
	def success(message: str, prefix: bool = True):
		"""Print success message.

		Args:
			message: Message to print
			prefix: Whether to add success prefix
		"""
		if prefix:
			console.print(f"[{STYLE_SUCCESS}]{PREFIX_SUCCESS}[/] {message}")
		else:
			console.print(f"[{STYLE_SUCCESS}]{message}[/]")

	@staticmethod
	def error(message: str, prefix: bool = True):
		"""Print error message.

		Args:
			message: Message to print
			prefix: Whether to add error prefix
		"""
		if prefix:
			console.print(f"[{STYLE_ERROR}]{PREFIX_ERROR}[/] {message}")
		else:
			console.print(f"[{STYLE_ERROR}]{message}[/]")

	@staticmethod
	def warning(message: str, prefix: bool = True):
		"""Print warning message.

		Args:
			message: Message to print
			prefix: Whether to add warning prefix
		"""
		if prefix:
			console.print(f"[{STYLE_WARNING}]{PREFIX_WARNING}[/] {message}")
		else:
			console.print(f"[{STYLE_WARNING}]{message}[/]")

	@staticmethod
	def info(message: str):
		"""Print info message."""
		console.print(f"[blue]ℹ[/] {message}")

	@staticmethod
	def list_items(items: List[str], title: str = "", numbered: bool = False):
		"""Print formatted list.

		Args:
			items: List of items to display
			title: Optional list title
			numbered: Whether to number items
		"""
		if title:
			console.print(f"\n[bold cyan]{title}[/]\n")

		for i, item in enumerate(items, 1):
			prefix = f"{i}. " if numbered else "• "
			console.print(f"  {prefix}{item}")

	@staticmethod
	def panel(content: str, title: str = "", style: str = "cyan"):
		"""Print paneled content.

		Args:
			content: Content to display
			title: Optional panel title
			style: Panel style
		"""
		panel = Panel(content, title=title, style=style)
		console.print(panel)

	@staticmethod
	def section(title: str):
		"""Print section header.

		Args:
			title: Section title
		"""
		console.print(f"\n[bold cyan]{title}[/cyan]")
		console.print("[cyan]" + "─" * len(title) + "[/cyan]\n")
