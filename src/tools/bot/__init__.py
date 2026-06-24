"""Bot management system for automated trading."""

from pathlib import Path
from typing import Optional, Dict, List, Any
import yaml
import shutil
from datetime import datetime

from utils.env import get_db_root
from tools.strategy import StrategyManager


class BotManager:
	"""Manages bot lifecycle, storage, and configuration.

	Bots are organized in get_db_root()/bots/<bot_name>/:
	- config.yml: Bot configuration (copied from template)
	- strategy.yml: Strategy configuration (copied from existing strategy)
	- portfolio.json: Portfolio state and positions
	- journal.csv: Trade journal
	- watchlist.txt: Watchlist of tickers
	"""

	def __init__(self, db_root: Optional[Path] = None):
		"""Initialize bot manager.

		Args:
			db_root: Root database directory (default: get_db_root())
		"""
		self.db_root = db_root or get_db_root()
		self.bots_dir = self.db_root / "bots"
		self.bots_dir.mkdir(parents=True, exist_ok=True)

	def create_bot(self, name: str, strategy_path: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Create and initialize a new bot.

		Args:
			name: Bot identifier (must be unique)
			strategy_path: Path to strategy.yml file OR strategy name (from config/agents.yml)
			config: Optional bot configuration dictionary (uses template if None)

		Returns:
			Bot configuration dictionary

		Raises:
			ValueError: If bot already exists or strategy not found
		"""
		bot_dir = self.bots_dir / name
		if bot_dir.exists():
			raise ValueError(f"Bot '{name}' already exists")

		# Resolve strategy file path - try file first, then config
		strategy_file = self._resolve_strategy_path(strategy_path)

		# If file not found, try to extract from StrategyManager
		if not strategy_file.exists():
			strategy_file = self._extract_strategy_from_config(strategy_path)

		if not strategy_file or not strategy_file.exists():
			# Provide helpful error message
			available = self._get_available_strategies()
			available_str = ", ".join(available[:5]) if available else "none found"
			raise ValueError(
				f"Strategy file not found: {strategy_path}\n"
				f"Available strategies: {available_str}\n"
				f"Use 'cresus strategy list' to see all strategies"
			)

		bot_dir.mkdir(parents=True, exist_ok=True)

		# Load default template if no config provided
		if config is None:
			config = self._load_default_template()

		# Set bot name and creation time. Note: no "strategy" field - strategy.yml
		# (copied below) is the bot's own complete, self-sufficient strategy spec;
		# storing the template name here previously got misread elsewhere as a
		# live portfolio identity, causing bots to read/write each other's data.
		config["name"] = name
		config["created_at"] = datetime.now().isoformat()
		config["state"] = "inactive"

		# Save configuration
		self.save_config(name, config)

		# Copy strategy file
		strategy_dest = bot_dir / "strategy.yml"
		shutil.copy2(strategy_file, strategy_dest)

		# Initialize portfolio file
		self._initialize_portfolio(name)

		# Initialize journal file
		self._initialize_journal(name)

		# Initialize watchlist file
		self._initialize_watchlist(name)

		return config

	def _get_available_strategies(self) -> List[str]:
		"""Get list of available strategies from StrategyManager.

		Returns:
			List of strategy names
		"""
		try:
			strategy_manager = StrategyManager()
			strategies = strategy_manager.list_strategies()
			return [s.get("name", "") for s in strategies.get("strategies", [])]
		except Exception:
			return []

	def _extract_strategy_from_config(self, strategy_name: str) -> Optional[Path]:
		"""Extract strategy from config/agents.yml and save to temp file.

		Args:
			strategy_name: Name of strategy to find

		Returns:
			Path to strategy file if found, None otherwise
		"""
		try:
			strategy_manager = StrategyManager()
			strategies = strategy_manager.list_strategies()

			# Check if strategy exists
			for strategy in strategies.get("strategies", []):
				if strategy.get("name") == strategy_name:
					# Try to load the strategy
					strategy_data = strategy_manager.load_strategy(strategy_name)
					if strategy_data.get("status") == "success":
						# Create temporary strategy file
						temp_strategy_path = self.bots_dir.parent / ".temp" / f"{strategy_name}.yml"
						temp_strategy_path.parent.mkdir(parents=True, exist_ok=True)

						with open(temp_strategy_path, "w") as f:
							yaml.dump(strategy_data.get("data", {}), f)

						return temp_strategy_path

			return None
		except Exception:
			return None

	def _resolve_strategy_path(self, strategy_input: str) -> Path:
		"""Resolve strategy name or path to actual file.

		Args:
			strategy_input: Strategy name (e.g., 'cac_top_5') or full path

		Returns:
			Path to strategy file
		"""
		from pathlib import Path

		# If it's already a full path and exists, use it
		strategy_file = Path(strategy_input)
		if strategy_file.exists():
			return strategy_file

		# Try with both .yml and .yaml extensions
		for ext in ['.yml', '.yaml']:
			# Try as full path with extension
			strategy_with_ext = Path(strategy_input + ext)
			if strategy_with_ext.exists():
				return strategy_with_ext

			# Get current working directory
			cwd = Path.cwd()

			# Try relative to current directory
			common_relative = [
				Path("config/strategies") / f"{strategy_input}{ext}",
				Path("config") / f"{strategy_input}{ext}",
				Path("strategies") / f"{strategy_input}{ext}",
			]

			for location in common_relative:
				if location.exists():
					return location

			# Try from parent directories (for when cwd is not project root)
			for parent_level in range(5):
				search_root = cwd
				for _ in range(parent_level):
					search_root = search_root.parent

				for subdir in ["config/strategies", "config", "strategies"]:
					location = search_root / subdir / f"{strategy_input}{ext}"
					if location.exists():
						return location

		# Return the input as Path (will fail later with proper error)
		return Path(strategy_input)

	def _load_default_template(self) -> Dict[str, Any]:
		"""Load default bot configuration template.

		Returns:
			Default configuration dictionary from init/templates/bots.yml
		"""
		template_path = self.db_root.parent / "init" / "templates" / "bots.yml"

		if template_path.exists():
			try:
				with open(template_path) as f:
					return yaml.safe_load(f) or {}
			except Exception:
				return {}

		# Fallback: return minimal default template
		return {
			"description": "Bot description",
			"portfolio": {
				"initial_capital": 100000,
				"risk_per_trade": 0.02,
				"max_drawdown": 0.20
			},
			"watchlist": []
		}

	def _initialize_portfolio(self, name: str) -> None:
		"""Initialize portfolio file for bot.

		Args:
			name: Bot name
		"""
		bot_dir = self.bots_dir / name
		portfolio_file = bot_dir / "portfolio.json"

		import json
		portfolio = {
			"bot_name": name,
			"initial_capital": 100000,
			"cash": 100000,
			"positions": [],
			"total_value": 100000,
			"pnl": 0.0,
			"pnl_pct": 0.0,
			"created_at": datetime.now().isoformat()
		}

		with open(portfolio_file, "w") as f:
			json.dump(portfolio, f, indent=2)

	def _initialize_journal(self, name: str) -> None:
		"""Initialize journal (CSV) file for bot.

		Args:
			name: Bot name
		"""
		bot_dir = self.bots_dir / name
		journal_file = bot_dir / "journal.csv"

		# Create CSV header
		with open(journal_file, "w") as f:
			f.write("date,ticker,type,quantity,price,pnl,pnl_pct,notes\n")

	def _initialize_watchlist(self, name: str) -> None:
		"""Initialize watchlist file for bot.

		Args:
			name: Bot name
		"""
		bot_dir = self.bots_dir / name
		watchlist_file = bot_dir / "watchlist.txt"

		# Create empty watchlist
		with open(watchlist_file, "w") as f:
			f.write("# Watchlist for bot: {}\n".format(name))
			f.write("# Add tickers one per line\n")

	def get_bot(self, name: str) -> Optional[Dict[str, Any]]:
		"""Load bot configuration.

		Args:
			name: Bot name

		Returns:
			Bot config dictionary if found, None otherwise
		"""
		bot_dir = self.bots_dir / name
		if not bot_dir.exists():
			return None

		return self.load_config(name)

	def delete_bot(self, name: str) -> bool:
		"""Delete a bot and all its data.

		Args:
			name: Bot name

		Returns:
			True if bot was deleted, False if bot doesn't exist
		"""
		bot_dir = self.bots_dir / name
		if not bot_dir.exists():
			return False

		shutil.rmtree(bot_dir)
		return True

	def list_bots(self, state_filter: Optional[str] = None) -> List[Dict[str, Any]]:
		"""List all bots, optionally filtered by state.

		Args:
			state_filter: Optional state filter ('active', 'inactive')

		Returns:
			List of bot configurations
		"""
		bots = []

		for bot_dir in self.bots_dir.iterdir():
			if not bot_dir.is_dir():
				continue

			bot_config = self.load_config(bot_dir.name)
			if bot_config is None:
				continue

			# Apply state filter
			if state_filter and bot_config.get("state") != state_filter:
				continue

			bots.append(bot_config)

		# Sort by name
		bots.sort(key=lambda b: b.get("name", ""))
		return bots

	def get_bots_summary(self) -> Dict[str, Any]:
		"""Get summary of all bots by state.

		Returns:
			Dictionary with bot counts by state
		"""
		all_bots = self.list_bots()

		summary = {
			"active": 0,
			"inactive": 0,
			"total": len(all_bots)
		}

		for bot in all_bots:
			state = bot.get("state", "inactive")
			if state in summary:
				summary[state] += 1

		return summary

	def activate_bot(self, name: str) -> bool:
		"""Activate a bot.

		Args:
			name: Bot name

		Returns:
			True if successful, False if bot doesn't exist
		"""
		bot_config = self.get_bot(name)
		if bot_config is None:
			return False

		bot_config["state"] = "active"
		bot_config["activated_at"] = datetime.now().isoformat()
		self.save_config(name, bot_config)

		return True

	def deactivate_bot(self, name: str) -> bool:
		"""Deactivate a bot.

		Args:
			name: Bot name

		Returns:
			True if successful, False if bot doesn't exist
		"""
		bot_config = self.get_bot(name)
		if bot_config is None:
			return False

		bot_config["state"] = "inactive"
		bot_config["deactivated_at"] = datetime.now().isoformat()
		self.save_config(name, bot_config)

		return True

	def save_config(self, name: str, config: Dict[str, Any]) -> None:
		"""Save bot configuration to file.

		Args:
			name: Bot name
			config: Configuration dictionary
		"""
		bot_dir = self.bots_dir / name
		config_file = bot_dir / "config.yml"

		with open(config_file, "w") as f:
			yaml.dump(config, f, default_flow_style=False)

	def load_config(self, name: str) -> Optional[Dict[str, Any]]:
		"""Load bot configuration from file.

		Args:
			name: Bot name

		Returns:
			Configuration dictionary if found, None otherwise
		"""
		bot_dir = self.bots_dir / name
		config_file = bot_dir / "config.yml"

		if not config_file.exists():
			return None

		try:
			with open(config_file) as f:
				return yaml.safe_load(f) or {}
		except Exception:
			return None

	def get_bot_dir(self, name: str) -> Path:
		"""Get bot directory path.

		Args:
			name: Bot name

		Returns:
			Path to bot directory
		"""
		return self.bots_dir / name

	def get_strategy_path(self, name: str) -> Optional[Path]:
		"""Get strategy file path for bot.

		Args:
			name: Bot name

		Returns:
			Path to strategy.yml if exists, None otherwise
		"""
		bot_dir = self.bots_dir / name
		strategy_file = bot_dir / "strategy.yml"

		return strategy_file if strategy_file.exists() else None

	def get_portfolio_path(self, name: str) -> Path:
		"""Get portfolio file path for bot.

		Args:
			name: Bot name

		Returns:
			Path to portfolio.json
		"""
		return self.bots_dir / name / "portfolio.json"

	def get_journal_path(self, name: str) -> Path:
		"""Get journal file path for bot.

		Args:
			name: Bot name

		Returns:
			Path to journal.csv
		"""
		return self.bots_dir / name / "journal.csv"

	def get_watchlist_path(self, name: str) -> Path:
		"""Get watchlist file path for bot.

		Args:
			name: Bot name

		Returns:
			Path to watchlist.txt
		"""
		return self.bots_dir / name / "watchlist.txt"

	def load_portfolio(self, name: str) -> Optional[Dict[str, Any]]:
		"""Load bot portfolio.

		Args:
			name: Bot name

		Returns:
			Portfolio dictionary if found, None otherwise
		"""
		portfolio_file = self.get_portfolio_path(name)

		if not portfolio_file.exists():
			return None

		try:
			import json
			with open(portfolio_file) as f:
				return json.load(f)
		except Exception:
			return None

	def save_portfolio(self, name: str, portfolio: Dict[str, Any]) -> None:
		"""Save bot portfolio.

		Args:
			name: Bot name
			portfolio: Portfolio dictionary
		"""
		portfolio_file = self.get_portfolio_path(name)

		import json
		with open(portfolio_file, "w") as f:
			json.dump(portfolio, f, indent=2)

	def load_watchlist(self, name: str) -> List[str]:
		"""Load bot watchlist.

		Args:
			name: Bot name

		Returns:
			List of ticker symbols
		"""
		watchlist_file = self.get_watchlist_path(name)

		if not watchlist_file.exists():
			return []

		try:
			with open(watchlist_file) as f:
				lines = f.readlines()
				# Filter out comments and empty lines
				return [line.strip() for line in lines if line.strip() and not line.startswith("#")]
		except Exception:
			return []

	def save_watchlist(self, name: str, tickers: List[str]) -> None:
		"""Save bot watchlist.

		Args:
			name: Bot name
			tickers: List of ticker symbols
		"""
		watchlist_file = self.get_watchlist_path(name)

		with open(watchlist_file, "w") as f:
			f.write(f"# Watchlist for bot: {name}\n")
			for ticker in tickers:
				f.write(f"{ticker}\n")

	def add_to_watchlist(self, name: str, ticker: str) -> bool:
		"""Add ticker to bot watchlist.

		Args:
			name: Bot name
			ticker: Ticker symbol

		Returns:
			True if added, False if already exists
		"""
		watchlist = self.load_watchlist(name)

		if ticker in watchlist:
			return False

		watchlist.append(ticker)
		self.save_watchlist(name, watchlist)
		return True

	def remove_from_watchlist(self, name: str, ticker: str) -> bool:
		"""Remove ticker from bot watchlist.

		Args:
			name: Bot name
			ticker: Ticker symbol

		Returns:
			True if removed, False if not found
		"""
		watchlist = self.load_watchlist(name)

		if ticker not in watchlist:
			return False

		watchlist.remove(ticker)
		self.save_watchlist(name, watchlist)
		return True

	def get_bot_info(self, name: str) -> Optional[Dict[str, Any]]:
		"""Get comprehensive bot information.

		Args:
			name: Bot name

		Returns:
			Dictionary with all bot data if found, None otherwise
		"""
		config = self.get_bot(name)
		if config is None:
			return None

		portfolio = self.load_portfolio(name)
		watchlist = self.load_watchlist(name)
		strategy_path = self.get_strategy_path(name)

		return {
			"config": config,
			"portfolio": portfolio,
			"watchlist": watchlist,
			"strategy_file": str(strategy_path) if strategy_path else None,
			"bot_dir": str(self.get_bot_dir(name))
		}

	def cleanup_old_bots(self, keep_count: int = 10, state_filter: Optional[str] = None) -> int:
		"""Delete old bots, keeping most recent.

		Args:
			keep_count: Number of most recent bots to keep
			state_filter: Optional state filter ('active', 'inactive')

		Returns:
			Number of bots deleted
		"""
		all_bots = self.list_bots(state_filter)

		if len(all_bots) <= keep_count:
			return 0

		# Sort by creation date, keep most recent
		all_bots.sort(key=lambda b: b.get("created_at", ""), reverse=True)
		to_delete = all_bots[keep_count:]

		deleted_count = 0
		for bot in to_delete:
			if self.delete_bot(bot["name"]):
				deleted_count += 1

		return deleted_count
