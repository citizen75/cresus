"""Examples of using the BotManager."""

from pathlib import Path
from tools.bot import BotManager


def example_create_bot():
	"""Example: Creating a bot."""
	print("=== Creating a Bot ===\n")

	manager = BotManager()

	# Create a bot with a strategy file
	# Note: This assumes config/strategies/momentum.yml exists
	try:
		config = manager.create_bot(
			name="momentum_example",
			strategy_path="config/strategies/momentum.yml"
		)

		print(f"✓ Bot created: {config['name']}")
		print(f"  Description: {config.get('description', '-')}")
		print(f"  State: {config['state']}")
		print(f"  Created: {config['created_at']}\n")
	except ValueError as e:
		print(f"Note: {e}\n")


def example_list_bots():
	"""Example: Listing bots."""
	print("=== Listing Bots ===\n")

	manager = BotManager()

	# List all bots
	all_bots = manager.list_bots()
	print(f"Total bots: {len(all_bots)}")

	# List by state
	for bot in all_bots:
		print(f"  {bot['name']}: {bot.get('state', 'unknown')}")

	if not all_bots:
		print("  No bots found")

	# Get summary
	summary = manager.get_bots_summary()
	print(f"\nSummary:")
	print(f"  Active: {summary['active']}")
	print(f"  Inactive: {summary['inactive']}")
	print(f"  Total: {summary['total']}\n")


def example_activate_deactivate():
	"""Example: Activating and deactivating bots."""
	print("=== Activating/Deactivating Bots ===\n")

	manager = BotManager()

	bots = manager.list_bots()
	if not bots:
		print("No bots to activate/deactivate\n")
		return

	bot_name = bots[0]['name']

	# Activate
	print(f"Activating {bot_name}...")
	if manager.activate_bot(bot_name):
		print(f"✓ {bot_name} is now active\n")

	# Check state
	bot = manager.get_bot(bot_name)
	print(f"Current state: {bot['state']}")
	print(f"Activated at: {bot.get('activated_at', '-')}\n")

	# Deactivate
	print(f"Deactivating {bot_name}...")
	if manager.deactivate_bot(bot_name):
		print(f"✓ {bot_name} is now inactive\n")


def example_watchlist_management():
	"""Example: Managing bot watchlist."""
	print("=== Managing Watchlist ===\n")

	manager = BotManager()

	bots = manager.list_bots()
	if not bots:
		print("No bots found\n")
		return

	bot_name = bots[0]['name']

	# Initialize with some tickers
	print(f"Setting watchlist for {bot_name}...")
	tickers = ["AC.PA", "OR.PA", "CS.PA", "GLE.PA"]
	manager.save_watchlist(bot_name, tickers)
	print(f"✓ Watchlist saved: {', '.join(tickers)}\n")

	# Load watchlist
	print("Loading watchlist...")
	loaded = manager.load_watchlist(bot_name)
	print(f"  Tickers: {', '.join(loaded)}\n")

	# Add ticker
	print("Adding ticker to watchlist...")
	if manager.add_to_watchlist(bot_name, "SAF.PA"):
		print(f"✓ Added SAF.PA\n")

	# Remove ticker
	print("Removing ticker from watchlist...")
	if manager.remove_from_watchlist(bot_name, "OR.PA"):
		print(f"✓ Removed OR.PA\n")

	# Show final watchlist
	final = manager.load_watchlist(bot_name)
	print(f"Final watchlist: {', '.join(final)}\n")


def example_portfolio_management():
	"""Example: Managing bot portfolio."""
	print("=== Managing Portfolio ===\n")

	manager = BotManager()

	bots = manager.list_bots()
	if not bots:
		print("No bots found\n")
		return

	bot_name = bots[0]['name']

	# Load portfolio
	print(f"Loading portfolio for {bot_name}...")
	portfolio = manager.load_portfolio(bot_name)

	if portfolio:
		print(f"  Initial Capital: ${portfolio.get('initial_capital', 0):,.2f}")
		print(f"  Cash: ${portfolio.get('cash', 0):,.2f}")
		print(f"  Total Value: ${portfolio.get('total_value', 0):,.2f}")
		print(f"  P&L: ${portfolio.get('pnl', 0):,.2f} ({portfolio.get('pnl_pct', 0):.2%})")
		print(f"  Positions: {len(portfolio.get('positions', []))}\n")

		# Simulate trading
		print("Simulating trade execution...")
		portfolio['cash'] -= 5000
		portfolio['total_value'] = portfolio['initial_capital'] + 5000
		portfolio['pnl'] = 5000
		portfolio['pnl_pct'] = 0.05

		position = {
			"ticker": "AC.PA",
			"quantity": 100,
			"entry_price": 50.0,
			"current_price": 50.0,
			"pnl": 0,
			"pnl_pct": 0.0
		}
		portfolio['positions'].append(position)

		# Save portfolio
		manager.save_portfolio(bot_name, portfolio)
		print(f"✓ Portfolio saved\n")

		# Reload and verify
		updated = manager.load_portfolio(bot_name)
		print(f"Updated portfolio:")
		print(f"  Cash: ${updated.get('cash', 0):,.2f}")
		print(f"  Positions: {len(updated.get('positions', []))}\n")


