"""Examples of running bots with the new run/process pattern."""

from pathlib import Path
from tools.bot import BotManager


def example_simple_run():
	"""Example: Simple bot run."""
	print("=== Simple Bot Run ===\n")

	manager = BotManager()

	# Get an existing bot
	bots = manager.list_bots(state_filter="active")
	if not bots:
		print("No active bots found. Create and activate a bot first.\n")
		return

	bot_name = bots[0]["name"]
	print(f"Running bot: {bot_name}\n")

	# In a real scenario, you would instantiate the bot and run it
	# For example, with BotPremarket:
	# from jobs import BotPremarket
	# bot = BotPremarket(bot_name, manager.get_bot_dir(bot_name))
	# result = bot.run(params={"markets": ["cac40"]})

	print(f"Bot '{bot_name}' would execute with default parameters\n")


def example_run_with_params():
	"""Example: Bot run with custom parameters."""
	print("=== Bot Run with Parameters ===\n")

	manager = BotManager()

	bots = manager.list_bots(state_filter="active")
	if not bots:
		print("No active bots found.\n")
		return

	bot_name = bots[0]["name"]

	# Custom parameters
	params = {
		"market": "cac40",
		"capital": 100000,
		"signal_strength_min": 0.7,
		"max_positions": 5
	}

	print(f"Running bot: {bot_name}")
	print(f"Parameters: {params}\n")

	# In a real scenario:
	# bot = BotPremarket(bot_name, manager.get_bot_dir(bot_name))
	# result = bot.run(params=params)
	# if result["status"] == "success":
	#     output = result["output"]
	#     print(f"Trades executed: {output.get('trades', 0)}")
	#     print(f"P&L: ${output.get('pnl', 0):.2f}")

	print("Bot execution would return:")
	print("  - Status: success/error")
	print("  - Output: Results dictionary")
	print("  - Message: Error message (if failed)\n")


def example_run_multiple_bots():
	"""Example: Run multiple bots sequentially."""
	print("=== Run Multiple Bots ===\n")

	manager = BotManager()

	active_bots = manager.list_bots(state_filter="active")
	if not active_bots:
		print("No active bots found.\n")
		return

	print(f"Active bots ({len(active_bots)}):")
	for bot in active_bots:
		print(f"  • {bot['name']}")

	print()

	# Parameters for each bot
	params_by_bot = {
		bot["name"]: {
			"market": "cac40",
			"capital": 100000
		}
		for bot in active_bots
	}

	print("Running bots with parameters:")
	for bot_name, params in params_by_bot.items():
		print(f"\n  Bot: {bot_name}")
		print(f"  Params: {params}")

		# In a real scenario:
		# bot = load_bot_by_name(bot_name)
		# result = bot.run(params=params)
		# print(f"  Status: {result['status']}")

	print()


def example_run_with_error_handling():
	"""Example: Bot run with error handling."""
	print("=== Bot Run with Error Handling ===\n")

	manager = BotManager()

	bots = manager.list_bots(state_filter="active")
	if not bots:
		print("No active bots found.\n")
		return

	bot_name = bots[0]["name"]

	# Simulate running bot
	print(f"Running bot: {bot_name}")

	# In a real scenario:
	# bot = load_bot_by_name(bot_name)
	# result = bot.run(params={"market": "cac40"})
	#
	# if result["status"] == "success":
	#     output = result["output"]
	#     print(f"✓ Bot executed successfully")
	#     print(f"  Trades: {output.get('trades', 0)}")
	#     print(f"  P&L: ${output.get('pnl', 0):.2f}")
	#     print(f"  Positions: {len(output.get('positions', []))}")
	# else:
	#     error_msg = result.get("message", "Unknown error")
	#     print(f"✗ Bot execution failed: {error_msg}")

	print("\nResponse structure:")
	print("""
	{
		"status": "success" | "error",
		"params": {...},           # Input parameters
		"output": {...},           # Results
		"message": "..."           # Error message (if error)
	}
	""")\


