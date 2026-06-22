"""Strategy version snapshotting.

Every strategy file carries a `version: N` field. Each versioned save:
1. Archives the current live file verbatim to
   `~/.cresus/db/strategies/_versions/<name>/v<N>.yml`.
2. Bumps `version` and writes the new config as the live file, optionally
   annotating changed YAML paths with an inline `# v{N}: <reason>` comment
   (round-tripped via ruamel.yaml so the rest of the file's formatting is
   preserved).
3. Optionally writes an audit report alongside the archived snapshot.

This module is deliberately separate from `StrategyManager.save_strategy()`,
which is also called by automated, high-frequency internal saves (e.g.
`agents/watchlist/sub_agents/volatility_agent.py` auto-declaring a missing
indicator) where bumping a version on every cycle would be noise, not
history. Call `save_strategy_version()` explicitly from user-facing save
paths (create/edit/duplicate/tune) instead.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from tools.strategy.strategy import StrategyManager


def _yaml() -> YAML:
	y = YAML()
	y.preserve_quotes = True
	y.indent(mapping=2, sequence=2, offset=0)
	y.width = 4096
	return y


def get_versions_dir(strategy_name: str, manager: Optional[StrategyManager] = None) -> Path:
	"""Return (creating if needed) the snapshot history dir for a strategy."""
	manager = manager or StrategyManager()
	versions_dir = manager.strategies_dir / "_versions" / strategy_name
	versions_dir.mkdir(parents=True, exist_ok=True)
	return versions_dir


def _read_current_version(strategy_file: Path) -> int:
	if not strategy_file.exists():
		return 0
	try:
		with open(strategy_file) as f:
			data = _yaml().load(f) or {}
		return int(data.get("version") or 0)
	except Exception:
		return 0


def archive_current(strategy_name: str, manager: Optional[StrategyManager] = None) -> Optional[int]:
	"""Copy the current live strategy file into `_versions/<name>/v<N>.yml`.

	Args:
		strategy_name: Strategy name (file stem under the strategies dir).
		manager: Optional pre-built StrategyManager (mainly for tests).

	Returns:
		The archived version number, or None if there was no prior live file.
	"""
	manager = manager or StrategyManager()
	strategy_file = manager._get_strategy_file(strategy_name)
	if not strategy_file.exists():
		return None

	current_version = _read_current_version(strategy_file) or 1
	versions_dir = get_versions_dir(strategy_name, manager)
	archive_path = versions_dir / f"v{current_version}.yml"
	if not archive_path.exists():
		archive_path.write_text(strategy_file.read_text())
	return current_version


def _to_commented(data: Any) -> Any:
	"""Recursively convert plain dict/list into ruamel's CommentedMap/CommentedSeq
	so individual keys can carry an inline comment."""
	if isinstance(data, dict):
		cm = CommentedMap()
		for k, v in data.items():
			cm[k] = _to_commented(v)
		return cm
	if isinstance(data, list):
		cs = CommentedSeq()
		for v in data:
			cs.append(_to_commented(v))
		return cs
	return data


def _annotate_path(node: Any, path: str, comment: str) -> None:
	"""Attach an end-of-line comment to the YAML node at dotted `path`.

	Walks to the parent of the final key and asks ruamel to comment that key.
	No-ops silently if the path doesn't resolve (e.g. it names a key that
	wasn't actually present in the written config).
	"""
	parts = path.split(".")
	cursor = node
	for part in parts[:-1]:
		if isinstance(cursor, dict) and part in cursor:
			cursor = cursor[part]
		else:
			return
	leaf = parts[-1]
	if isinstance(cursor, CommentedMap) and leaf in cursor:
		try:
			cursor.yaml_add_eol_comment(comment, leaf)
		except Exception:
			pass


def save_strategy_version(
	strategy_name: str,
	new_config: Dict[str, Any],
	changelog: Optional[List[Dict[str, str]]] = None,
	report: Optional[Dict[str, Any]] = None,
	manager: Optional[StrategyManager] = None,
) -> int:
	"""Archive the current live file, bump version, write `new_config` as the
	new live file with inline change comments, and optionally persist an
	audit report next to the archived snapshot.

	Args:
		strategy_name: Strategy name (file stem under the strategies dir).
		new_config: Full strategy config dict to write as the new live file.
		changelog: Optional list of `{"path": "entry.parameters.X.formula",
			"reason": "..."}` dicts. Each path's leaf gets an end-of-line
			`# v{N}: <reason>` comment in the written YAML.
		report: Optional dict (e.g. a tuning iteration_summary) written to
			`_versions/<name>/v{N}_report.yml` for audit history.
		manager: Optional pre-built StrategyManager (mainly for tests).

	Returns:
		The new version number, also set on `new_config["version"]`.
	"""
	manager = manager or StrategyManager()
	strategy_file = manager._get_strategy_file(strategy_name)

	archived_version = archive_current(strategy_name, manager)
	new_version = (archived_version or 0) + 1

	new_config = dict(new_config)
	new_config["version"] = new_version
	new_config["name"] = new_config.get("name", strategy_name)

	commented = _to_commented(new_config)
	for entry in changelog or []:
		_annotate_path(commented, entry["path"], f"v{new_version}: {entry['reason']}")

	yaml = _yaml()
	manager._ensure_strategies_dir()
	with open(strategy_file, "w") as f:
		yaml.dump(commented, f)

	if report is not None:
		versions_dir = get_versions_dir(strategy_name, manager)
		report_path = versions_dir / f"v{new_version}_report.yml"
		with open(report_path, "w") as f:
			yaml.dump(_to_commented(report), f)

	return new_version