def example_get_bot_info():
	"""Example: Getting comprehensive bot info."""
	print("=== Getting Bot Information ===\n")

	manager = BotManager()

	bots = manager.list_bots()
	if not bots:
		print("No bots found\n")
		return

	bot_name = bots[0]['name']

	print(f"Getting info for {bot_name}...\n")
	info = manager.get_bot_info(bot_name)

	if info:
		config = info['config']
		portfolio = info['portfolio']
		watchlist = info['watchlist']
		bot_dir = info['bot_dir']

		print(f"Bot Configuration:")
		print(f"  Name: {config.get('name', '-')}")
		print(f"  Description: {config.get('description', '-')}")
		print(f"  State: {config.get('state', '-')}")
		print(f"  Strategy: {config.get('strategy', '-')}\n")

		print(f"Portfolio:")
		print(f"  Capital: ${portfolio.get('initial_capital', 0):,.2f}")
		print(f"  Total Value: ${portfolio.get('total_value', 0):,.2f}\n")

		print(f"Watchlist:")
		print(f"  Tickers: {', '.join(watchlist) if watchlist else 'Empty'}\n")

		print(f"Paths:")
		print(f"  Bot Directory: {bot_dir}")
		print(f"  Strategy File: {info['strategy_file']}\n")


def example_manage_configuration():
	"""Example: Managing bot configuration."""
	print("=== Managing Configuration ===\n")

	manager = BotManager()

	bots = manager.list_bots()
	if not bots:
		print("No bots found\n")
		return

	bot_name = bots[0]['name']

	# Load config
	print(f"Loading configuration for {bot_name}...")
	config = manager.load_config(bot_name)

	if config:
		print(f"  Current description: {config.get('description', '-')}\n")

		# Modify config
		config['description'] = "Updated bot description"
		config['updated_at'] = "2026-06-18T15:30:00"

		# Save config
		manager.save_config(bot_name, config)
		print(f"✓ Configuration updated\n")

		# Reload to verify
		updated = manager.load_config(bot_name)
		print(f"  New description: {updated.get('description', '-')}\n")


def example_list_by_state():
	"""Example: Listing bots filtered by state."""
	print("=== Listing Bots by State ===\n")

	manager = BotManager()

	# Active bots
	print("Active Bots:")
	active = manager.list_bots(state_filter="active")
	if active:
		for bot in active:
			print(f"  {bot['name']}")
	else:
		print("  None")

	print()

	# Inactive bots
	print("Inactive Bots:")
	inactive = manager.list_bots(state_filter="inactive")
	if inactive:
		for bot in inactive:
			print(f"  {bot['name']}")
	else:
		print("  None")

	print()


def example_bot_orchestration():
	"""Example: Complex bot orchestration."""
	print("=== Bot Orchestration ===\n")

	manager = BotManager()

	# Get all bots
	all_bots = manager.list_bots()
	print(f"Found {len(all_bots)} bots\n")

	# Analyze performance
	print("Bot Performance Analysis:")
	for bot in all_bots:
		portfolio = manager.load_portfolio(bot['name'])
		pnl_pct = portfolio.get('pnl_pct', 0)
		status = "✓" if pnl_pct > 0 else "✗"
		print(f"  {status} {bot['name']}: {pnl_pct:.2%} P&L")

	print()

	# Activate top performers
	print("Activating top performers...")
	sorted_bots = sorted(
		all_bots,
		key=lambda b: manager.load_portfolio(b['name']).get('pnl_pct', 0),
		reverse=True
	)

	top_3 = sorted_bots[:3]
	for bot in top_3:
		if bot.get('state') != 'active':
			manager.activate_bot(bot['name'])
			print(f"  ✓ Activated {bot['name']}")

	print()


if __name__ == "__main__":
	# Run all examples
	example_list_bots()
	example_create_bot()
	example_activate_deactivate()
	example_watchlist_management()
	example_portfolio_management()
	example_manage_configuration()
	example_get_bot_info()
	example_list_by_state()
	example_bot_orchestration()

	print("\n=== All Examples Complete ===")
