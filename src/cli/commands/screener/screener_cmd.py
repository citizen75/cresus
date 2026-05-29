"""Screener management command - refactored."""

from typing import Optional

from src.cli.base import BaseCommand, CommandResult, ValidationError
from src.cli.utils import ArgParser, Formatter, Validator
from src.tools.screener import ScreenerConfig, ScreenerManager


class ScreenerCommand(BaseCommand):
	"""Manage screeners - create, list, run, and view results.

	Subcommands:
		list                        List all screeners
		info <name>                 Show screener details
		create <name> <formula> <indicators> [options]
		delete <name>
		run <name>
		results <name>
		result-show <name> <result_id>
		result-delete <name> <result_id>
		clear-results <name>
		export <name> <result_id> <path>
	"""

	def __init__(self):
		"""Initialize screener command."""
		super().__init__()
		self.manager = ScreenerManager()

	def handle(self, args: str) -> CommandResult:
		"""Handle screener command."""
		try:
			subcommand, subargs = ArgParser.extract_subcommand(args)

			if not subcommand:
				return self._cmd_list("")

			# Route to subcommand
			cmd_map = {
				"list": self._cmd_list,
				"info": self._cmd_info,
				"create": self._cmd_create,
				"delete": self._cmd_delete,
				"run": self._cmd_run,
				"results": self._cmd_results,
				"result-show": self._cmd_result_show,
				"result-delete": self._cmd_result_delete,
				"clear-results": self._cmd_clear_results,
				"export": self._cmd_export,
			}

			if subcommand not in cmd_map:
				return self._error(f"Unknown screener subcommand: {subcommand}")

			result = cmd_map[subcommand](subargs)
			self._print_result(result)
			return result

		except ValidationError as e:
			result = self._error(str(e), error_type="validation")
			self._print_result(result)
			return result
		except Exception as e:
			result = self._error(f"Unexpected error: {e}", error_type="error")
			self._print_result(result)
			return result

	def _cmd_list(self, args: str) -> CommandResult:
		"""List all screeners."""
		screeners = self.manager.list_screeners()

		if not screeners:
			return self._success("No screeners found")

		# Build display data
		data = []
		for name in screeners:
			config = self.manager.get_screener(name)
			if config:
				data.append({
					"name": name,
					"source": config.source or "Custom",
					"indicators": ", ".join(config.indicators[:2]) + ("..." if len(config.indicators) > 2 else ""),
					"description": (config.description[:40] + "...") if config.description and len(config.description) > 40 else config.description or "-",
				})

		table = Formatter.table(
			data,
			title="Screeners",
			columns={"name": "Name", "source": "Source", "indicators": "Indicators", "description": "Description"}
		)
		self.console.print(table)
		return self._success(f"Found {len(screeners)} screener(s)")

	def _cmd_info(self, args: str) -> CommandResult:
		"""Show screener information."""
		try:
			parsed = ArgParser.parse_positional(args, ["name"])
			name = parsed["name"]
		except ValidationError as e:
			return self._error(f"Usage: screener info <name>\n{str(e)}", error_type="usage")

		config = self.manager.get_screener(name)
		if not config:
			return self._error(f"Screener '{name}' not found", error_type="not_found")

		# Display configuration
		config_data = {
			"Name": config.name,
			"Source": config.source or "Custom",
			"Tickers": ", ".join(config.tickers) if config.tickers else "-",
			"Indicators": ", ".join(config.indicators),
			"Formula": config.formula,
			"Description": config.description or "-",
		}

		table = Formatter.key_value_table(config_data, title=f"Screener: {name}")
		self.console.print(table)

		# Show recent results
		results = self.manager.list_results(name)
		if results:
			Formatter.section("Recent Results")
			results_data = []
			for result_id, timestamp in results[:5]:
				result_data = self.manager.get_result(name, result_id)
				match_count = len(result_data) if result_data else 0
				results_data.append({
					"id": result_id,
					"timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
					"matches": str(match_count),
				})

			table = Formatter.table(
				results_data,
				columns={"id": "Result ID", "timestamp": "Timestamp", "matches": "Matches"}
			)
			self.console.print(table)

		return self._success(f"Screener '{name}' information displayed")

	def _cmd_create(self, args: str) -> CommandResult:
		"""Create new screener."""
		try:
			parsed = ArgParser.parse_positional(args, ["name", "formula", "indicators"])
			name = parsed["name"]
			formula = parsed["formula"]
			indicators_str = parsed["indicators"]
		except ValidationError as e:
			return self._error(
				f"Usage: screener create <name> <formula> <indicators>\n{str(e)}",
				error_type="usage"
			)

		# Validate name
		if not Validator.is_valid_identifier(name):
			return self._error(f"Invalid screener name: {name}", error_type="validation")

		# Parse indicators
		try:
			indicators = ArgParser.parse_comma_separated(indicators_str)
		except ValidationError as e:
			return self._error(f"Invalid indicators: {str(e)}", error_type="validation")

		# Create config (use cac40 as default source)
		config = ScreenerConfig(
			name=name,
			source="cac40",
			indicators=indicators,
			formula=formula,
			description=""
		)

		success, message = self.manager.create_screener(config)
		return self._success(message) if success else self._error(message, error_type="conflict")

	def _cmd_delete(self, args: str) -> CommandResult:
		"""Delete screener."""
		try:
			parsed = ArgParser.parse_positional(args, ["name"])
			name = parsed["name"]
		except ValidationError as e:
			return self._error(f"Usage: screener delete <name>\n{str(e)}", error_type="usage")

		success, message = self.manager.delete_screener(name)
		return self._success(message) if success else self._error(message, error_type="not_found")

	def _cmd_run(self, args: str) -> CommandResult:
		"""Run screener."""
		try:
			parsed = ArgParser.parse_positional(args, ["name"])
			name = parsed["name"]
		except ValidationError as e:
			return self._error(f"Usage: screener run <name>\n{str(e)}", error_type="usage")

		config = self.manager.get_screener(name)
		if not config:
			return self._error(f"Screener '{name}' not found", error_type="not_found")

		message = f"Screener '{name}' execution delegated to BacktestAgent\nSource: {config.source or 'Custom'}\nFormula: {config.formula}"
		return self._success(message)

	def _cmd_results(self, args: str) -> CommandResult:
		"""List screener results."""
		try:
			parsed = ArgParser.parse_positional(args, ["name"])
			name = parsed["name"]
		except ValidationError as e:
			return self._error(f"Usage: screener results <name>\n{str(e)}", error_type="usage")

		config = self.manager.get_screener(name)
		if not config:
			return self._error(f"Screener '{name}' not found", error_type="not_found")

		results = self.manager.list_results(name)
		if not results:
			return self._success(f"No results for screener '{name}'")

		data = []
		for result_id, timestamp in results:
			result_data = self.manager.get_result(name, result_id)
			match_count = len(result_data) if result_data else 0
			data.append({
				"id": result_id,
				"timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
				"matches": str(match_count),
			})

		table = Formatter.table(
			data,
			title=f"Results for: {name}",
			columns={"id": "Result ID", "timestamp": "Timestamp", "matches": "Matches"}
		)
		self.console.print(table)
		return self._success(f"Found {len(results)} result(s)")

	def _cmd_result_show(self, args: str) -> CommandResult:
		"""Show specific result."""
		try:
			parsed = ArgParser.parse_positional(args, ["name", "result_id"])
			name = parsed["name"]
			result_id = parsed["result_id"]
		except ValidationError as e:
			return self._error(
				f"Usage: screener result-show <name> <result_id>\n{str(e)}",
				error_type="usage"
			)

		result_data = self.manager.get_result(name, result_id)
		if not result_data:
			return self._error(f"Result '{result_id}' not found", error_type="not_found")

		if not result_data:
			return self._success("Result: No matches")

		# Limit display to 100 rows
		display_data = result_data[:100]
		table = Formatter.table(
			display_data,
			title=f"Result: {result_id}"
		)
		self.console.print(table)
		return self._success(f"Showing {len(display_data)} of {len(result_data)} rows")

	def _cmd_result_delete(self, args: str) -> CommandResult:
		"""Delete result."""
		try:
			parsed = ArgParser.parse_positional(args, ["name", "result_id"])
			name = parsed["name"]
			result_id = parsed["result_id"]
		except ValidationError as e:
			return self._error(
				f"Usage: screener result-delete <name> <result_id>\n{str(e)}",
				error_type="usage"
			)

		success, message = self.manager.delete_result(name, result_id)
		return self._success(message) if success else self._error(message, error_type="not_found")

	def _cmd_clear_results(self, args: str) -> CommandResult:
		"""Clear all results."""
		try:
			parsed = ArgParser.parse_positional(args, ["name"])
			name = parsed["name"]
		except ValidationError as e:
			return self._error(f"Usage: screener clear-results <name>\n{str(e)}", error_type="usage")

		success, message = self.manager.clear_results(name)
		return self._success(message) if success else self._error(message)

	def _cmd_export(self, args: str) -> CommandResult:
		"""Export result to file."""
		try:
			parsed = ArgParser.parse_positional(args, ["name", "result_id", "path"])
			name = parsed["name"]
			result_id = parsed["result_id"]
			path = parsed["path"]
		except ValidationError as e:
			return self._error(
				f"Usage: screener export <name> <result_id> <path>\n{str(e)}",
				error_type="usage"
			)

		try:
			import shutil
			source = self.manager._get_results_dir(name) / f"{result_id}.csv"
			if not source.exists():
				return self._error(f"Result '{result_id}' not found", error_type="not_found")

			shutil.copy(source, path)
			return self._success(f"Exported to {path}")
		except Exception as e:
			return self._error(f"Export failed: {e}", error_type="error")

	def _print_result(self, result: CommandResult):
		"""Print command result."""
		if result.success:
			Formatter.success(result.message)
		else:
			Formatter.error(result.message)
