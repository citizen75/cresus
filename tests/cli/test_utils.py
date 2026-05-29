"""Tests for CLI utilities."""

import pytest

from src.cli.utils import ArgParser, Formatter, Validator, ValidationError


class TestArgParser:
	"""Test argument parsing utilities."""

	def test_parse_positional_basic(self):
		"""Test basic positional argument parsing."""
		result = ArgParser.parse_positional("foo bar baz", ["name", "value", "extra"])
		assert result["name"] == "foo"
		assert result["value"] == "bar"
		assert result["extra"] == "baz"

	def test_parse_positional_missing_required(self):
		"""Test error when required arguments missing."""
		with pytest.raises(ValidationError, match="Missing required"):
			ArgParser.parse_positional("foo", ["name", "value"])

	def test_parse_positional_optional(self):
		"""Test optional positional arguments."""
		result = ArgParser.parse_positional("foo", ["name", "value"], optional=["value"])
		assert result["name"] == "foo"
		assert result["value"] is None

	def test_parse_with_flags_bool(self):
		"""Test parsing boolean flags."""
		result = ArgParser.parse_with_flags("--force", {"--force": "bool"})
		assert result["--force"] is True

	def test_parse_with_flags_string(self):
		"""Test parsing string flags."""
		result = ArgParser.parse_with_flags("--name foo", {"--name": "str"})
		assert result["--name"] == "foo"

	def test_parse_with_flags_int(self):
		"""Test parsing integer flags."""
		result = ArgParser.parse_with_flags("--count 42", {"--count": "int"})
		assert result["--count"] == 42

	def test_parse_with_flags_missing_value(self):
		"""Test error when flag value missing."""
		with pytest.raises(ValidationError, match="requires a value"):
			ArgParser.parse_with_flags("--name", {"--name": "str"})

	def test_extract_subcommand(self):
		"""Test extracting subcommand."""
		cmd, args = ArgParser.extract_subcommand("list --limit 10")
		assert cmd == "list"
		assert args == "--limit 10"

	def test_extract_subcommand_empty(self):
		"""Test extracting subcommand from empty string."""
		cmd, args = ArgParser.extract_subcommand("")
		assert cmd is None
		assert args == ""

	def test_parse_comma_separated(self):
		"""Test parsing comma-separated values."""
		result = ArgParser.parse_comma_separated("foo, bar, baz")
		assert result == ["foo", "bar", "baz"]

	def test_parse_comma_separated_no_strip(self):
		"""Test comma-separated without stripping."""
		result = ArgParser.parse_comma_separated("foo, bar", strip=False)
		assert result[0] == "foo"
		assert result[1] == " bar"


class TestValidator:
	"""Test input validation utilities."""

	def test_is_valid_date(self):
		"""Test date validation."""
		assert Validator.is_valid_date("2025-01-15")
		assert not Validator.is_valid_date("2025-13-01")
		assert not Validator.is_valid_date("invalid")

	def test_is_valid_ticker(self):
		"""Test ticker validation."""
		assert Validator.is_valid_ticker("AAPL")
		assert Validator.is_valid_ticker("TTE.PA")
		assert not Validator.is_valid_ticker("aapl")  # lowercase
		assert not Validator.is_valid_ticker("A")  # too short in symbol part
		assert not Validator.is_valid_ticker("AAPL.USA")  # exchange too long

	def test_is_valid_identifier(self):
		"""Test identifier validation."""
		assert Validator.is_valid_identifier("my_screener")
		assert Validator.is_valid_identifier("_private")
		assert not Validator.is_valid_identifier("123invalid")  # starts with number
		assert not Validator.is_valid_identifier("invalid-name")  # hyphen not allowed

	def test_is_valid_percentage(self):
		"""Test percentage validation."""
		assert Validator.is_valid_percentage("0")
		assert Validator.is_valid_percentage("50")
		assert Validator.is_valid_percentage("100")
		assert not Validator.is_valid_percentage("-1")
		assert not Validator.is_valid_percentage("101")

	def test_is_positive_number(self):
		"""Test positive number validation."""
		assert Validator.is_positive_number("1")
		assert Validator.is_positive_number("0.5")
		assert not Validator.is_positive_number("0")
		assert not Validator.is_positive_number("-1")

	def test_is_valid_formula(self):
		"""Test formula validation."""
		assert Validator.is_valid_formula("rsi_14 > 50")
		assert Validator.is_valid_formula("rsi_14 > 50 && rsi_7 < 70")
		assert not Validator.is_valid_formula("")  # empty
		assert not Validator.is_valid_formula("no_operators")
		assert not Validator.is_valid_formula("unbalanced[bracket")

	def test_validate_required_string(self):
		"""Test required string validation."""
		is_valid, error = Validator.validate_required_string("foo")
		assert is_valid
		assert error is None

		is_valid, error = Validator.validate_required_string("")
		assert not is_valid
		assert "required" in error.lower()

	def test_validate_choice(self):
		"""Test choice validation."""
		is_valid, error = Validator.validate_choice("foo", ["foo", "bar"])
		assert is_valid

		is_valid, error = Validator.validate_choice("baz", ["foo", "bar"])
		assert not is_valid
		assert "must be one of" in error

	def test_validate_range(self):
		"""Test range validation."""
		is_valid, error = Validator.validate_range("50", min_val=0, max_val=100)
		assert is_valid

		is_valid, error = Validator.validate_range("-1", min_val=0)
		assert not is_valid

		is_valid, error = Validator.validate_range("101", max_val=100)
		assert not is_valid

	def test_validate_length(self):
		"""Test length validation."""
		is_valid, error = Validator.validate_length("hello", min_len=3, max_len=10)
		assert is_valid

		is_valid, error = Validator.validate_length("hi", min_len=3)
		assert not is_valid

		is_valid, error = Validator.validate_length("verylongstring", max_len=10)
		assert not is_valid


class TestFormatter:
	"""Test output formatting utilities."""

	def test_table_creation(self):
		"""Test table creation."""
		data = [{"name": "foo", "value": "1"}]
		table = Formatter.table(data, title="Test")
		assert table is not None

	def test_key_value_table(self):
		"""Test key-value table creation."""
		data = {"Key1": "Value1", "Key2": "Value2"}
		table = Formatter.key_value_table(data, title="Test")
		assert table is not None

	def test_parse_comma_separated_empty(self):
		"""Test parsing comma-separated with empty items."""
		result = ArgParser.parse_comma_separated("foo,,bar")
		assert result == ["foo", "bar"]  # Empty items filtered out