def example_run_intraday_bot():
	"""Example: Run intraday bot with trading logic."""
	print("=== Run Intraday Trading Bot ===\n")

	manager = BotManager()

	# Get active bot
	bots = manager.list_bots(state_filter="active")
	if not bots:
		print("No active bots found.\n")
		return

	bot_name = bots[0]["name"]
	portfolio = manager.load_portfolio(bot_name)

	# Parameters for intraday execution
	params = {
		"portfolio": portfolio,
		"exit_rules": {
			"stop_loss": 0.05,
			"take_profit": 0.10
		},
		"scaling_rules": {
			"scale_in_threshold": 0.7,
			"scale_out_threshold": -0.03
		}
	}

	print(f"Running intraday bot: {bot_name}")
	print(f"Portfolio value: ${portfolio.get('total_value', 0):,.2f}")
	print(f"Open positions: {len(portfolio.get('positions', []))}\n")

	# In a real scenario:
	# from jobs import BotIntraday
	# bot = BotIntraday(bot_name, manager.get_bot_dir(bot_name))
	# result = bot.run(params=params)
	#
	# if result["status"] == "success":
	#     output = result["output"]
	#     print(f"✓ Intraday cycle completed")
	#     print(f"  Trades executed: {output.get('trades_executed', 0)}")
	#     print(f"  Positions exited: {output.get('positions_exited', 0)}")
	#     print(f"  Total P&L: ${output.get('total_pnl', 0):,.2f}")

	print("Would execute:")
	print("  1. Monitor active positions")
	print("  2. Check exit conditions (stop loss / take profit)")
	print("  3. Execute position exits")
	print("  4. Scale in/out based on price action")
	print("  5. Return execution summary\n")


def example_run_with_response_processing():
	"""Example: Process bot run response."""
	print("=== Process Bot Run Response ===\n")

	# Example response structure
	response = {
		"status": "success",
		"params": {
			"market": "cac40",
			"capital": 100000
		},
		"output": {
			"trades_executed": 3,
			"pnl": 1500.00,
			"positions": [
				{
					"ticker": "AC.PA",
					"quantity": 100,
					"entry_price": 50.0,
					"current_price": 51.5,
					"pnl": 150.00
				}
			],
			"execution_time_ms": 234.56
		}
	}

	print("Processing bot run response:")
	print()

	# Check status
	if response["status"] == "success":
		print("✓ Bot execution succeeded\n")

		output = response["output"]

		# Display summary
		print("Summary:")
		print(f"  Trades executed: {output['trades_executed']}")
		print(f"  P&L: ${output['pnl']:,.2f}")
		print(f"  Positions: {len(output['positions'])}")
		print(f"  Execution time: {output['execution_time_ms']:.2f}ms\n")

		# Display positions
		if output["positions"]:
			print("Open Positions:")
			for pos in output["positions"]:
				print(f"  • {pos['ticker']}: {pos['quantity']} @ ${pos['current_price']} ({pos['pnl']:+.2f})")

	else:
		error_msg = response.get("message", "Unknown error")
		print(f"✗ Bot execution failed: {error_msg}\n")

	print()


def example_continuous_bot_execution():
	"""Example: Continuous bot execution (polling)."""
	print("=== Continuous Bot Execution ===\n")

	manager = BotManager()

	bots = manager.list_bots(state_filter="active")
	if not bots:
		print("No active bots found.\n")
		return

	bot_name = bots[0]["name"]

	print(f"Simulating continuous execution of: {bot_name}")
	print("(In production, this would run on a schedule)\n")

	# Simulate multiple execution cycles
	for cycle in range(3):
		print(f"Cycle {cycle + 1}:")
		print(f"  Timestamp: 2026-06-18 10:{30 + cycle * 5}:00")

		# Parameters for this cycle
		params = {
			"market": "cac40",
			"capital": 100000,
			"cycle": cycle + 1
		}

		print(f"  Running with params: {params}")

		# In a real scenario:
		# result = bot.run(params=params)
		# if result["status"] == "success":
		#     output = result["output"]
		#     print(f"  Trades: {output.get('trades_executed', 0)}")
		#     print(f"  P&L: ${output.get('total_pnl', 0):,.2f}")

		print(f"  Status: ✓ Completed\n")

	print("For production, use a scheduler (e.g., APScheduler, Cron)")
	print()


if __name__ == "__main__":
	# Run all examples
	example_simple_run()
	example_run_with_params()
	example_run_multiple_bots()
	example_run_with_error_handling()
	example_run_intraday_bot()
	example_run_with_response_processing()
	example_continuous_bot_execution()

	print("=== All Examples Complete ===")
