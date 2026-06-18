"""Examples of using BotFinance for algorithmic trading."""

from pathlib import Path
from bot.finance import BotFinance
from tools.bot import BotManager


def example_pre_market_workflow():
	"""Example: Pre-market bot execution."""
	print("=== Pre-Market Workflow ===\n")

	manager = BotManager()

	# Get or create bot
	bots = manager.list_bots(state_filter="active")
	if not bots:
		print("No active bots found. Create one first:")
		print("  cresus> bot create my_bot cac_top_5")
		print("  cresus> bot activate my_bot")
		return

	bot_name = bots[0]["name"]
	bot_dir = manager.get_bot_dir(bot_name)

	print(f"Creating BotFinance instance: {bot_name}\n")

	# Create finance bot instance
	bot = BotFinance(bot_name, bot_dir)

	# Run pre-market workflow
	print(f"Running pre-market workflow...")
	result = bot.run(params={"step": "pre_market"})

	print(f"Status: {result['status']}")
	if result['status'] == "success":
		output = result['output']
		print(f"Agents executed: {len(output.get('agents_executed', []))}")
		print(f"Tickers analyzed: {len(output.get('market_data', {}).keys())}")
		print(f"Alphas generated: {len(output.get('alphas', {}))}")
		print(f"Watchlist items: {len(output.get('watchlist', []))}")
	else:
		print(f"Error: {result.get('message')}")

	print()


def example_step_by_step():
	"""Example: Running all steps sequentially."""
	print("=== Step-by-Step Workflow ===\n")

	manager = BotManager()

	bots = manager.list_bots(state_filter="active")
	if not bots:
		print("No active bots found.\n")
		return

	bot_name = bots[0]["name"]
	bot_dir = manager.get_bot_dir(bot_name)

	bot = BotFinance(bot_name, bot_dir)

	steps = ["pre_market", "in_market", "post_market"]

	for step in steps:
		print(f"Step: {step}")
		print("-" * 40)

		result = bot.run(params={"step": step})

		if result['status'] == "success":
			output = result['output']
			print(f"✓ {step} completed")
			print(f"  Timestamp: {output.get('timestamp')}")
			print(f"  Agents: {len(output.get('agents_executed', []))}")
		else:
			print(f"✗ {step} failed: {result.get('message')}")

		print()


def example_pre_market_details():
	"""Example: Pre-market workflow with detailed output."""
	print("=== Pre-Market Detailed Output ===\n")

	manager = BotManager()

	bots = manager.list_bots(state_filter="active")
	if not bots:
		print("No active bots found.\n")
		return

	bot_name = bots[0]["name"]
	bot_dir = manager.get_bot_dir(bot_name)

	bot = BotFinance(bot_name, bot_dir)

	print(f"Bot: {bot_name}")
	print(f"Dir: {bot_dir}")
	print()

	# Execute pre-market
	result = bot.run(params={
		"step": "pre_market",
		"timestamp": "09:00:00"
	})

	print("Pre-Market Execution Results:")
	print("=" * 50)

	if result['status'] == "success":
		output = result['output']

		print(f"\nStep: {output['step']}")
		print(f"Timestamp: {output['timestamp']}")

		print(f"\nAgents Executed ({len(output.get('agents_executed', []))}):")
		for agent in output.get('agents_executed', []):
			print(f"  ✓ {agent}")

		print(f"\nMarket Data:")
		market_data = output.get('market_data', {})
		print(f"  Tickers: {len(market_data)}")
		for ticker in list(market_data.keys())[:5]:
			print(f"    • {ticker}")

		print(f"\nAlphas Generated ({len(output.get('alphas', {}))}):")
		alphas = output.get('alphas', {})
		for ticker, alpha in list(alphas.items())[:5]:
			print(f"  • {ticker}: {alpha}")

		print(f"\nWatchlist Items ({len(output.get('watchlist', []))}):")
		for ticker in output.get('watchlist', [])[:5]:
			print(f"  • {ticker}")

	else:
		print(f"✗ Error: {result.get('message')}")

	print()


def example_response_structure():
	"""Example: Understanding response structure."""
	print("=== Response Structure ===\n")

	print("Pre-market response:")
	print("""
	{
		"status": "success" | "error",
		"params": {
			"step": "pre_market"
		},
		"output": {
			"step": "pre_market",
			"agents_executed": [
				"DataAgent[momentum_cac40]",
				"WatchlistAlphasAgent",
				"WatchListAgent"
			],
			"market_data": {
				"AC.PA": {...},
				"OR.PA": {...},
				...
			},
			"alphas": {
				"AC.PA": 0.85,
				"OR.PA": 0.72,
				...
			},
			"watchlist": ["AC.PA", "OR.PA", ...],
			"timestamp": "2026-06-18T09:30:00"
		},
		"message": "..." (only if error)
	}
	""")

	print("In-market response:")
	print("""
	{
		"status": "success",
		"params": {"step": "in_market"},
		"output": {
			"step": "in_market",
			"trades_executed": 3,
			"pnl": 1500.00,
			"positions": 2,
			"timestamp": "2026-06-18T10:15:00"
		}
	}
	""")

	print("Post-market response:")
	print("""
	{
		"status": "success",
		"params": {"step": "post_market"},
		"output": {
			"step": "post_market",
			"trades_analyzed": 5,
			"pnl_daily": 2000.00,
			"positions_closed": 1,
			"timestamp": "2026-06-18T17:30:00"
		}
	}
	""")

	print()


def example_context_flow():
	"""Example: Context flow through agents."""
	print("=== Context Flow Through Agents ===\n")

	print("""
	Context initialized with:
	├── bot_name: "momentum_cac40"
	├── strategy_name: "cac_top_5"
	├── strategy_config: {...}
	├── portfolio: {...}
	├── tickers: ["AC.PA", "OR.PA", "CS.PA", ...]
	└── timestamp: "2026-06-18T09:00:00"

	DataAgent execution:
	├── Input: {tickers, strategy, timestamp}
	├── Process: Fetch market data for tickers
	├── Output: market_data
	└── Context update: context.set("market_data", output)

	WatchlistAlphasAgent execution:
	├── Input: {tickers, strategy}
	├── Process: Generate alphas from market data
	├── Output: alphas
	└── Context update: context.set("alphas", output)

	WatchListAgent execution:
	├── Input: {tickers, strategy, alphas}
	├── Process: Build watchlist from alphas
	├── Output: watchlist
	└── Context update: context.set("watchlist", output)
	""")

	print()


def example_error_handling():
	"""Example: Error handling."""
	print("=== Error Handling ===\n")

	print("Invalid step:")
	result = {
		"status": "error",
		"params": {"step": "invalid_step"},
		"output": {},
		"message": "Invalid step: invalid_step. Must be one of ['pre_market', 'in_market', 'post_market']"
	}
	print(f"Result: {result}\n")

	print("Missing bot config:")
	result = {
		"status": "error",
		"params": {"step": "pre_market"},
		"output": {},
		"message": "Failed to initialize context"
	}
	print(f"Result: {result}\n")

	print("DataAgent failure:")
	result = {
		"status": "error",
		"params": {"step": "pre_market"},
		"output": {},
		"message": "DataAgent failed"
	}
	print(f"Result: {result}\n")


if __name__ == "__main__":
	print("BotFinance Examples\n")
	print("=" * 60)
	print()

	example_step_by_step()
	example_pre_market_details()
	example_response_structure()
	example_context_flow()
	example_error_handling()

	print("=" * 60)
	print("Examples complete!")
