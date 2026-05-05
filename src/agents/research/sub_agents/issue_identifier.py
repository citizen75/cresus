"""Issue identifier sub-agent for finding problems in backtest results."""

from typing import Any, Dict, Optional, List
from core.agent import Agent


class IssueIdentifierAgent(Agent):
	"""Identify issues and anomalies in backtest results.

	Looks for:
	- Zero or abnormal metrics
	- Position sizing anomalies
	- Trade execution issues
	- Data inconsistencies
	"""

	def __init__(self, name: str = "IssueIdentifierAgent"):
		"""Initialize issue identifier agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Identify issues in backtest results.

		Args:
			input_data: Input data with journal_analysis and order_analysis

		Returns:
			Response with identified issues and severity
		"""
		if input_data is None:
			input_data = {}

		journal_analysis = input_data.get("journal_analysis", {})
		order_analysis = input_data.get("order_analysis", {})

		# Identify issues
		issues = []
		severity_scores = []

		# Check journal issues
		journal_issues, j_severity = self._check_journal_issues(journal_analysis)
		issues.extend(journal_issues)
		severity_scores.extend(j_severity)

		# Check order issues
		order_issues, o_severity = self._check_order_issues(order_analysis)
		issues.extend(order_issues)
		severity_scores.extend(o_severity)

		# Determine overall severity
		overall_severity = self._get_severity_level(severity_scores)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"identified_issues": issues,
				"total_issues": len(issues),
				"severity_level": overall_severity,
				"by_category": self._categorize_issues(issues),
			},
			"message": f"Identified {len(issues)} issues (severity: {overall_severity})"
		}

	def _check_journal_issues(self, journal_analysis: Dict[str, Any]) -> tuple[List[Dict], List[str]]:
		"""Check journal for issues.

		Args:
			journal_analysis: Journal analysis from JournalAnalyzerAgent

		Returns:
			Tuple of (issues list, severity list)
		"""
		issues = []
		severities = []

		total_trades = journal_analysis.get("total_trades", 0)

		# No trades issue
		if total_trades == 0:
			issues.append({
				"category": "journal",
				"type": "no_trades",
				"message": "No trades executed",
				"severity": "high",
				"details": "Backtest produced zero trades. Check strategy signals and entry conditions.",
			})
			severities.append("high")

		# Anomaly detection
		anomalies = journal_analysis.get("anomalies", {})
		if anomalies.get("zero_price_trades", 0) > 0:
			issues.append({
				"category": "journal",
				"type": "zero_price_trades",
				"message": f"{anomalies['zero_price_trades']} trades with zero price",
				"severity": "critical",
				"details": "Trades recorded with $0 price. Indicates data or entry issue.",
			})
			severities.append("critical")

		if anomalies.get("zero_quantity_trades", 0) > 0:
			issues.append({
				"category": "journal",
				"type": "zero_quantity_trades",
				"message": f"{anomalies['zero_quantity_trades']} trades with zero quantity",
				"severity": "critical",
				"details": "Trades recorded with 0 quantity. Check position sizing logic.",
			})
			severities.append("critical")

		# Imbalanced buy/sell issue
		buy_trades = journal_analysis.get("buy_trades", 0)
		sell_trades = journal_analysis.get("sell_trades", 0)
		
		if total_trades > 5 and buy_trades > 0 and sell_trades == 0:
			issues.append({
				"category": "journal",
				"type": "no_sells",
				"message": f"All trades are buys ({buy_trades} buy, 0 sell)",
				"severity": "medium",
				"details": "No exit trades found. Strategy may not have exit conditions implemented.",
			})
			severities.append("medium")

		return issues, severities

	def _check_order_issues(self, order_analysis: Dict[str, Any]) -> tuple[List[Dict], List[str]]:
		"""Check orders for issues.

		Args:
			order_analysis: Order analysis from OrderAnalyzerAgent

		Returns:
			Tuple of (issues list, severity list)
		"""
		issues = []
		severities = []

		total_orders = order_analysis.get("total_orders", 0)

		# No orders issue
		if total_orders == 0:
			issues.append({
				"category": "orders",
				"type": "no_orders",
				"message": "No orders executed",
				"severity": "high",
				"details": "Backtest produced zero orders. Check if strategy is working.",
			})
			severities.append("high")

		# Anomaly detection
		anomalies = order_analysis.get("anomalies", {})
		if anomalies.get("zero_price_orders", 0) > 0:
			issues.append({
				"category": "orders",
				"type": "zero_price_orders",
				"message": f"{anomalies['zero_price_orders']} orders with zero price",
				"severity": "critical",
				"details": "Orders executed at $0 price. Data fetch or price calculation error.",
			})
			severities.append("critical")

		if anomalies.get("zero_quantity_orders", 0) > 0:
			issues.append({
				"category": "orders",
				"type": "zero_quantity_orders",
				"message": f"{anomalies['zero_quantity_orders']} orders with zero quantity",
				"severity": "critical",
				"details": "Orders placed for 0 quantity. Position sizing misconfiguration.",
			})
			severities.append("critical")

		# Order size consistency
		avg_order_size = order_analysis.get("avg_order_size", 0)
		if avg_order_size < 1 and total_orders > 0:
			issues.append({
				"category": "orders",
				"type": "small_orders",
				"message": f"Average order size is {avg_order_size:.2f} quantity",
				"severity": "low",
				"details": "Orders are very small. Check position sizing formula.",
			})
			severities.append("low")

		return issues, severities

	def _get_severity_level(self, severities: List[str]) -> str:
		"""Determine overall severity from list.

		Args:
			severities: List of severity levels

		Returns:
			Overall severity level
		"""
		if not severities:
			return "none"
		if "critical" in severities:
			return "critical"
		if "high" in severities:
			return "high"
		if "medium" in severities:
			return "medium"
		return "low"

	def _categorize_issues(self, issues: List[Dict]) -> Dict[str, List[Dict]]:
		"""Categorize issues by type.

		Args:
			issues: List of issues

		Returns:
			Dict of issues grouped by category
		"""
		categorized = {}
		for issue in issues:
			category = issue.get("category", "unknown")
			if category not in categorized:
				categorized[category] = []
			categorized[category].append(issue)
		return categorized
