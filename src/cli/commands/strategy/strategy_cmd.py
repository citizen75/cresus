"""Strategy management command - refactored."""

from pathlib import Path
from typing import Optional

from src.cli.base import BaseCommand, CommandResult, ValidationError
from src.cli.utils import ArgParser, Formatter, Validator


class StrategyCommand(BaseCommand):
	"""Manage strategies - validate, edit, duplicate, check indicators.

	Subcommands:
		list                            List all available strategies
		check <name> [--fix] [--template]
		                                Check strategy compliance
		edit <name> [--editor]          Edit strategy config
		duplicate <from> <to>           Duplicate a strategy
		show <name>                     Show strategy details
	"""

	def __init__(self, project_root: Optional[Path] = None):
		"""Initialize strategy command."""
		super().__init__()
		self.project_root = project_root or Path.cwd()
		self._load_tools()

	def _load_tools(self):
		"""Load strategy management tools."""
		try:
			from tools.strategy.strategy import StrategyManager
			from tools.strategy.validator import StrategyValidator
			from tools.indicators import IndicatorChecker

			self.strategy_manager = StrategyManager()
			self.validator = StrategyValidator()
			self.checker = IndicatorChecker()
			self.tools_available = True
		except ImportError:
			self.strategy_manager = None
			self.validator = None
			self.checker = None
			self.tools_available = False

	def handle(self, args: str) -> CommandResult:
		"""Handle strategy command."""
		try:
			if not self.tools_available:
				return self._error("Strategy tools not available", error_type="error")

			subcommand, subargs = ArgParser.extract_subcommand(args)

			if not subcommand:
				return self._cmd_list("")

			cmd_map = {
				"list": self._cmd_list,
				"check": self._cmd_check,
				"edit": self._cmd_edit,
				"duplicate": self._cmd_duplicate,
				"show": self._cmd_show,
			}

			if subcommand not in cmd_map:
				return self._error(f"Unknown strategy subcommand: {subcommand}", error_type="usage")

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
		"""List all available strategies."""
		try:
			strategies = self.strategy_manager.list_strategies()

			if not strategies:
				return self._success("No strategies found")

			# Build display data
			data = []
			for strategy_name in sorted(strategies):
				try:
					result = self.strategy_manager.load_strategy(strategy_name)
					if result.get("status") == "success":
						strategy_data = result.get("data", {})
						data.append({
							"name": strategy_name,
							"universe": strategy_data.get("universe", "-"),
							"indicators": str(len(strategy_data.get("indicators", []))),
							"description": (strategy_data.get("description", "-")[:40] + "...") if len(str(strategy_data.get("description", "-"))) > 40 else strategy_data.get("description", "-"),
						})
				except:
					pass

			if data:
				table = Formatter.table(
					data,
					title="Strategies",
					columns={
						"name": "Name",
						"universe": "Universe",
						"indicators": "Indicators",
						"description": "Description",
					}
				)
				self.console.print(table)

			return self._success(f"Found {len(strategies)} strategy(ies)")

		except Exception as e:
			return self._error(f"Error listing strategies: {e}", error_type="error")

	def _cmd_check(self, args: str) -> CommandResult:
		"""Check strategy compliance."""
		try:
			# Parse arguments
			flag_spec = {"--fix": "bool", "--template": "bool"}
			parsed = ArgParser.parse_with_flags(args, flag_spec, positional=["name"])

			strategy_name = parsed.get("name")
			if not strategy_name:
				return self._error("Usage: strategy check <name> [--fix] [--template]", error_type="usage")

			fix = parsed.get("--fix", False)
			template = parsed.get("--template", False)

			if template:
				return self._show_template()

			# Load strategy
			result = self.strategy_manager.load_strategy(strategy_name)
			if result.get("status") != "success":
				return self._error(f"Failed to load strategy: {result.get('message')}", error_type="not_found")

			strategy_data = result.get("data", {})

			# Validate
			validation_result = self.strategy_manager.validate_against_template(strategy_name)
			errors = validation_result.get("errors", [])
			warnings = validation_result.get("warnings", [])

			# Validate formulas
			formula_errors, invalid_formulas = self.validator.validate_formulas(strategy_data)
			errors.extend(formula_errors)

			# Extract and validate indicators
			extracted_indicators = self.validator.extract_indicators_from_strategy(strategy_data)
			declared_indicators = set(strategy_data.get("indicators", []))

			# Filter data fields
			data_fields = {'open', 'high', 'low', 'close', 'volume', 'timestamp', 'ticker', 'date'}
			extracted_filtered = extracted_indicators - data_fields
			missing_indicators = extracted_filtered - declared_indicators

			# Indicator validation
			indicator_validation = self.validator.validate_all_indicators(strategy_data)
			declared_errors = indicator_validation.get("declared_errors", [])
			extracted_errors = indicator_validation.get("extracted_errors", [])

			# Filter data field errors
			declared_errors = [e for e in declared_errors if not any(f in e.lower() for f in data_fields)]
			extracted_errors = [e for e in extracted_errors if not any(f in e.lower() for f in data_fields)]

			all_errors = errors + declared_errors + extracted_errors
			is_valid = len(all_errors) == 0

			# Apply fixes if requested
			if fix and not is_valid:
				fix_result = self._apply_fixes(strategy_name, strategy_data, declared_indicators, missing_indicators)
				if fix_result:
					return self._success(f"Strategy fixed: {fix_result}")

			# Display results
			summary_data = {
				"Strategy": strategy_name,
				"Universe": strategy_data.get("universe", "-"),
				"Indicators": str(len(declared_indicators)),
				"Status": "✓ Valid" if is_valid else "✗ Invalid",
				"Errors": str(len(all_errors)),
				"Warnings": str(len(warnings)),
			}

			table = Formatter.key_value_table(summary_data, title="Strategy Check")
			self.console.print(table)

			if all_errors:
				error_data = [{"error": e} for e in all_errors[:10]]
				error_table = Formatter.table(
					error_data,
					title=f"Errors (showing {len(error_data)} of {len(all_errors)})",
					columns={"error": "Issue"}
				)
				self.console.print(error_table)

			if warnings:
				Formatter.warning(f"{len(warnings)} warning(s) found")

			return self._success("Check completed")

		except Exception as e:
			return self._error(f"Check error: {str(e)}", error_type="error")

	def _cmd_edit(self, args: str) -> CommandResult:
		"""Edit a strategy."""
		try:
			flag_spec = {"--editor": "bool"}
			parsed = ArgParser.parse_with_flags(args, flag_spec, positional=["name"])

			strategy_name = parsed.get("name")
			if not strategy_name:
				return self._error("Usage: strategy edit <name> [--editor]", error_type="usage")

			use_editor = parsed.get("--editor", False)

			# Load strategy
			result = self.strategy_manager.load_strategy(strategy_name)
			if result.get("status") != "success":
				return self._error(f"Strategy not found: {strategy_name}", error_type="not_found")

			if use_editor:
				return self._edit_in_editor(strategy_name)
			else:
				return self._success(f"Edit wizard for '{strategy_name}' - manual editing required")

		except Exception as e:
			return self._error(f"Edit error: {str(e)}", error_type="error")

	def _cmd_duplicate(self, args: str) -> CommandResult:
		"""Duplicate a strategy."""
		try:
			parsed = ArgParser.parse_positional(args, ["from_name", "to_name"])
			from_name = parsed["from_name"]
			to_name = parsed["to_name"]
		except ValidationError as e:
			return self._error(f"Usage: strategy duplicate <from> <to>\n{str(e)}", error_type="usage")

		try:
			# Load source
			result = self.strategy_manager.load_strategy(from_name)
			if result.get("status") != "success":
				return self._error(f"Source strategy not found: {from_name}", error_type="not_found")

			# Check destination doesn't exist
			dest_check = self.strategy_manager.load_strategy(to_name)
			if dest_check.get("status") == "success":
				return self._error(f"Destination strategy already exists: {to_name}", error_type="conflict")

			# Duplicate
			strategy_data = result.get("data", {})
			strategy_data["name"] = to_name

			save_result = self.strategy_manager.save_strategy(to_name, strategy_data)
			if save_result.get("status") == "success":
				return self._success(f"Duplicated '{from_name}' to '{to_name}'")
			else:
				return self._error(f"Failed to save: {save_result.get('message')}", error_type="error")

		except Exception as e:
			return self._error(f"Duplicate error: {str(e)}", error_type="error")

	def _cmd_show(self, args: str) -> CommandResult:
		"""Show strategy details."""
		try:
			parsed = ArgParser.parse_positional(args, ["name"])
			strategy_name = parsed["name"]
		except ValidationError as e:
			return self._error(f"Usage: strategy show <name>\n{str(e)}", error_type="usage")

		try:
			result = self.strategy_manager.load_strategy(strategy_name)
			if result.get("status") != "success":
				return self._error(f"Strategy not found: {strategy_name}", error_type="not_found")

			strategy_data = result.get("data", {})

			# Display summary
			summary_data = {
				"Name": strategy_data.get("name", "-"),
				"Universe": strategy_data.get("universe", "-"),
				"Description": strategy_data.get("description", "-"),
				"Indicators": str(len(strategy_data.get("indicators", []))),
			}

			table = Formatter.key_value_table(summary_data, title=f"Strategy: {strategy_name}")
			self.console.print(table)

			# Display indicators if any
			indicators = strategy_data.get("indicators", [])
			if indicators:
				ind_data = [{"indicator": ind} for ind in indicators]
				ind_table = Formatter.table(
					ind_data,
					title="Indicators",
					columns={"indicator": "Name"}
				)
				self.console.print(ind_table)

			return self._success("Strategy details displayed")

		except Exception as e:
			return self._error(f"Show error: {str(e)}", error_type="error")

	def _apply_fixes(self, strategy_name: str, strategy_data: dict, declared: set, missing: set) -> Optional[str]:
		"""Apply automatic fixes to strategy."""
		changes = []

		# Remove data fields from indicators
		data_fields = {'open', 'high', 'low', 'close', 'volume', 'timestamp', 'ticker', 'date'}
		indicators = strategy_data.get("indicators", [])
		indicators_in_data = [i for i in indicators if i.lower() in data_fields]

		if indicators_in_data:
			new_indicators = [i for i in indicators if i.lower() not in data_fields]
			strategy_data["indicators"] = new_indicators
			changes.append(f"Removed {len(indicators_in_data)} data field(s)")

		# Add missing valid indicators
		if missing:
			valid_missing = []
			for ind in missing:
				try:
					ind_result = self.checker.check(ind, verbose=False)
					if isinstance(ind_result, dict):
						ind_result = list(ind_result.values())[0]
					if hasattr(ind_result, 'exists') and ind_result.exists:
						valid_missing.append(ind)
				except:
					pass

			if valid_missing:
				new_indicators = strategy_data.get("indicators", []) + valid_missing
				new_indicators = sorted(list(set(new_indicators)))
				strategy_data["indicators"] = new_indicators
				changes.append(f"Added {len(valid_missing)} missing indicator(s)")

		# Save if changes made
		if changes:
			save_result = self.strategy_manager.save_strategy(strategy_name, strategy_data)
			if save_result.get("status") == "success":
				return ", ".join(changes)

		return None

	def _edit_in_editor(self, strategy_name: str) -> CommandResult:
		"""Open strategy in $EDITOR."""
		import subprocess
		import os

		try:
			editor = os.environ.get("EDITOR", "nano")
			strategy_file = self.strategy_manager._get_strategy_file(strategy_name)

			# Open editor
			subprocess.run([editor, str(strategy_file)], check=False)

			# Validate after edit
			validation = self.strategy_manager.validate_against_template(strategy_name)
			errors = validation.get("errors", [])

			if errors:
				return self._success(f"Strategy edited with {len(errors)} validation issue(s) - review required")
			else:
				return self._success(f"Strategy edited successfully")

		except Exception as e:
			return self._error(f"Editor error: {str(e)}", error_type="error")

	def _show_template(self) -> CommandResult:
		"""Show strategy template."""
		import yaml

		try:
			template_path = self.project_root / "init" / "templates" / "strategy.yml"
			if not template_path.exists():
				template_path = self.project_root / "src" / "config" / "template.yml"

			if template_path.exists():
				with open(template_path, 'r') as f:
					content = f.read()
				Formatter.panel(content, title="Strategy Template")
				return self._success("Template displayed")
			else:
				return self._error("Template file not found", error_type="not_found")

		except Exception as e:
			return self._error(f"Template error: {str(e)}", error_type="error")

	def _print_result(self, result: CommandResult):
		"""Print command result."""
		if result.success:
			Formatter.success(result.message)
		else:
			Formatter.error(result.message)
