"""Intraday job: runs the in_market step for every active bot."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.job import Job, STATUS_SUCCESS, STATUS_ERROR
from tools.bot import BotManager
from utils.env import get_db_root


class JobPreMarket(Job):
	"""Runs BotFinance's in_market step for every currently active bot.

	Scheduled via config/cron.yml during market hours so pending orders and
	exits get checked periodically across all active bots, without needing
	one cron entry per bot.
	"""

	def __init__(self, name: str = "job_intraday", job_dir: Optional[Path] = None, context: Optional[Any] = None):
		"""Initialize the intraday job.

		Args:
			name: Job identifier
			job_dir: Directory to store job data (default: db/jobs/<name>)
			context: Optional AgentContext for shared state
		"""
		if job_dir is None:
			job_dir = get_db_root() / "jobs" / name
		super().__init__(name, job_dir, context)
		self.bot_manager = BotManager()

	def process(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Run the in_market step for every active bot.

		Args:
			params: Unused, present for interface consistency with Job.process()

		Returns:
			Response with status "success" if all active bots ran (even if a
			given bot's in_market step itself failed - failures are recorded
			per-bot in output.results rather than aborting the whole job)
		"""
		if params is None:
			params = {}

		from bot.finance import BotFinance

		active_bots = self.bot_manager.list_bots(state_filter="active")
		self.logger.info(f"JobIntraday: found {len(active_bots)} active bot(s)")

		results: List[Dict[str, Any]] = []
		for bot_config in active_bots:
			bot_name = bot_config.get("name")
			if not bot_name:
				continue

			try:
				bot_dir = self.bot_manager.get_bot_dir(bot_name)
				bot = BotFinance(bot_name, bot_dir)
				bot.activate()
				result = bot.run(params={"step": "pre_market"})

				self.agents_executed.append(bot_name)
				results.append({
					"bot": bot_name,
					"status": result.get("status"),
					"output": result.get("output", {}),
				})

				if result.get("status") != STATUS_SUCCESS:
					self.logger.warning(
						f"JobIntraday: bot '{bot_name}' returned non-success: {result.get('message')}"
					)
			except Exception as e:
				self.logger.error(f"JobIntraday: bot '{bot_name}' failed: {e}")
				results.append({"bot": bot_name, "status": STATUS_ERROR, "message": str(e)})

		succeeded = len([r for r in results if r.get("status") == STATUS_SUCCESS])
		self.logger.info(f"JobIntraday: completed {succeeded}/{len(results)} bot(s) successfully")

		return {
			"status": STATUS_SUCCESS,
			"params": params,
			"output": {
				"bots_processed": len(results),
				"bots_succeeded": succeeded,
				"results": results,
			},
		}
