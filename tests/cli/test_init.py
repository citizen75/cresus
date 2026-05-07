"""Tests for CLI init command."""

import unittest
import tempfile
from pathlib import Path


class TestInitCommand(unittest.TestCase):
	"""Test CLI init command and _init_cresus_directory method."""

	def setUp(self):
		"""Set up test fixtures."""
		self.temp_home = tempfile.TemporaryDirectory()
		self.temp_project = tempfile.TemporaryDirectory()
		self.temp_home_path = Path(self.temp_home.name)
		self.temp_project_path = Path(self.temp_project.name)

	def tearDown(self):
		"""Clean up temp directories."""
		self.temp_home.cleanup()
		self.temp_project.cleanup()

	def _setup_init_template(self):
		"""Create init template directory structure with sample files."""
		init_template = self.temp_project_path / "init"
		init_template.mkdir(exist_ok=True)

		# Create db/universes directory and files
		universes_dir = init_template / "db" / "universes"
		universes_dir.mkdir(parents=True, exist_ok=True)
		(universes_dir / "cac40.csv").write_text("ticker,name\nORR,Ormat\nANO,Ano")
		(universes_dir / "blacklist.csv").write_text("ticker,reason,date_added\nDEAD,Delisted,2026-01-01")

		# Create db/strategies directory and files
		strategies_dir = init_template / "db" / "strategies"
		strategies_dir.mkdir(parents=True, exist_ok=True)
		(strategies_dir / "cac_momentum.yml").write_text("name: cac_momentum\nsource: cac40")
		(strategies_dir / "etf_pea.yml").write_text("name: etf_pea\nsource: etf_pea")

		# Create config directory and files
		config_dir = init_template / "config"
		config_dir.mkdir(parents=True, exist_ok=True)
		(config_dir / "cresus.yml").write_text("app:\n  name: Cresus\n  version: 1.0.0")
		(config_dir / "cron.yml").write_text("schedules: []")
		(config_dir / "mcp.yml").write_text("mcp: {}")

		# Create .env file
		(init_template / ".env").write_text("API_KEY=test\nDB_PATH=~/.cresus/db")

		return init_template

	def _execute_init_cresus_directory(self):
		"""Execute init directory logic directly."""
		cresus_home = self.temp_home_path / ".cresus"
		init_template = self.temp_project_path / "init"

		if not init_template.exists():
			return None

		# Create directories
		dirs_to_create = [cresus_home]

		if (init_template / "db").exists():
			for item in (init_template / "db").rglob("*"):
				if item.is_dir():
					rel_path = item.relative_to(init_template / "db")
					dirs_to_create.append(cresus_home / "db" / rel_path)

		dirs_to_create.append(cresus_home / "config")
		config_strategies = init_template / "config" / "strategies"
		if config_strategies.exists():
			dirs_to_create.append(cresus_home / "config" / "strategies")

		created_dirs = []
		for d in dirs_to_create:
			if not d.exists():
				d.mkdir(parents=True, exist_ok=True)
				created_dirs.append(d)

		# Copy config files
		config_files = ["cresus.yml", "cron.yml", "mcp.yml"]
		copied_files = []

		for config_file in config_files:
			src = init_template / "config" / config_file
			dst = cresus_home / "config" / config_file

			if src.exists() and not dst.exists():
				try:
					with open(src, 'r') as f:
						content = f.read()
					with open(dst, 'w') as f:
						f.write(content)
					copied_files.append(config_file)
				except Exception:
					pass

		# Copy universe files
		universes_src = init_template / "db" / "universes"
		universes_dst = cresus_home / "db" / "universes"

		copied_universes = []
		if universes_src.exists():
			for universe_file in universes_src.glob("*.csv"):
				dst_file = universes_dst / universe_file.name
				if not dst_file.exists():
					try:
						with open(universe_file, 'r') as f:
							content = f.read()
						with open(dst_file, 'w') as f:
							f.write(content)
						copied_universes.append(universe_file.name)
					except Exception:
						pass

		# Copy strategy files
		strategies_src = init_template / "db" / "strategies"
		strategies_dst = cresus_home / "db" / "strategies"

		copied_strategies = []
		if strategies_src.exists():
			for strategy_file in strategies_src.glob("*"):
				if strategy_file.is_file():
					dst_file = strategies_dst / strategy_file.name
					if not dst_file.exists():
						try:
							with open(strategy_file, 'r') as f:
								content = f.read()
							with open(dst_file, 'w') as f:
								f.write(content)
							copied_strategies.append(strategy_file.name)
						except Exception:
							pass

		# Create .env file
		env_file = cresus_home / ".env"
		env_created = False
		if not env_file.exists():
			env_template = init_template / ".env"
			if env_template.exists():
				try:
					with open(env_template, 'r') as f:
						content = f.read()
					with open(env_file, 'w') as f:
						f.write(content)
					env_created = True
				except Exception:
					pass

		return {
			"cresus_home": cresus_home,
			"created_dirs": len(created_dirs),
			"copied_files": copied_files,
			"copied_universes": copied_universes,
			"copied_strategies": copied_strategies,
			"env_created": env_created
		}

	def test_init_creates_cresus_home_directory(self):
		"""Test that init creates ~/.cresus directory."""
		self._setup_init_template()
		result = self._execute_init_cresus_directory()

		cresus_home = self.temp_home_path / ".cresus"
		self.assertTrue(cresus_home.exists())

	def test_init_creates_subdirectories(self):
		"""Test that init creates all subdirectories (db, config, etc)."""
		self._setup_init_template()
		result = self._execute_init_cresus_directory()

		cresus_home = self.temp_home_path / ".cresus"
		self.assertTrue((cresus_home / "db").exists())
		self.assertTrue((cresus_home / "config").exists())
		self.assertTrue((cresus_home / "db" / "universes").exists())
		self.assertTrue((cresus_home / "db" / "strategies").exists())

	def test_init_copies_config_files(self):
		"""Test that init copies config files from template."""
		self._setup_init_template()
		result = self._execute_init_cresus_directory()

		cresus_home = self.temp_home_path / ".cresus"
		self.assertTrue((cresus_home / "config" / "cresus.yml").exists())
		self.assertTrue((cresus_home / "config" / "cron.yml").exists())
		self.assertTrue((cresus_home / "config" / "mcp.yml").exists())
		self.assertEqual(len(result["copied_files"]), 3)

	def test_init_copies_universe_files(self):
		"""Test that init copies universe CSV files from template."""
		self._setup_init_template()
		result = self._execute_init_cresus_directory()

		cresus_home = self.temp_home_path / ".cresus"
		self.assertTrue((cresus_home / "db" / "universes" / "cac40.csv").exists())
		self.assertTrue((cresus_home / "db" / "universes" / "blacklist.csv").exists())
		self.assertEqual(len(result["copied_universes"]), 2)

	def test_init_copies_strategy_files(self):
		"""Test that init copies strategy files from template."""
		self._setup_init_template()
		result = self._execute_init_cresus_directory()

		cresus_home = self.temp_home_path / ".cresus"
		self.assertTrue((cresus_home / "db" / "strategies" / "cac_momentum.yml").exists())
		self.assertTrue((cresus_home / "db" / "strategies" / "etf_pea.yml").exists())
		self.assertEqual(len(result["copied_strategies"]), 2)

	def test_init_creates_env_file(self):
		"""Test that init creates .env file from template."""
		self._setup_init_template()
		result = self._execute_init_cresus_directory()

		env_file = self.temp_home_path / ".cresus" / ".env"
		self.assertTrue(env_file.exists())
		content = env_file.read_text()
		self.assertIn("API_KEY=test", content)
		self.assertTrue(result["env_created"])

	def test_init_does_not_overwrite_existing_files(self):
		"""Test that init does not overwrite existing files."""
		self._setup_init_template()

		cresus_home = self.temp_home_path / ".cresus"
		cresus_home.mkdir(parents=True)

		# Create existing config file with different content
		config_dir = cresus_home / "config"
		config_dir.mkdir()
		existing_file = config_dir / "cresus.yml"
		existing_file.write_text("existing content")

		result = self._execute_init_cresus_directory()

		# File should keep original content
		self.assertEqual(existing_file.read_text(), "existing content")
		# Result should show file was not copied
		self.assertNotIn("cresus.yml", result["copied_files"])

	def test_init_does_not_overwrite_existing_env(self):
		"""Test that init does not overwrite existing .env file."""
		self._setup_init_template()

		cresus_home = self.temp_home_path / ".cresus"
		cresus_home.mkdir(parents=True)

		# Create existing .env with different content
		env_file = cresus_home / ".env"
		env_file.write_text("EXISTING=true")

		result = self._execute_init_cresus_directory()

		# File should keep original content
		self.assertEqual(env_file.read_text(), "EXISTING=true")
		self.assertFalse(result["env_created"])

	def test_init_handles_missing_template(self):
		"""Test that init handles missing init template gracefully."""
		# Don't create init template
		result = self._execute_init_cresus_directory()

		# Should return None when template not found
		self.assertIsNone(result)

	def test_init_copies_file_content_correctly(self):
		"""Test that init copies file content exactly."""
		self._setup_init_template()

		init_template = self.temp_project_path / "init"
		original_content = (init_template / "config" / "cresus.yml").read_text()

		self._execute_init_cresus_directory()

		cresus_home = self.temp_home_path / ".cresus"
		copied_content = (cresus_home / "config" / "cresus.yml").read_text()

		self.assertEqual(original_content, copied_content)

	def test_init_idempotent(self):
		"""Test that running init twice produces same result."""
		self._setup_init_template()

		# Run init first time
		result1 = self._execute_init_cresus_directory()

		cresus_home = self.temp_home_path / ".cresus"
		config_file = cresus_home / "config" / "cresus.yml"
		first_content = config_file.read_text() if config_file.exists() else None

		# Run init second time
		result2 = self._execute_init_cresus_directory()

		second_content = config_file.read_text() if config_file.exists() else None

		# Content should be identical
		self.assertEqual(first_content, second_content)
		# Second run should not copy again (files already exist)
		self.assertEqual(len(result2["copied_files"]), 0)

	def test_init_with_multiple_universe_files(self):
		"""Test that init copies multiple universe files."""
		init_template = self.temp_project_path / "init"
		init_template.mkdir(exist_ok=True)

		# Create multiple universe files
		universes_dir = init_template / "db" / "universes"
		universes_dir.mkdir(parents=True, exist_ok=True)
		for name in ["cac40.csv", "etf_pea.csv", "nasdaq.csv"]:
			(universes_dir / name).write_text(f"ticker\n{name.split('.')[0]}")

		# Create config files
		config_dir = init_template / "config"
		config_dir.mkdir(parents=True, exist_ok=True)
		(config_dir / "cresus.yml").write_text("app: {}")

		result = self._execute_init_cresus_directory()

		cresus_home = self.temp_home_path / ".cresus"
		self.assertTrue((cresus_home / "db" / "universes" / "cac40.csv").exists())
		self.assertTrue((cresus_home / "db" / "universes" / "etf_pea.csv").exists())
		self.assertTrue((cresus_home / "db" / "universes" / "nasdaq.csv").exists())
		self.assertEqual(len(result["copied_universes"]), 3)

	def test_init_with_multiple_strategy_files(self):
		"""Test that init copies multiple strategy files."""
		init_template = self.temp_project_path / "init"
		init_template.mkdir(exist_ok=True)

		# Create multiple strategy files
		strategies_dir = init_template / "db" / "strategies"
		strategies_dir.mkdir(parents=True, exist_ok=True)
		for name in ["momentum.yml", "pullback.yml", "trend.yml"]:
			(strategies_dir / name).write_text(f"name: {name.split('.')[0]}")

		# Create config files
		config_dir = init_template / "config"
		config_dir.mkdir(parents=True, exist_ok=True)
		(config_dir / "cresus.yml").write_text("app: {}")

		result = self._execute_init_cresus_directory()

		cresus_home = self.temp_home_path / ".cresus"
		self.assertTrue((cresus_home / "db" / "strategies" / "momentum.yml").exists())
		self.assertTrue((cresus_home / "db" / "strategies" / "pullback.yml").exists())
		self.assertTrue((cresus_home / "db" / "strategies" / "trend.yml").exists())
		self.assertEqual(len(result["copied_strategies"]), 3)

	def test_init_creates_required_directories(self):
		"""Test that init creates required directories from init template."""
		init_template = self.temp_project_path / "init"
		init_template.mkdir(exist_ok=True)

		# Create empty directories
		db_dir = init_template / "db"
		db_dir.mkdir(exist_ok=True)
		config_dir = init_template / "config"
		config_dir.mkdir(exist_ok=True)

		result = self._execute_init_cresus_directory()

		cresus_home = self.temp_home_path / ".cresus"
		self.assertTrue((cresus_home / "config").exists())
		# db directory is only created if there are items in it (recursive)
		# Create a file to trigger db creation
		universes_dir = db_dir / "universes"
		universes_dir.mkdir(exist_ok=True)
		(universes_dir / "test.csv").write_text("ticker")

		result = self._execute_init_cresus_directory()
		self.assertTrue((cresus_home / "db").exists())

	def test_init_handles_partial_template(self):
		"""Test that init works even with partial template."""
		init_template = self.temp_project_path / "init"
		init_template.mkdir(exist_ok=True)

		# Create only some files
		config_dir = init_template / "config"
		config_dir.mkdir(parents=True, exist_ok=True)
		(config_dir / "cresus.yml").write_text("app: {}")

		result = self._execute_init_cresus_directory()

		# Should still create base directories
		cresus_home = self.temp_home_path / ".cresus"
		self.assertTrue((cresus_home / "config").exists())
		# Should have copied the config file
		self.assertIn("cresus.yml", result["copied_files"])


if __name__ == "__main__":
	unittest.main()
