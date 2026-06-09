"""Tests for shell execution flow."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import subprocess

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from flows.shell_exec import ShellExecFlow


class TestShellExecFlowInitialization:
	"""Test cases for ShellExecFlow initialization."""

	def test_shell_exec_flow_initialization(self):
		"""Test that ShellExecFlow can be initialized."""
		flow = ShellExecFlow()
		assert flow.name == "ShellExecFlow"
		assert flow.context is not None

	def test_shell_exec_flow_has_logger(self):
		"""Test that ShellExecFlow has a logger instance."""
		flow = ShellExecFlow()
		assert flow.logger is not None


class TestShellExecFlowAllowedCommands:
	"""Test cases for command allowlisting."""

	@patch("flows.shell_exec.subprocess.run")
	def test_cresus_command_allowed(self, mock_run):
		"""Test that cresus commands are allowed."""
		mock_run.return_value.returncode = 0
		mock_run.return_value.stdout = "output"
		mock_run.return_value.stderr = ""

		flow = ShellExecFlow()
		result = flow.process({
			"command": "cresus data fetch cac40"
		})

		assert result["status"] == "success"
		mock_run.assert_called_once()

	@patch("flows.shell_exec.subprocess.run")
	def test_python_command_allowed(self, mock_run):
		"""Test that python commands are allowed."""
		mock_run.return_value.returncode = 0
		mock_run.return_value.stdout = "output"
		mock_run.return_value.stderr = ""

		flow = ShellExecFlow()
		result = flow.process({
			"command": "python script.py"
		})

		assert result["status"] == "success"
		mock_run.assert_called_once()

	@patch("flows.shell_exec.subprocess.run")
	def test_env_python_command_allowed(self, mock_run):
		"""Test that /usr/bin/env python commands are allowed."""
		mock_run.return_value.returncode = 0
		mock_run.return_value.stdout = "output"
		mock_run.return_value.stderr = ""

		flow = ShellExecFlow()
		result = flow.process({
			"command": "/usr/bin/env python -m pytest"
		})

		assert result["status"] == "success"
		mock_run.assert_called_once()

	def test_unauthorized_command_blocked(self):
		"""Test that unauthorized commands are blocked."""
		flow = ShellExecFlow()
		result = flow.process({
			"command": "rm -rf /"
		})

		assert result["status"] == "error"
		assert "not allowed" in result["error"].lower()

	def test_curl_command_blocked(self):
		"""Test that raw curl commands are blocked."""
		flow = ShellExecFlow()
		result = flow.process({
			"command": "curl http://api.example.com"
		})

		assert result["status"] == "error"
		assert "not allowed" in result["error"].lower()


class TestShellExecFlowSuccess:
	"""Test cases for successful command execution."""

	@patch("flows.shell_exec.subprocess.run")
	def test_successful_command(self, mock_run):
		"""Test successful command execution."""
		mock_run.return_value.returncode = 0
		mock_run.return_value.stdout = "command output"
		mock_run.return_value.stderr = ""

		flow = ShellExecFlow()
		result = flow.process({
			"command": "cresus data fetch cac40"
		})

		assert result["status"] == "success"
		assert result["return_code"] == 0
		assert result["stdout"] == "command output"
		assert result["stderr"] == ""

	@patch("flows.shell_exec.subprocess.run")
	def test_command_with_output(self, mock_run):
		"""Test command that produces output."""
		mock_run.return_value.returncode = 0
		mock_run.return_value.stdout = "Line 1\nLine 2\nLine 3"
		mock_run.return_value.stderr = ""

		flow = ShellExecFlow()
		result = flow.process({
			"command": "cresus list strategies"
		})

		assert result["status"] == "success"
		assert "Line 1" in result["stdout"]


class TestShellExecFlowFailure:
	"""Test cases for failed command execution."""

	@patch("flows.shell_exec.subprocess.run")
	def test_failed_command(self, mock_run):
		"""Test failed command execution."""
		mock_run.return_value.returncode = 1
		mock_run.return_value.stdout = ""
		mock_run.return_value.stderr = "error message"

		flow = ShellExecFlow()
		result = flow.process({
			"command": "cresus invalid-command"
		})

		assert result["status"] == "failed"
		assert result["return_code"] == 1
		assert result["stderr"] == "error message"

	@patch("flows.shell_exec.subprocess.run")
	def test_command_with_nonzero_exit(self, mock_run):
		"""Test command that exits with non-zero code."""
		mock_run.return_value.returncode = 127
		mock_run.return_value.stdout = ""
		mock_run.return_value.stderr = "command not found"

		flow = ShellExecFlow()
		result = flow.process({
			"command": "cresus nonexistent"
		})

		assert result["status"] == "failed"
		assert result["return_code"] == 127


class TestShellExecFlowTimeout:
	"""Test cases for timeout handling."""

	@patch("flows.shell_exec.subprocess.run")
	def test_timeout_error(self, mock_run):
		"""Test handling of timeout errors."""
		mock_run.side_effect = subprocess.TimeoutExpired("cresus long-task", 300)

		flow = ShellExecFlow()
		result = flow.process({
			"command": "cresus long-task"
		})

		assert result["status"] == "timeout"
		assert "timed out after 300 seconds" in result["error"]

	@patch("flows.shell_exec.subprocess.run")
	def test_timeout_value(self, mock_run):
		"""Test that timeout is applied."""
		mock_run.return_value.returncode = 0
		mock_run.return_value.stdout = ""
		mock_run.return_value.stderr = ""

		flow = ShellExecFlow()
		flow.process({
			"command": "cresus data fetch cac40"
		})

		# Check that timeout was passed
		call_kwargs = mock_run.call_args[1]
		assert call_kwargs["timeout"] == 300


class TestShellExecFlowExceptionHandling:
	"""Test cases for exception handling."""

	@patch("flows.shell_exec.subprocess.run")
	def test_general_exception(self, mock_run):
		"""Test handling of general exceptions."""
		mock_run.side_effect = OSError("Permission denied")

		flow = ShellExecFlow()
		result = flow.process({
			"command": "cresus protected-command"
		})

		assert result["status"] == "error"
		assert "Permission denied" in result["error"]

	def test_missing_command_parameter(self):
		"""Test that missing command parameter returns error."""
		flow = ShellExecFlow()
		result = flow.process({
			"other_param": "value"
		})

		assert result["status"] == "error"
		assert "command parameter is required" in result["error"]

	def test_empty_input_data(self):
		"""Test that empty input returns error."""
		flow = ShellExecFlow()
		result = flow.process(None)

		assert result["status"] == "error"
		assert "command parameter is required" in result["error"]


class TestShellExecFlowOutputTruncation:
	"""Test cases for output truncation."""

	@patch("flows.shell_exec.subprocess.run")
	def test_stdout_truncation(self, mock_run):
		"""Test that stdout is truncated to 500 chars."""
		long_output = "x" * 1000
		mock_run.return_value.returncode = 0
		mock_run.return_value.stdout = long_output
		mock_run.return_value.stderr = ""

		flow = ShellExecFlow()
		result = flow.process({
			"command": "cresus verbose-output"
		})

		assert result["status"] == "success"
		assert len(result["stdout"]) <= 500

	@patch("flows.shell_exec.subprocess.run")
	def test_stderr_truncation(self, mock_run):
		"""Test that stderr is truncated to 500 chars."""
		long_error = "y" * 1000
		mock_run.return_value.returncode = 1
		mock_run.return_value.stdout = ""
		mock_run.return_value.stderr = long_error

		flow = ShellExecFlow()
		result = flow.process({
			"command": "cresus failing-command"
		})

		assert result["status"] == "failed"
		assert len(result["stderr"]) <= 500


class TestShellExecFlowReturnStructure:
	"""Test cases for return value structure."""

	@patch("flows.shell_exec.subprocess.run")
	def test_success_response_structure(self, mock_run):
		"""Test structure of successful response."""
		mock_run.return_value.returncode = 0
		mock_run.return_value.stdout = "output"
		mock_run.return_value.stderr = ""

		flow = ShellExecFlow()
		result = flow.process({
			"command": "cresus test"
		})

		assert "status" in result
		assert "command" in result
		assert "return_code" in result
		assert "stdout" in result
		assert "stderr" in result

	@patch("flows.shell_exec.subprocess.run")
	def test_failure_response_structure(self, mock_run):
		"""Test structure of failure response."""
		mock_run.return_value.returncode = 1
		mock_run.return_value.stdout = ""
		mock_run.return_value.stderr = "error"

		flow = ShellExecFlow()
		result = flow.process({
			"command": "cresus failing"
		})

		assert result["status"] == "failed"
		assert "command" in result
		assert "return_code" in result
		assert "stdout" in result
		assert "stderr" in result

	def test_error_response_structure(self):
		"""Test structure of error response."""
		flow = ShellExecFlow()
		result = flow.process({
			"command": "invalid-command-blocked"
		})

		assert result["status"] == "error"
		assert "error" in result


class TestShellExecFlowEdgeCases:
	"""Test cases for edge cases."""

	@patch("flows.shell_exec.subprocess.run")
	def test_empty_stdout(self, mock_run):
		"""Test handling of empty stdout."""
		mock_run.return_value.returncode = 0
		mock_run.return_value.stdout = ""
		mock_run.return_value.stderr = ""

		flow = ShellExecFlow()
		result = flow.process({
			"command": "cresus silent-command"
		})

		assert result["status"] == "success"
		assert result["stdout"] == ""

	@patch("flows.shell_exec.subprocess.run")
	def test_empty_stderr(self, mock_run):
		"""Test handling of empty stderr."""
		mock_run.return_value.returncode = 0
		mock_run.return_value.stdout = "output"
		mock_run.return_value.stderr = ""

		flow = ShellExecFlow()
		result = flow.process({
			"command": "cresus test"
		})

		assert result["stderr"] == ""

	@patch("flows.shell_exec.subprocess.run")
	def test_command_with_special_chars(self, mock_run):
		"""Test command with special characters."""
		mock_run.return_value.returncode = 0
		mock_run.return_value.stdout = ""
		mock_run.return_value.stderr = ""

		flow = ShellExecFlow()
		result = flow.process({
			"command": "cresus data fetch 'market-data'"
		})

		assert result["status"] == "success"

	@patch("flows.shell_exec.subprocess.run")
	def test_command_with_pipes(self, mock_run):
		"""Test command with pipes (should be blocked if not cresus prefix)."""
		flow = ShellExecFlow()
		result = flow.process({
			"command": "cat file.txt | grep pattern"
		})

		assert result["status"] == "error"
